import React from 'react';
import type { User, Role } from '../../types';
import { Badge } from '../ui/Badge';
import { Bell, RotateCcw, HelpCircle, LogOut } from 'lucide-react';

interface TopNavbarProps {
  currentPageTitle: string;
  currentUser: User;
  onSwitchRole: (role: Role) => void;
  openAlertCount: number;
  onOpenAlerts: () => void;
  onResetDemo: () => void;
  onOpenResponsibleUse: () => void;
  onLogout: () => void;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({
  currentPageTitle,
  currentUser,
  onSwitchRole,
  openAlertCount,
  onOpenAlerts,
  onResetDemo,
  onOpenResponsibleUse,
  onLogout,
}) => {
  return (
    <header className="h-12 bg-[#10151f] border-b border-[#1e2636] px-4 flex items-center justify-between gap-4 select-none">
      {/* Breadcrumb / Current page title */}
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-mono text-slate-500 uppercase">Platform</span>
        <span className="text-slate-600">/</span>
        <span className="text-xs font-semibold text-slate-200">{currentPageTitle}</span>
      </div>

      {/* Center Data Context Tag */}
      <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded bg-[#0b0e14] border border-[#1b2332] text-[11px] font-mono">
        <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
        <span className="text-slate-400">DATASET:</span>
        <span className="text-slate-200 font-semibold">NASA C-MAPSS FD001</span>
        <Badge variant="demo" size="xs">
          Demo
        </Badge>
      </div>

      {/* Right controls: Role switcher, reset demo, notifications, profile */}
      <div className="flex items-center gap-2.5">
        {/* Compact Role Toggle */}
        <div className="flex items-center bg-[#0c1018] border border-[#20293a] rounded p-0.5 text-[11px] font-mono">
          <button
            onClick={() => onSwitchRole('engineer')}
            className={`px-2 py-0.5 rounded transition-colors cursor-pointer ${
              currentUser.role === 'engineer'
                ? 'bg-[#1e2738] text-slate-100 font-semibold shadow-xs'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ENG
          </button>
          <button
            onClick={() => onSwitchRole('admin')}
            className={`px-2 py-0.5 rounded transition-colors cursor-pointer ${
              currentUser.role === 'admin'
                ? 'bg-blue-600 text-white font-semibold shadow-xs'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            ADM
          </button>
        </div>

        {/* Reset Demo State (Admin only) */}
        {currentUser.role === 'admin' && (
          <button
            onClick={onResetDemo}
            className="hidden lg:flex items-center gap-1 px-2 py-1 rounded text-[11px] text-slate-400 hover:text-slate-200 hover:bg-[#18212e] border border-transparent hover:border-[#2b394e] transition-colors cursor-pointer"
            title="Reset seeded demo state"
          >
            <RotateCcw className="w-3 h-3 text-slate-500" />
            <span className="font-mono">Reset</span>
          </button>
        )}

        {/* Responsible Use */}
        <button
          onClick={onOpenResponsibleUse}
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-[#18212e] rounded transition-colors"
          title="Product Limitations & Responsible Use"
        >
          <HelpCircle className="w-3.5 h-3.5" />
        </button>

        {/* Alert Bell */}
        <button
          onClick={onOpenAlerts}
          className="relative p-1.5 text-slate-400 hover:text-slate-200 hover:bg-[#18212e] rounded transition-colors cursor-pointer"
          title="Alerts"
        >
          <Bell className="w-3.5 h-3.5" />
          {openAlertCount > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-[#10151f]" />
          )}
        </button>

        {/* User Identity & Logout */}
        <div className="flex items-center gap-2 pl-2 border-l border-[#1e2636]">
          <span className="text-xs font-mono text-slate-300 hidden sm:inline">
            {currentUser.role === 'admin' ? 'admin' : 'engineer'}
          </span>
          <button
            onClick={onLogout}
            className="p-1.5 text-slate-400 hover:text-rose-400 rounded transition-colors cursor-pointer"
            title="Sign out"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
};
