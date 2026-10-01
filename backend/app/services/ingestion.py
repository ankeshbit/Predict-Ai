"""
Data Ingestion Service
Handles asynchronous ingestion of staged datasets into the Neon relational database.
Creates Machine entities and inserts SensorReadings in bulk with DB-backed progress tracking.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.cmapss_fd001 import CmapssFd001Adapter
from app.core.db import SessionLocal
from app.models.entities import Dataset, Job, Machine, SensorReading
from app.services.upload import get_staged_file_path

logger = logging.getLogger(__name__)


def run_ingestion_job(
    job_id: uuid.UUID,
    dataset_id: uuid.UUID,
    _db: Optional[Session] = None,
):
    """
    Background worker task for data ingestion.
    Executes in a background thread/task using its own isolated database session,
    OR uses the provided _db session (for synchronous test execution).
    """
    own_session = _db is None
    db: Session = _db if _db is not None else SessionLocal()
    job = None
    dataset = None
    try:
        job = db.get(Job, job_id)
        dataset = db.get(Dataset, dataset_id)

        if not job or not dataset:
            logger.error(f"Ingestion job {job_id} or dataset {dataset_id} not found.")
            return

        # Mark job as running
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.progress_pct = 5.0
        dataset.status = "ingesting"
        db.commit()

        # 1. Resolve staged file
        staged_path = get_staged_file_path(dataset.staging_filename)
        logger.info(f"Ingesting dataset {dataset.name} from {staged_path}")
        job.progress_pct = 15.0
        db.commit()

        # 2. Read CSV
        # Support whitespace or comma delimited
        try:
            df_raw = pd.read_csv(staged_path)
            if df_raw.shape[1] == 1:
                df_raw = pd.read_csv(staged_path, sep=r"\s+", header=None)
        except Exception:
            df_raw = pd.read_csv(staged_path, sep=r"\s+", header=None)

        job.progress_pct = 30.0
        db.commit()

        # 3. Transform via adapter
        adapter = CmapssFd001Adapter()
        df = adapter.transform(df_raw, dataset.schema_mapping)
        job.progress_pct = 45.0
        db.commit()

        # 4. Create or fetch Machine records
        unit_ids = sorted(df["unit_id"].unique().tolist())
        machine_map: Dict[int, uuid.UUID] = {}

        for unit_id in unit_ids:
            machine_code = f"{dataset.slug}-u{int(unit_id):03d}"
            existing = db.scalar(select(Machine).where(Machine.machine_code == machine_code))
            if existing:
                machine_map[unit_id] = existing.id
            else:
                new_machine = Machine(
                    id=uuid.uuid4(),
                    dataset_id=dataset.id,
                    machine_code=machine_code,
                    operational_status="active",
                    health_indicator=100.0,
                    health_band="excellent",
                    is_demo=False,
                )
                db.add(new_machine)
                db.flush()
                machine_map[unit_id] = new_machine.id

        job.progress_pct = 60.0
        db.commit()

        # 5. Insert SensorReadings in chunks (clearing any existing readings for idempotent re-ingestion)
        db.query(SensorReading).filter(SensorReading.dataset_id == dataset.id).delete()
        db.commit()

        sensor_cols = [c for c in adapter.canonical_columns if c not in ["unit_id", "cycle"]]
        total_rows = len(df)
        chunk_size = 5000
        records_to_insert = []

        now_utc = datetime.now(timezone.utc)
        for i, row in df.iterrows():
            m_id = machine_map[int(row["unit_id"])]
            reading_dict = {
                "machine_id": m_id,
                "dataset_id": dataset.id,
                "cycle_index": int(row["cycle"]),
                "recorded_at": now_utc,
            }
            for col in sensor_cols:
                reading_dict[col] = float(row[col]) if col in row and not pd.isna(row[col]) else None

            records_to_insert.append(SensorReading(**reading_dict))

            if len(records_to_insert) >= chunk_size:
                db.bulk_save_objects(records_to_insert)
                db.commit()
                records_to_insert.clear()
                pct = 60.0 + (i / total_rows) * 35.0
                job.progress_pct = round(pct, 1)
                db.commit()

        if records_to_insert:
            db.bulk_save_objects(records_to_insert)
            db.commit()
            records_to_insert.clear()

        # 6. Finalize dataset and job
        dataset.status = "ingested"
        dataset.row_count = total_rows
        dataset.unit_count = len(unit_ids)
        dataset.updated_at = datetime.now(timezone.utc)

        job.status = "completed"
        job.progress_pct = 100.0
        job.completed_at = datetime.now(timezone.utc)
        job.result = {
            "dataset_id": str(dataset.id),
            "rows_ingested": total_rows,
            "units_ingested": len(unit_ids),
        }
        db.commit()
        logger.info(f"Ingestion job {job_id} successfully completed: {total_rows} rows for {len(unit_ids)} units.")

    except Exception as e:
        logger.exception(f"Ingestion job {job_id} failed: {e}")
        db.rollback()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
        if dataset:
            dataset.status = "failed"
            dataset.error_message = str(e)
        db.commit()
    finally:
        if own_session:
            db.close()
