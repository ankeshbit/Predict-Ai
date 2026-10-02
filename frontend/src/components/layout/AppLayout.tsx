import React, { useState } from 'react';
import { Sidebar } from './Sidebar';
import type { NavPage } from './Sidebar';
import { TopNavbar } from './TopNavbar';
import type { User } from '../../types';
import { AboutResponsibleUseModal } from '../modals/AboutResponsibleUseModal';

interface AppLayoutProps {
  currentPage: NavPage;
  onNavigate: (page: NavPage) => void;
  currentUser: User;
  openAlertCount: number;
  onResetDemo: () => void;
  onLogout: () => void;
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  currentPage,
  onNavigate,
  currentUser,
  openAlertCount,
  onResetDemo,
  onLogout,
  children,
}) => {
  const [isResponsibleUseOpen, setIsResponsibleUseOpen] = useState(false);

  const pageTitles: Record<NavPage, string> = {
    overview: 'Fleet Overview',
    fleet: 'Fleet Inventory',
    machines: 'Machine Detail',
    datasets: 'Dataset Management',
    alerts: 'Operational Alerts',
    maintenance: 'Maintenance Records',
    'model-performance': 'Model Performance',
    settings: 'System Settings',
  };

  return (
    <div className="min-h-screen bg-[#0e131b] text-slate-100 flex flex-col md:flex-row antialiased">
      {/* Sidebar Navigation */}
      <Sidebar
        currentPage={currentPage}
        onNavigate={onNavigate}
        openAlertsCount={openAlertCount}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        <TopNavbar
          currentPageTitle={pageTitles[currentPage] || 'Dashboard'}
          currentUser={currentUser}
          openAlertCount={openAlertCount}
          onOpenAlerts={() => onNavigate('alerts')}
          onResetDemo={onResetDemo}
          onOpenResponsibleUse={() => setIsResponsibleUseOpen(true)}
          onLogout={onLogout}
        />

        <main className="flex-1 p-4 lg:p-6 max-w-7xl w-full mx-auto space-y-5">
          {children}
        </main>

        {/* Global Responsible Use Modal */}
        <AboutResponsibleUseModal
          isOpen={isResponsibleUseOpen}
          onClose={() => setIsResponsibleUseOpen(false)}
        />
      </div>
    </div>
  );
};
