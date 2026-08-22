import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, ShieldAlert, RefreshCw, X } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';

export const Escalations: React.FC = () => {
  const [escalations, setEscalations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedEsc, setSelectedEsc] = useState<any>(null);
  const [notes, setNotes] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  
  const { showToast } = useToast();

  const fetchEscalations = async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const data = await api.getEscalations();
      setEscalations(data);
    } catch (err: any) {
      showToast(err.message || 'Failed to load escalations', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEscalations();
  }, []);

  const handleSelectEscalation = (esc: any) => {
    setSelectedEsc(esc);
    setNotes(esc.notes || esc.summary || '');
  };

  const handleUpdateStatus = async (status: 'open' | 'resolved') => {
    if (!selectedEsc) return;
    setActionLoading(true);
    try {
      await api.updateEscalation(selectedEsc.id, {
        status,
        notes: notes,
      });
      showToast(`Escalation status set to ${status}`, 'success');
      setSelectedEsc(null);
      await fetchEscalations(true);
    } catch (err: any) {
      showToast(err.message || 'Failed to update escalation', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '60vh', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 size={32} className="animate-spin" color="var(--text-secondary)" />
      </div>
    );
  }

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'left', position: 'relative' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 600 }}>Human Handoff & Escalations</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Review cases where the autonomous recovery agent hit limits and requires merchant approval.
          </p>
        </div>
        <button onClick={() => fetchEscalations(true)} className="btn btn-secondary btn-sm">
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {/* Main Table */}
      <div className="table-container">
        {escalations.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No pending human escalations. AI loop is running smoothly.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Created At</th>
                <th>Case Reference</th>
                <th>Reason</th>
                <th>Priority</th>
                <th>Handoff Status</th>
                <th style={{ textAlign: 'right' }}>Review</th>
              </tr>
            </thead>
            <tbody>
              {escalations.map((esc) => (
                <tr
                  key={esc.id}
                  onClick={() => handleSelectEscalation(esc)}
                  style={{ cursor: 'pointer' }}
                >
                  <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {formatDateTime(esc.created_at)}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                    <span style={{ color: 'var(--color-info)' }}>{esc.case_id.substring(0, 13)}...</span>
                  </td>
                  <td style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {esc.reason}
                  </td>
                  <td>
                    <span className={`badge ${esc.priority === 'high' ? 'badge-error' : esc.priority === 'medium' ? 'badge-warning' : 'badge-info'}`}>
                      {esc.priority}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${esc.status === 'resolved' ? 'badge-success' : 'badge-warning'}`}>
                      <span className="badge-dot" />
                      {esc.status}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button className="btn btn-secondary btn-sm" style={{ padding: '4px 8px' }}>
                      Review
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Escalation Detail Side Drawer */}
      {selectedEsc && (
        <div
          style={{
            position: 'fixed',
            right: 0,
            top: 0,
            width: '450px',
            maxWidth: '100%',
            height: '100vh',
            backgroundColor: 'var(--bg-secondary)',
            borderLeft: '1px solid var(--border-color)',
            boxShadow: '-10px 0 30px rgba(0, 0, 0, 0.5)',
            zIndex: 1100,
            display: 'flex',
            flexDirection: 'column',
            animation: 'slideLeft 0.2s ease-out',
          }}
        >
          <style>{`
            @keyframes slideLeft {
              from { transform: translateX(100%); }
              to { transform: translateX(0); }
            }
          `}</style>

          {/* Drawer Header */}
          <div
            style={{
              padding: '20px',
              borderBottom: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <ShieldAlert size={18} color="var(--color-error)" />
              <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Review Escalation</h3>
            </div>
            <button
              onClick={() => setSelectedEsc(null)}
              className="btn btn-ghost btn-sm"
              style={{ padding: '6px' }}
            >
              <X size={16} />
            </button>
          </div>

          {/* Drawer Content */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Meta details */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Case reference</span>
                <Link to={`/recovery/cases/${selectedEsc.case_id}`} style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-info)' }}>
                  {selectedEsc.case_id}
                </Link>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Escalation ID</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{selectedEsc.id}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Priority</span>
                <span className={`badge ${selectedEsc.priority === 'high' ? 'badge-error' : 'badge-warning'}`}>{selectedEsc.priority}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Date Escalated</span>
                <span style={{ fontSize: '12px' }}>{formatDateTime(selectedEsc.created_at)}</span>
              </div>
            </div>

            <div style={{ height: '1px', backgroundColor: 'var(--border-color)' }}></div>

            {/* Handoff Reason */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                AI Handoff Reason
              </span>
              <div style={{ padding: '14px', borderRadius: 'var(--radius-md)', backgroundColor: 'rgba(244, 63, 94, 0.03)', border: '1px solid var(--color-error-border)', fontSize: '13px', lineHeight: '1.5' }}>
                {selectedEsc.reason}
              </div>
            </div>

            {/* Operator Notes */}
            <div className="form-group">
              <label className="form-label">Internal Resolution Notes</label>
              <textarea
                className="form-input"
                rows={4}
                placeholder="Describe steps taken to resolve this escalation (e.g. called client, manually triggered Razorpay link)..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                style={{ resize: 'vertical', fontSize: '13px' }}
              />
            </div>

            {/* Resolve buttons */}
            <div style={{ display: 'flex', gap: '10px', marginTop: 'auto', paddingTop: '20px' }}>
              {selectedEsc.status === 'open' ? (
                <button
                  onClick={() => handleUpdateStatus('resolved')}
                  disabled={actionLoading}
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                >
                  {actionLoading ? <Loader2 size={14} className="animate-spin" /> : 'Mark Resolved'}
                </button>
              ) : (
                <button
                  onClick={() => handleUpdateStatus('open')}
                  disabled={actionLoading}
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                >
                  {actionLoading ? <Loader2 size={14} className="animate-spin" /> : 'Re-open Escalation'}
                </button>
              )}
            </div>

          </div>
        </div>
      )}
    </div>
  );
};
