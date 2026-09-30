# Dataset Catalog & Telemetry Specifications

## 1. Primary Benchmark: NASA C-MAPSS FD001

- **Origin**: NASA Ames Prognostics Center of Excellence.
- **Description**: Simulated run-to-failure degradation of commercial modular aero-propulsion system engines under single operational conditions (Sea Level).
- **Files**:
  - `train_FD001.txt`: 100 engines run until complete failure.
  - `test_FD001.txt`: 100 engines stopped at an arbitrary cycle prior to failure.
  - `RUL_FD001.txt`: Ground truth remaining useful life for the 100 test engines at their final recorded cycle.
- **Format**: 26 whitespace-delimited numerical columns without headers:
  1. `unit_id`: Engine identifier (integer $1 \dots 100$)
  2. `cycle`: Operating time in cycles (integer $1 \dots N$)
  3. `op_setting_1`: Altitude / throttle setting 1
  4. `op_setting_2`: Mach number / throttle setting 2
  5. `op_setting_3`: Throttle resolver angle
  6. `sensor_1` through `sensor_21`: 21 raw sensor telemetry measurements.

### Constant Sensor Channels in FD001:
In standard FD001 operating conditions, the following channels exhibit near-zero variance across all units:
`sensor_1`, `sensor_5`, `sensor_6`, `sensor_10`, `sensor_16`, `sensor_18`, `sensor_19`, and `op_setting_3`.
These are dropped deterministically by the feature engineering pipeline based on empirical training variance rules.

---

## 2. Incompatible Test Case: AI4I 2020 Predictive Maintenance Dataset

- **Origin**: UCI Machine Learning Repository / Stephan Matzka.
- **Description**: Synthetic tabular dataset with 10,000 rows representing milling machine failures.
- **Columns**: `UDI`, `Product ID`, `Type`, `Air temperature [K]`, `Process temperature [K]`, `Rotational speed [rpm]`, `Torque [Nm]`, `Tool wear [min]`, `Machine failure`, `TWF`, `HDF`, `PWF`, `OSF`, `RNF`.
- **Role in Predict-Ai**: Used exclusively as the negative validation benchmark to test the FR-6 Dataset Compatibility Gate. It must fail schema validation and be rejected with an actionable Expected / Found / How-to-Fix report.
