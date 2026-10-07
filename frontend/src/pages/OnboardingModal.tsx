import React from 'react';
import { Modal } from '../components/ui/Modal';
import { Button } from '../components/ui/Button';
import { Play, ArrowRight, ShieldCheck, CheckCircle2, AlertTriangle, AlertCircle } from 'lucide-react';

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStartDemoJourney: () => void;
}

export const OnboardingModal: React.FC<OnboardingModalProps> = ({
  isOpen,
  onClose,
  onStartDemoJourney,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Welcome to the Predictive Maintenance System"
      description="PRD §7.1 Acceptance Tour — explore pre-scored simulated turbofan engines with real model evaluations."
      maxWidth="2xl"
      footer={
        <div className="flex items-center justify-between w-full">
          <button
            onClick={onClose}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            Dismiss & explore freely
          </button>
          <Button
            variant="primary"
            size="sm"
            onClick={onStartDemoJourney}
            icon={<Play className="w-4 h-4 fill-current" />}
          >
            Explore Critical Unit #3 Workflow
          </Button>
        </div>
      }
    >
      <div className="space-y-5 text-slate-200 text-xs">
        {/* Banner */}
        <div className="p-3.5 rounded-xl bg-blue-950/40 border border-blue-800/60 text-blue-200 leading-relaxed">
          <p className="font-semibold text-white text-sm mb-1">
            Seeded First-Run Experience (NASA C-MAPSS FD001)
          </p>
          <p>
            No CSV upload is required to experience the platform. Eight simulated turbofan engines have been pre-scored using an active LightGBM calibrated classifier and Isolation Forest anomaly detector.
          </p>
        </div>

        {/* 3 Reference Machines (§7.2 Demo Scenario) */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <h4 className="font-semibold text-slate-100 uppercase tracking-wider text-[11px]">
              Key Demonstrator Engines in Fleet
            </h4>
            <span className="text-[10px] font-mono text-amber-400/90">
              Example only (not live data)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-[#090f1d] border border-emerald-900/40 space-y-1.5">
              <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                <CheckCircle2 className="w-4 h-4" />
                <span>Unit #1: Healthy</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Health Indicator 94/100. Low failure probability (6%). Nominal baseline sensors.
              </p>
              <div className="text-[10px] text-amber-400/90 font-mono italic">
                Example only (not live data)
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[#090f1d] border border-amber-900/40 space-y-1.5">
              <div className="flex items-center gap-1.5 text-amber-400 font-semibold">
                <AlertTriangle className="w-4 h-4" />
                <span>Unit #2: Warning</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Health Indicator 64/100. Failure probability 42%. Mild upward drift on sensor_11.
              </p>
              <div className="text-[10px] text-amber-400/90 font-mono italic">
                Example only (not live data)
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[#090f1d] border border-rose-900/60 space-y-1.5 ring-1 ring-rose-500/30">
              <div className="flex items-center gap-1.5 text-rose-400 font-semibold">
                <AlertCircle className="w-4 h-4" />
                <span>Unit #3: Critical Alert</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Health Indicator 34/100. Failure probability 82%. Open alert with AI recommendation!
              </p>
              <div className="text-[10px] text-amber-400/90 font-mono italic">
                Example only (not live data)
              </div>
            </div>
          </div>
        </div>

        {/* The 5-Step Workflow (§FR-14) */}
        <div className="p-3.5 rounded-xl bg-[#0c1424] border border-[#1b2b48] space-y-2">
          <h4 className="font-semibold text-slate-100 text-[11px] uppercase tracking-wider flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-400" />
            Human-in-the-Loop Workflow Steps
          </h4>
          <div className="flex items-center justify-between text-[11px] text-slate-300 font-mono py-1 overflow-x-auto gap-2">
            <span className="text-blue-400">AI Prediction</span>
            <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />
            <span className="text-amber-400">Alert Generated</span>
            <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />
            <span className="text-purple-400">AI Recommendation</span>
            <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />
            <span className="text-emerald-400">Engineer Action</span>
            <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />
            <span className="text-slate-100">Outcome Resolved</span>
          </div>
        </div>
      </div>
    </Modal>
  );
};
