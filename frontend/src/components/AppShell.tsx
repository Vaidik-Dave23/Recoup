import React from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  AlertTriangle,
  Mail,
  TrendingUp,
  UserCheck,
  History,
  FlaskConical,
  Settings,
  LogOut,
  User,
  Activity,
} from 'lucide-react';
import { api } from '../services/api';

interface AppShellProps {
  children?: React.ReactNode;
  user: any;
  onLogout: () => void;
}

export const AppShell: React.FC<AppShellProps> = ({ children, user, onLogout }) => {
  const location = useLocation();
  const navigate = useNavigate();

  const menuItems = [
    { name: 'Overview', path: '/dashboard', icon: LayoutDashboard },
    { name: 'At-Risk Queue', path: '/recovery/at-risk', icon: AlertTriangle },
    { name: 'Recovery Actions', path: '/recovery/actions', icon: Mail },
    { name: 'Outcomes', path: '/recovery/outcomes', icon: TrendingUp },
    { name: 'Escalations', path: '/recovery/escalations', icon: UserCheck },
    { name: 'Audit Trail', path: '/audit', icon: History },
    { name: 'Fault Lab', path: '/fault-lab', icon: FlaskConical },
  ];

  const handleLogout = () => {
    api.logout();
    onLogout();
    navigate('/login');
  };

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden' }}>
      {/* Sidebar */}
      <aside
        style={{
          width: '260px',
          borderRight: '1px solid var(--border-color)',
          backgroundColor: 'var(--bg-secondary)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          padding: '24px 16px',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
          {/* Logo / Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingLeft: '8px' }}>
            <Activity size={22} color="var(--color-info)" style={{ flexShrink: 0 }} />
            <span
              style={{
                fontFamily: 'var(--font-sans)',
                fontWeight: 700,
                fontSize: '18px',
                letterSpacing: '-0.03em',
                color: 'var(--text-primary)',
              }}
            >
              Recoup
            </span>
            <span
              style={{
                fontSize: '10px',
                fontWeight: 600,
                backgroundColor: 'rgba(255, 255, 255, 0.05)',
                color: 'var(--text-secondary)',
                padding: '2px 6px',
                borderRadius: '4px',
                border: '1px solid var(--border-color)',
              }}
            >
              v1.0
            </span>
          </div>

          {/* Navigation Links */}
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-md)',
                    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                    backgroundColor: isActive ? 'rgba(255, 255, 255, 0.03)' : 'transparent',
                    fontSize: '13px',
                    fontWeight: isActive ? 500 : 400,
                    border: isActive ? '1px solid var(--border-color)' : '1px solid transparent',
                  }}
                >
                  <Icon size={16} color={isActive ? 'var(--text-primary)' : 'var(--text-muted)'} />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User profile & Settings */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ height: '1px', backgroundColor: 'var(--border-color)' }}></div>
          
          <Link
            to="/settings"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              padding: '10px 12px',
              borderRadius: 'var(--radius-md)',
              color: location.pathname.startsWith('/settings') ? 'var(--text-primary)' : 'var(--text-secondary)',
              backgroundColor: location.pathname.startsWith('/settings') ? 'rgba(255, 255, 255, 0.03)' : 'transparent',
              fontSize: '13px',
            }}
          >
            <Settings size={16} color="var(--text-muted)" />
            <span>Settings</span>
          </Link>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '1px solid var(--border-color)',
                  flexShrink: 0,
                }}
              >
                <User size={14} color="var(--text-secondary)" />
              </div>
              <div style={{ minWidth: 0 }}>
                <div
                  style={{
                    fontSize: '12px',
                    fontWeight: 500,
                    color: 'var(--text-primary)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {user?.name || 'Vaidik Dave'}
                </div>
                <div
                  style={{
                    fontSize: '10px',
                    color: 'var(--text-muted)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {user?.email || 'vaidikdave236@gmail.com'}
                </div>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Logout"
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-error)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        {/* Top Header */}
        <header
          style={{
            height: '60px',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            backgroundColor: 'var(--bg-primary)',
          }}
        >
          {/* Section title */}
          <div>
            <h1
              style={{
                fontSize: '14px',
                fontWeight: 600,
                color: 'var(--text-primary)',
                margin: 0,
                letterSpacing: '-0.01em',
              }}
            >
              {menuItems.find((item) => location.pathname.startsWith(item.path))?.name || 'Recoup Operations Control'}
            </h1>
          </div>


        </header>

        {/* Page Content Panel */}
        <main style={{ flex: 1, overflowY: 'auto', padding: '24px', position: 'relative' }}>
          {children || <Outlet />}
        </main>
      </div>
    </div>
  );
};
