import React, { useState } from 'react';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import type { Role } from '../types';
import { ArrowRight, ShieldCheck, Mail, Lock, Activity } from 'lucide-react';

interface LoginPageProps {
  onLogin: (role: Role) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [email, setEmail] = useState('engineer@predicore.internal');
  const [password, setPassword] = useState('••••••••••••');
  const [rememberMe, setRememberMe] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onLogin('engineer');
  };

  return (
    <div className="min-h-screen w-full bg-[#0a0e16] flex flex-col lg:flex-row items-stretch select-none text-slate-200">
      {/* Left Technical Specification Panel */}
      <div className="flex-1 bg-[#0d121a] p-8 lg:p-14 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-[#1f2838]">
        {/* Brand Header */}
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded bg-[#162132] border border-[#253650] flex items-center justify-center text-blue-400 font-mono font-bold text-sm">
            PC
          </div>
          <div>
            <div className="text-base font-semibold text-slate-100 tracking-tight flex items-center gap-2">
              PrediCore
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#162030] text-slate-400 border border-[#24334a]">
                v3.0.0
              </span>
            </div>
            <div className="text-xs text-slate-400">Predictive Maintenance &amp; Machine Intelligence Platform</div>
          </div>
        </div>

        {/* Technical Value & Industrial Observability */}
        <div className="my-10 lg:my-0 max-w-lg space-y-6">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded bg-[#131a26] border border-[#222d3e] text-slate-300 text-xs font-mono">
            <Activity className="w-3.5 h-3.5 text-blue-400" />
            <span>Industrial Telemetry &bull; NASA C-MAPSS FD001</span>
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-100 tracking-tight leading-snug">
              Machine health intelligence with mathematical rigor.
            </h1>
            <p className="text-xs text-slate-400 leading-relaxed">
              Industrial predictive-maintenance analytics for understanding turbofan condition, detecting anomalous sensor drift, evaluating calibrated failure risk at horizon H=30, and supporting human-in-the-loop maintenance decisions.
            </p>
          </div>

          {/* 4 Analytical Capability Indicators */}
          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="p-3.5 rounded-md bg-[#111620] border border-[#1f2838] space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400">Calibrated ROC-AUC</div>
              <div className="text-xl font-bold font-mono text-blue-400">0.946</div>
              <div className="text-[10px] font-mono text-slate-400">Held-out engine split</div>
            </div>

            <div className="p-3.5 rounded-md bg-[#111620] border border-[#1f2838] space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400">Prediction Horizon</div>
              <div className="text-xl font-bold font-mono text-slate-100">H = 30</div>
              <div className="text-[10px] font-mono text-slate-400">Operating cycles</div>
            </div>

            <div className="p-3.5 rounded-md bg-[#111620] border border-[#1f2838] space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400">Class-Imbalance PR-AUC</div>
              <div className="text-xl font-bold font-mono text-emerald-400">0.892</div>
              <div className="text-[10px] font-mono text-slate-400">Baseline 0.320</div>
            </div>

            <div className="p-3.5 rounded-md bg-[#111620] border border-[#1f2838] space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400">Explainability</div>
              <div className="text-xl font-bold font-mono text-slate-200">SHAP</div>
              <div className="text-[10px] font-mono text-slate-400">Local feature attribution</div>
            </div>
          </div>
        </div>

        {/* Compliance Footer */}
        <div className="text-[11px] font-mono text-slate-400 flex items-center gap-2">
          <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
          <span>PRD §FR-14 Human Authority Boundary &bull; Advisory Decision Support Only</span>
        </div>
      </div>

      {/* Right Login Station */}
      <div className="w-full lg:w-[460px] p-8 lg:p-14 flex flex-col justify-center bg-[#0a0e16]">
        <div className="w-full max-w-sm mx-auto space-y-5">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold text-slate-100 tracking-tight">Workstation Sign In</h2>
            <p className="text-xs text-slate-400">
              Access the operational fleet console and inference engine
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
            <Input
              label="Operator Identity / Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="engineer@predicore.internal"
              leftIcon={<Mail className="w-4 h-4 text-slate-500" />}
              required
            />

            <Input
              label="Passcode"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter passcode"
              leftIcon={<Lock className="w-4 h-4 text-slate-500" />}
              required
            />

            <div className="flex items-center justify-between text-xs pt-1">
              <label className="flex items-center gap-2 text-slate-400 cursor-pointer text-xs">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="rounded bg-[#161f2e] border-[#253246] text-blue-600 focus:ring-0 cursor-pointer"
                />
                <span>Remember session</span>
              </label>
              <span className="text-xs text-slate-400 hover:text-slate-300 cursor-pointer">
                Forgot passcode?
              </span>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="md"
              className="w-full mt-2"
              icon={<ArrowRight className="w-4 h-4" />}
            >
              Sign In to Workstation
            </Button>
          </form>

          {/* Quick Demo Access Bar */}
          <div className="pt-2 border-t border-[#1f2838] space-y-2">
            <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider text-center">
              Direct Demonstration Access
            </div>

            <div className="space-y-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => onLogin('engineer')}
                className="w-full text-xs text-slate-200 justify-center"
              >
                Sign In as Reliability Engineer (Operator)
              </Button>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onLogin('admin')}
                className="w-full text-xs text-slate-400 hover:text-slate-200 justify-center border-[#233148]"
              >
                Sign In as System Administrator (Governance)
              </Button>
            </div>
          </div>

          <div className="p-3 rounded-md bg-[#0e141f] border border-[#1f2838] text-center text-[11px] text-slate-400 leading-relaxed font-mono">
            Demo Environment: 8 turbofan engines seeded with run-to-failure telemetry from NASA C-MAPSS FD001 test partition.
          </div>
        </div>
      </div>
    </div>
  );
};
