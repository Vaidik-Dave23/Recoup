import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { api } from './services/api';
import { ToastProvider, useToast } from './components/Toast';
import { AppShell } from './components/AppShell';

import { Home } from './pages/Home';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { AtRiskQueue } from './pages/AtRiskQueue';
import { CaseDetail } from './pages/CaseDetail';
import { AgentTrace } from './pages/AgentTrace';
import { RecoveryActions } from './pages/RecoveryActions';
import { Outcomes } from './pages/Outcomes';
import { Escalations } from './pages/Escalations';
import { Audit } from './pages/Audit';
import { FaultLab } from './pages/FaultLab';
import { Settings } from './pages/Settings';

interface LayoutProps {
  user: any;
  onLogout: () => void;
}

const AuthenticatedLayout: React.FC<LayoutProps> = ({ user, onLogout }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return (
    <AppShell user={user} onLogout={onLogout}>
      <Outlet />
    </AppShell>
  );
};

const GuestLayout: React.FC<{ user: any }> = ({ user }) => {
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
};

const AppContent: React.FC = () => {
  const [user, setUser] = useState<any>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const { showToast } = useToast();

  useEffect(() => {
    let isMounted = true;

    const checkAuth = async () => {
      const token = localStorage.getItem('recoup_token');
      if (!token) {
        if (isMounted) setCheckingAuth(false);
        return;
      }
      try {
        const profile = await api.getMe();
        if (isMounted) setUser(profile);
      } catch {
        api.logout();
        if (isMounted) setUser(null);
      } finally {
        if (isMounted) setCheckingAuth(false);
      }
    };

    checkAuth();

    const handleAuthExpired = () => {
      setUser(null);
      showToast('Your session has expired. Please log in again.', 'error');
    };

    window.addEventListener('auth_expired', handleAuthExpired);
    return () => {
      isMounted = false;
      window.removeEventListener('auth_expired', handleAuthExpired);
    };
  }, []);

  if (checkingAuth) {
    return (
      <div style={{ display: 'flex', height: '100vh', width: '100vw', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-primary)' }}>
        <Loader2 size={36} className="animate-spin" color="var(--text-secondary)" />
      </div>
    );
  }

  return (
    <Routes>
      {/* Public / Guest Routes */}
      <Route element={<GuestLayout user={user} />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login onLoginSuccess={setUser} />} />
        <Route path="/register" element={<Register onRegisterSuccess={setUser} />} />
      </Route>

      {/* Authenticated Dashboard Pages */}
      <Route element={<AuthenticatedLayout user={user} onLogout={() => setUser(null)} />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/recovery/at-risk" element={<AtRiskQueue />} />
        <Route path="/recovery/cases/:id" element={<CaseDetail />} />
        <Route path="/recovery/cases/:id/trace" element={<AgentTrace />} />
        <Route path="/recovery/cases/:id/actions" element={<RecoveryActions />} />
        <Route path="/recovery/actions" element={<RecoveryActions />} />
        <Route path="/recovery/outcomes" element={<Outcomes />} />
        <Route path="/recovery/escalations" element={<Escalations />} />
        <Route path="/audit" element={<Audit />} />
        <Route path="/fault-lab" element={<FaultLab />} />
        <Route path="/settings" element={<Settings user={user} onUserUpdate={setUser} />} />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to={user ? "/dashboard" : "/"} replace />} />
    </Routes>
  );
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <ToastProvider>
        <AppContent />
      </ToastProvider>
    </BrowserRouter>
  );
};

