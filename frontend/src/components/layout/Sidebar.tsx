import React from 'react';
import {
  Activity,
  Layers,
  Cpu,
  Database,
  BellRing,
  Wrench,
  Gauge,
  Settings,
} from 'lucide-react';

export type NavPage =
  | 'overview'
  | 'fleet'
  | 'machines'
  | 'datasets'
  | 'alerts'
  | 'maintenance'
  | 'model-performance'
  | 'settings';

interface SidebarProps {
  currentPage: NavPage;
  onNavigate: (page: NavPage) => void;
  openAlertsCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onNavigate,
  openAlertsCount,
}) => {
  const sections: Array<{
    group: string;
    items: Array<{
      id: NavPage;
      label: string;
      icon: React.ReactNode;
      badge?: number | string;
    }>;
  }> = [
    {
      group: 'MONITOR',
      items: [
        { id: 'overview', label: 'Overview', icon: <Activity className="w-4 h-4" /> },
        { id: 'fleet', label: 'Fleet', icon: <Layers className="w-4 h-4" /> },
        { id: 'machines', label: 'Machines', icon: <Cpu className="w-4 h-4" /> },
      ],
    },
    {
      group: 'ANALYZE',
      items: [
        { id: 'datasets', label: 'Datasets', icon: <Database className="w-4 h-4" /> },
        { id: 'model-performance', label: 'Model Performance', icon: <Gauge className="w-4 h-4" /> },
      ],
    },
    {
      group: 'OPERATE',
      items: [
        {
          id: 'alerts',
          label: 'Alerts',
          icon: <BellRing className="w-4 h-4" />,
          badge: openAlertsCount > 0 ? openAlertsCount : undefined,
        },
        { id: 'maintenance', label: 'Maintenance', icon: <Wrench className="w-4 h-4" /> },
      ],
    },
    {
      group: 'SYSTEM',
      items: [
        { id: 'settings', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
      ],
    },
  ];

  return (
    <aside className="w-56 bg-[#10151f] border-r border-[#1e2636] flex flex-col shrink-0 min-h-screen text-slate-300 select-none">
      {/* Brand Header */}
      <div className="h-12 px-4 border-b border-[#1e2636] flex items-center gap-2.5">
        <div className="w-6 h-6 rounded bg-blue-600 flex items-center justify-center text-white font-mono font-bold text-xs tracking-wider">
          P
        </div>
        <div className="flex items-baseline gap-1.5 overflow-hidden">
          <span className="font-semibold text-slate-100 text-sm tracking-tight">PrediCore</span>
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">PdM</span>
        </div>
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 px-2 py-3 space-y-4 overflow-y-auto">
        {sections.map((sec) => (
          <div key={sec.group} className="space-y-0.5">
            <div className="px-2.5 py-1 text-[10px] font-mono font-semibold text-slate-500 tracking-wider">
              {sec.group}
            </div>
            {sec.items.map((item) => {
              const isActive = currentPage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onNavigate(item.id)}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition-colors cursor-pointer ${
                    isActive
                      ? 'bg-[#1b2434] text-white font-semibold border-l-2 border-blue-500 rounded-l-none'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-[#141b27]'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <span className={isActive ? 'text-blue-400' : 'text-slate-500'}>{item.icon}</span>
                    <span className="truncate">{item.label}</span>
                  </div>
                  {item.badge !== undefined && (
                    <span className="px-1.5 py-0.2 rounded font-mono text-[10px] font-bold bg-rose-950/80 text-rose-300 border border-rose-800/80">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Subtle Engine & Domain Footer */}
      <div className="p-3 border-t border-[#1e2636] bg-[#0c1018] text-[10px] font-mono text-slate-500 space-y-0.5">
        <div className="text-slate-400 font-semibold truncate">NASA C-MAPSS FD001</div>
        <div className="truncate">Simulated Engine Benchmark</div>
      </div>
    </aside>
  );
};
