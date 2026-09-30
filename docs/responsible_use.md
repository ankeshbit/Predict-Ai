# Limitations and Responsible Use Policy

*(Verbatim from PRD §6 — Mandatory Disclosures for Predict-Ai / PrediCore)*

1. **Demonstration Nature**: The MVP is an analytics demonstration on public simulated benchmarks and has not been certified or validated on physical industrial machines in active service.
2. **Turbofan Simulation**: NASA C-MAPSS FD001 represents simulated turbofan aero-engine degradation, not pump, compressor, gearbox, or motor telemetry. AI4I 2020 is synthetic tabular data. Neither represents real plant operational conditions.
3. **Abstract Sensor Identifiers**: All sensors are displayed exclusively by their original identifiers (`sensor_1` \dots `sensor_21`). No physical meaning (temperature, pressure, vibration) is asserted for them in the platform.
4. **Statistical Estimates Only**: Predictions represent statistical failure probabilities over a finite prediction horizon $H$; they are not deterministic guarantees of equipment failure. Low probability does not guarantee safety; elevated probability does not confirm a physical fault.
5. **Not a Certified Safety System**: The system is not a certified industrial safety instrumented system (SIS) and must never be the sole basis for safety-critical shutoff or operational decisions.
6. **No Autonomous Intervention**: The system does not physically diagnose, control, or repair equipment. Recommendations provide decision support only; human engineers retain sole authority to authorize and perform physical maintenance.
7. **Derived Health Indicator**: The Machine Health Indicator is a derived operational index (0–100), not an ISO-standardized physical health measurement.
8. **Prediction Reliability Scope**: Reliability indicators evaluate whether current operational telemetry falls within the statistical manifold of training data; they do not certify whether a particular prediction is true.
9. **Domain Retraining Requirement**: Deployment to real-world industrial equipment requires domain-specific data collection, bespoke feature engineering, and offline re-validation.
10. **Clear Demo Labeling**: All demonstration content is explicitly labelled `"Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data"` with a `"Demo / Simulated Data"` badge.
