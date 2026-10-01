# ADR-06: Database Schema Alignment and Architectural Deviations from PRD §13

## Status
Accepted / Conformed (Phase 2 & Phase 3)

## Context
During the Phase 2 & 3 verification against PRD v3.0 §13, a rigorous table-by-table audit was performed comparing the SQLAlchemy 2.0 ORM entities (`backend/app/models/entities.py`) and Alembic migration `001_initial_schema.py` against the PRD §13 specifications.

The audit identified specific deviations and nuances in table definitions, field naming, and check constraints across the 16 core relational tables.

---

## Decision & Table-by-Table Alignment

### 1. `users`
- **Specification**: `id` (UUID PK), `email` (VARCHAR(255) UNIQUE), `password_hash` (VARCHAR(255)), `role` (VARCHAR(32), CHECK `'admin' | 'engineer'`), `is_active` (BOOLEAN), `created_at`, `updated_at`.
- **Status**: **100% Conformed**. Verified with `test_user_role_check_constraint`.

### 2. `datasets`
- **Specification**: Requires dataset versioning, schema mapping tracking, and lifecycle status checks.
- **Deviations Identified**:
  - `version` column was missing in early draft;
  - `status` had no DB-level CHECK constraint;
  - Storage metadata used `staging_filename` vs `raw_file_path`.
- **Resolution**: **Conformed**. Added `version` (default `'1.0'`), `schema_mapping_hash` (SHA-256), `staging_filename` (UUID-based secure staging path), and `check_dataset_status` enforcing `('uploaded', 'valid', 'invalid', 'compatible', 'rejected_incompatible', 'ingesting', 'ingested', 'failed')`.

### 3. `dataset_compatibility_checks`
- **Specification**: PRD §13 initially proposed 1 row per dataset check run with a single JSONB report blob.
- **Architectural Deviation**:
  - We adopted a normalized schema: **1 row per individual verification check** (11 rows per dataset evaluation: `check_number`, `check_name`, `status`, `expected_value`, `found_value`, `how_to_fix`, `details`, `checked_at`).
- **Rationale**:
  - Normalized rows enable relational querying, aggregation, and indexing by check failure type (e.g. `SELECT check_name, count(*) FROM dataset_compatibility_checks WHERE status = 'failed' GROUP BY check_name`).
  - The API continues to return the complete hierarchical `CompatibilityReport` matching PRD FR-6 with the Expected/Found/How-to-fix matrix.

### 4. `machines`
- **Specification**: `id`, `dataset_id` (FK), `machine_code` (UNIQUE), `operational_status` (CHECK), `health_indicator`, `health_band`, `is_demo`, `demo_cluster`, timestamps.
- **Resolution**: **Conformed**. Added `'warning'` and `'critical'` into `check_machine_status` constraint alongside `'active', 'maintenance', 'degraded', 'offline'`.

### 5. `sensor_readings`
- **Specification**: High-volume telemetry table. Required `UNIQUE(machine_id, dataset_id, cycle_index)`.
- **Deviations Identified**:
  - Earlier entity used column name `cycle` and lacked `dataset_id` foreign key.
- **Resolution**: **Conformed**. Added `dataset_id` (UUID FK to `datasets.id`) and renamed database column to `cycle_index`.
  - Added PostgreSQL unique index `uq_machine_dataset_cycle` on `(machine_id, dataset_id, cycle_index)` and unique index `uq_machine_cycle` on `(machine_id, cycle_index)`.
  - Implemented `@hybrid_property cycle` on `SensorReading` so existing queries (`SensorReading.cycle >= from_cycle`) and API models continue to work transparently without breaking changes.

### 6. `model_versions`
- **Specification**: Model governance table storing bundle metadata, task type, hashes, and activation flags.
- **Constraints Enforced**:
  - `CHECK task IN ('failure_risk', 'anomaly')`
  - `CHECK NOT (is_active = TRUE AND model_card_complete = FALSE)` (`check_model_card_complete_if_active`)
  - Partial Unique Index: `uq_active_model_per_task` on `(adapter_key, task) WHERE is_active = TRUE` (enforcing exactly one active model per task).
- **Status**: **100% Conformed**. Verified by PostgreSQL integration tests.

### 7. `model_evaluations`
- **Specification**: Offline Colab evaluation results (`metrics`, `confusion_matrix`, `calibration_curve`, `curves`, `feature_importance`, `methodology`, `limitations`).
- **Status**: **100% Conformed**. Zero fabricated literals permitted; strictly loaded from evaluated bundles.

### 8. `health_indicator_configs`
- **Specification**: Deterministic composite formula weights ($W_{risk} + W_{anom} + W_{trend} = 100$).
- **Constraints Enforced**:
  - `CHECK (weight_risk + weight_anomaly + weight_trend) = 100.0` (`check_health_weights_sum_100`)
  - Partial Unique Index: only 1 active config (`WHERE is_active = TRUE`).
- **Status**: **100% Conformed**. Verified by unit tests.

### 9. `predictions`
- **Specification**: Scored inference outcomes with complete lineage (*"How was this prediction generated?"*).
- **Status**: **100% Conformed**. Includes all 11 lineage fields (`dataset_version`, `schema_mapping_hash`, `feature_config_version`, `preprocessing_version`, `failure_model_version_id`, `anomaly_model_version_id`, `health_config_id`, `horizon`, `horizon_unit`, `as_of_index`, `predicted_at`).

### 10. `anomalies`
- **Specification**: Rolling unsupervised anomaly scores, severity classification, and episode IDs.
- **Status**: **100% Conformed**.

### 11. `alerts`
- **Specification**: Triggered failure risk and anomaly alerts.
- **Constraints Enforced**:
  - `CHECK status IN ('open', 'acknowledged', 'resolved')`
  - `CHECK severity IN ('warning', 'critical')`
  - Partial Unique Index: `uq_open_alert_per_type` on `(machine_id, alert_type) WHERE status IN ('open', 'acknowledged')` (preventing alert flooding).
- **Status**: **100% Conformed**. Verified by PostgreSQL integration tests.

### 12. `maintenance_records`
- **Specification**: Engineer work orders and verified physical outcomes.
- **Constraints Enforced**:
  - `CHECK action_status IN ('in_progress', 'completed')`
  - `CHECK outcome IS NULL OR outcome IN ('resolved', 'no_issue_found', 'unresolved')`
- **Status**: **100% Conformed**.

### 13. `alert_rules`
- **Specification**: Configurable threshold rules and consecutive cycle noise filters.
- **Status**: **100% Conformed**.

### 14. `settings`
- **Specification**: Key-value JSONB settings store.
- **Status**: **100% Conformed**.

### 15. `jobs`
- **Specification**: Database-backed asynchronous queue for long-running operations (upload, ingest, batch scoring).
- **Resolution**: **Conformed**. Aligned schema across `Job` entity, `001_initial_schema.py`, and API serializers: `id`, `job_type`, `status` (`CHECK IN ('queued', 'running', 'completed', 'failed')`), `progress_pct` (Float), `input_params` (JSONB), `result` (JSONB), `error_message` (TEXT), `created_by_user_id`, timestamps.

### 16. `audit_log`
- **Specification**: Immutable compliance event trail.
- **Status**: **100% Conformed**.

---

## Consequences
All 16 tables now match PRD §13 constraints. The full backend test suite (49 tests) and ML test suite (18 tests) execute directly against real PostgreSQL 16 with zero SQLite usage.
