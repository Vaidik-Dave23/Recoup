import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Loader2, ArrowLeft, Mail, Info, RefreshCw, X, MessageSquare } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';

export const RecoveryActions: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [actions, setActions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAction, setSelectedAction] = useState<any>(null);
  
  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchActions = async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const data = await api.getRecoveryActions(id);
      setActions(data);
    } catch (err: any) {
      showToast(err.message || 'Failed to load recovery actions', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActions();
  }, [id]);

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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {id && (
            <button onClick={() => navigate(`/recovery/cases/${id}`)} className="btn btn-ghost btn-sm">
              <ArrowLeft size={14} /> Back to Case Detail
            </button>
          )}
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 600 }}>Sent Recovery Actions</h2>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              {id ? `Communication attempts for Case: ${id.substring(0, 13)}...` : 'Comprehensive log of all outgoing dunning operations.'}
            </p>
          </div>
        </div>
        <button onClick={() => fetchActions(true)} className="btn btn-secondary btn-sm">
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {/* Main Table */}
      <div className="table-container">
        {actions.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No communication actions recorded.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Sent At</th>
                {!id && <th>Case ID</th>}
                <th>Action Type</th>
                <th>Channel</th>
                <th>Subject / Content</th>
                <th>Delivery Status</th>
                <th style={{ textAlign: 'right' }}>View Detail</th>
              </tr>
            </thead>
            <tbody>
              {actions.map((act) => (
                <tr
                  key={act.id}
                  onClick={() => setSelectedAction(act)}
                  style={{ cursor: 'pointer' }}
                >
                  <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {formatDateTime(act.created_at || act.sent_at)}
                  </td>
                  {!id && (
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                      <Link to={`/recovery/cases/${act.case_id}`} onClick={(e) => e.stopPropagation()} style={{ color: 'var(--color-info)' }}>
                        {act.case_id.substring(0, 8)}...
                      </Link>
                    </td>
                  )}
                  <td style={{ textTransform: 'capitalize', fontWeight: 500 }}>
                    {act.action_type}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {act.channel === 'email' ? (
                        <Mail size={14} color="var(--text-muted)" />
                      ) : (
                        <MessageSquare size={14} color="var(--text-muted)" />
                      )}
                      <span style={{ fontSize: '13px' }}>{act.channel}</span>
                    </div>
                  </td>
                  <td style={{ color: 'var(--text-secondary)', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {act.subject || act.message_body || 'N/A'}
                  </td>
                  <td>
                    <span className={`badge ${act.status === 'delivered' || act.status === 'sent' ? 'badge-success' : act.status === 'failed' ? 'badge-error' : 'badge-warning'}`}>
                      <span className="badge-dot" />
                      {act.status}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button className="btn btn-ghost btn-sm" style={{ padding: '4px 8px' }}>
                      <Info size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Side Detail Drawer (Email Proof Panel) */}
      {selectedAction && (
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
          {/* Style rule for sliding animation */}
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
              <Mail size={18} color="var(--color-info)" />
              <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Message Proof Details</h3>
            </div>
            <button
              onClick={() => setSelectedAction(null)}
              className="btn btn-ghost btn-sm"
              style={{ padding: '6px' }}
            >
              <X size={16} />
            </button>
          </div>

          {/* Drawer Content */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Properties */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Status</span>
                <span className={`badge ${selectedAction.status === 'delivered' || selectedAction.status === 'sent' ? 'badge-success' : 'badge-error'}`}>
                  {selectedAction.status}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Action Type</span>
                <span style={{ fontWeight: 500, textTransform: 'uppercase' }}>{selectedAction.action_type}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Dispatch Channel</span>
                <span style={{ fontWeight: 500, textTransform: 'capitalize' }}>{selectedAction.channel}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Sent Timestamp</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                  {formatDateTime(selectedAction.created_at || selectedAction.sent_at)}
                </span>
              </div>
              {selectedAction.provider_ref && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Provider Ref</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                    {selectedAction.provider_ref}
                  </span>
                </div>
              )}
            </div>

            <div style={{ height: '1px', backgroundColor: 'var(--border-color)' }}></div>

            {/* Email Message Preview Box */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Rendered Preview
              </span>
              
              <div
                style={{
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: 'var(--bg-primary)',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
              >
                {selectedAction.subject && (
                  <div style={{ fontSize: '13px', fontWeight: 600, borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', color: 'var(--text-primary)' }}>
                    Subject: {selectedAction.subject}
                  </div>
                )}
                <div
                  style={{
                    fontSize: '13px',
                    color: 'var(--text-secondary)',
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'var(--font-sans)',
                    lineHeight: '1.6',
                  }}
                >
                  {selectedAction.message_body || 'No message content body recorded.'}
                </div>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
};
