import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, ArrowRight, TrendingUp, AlertTriangle, ShieldCheck, RefreshCw, Layers } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';
import { formatCurrency } from '../lib/currency';

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchDashboardData = async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const overview = await api.getDashboardOverview();
      setData(overview);
    } catch (err: any) {
      showToast(err.message || 'Failed to fetch dashboard data', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '60vh', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 size={32} className="animate-spin" color="var(--text-secondary)" />
      </div>
    );
  }

  const kpis = data?.kpis || {
    active_cases: 0,
    total_cases: 0,
    recovered_cases: 0,
    amount_at_risk: 0,
    amount_recovered: 0,
    recovery_rate: 0,
  };

  const priorityCases = data?.priority_queue || [];
  const recentActivity = data?.recent_activity || [];



  // Calculate percentage for visual summary
  const totalFinancialImpact = kpis.amount_at_risk + kpis.amount_recovered;
  const recoveryPercent = totalFinancialImpact > 0 ? (kpis.amount_recovered / totalFinancialImpact) * 100 : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header Banner */}
      <div
        className="card"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '24px',
          background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.01) 0%, rgba(255, 255, 255, 0.03) 100%)',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', textAlign: 'left' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600 }}>Recovery Control Dashboard</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Real-time tracking of failed payments and agentic communication loops.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={() => fetchDashboardData(true)} className="btn btn-secondary" style={{ padding: '8px 12px' }}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button onClick={() => navigate('/recovery/at-risk')} className="btn btn-primary">
            View At-Risk Queue <ArrowRight size={14} />
          </button>
        </div>
      </div>

      {/* KPIs Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        {/* KPI 1: At Risk */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px', textAlign: 'left' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
            <span style={{ fontSize: '11px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              At-Risk Exposure
            </span>
            <AlertTriangle size={16} color="var(--color-error)" />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
              {formatCurrency(kpis.amount_at_risk)}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Across {kpis.active_cases} active cases
            </div>
          </div>
        </div>

        {/* KPI 2: Recovered */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px', textAlign: 'left' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
            <span style={{ fontSize: '11px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Recovered Revenue
            </span>
            <ShieldCheck size={16} color="var(--color-success)" />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-success)' }}>
              {formatCurrency(kpis.amount_recovered)}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              From {kpis.recovered_cases} closed cases
            </div>
          </div>
        </div>

        {/* KPI 3: Active Cases */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px', textAlign: 'left' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
            <span style={{ fontSize: '11px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Active Recovery
            </span>
            <Layers size={16} color="var(--color-info)" />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
              {kpis.active_cases}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Pending autonomous resolution
            </div>
          </div>
        </div>

        {/* KPI 4: Recovery Rate */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px', textAlign: 'left' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
            <span style={{ fontSize: '11px', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Recovery Rate
            </span>
            <TrendingUp size={16} color="var(--color-info)" />
          </div>
          <div>
            <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
              {kpis.recovery_rate}%
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Resolved vs total cases
            </div>
          </div>
        </div>
      </div>

      {/* Recovery Summary Split Bar Visualizer */}
      <div className="card" style={{ textAlign: 'left' }}>
        <div className="card-header">
          <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Financial Payoff Breakdown</h3>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Recovered ratio: <strong style={{ color: 'var(--color-success)' }}>{roundPercent(recoveryPercent)}%</strong>
          </span>
        </div>
        <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden', backgroundColor: 'var(--bg-tertiary)', marginBottom: '16px' }}>
          <div style={{ width: `${recoveryPercent}%`, backgroundColor: 'var(--color-success)' }} title="Recovered" />
          <div style={{ width: `${100 - recoveryPercent}%`, backgroundColor: 'var(--color-error-bg)', borderLeft: '1px solid var(--bg-primary)' }} title="At Risk" />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--color-success)' }}></span>
            <span style={{ color: 'var(--text-secondary)' }}>Recovered: {formatCurrency(kpis.amount_recovered)}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--color-error)' }}></span>
            <span style={{ color: 'var(--text-secondary)' }}>Remaining At Risk: {formatCurrency(kpis.amount_at_risk)}</span>
          </div>
        </div>
      </div>

      {/* Grid: Priority Cases & Activity */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        {/* Priority Cases */}
        <div className="card" style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card-header">
            <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Priority Queue (Top At-Risk)</h3>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Sorted by value</span>
          </div>

          {priorityCases.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No active at-risk cases in queue.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {priorityCases.map((c: any) => (
                <div
                  key={c.id}
                  onClick={() => navigate(`/recovery/cases/${c.id}`)}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'rgba(255, 255, 255, 0.01)',
                    cursor: 'pointer',
                    transition: 'var(--transition-fast)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--border-focus)')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-color)')}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '12px', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                        {c.id.substring(0, 8)}...
                      </span>
                      <span className={`badge ${c.stage === 'recovered' ? 'badge-success' : c.stage === 'escalated' ? 'badge-error' : 'badge-info'}`}>
                        {c.stage}
                      </span>
                    </div>
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {c.failure_reason.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                      {formatCurrency(c.amount_at_risk)}
                    </span>
                    <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                      {new Date(c.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="card" style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card-header">
            <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Recent Agent Activity</h3>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Dunning execution logs</span>
          </div>

          {recentActivity.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
              No recent activity recorded.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingLeft: '8px', borderLeft: '1px solid var(--border-color)' }}>
              {recentActivity.map((act: any) => (
                <div key={act.id} style={{ position: 'relative', paddingLeft: '16px' }}>
                  {/* Timeline Dot */}
                  <div
                    style={{
                      position: 'absolute',
                      left: '-5px',
                      top: '4px',
                      width: '9px',
                      height: '9px',
                      borderRadius: '50%',
                      backgroundColor: act.status === 'delivered' || act.status === 'sent' ? 'var(--color-success)' : 'var(--color-info)',
                      border: '2px solid var(--bg-secondary)',
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', fontSize: '12px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <span style={{ fontWeight: 500 }}>
                        Executed {act.action_type.toUpperCase()} via {act.channel}
                      </span>
                      <span style={{ color: 'var(--text-secondary)' }}>
                        Case: <a href={`/recovery/cases/${act.case_id}`} style={{ fontFamily: 'var(--font-mono)' }}>{act.case_id.substring(0, 8)}</a>
                      </span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px' }}>
                      <span className={`badge ${act.status === 'delivered' || act.status === 'sent' ? 'badge-success' : act.status === 'failed' ? 'badge-error' : 'badge-warning'}`}>
                        {act.status}
                      </span>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                        {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

function roundPercent(val: number) {
  return isNaN(val) ? 0 : Math.round(val);
}
