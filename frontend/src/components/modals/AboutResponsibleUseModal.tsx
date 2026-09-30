import React from 'react';
import { Modal } from '../ui/Modal';
import { AlertTriangle, ShieldCheck, Check } from 'lucide-react';
import { Button } from '../ui/Button';

interface AboutResponsibleUseModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AboutResponsibleUseModal: React.FC<AboutResponsibleUseModalProps> = ({
  isOpen,
  onClose,
}) => {
  const limitations = [
    'The MVP is a demonstration on public datasets and has not been validated on real industrial machines.',
    'C-MAPSS FD001 is simulated turbofan engine degradation data, not motor, pump, or compressor telemetry. AI4I 2020 is synthetic tabular data. Neither represents real plant conditions.',
    'C-MAPSS sensors are shown with their original identifiers (sensor_1 ... sensor_21); no physical meaning is asserted for them in the MVP.',
    'Predictions are statistical estimates, not guaranteed failure events. Low probability does not guarantee safety; high probability does not confirm a fault.',
    'The system is not a certified industrial safety system and must not be the sole basis for safety-critical decisions.',
    'The system does not physically diagnose or repair equipment. Recommendations are decision support; humans decide and act.',
    'The Machine Health Indicator is a derived product indicator, not a standardized or scientifically validated industrial health measurement.',
    'Prediction Reliability indicators compare inputs to training data; they do not measure whether a prediction is correct.',
    'Real deployment would require representative domain data, new model development, and re-validation. Performance may change across machines and operating conditions.',
    'All demo content is explicitly labelled "Demo / Simulated Data".',
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Limitations and Responsible Use Policy"
      description="PRD §6 mandatory disclosures regarding predictive maintenance data, ML capabilities, and human authority."
      maxWidth="2xl"
      footer={
        <Button variant="primary" size="sm" onClick={onClose} icon={<Check className="w-4 h-4" />}>
          Acknowledge Guidelines
        </Button>
      }
    >
      <div className="space-y-4 text-xs text-slate-300">
        <div className="flex items-start gap-3 p-3 rounded-md bg-[#181415] border border-amber-900/40 text-amber-200">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <h4 className="font-semibold text-slate-100 text-xs font-mono uppercase">Operational Guidance</h4>
            <p className="text-[11px] leading-relaxed text-slate-300">
              This analytics platform provides statistical forecasting and algorithmic triage. It does NOT supersede maintenance engineers, plant operators, or original equipment manufacturer (OEM) manuals.
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <h4 className="font-semibold text-slate-200 flex items-center gap-2 text-xs font-mono uppercase tracking-wider">
            <ShieldCheck className="w-4 h-4 text-blue-400" />
            10 Mandatory Product Limitations (PRD Section 6)
          </h4>
          <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
            {limitations.map((text, idx) => (
              <div key={idx} className="flex items-start gap-2 p-2 rounded-md bg-[#131924] border border-[#222b3b]">
                <span className="font-mono text-blue-400 font-semibold text-[11px] shrink-0 w-5">{idx + 1}.</span>
                <span className="leading-relaxed text-slate-300 text-[11px]">{text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
};
