import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, AlertTriangle, Play } from 'lucide-react';
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
      showToast(res.message || 'Scenario executed successfully!', 'success');
      // Redirect to case detail page
      navigate(`/recovery/cases/${res.case_id}`);
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
        <h2 style={{ fontSize: '20px', fontWeight: 600 }}>Deterministic Fault Lab</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Seed mock failures directly into your database. Essential for verifying agent logic and demonstrating dunning outcomes.
        </p>
      </div>

      {/* Warning Alert */}
      <div
        className="card"
        style={{
          borderLeft: '4px solid var(--color-warning)',
          backgroundColor: 'rgba(245, 158, 11, 0.03)',
          borderColor: 'var(--color-warning-border)',
          display: 'flex',
          gap: '12px',
          padding: '16px',
        }}
      >
        <AlertTriangle size={18} color="var(--color-warning)" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <h4 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-warning)' }}>Developer Testing Sandbox</h4>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px', lineHeight: '1.4' }}>
            These actions create real database orders, transaction attempts, and recovery case state records under your merchant profile, simulating live events.
          </p>
        </div>
      </div>

      {/* Scenarios Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
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
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className="badge badge-info" style={{ textTransform: 'uppercase', fontSize: '10px' }}>
                  {sc.case_type}
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
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
                className="btn btn-primary btn-sm"
              >
                {executingMap[sc.id] ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <>
                    <Play size={12} fill="currentColor" /> Trigger
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
