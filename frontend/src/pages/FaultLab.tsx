import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Zap, CheckCircle2, ArrowRight } from 'lucide-react';
import { formatCurrency } from '../lib/currency';
import { api } from '../services/api';
import { useToast } from '../components/Toast';

export const FaultLab: React.FC = () => {
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [executingMap, setExecutingMap] = useState<Record<string, boolean>>({});
  
  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchScenarios = async () => {
    setLoading(true);
    try {
      const data = await api.getScenarios();
      setScenarios(data);
    } catch (err: any) {
      showToast(err.message || 'Failed to fetch scenarios', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchScenarios();
  }, []);

  const handleExecute = async (scenarioId: string) => {
    setExecutingMap((prev) => ({ ...prev, [scenarioId]: true }));
    try {
      const res = await api.executeScenario(scenarioId);
      showToast(res.message || 'Payment failure simulated & AI recovery pipeline initiated!', 'success');
      // Redirect to case detail page with automated live pipeline view
      navigate(`/recovery/cases/${res.case_id}?auto=true`);
    } catch (err: any) {
      showToast(err.message || 'Failed to execute scenario', 'error');
    } finally {
      setExecutingMap((prev) => ({ ...prev, [scenarioId]: false }));
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '60vh', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 size={32} className="animate-spin" color="var(--text-secondary)" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'left' }}>
      {/* Title */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Zap size={22} color="var(--color-primary)" />
          <h2 style={{ fontSize: '20px', fontWeight: 600 }}>Deterministic Fault Lab & Live Simulator</h2>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Trigger simulated payment failures to experience Recoup's genuine autonomous recovery flow end-to-end.
        </p>
      </div>

      {/* Automated Pipeline Flow Banner */}
      <div
        className="card"
        style={{
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(16, 185, 129, 0.05) 100%)',
          borderColor: 'var(--color-info-border)',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          padding: '16px 20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={18} color="var(--color-success)" />
          <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            One-Click Autonomous Recovery Chain
          </h4>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
          <span className="badge badge-info" style={{ fontSize: '11px' }}>1. Simulate Failure</span>
          <ArrowRight size={12} />
          <span className="badge badge-info" style={{ fontSize: '11px' }}>2. AI Triage & Strategy</span>
          <ArrowRight size={12} />
          <span className="badge badge-info" style={{ fontSize: '11px' }}>3. Razorpay Link & Email</span>
          <ArrowRight size={12} />
          <span className="badge badge-success" style={{ fontSize: '11px' }}>4. Customer Pays</span>
          <ArrowRight size={12} />
          <span className="badge badge-success" style={{ fontSize: '11px' }}>5. Auto-Verified Recovery</span>
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0, lineHeight: '1.4' }}>
          Clicking <strong>Simulate Failed Payment</strong> below immediately creates the failure, triggers Gemini triage & policy guardrails, generates a live Razorpay test checkout link, and dispatches the recovery email.
        </p>
      </div>

      {/* Scenarios Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
        {scenarios.map((sc) => (
          <div
            key={sc.id}
            className="card"
            style={{
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '16px',
              backgroundColor: 'var(--bg-secondary)',
              border: sc.id === 'soft_decline' ? '1px solid rgba(99, 102, 241, 0.4)' : undefined,
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className={`badge ${sc.id === 'hard_decline' ? 'badge-error' : 'badge-info'}`} style={{ textTransform: 'uppercase', fontSize: '10px' }}>
                  {sc.case_type}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                  {formatCurrency(sc.amount, sc.currency)}
                </span>
              </div>
              <h3 style={{ fontSize: '15px', fontWeight: 600 }}>{sc.name}</h3>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                {sc.description}
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Reason: <code>{sc.failure_reason}</code>
              </span>
              
              <button
                onClick={() => handleExecute(sc.id)}
                disabled={executingMap[sc.id]}
                className={`btn btn-sm ${sc.id === 'hard_decline' ? 'btn-secondary' : 'btn-primary'}`}
              >
                {executingMap[sc.id] ? (
                  <>
                    <Loader2 size={12} className="animate-spin" /> Simulating...
                  </>
                ) : (
                  <>
                    <Zap size={12} fill="currentColor" /> Simulate Failed Payment
                  </>
                )}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
