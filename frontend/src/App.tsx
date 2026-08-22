import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
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

const AppContent: React.FC = () => {
  const [user, setUser] = useState<any>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const { showToast } = useToast();

  const checkAuth = async () => {
    const token = localStorage.getItem('recoup_token');
    if (!token) {
      setCheckingAuth(false);
      return;
    }
    try {
      const profile = await api.getMe();
      setUser(profile);
    } catch (err) {
      api.logout();
      setUser(null);
    } finally {
      setCheckingAuth(false);
    }
  };

  useEffect(() => {
    checkAuth();

    const handleAuthExpired = () => {
      setUser(null);
      showToast('Your session has expired. Please log in again.', 'error');
    };

    window.addEventListener('auth_expired', handleAuthExpired);
    return () => {
      window.removeEventListener('auth_expired', handleAuthExpired);
    };
  }, [showToast]);

  if (checkingAuth) {
    return (
      <div style={{ display: 'flex', height: '100vh', width: '100vw', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-primary)' }}>
        <Loader2 size={36} className="animate-spin" color="var(--text-secondary)" />
      </div>
    );
  }

  // Authentication Route Guards
  const RequireAuth: React.FC<{ children: React.ReactElement }> = ({ children }) => {
    if (!user) {
      return <Navigate to="/login" replace />;
    }
    return <AppShell user={user} onLogout={() => setUser(null)}>{children}</AppShell>;
  };

  const RedirectIfAuth: React.FC<{ children: React.ReactElement }> = ({ children }) => {
    if (user) {
      return <Navigate to="/dashboard" replace />;
    }
    return children;
  };

  return (
    <Routes>
      {/* Public Pages */}
      <Route path="/" element={<RedirectIfAuth><Home /></RedirectIfAuth>} />
      
      {/* Auth Pages */}
      <Route path="/login" element={<RedirectIfAuth><Login onLoginSuccess={setUser} /></RedirectIfAuth>} />
      <Route path="/register" element={<RedirectIfAuth><Register onRegisterSuccess={setUser} /></RedirectIfAuth>} />

      {/* Authenticated Dashboard Pages */}
      <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
      <Route path="/recovery/at-risk" element={<RequireAuth><AtRiskQueue /></RequireAuth>} />
      <Route path="/recovery/cases/:id" element={<RequireAuth><CaseDetail /></RequireAuth>} />
      <Route path="/recovery/cases/:id/trace" element={<RequireAuth><AgentTrace /></RequireAuth>} />
      <Route path="/recovery/cases/:id/actions" element={<RequireAuth><RecoveryActions /></RequireAuth>} />
      <Route path="/recovery/actions" element={<RequireAuth><RecoveryActions /></RequireAuth>} />
      <Route path="/recovery/outcomes" element={<RequireAuth><Outcomes /></RequireAuth>} />
      <Route path="/recovery/escalations" element={<RequireAuth><Escalations /></RequireAuth>} />
      <Route path="/audit" element={<RequireAuth><Audit /></RequireAuth>} />
      <Route path="/fault-lab" element={<RequireAuth><FaultLab /></RequireAuth>} />
      <Route path="/settings" element={<RequireAuth><Settings user={user} onUserUpdate={setUser} /></RequireAuth>} />

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
