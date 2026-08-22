import React, { useEffect, useState } from 'react';
import { Loader2, History, Search, RefreshCw, X, FileJson, Copy, Check } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';

export const Audit: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedLog, setSelectedLog] = useState<any>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  
  const { showToast } = useToast();

  const fetchLogs = async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const data = await api.getAuditLogs();
      setLogs(data);
    } catch (err: any) {
      showToast(err.message || 'Failed to fetch audit logs', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const handleCopyId = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    showToast('Copied to clipboard', 'info');
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '60vh', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 size={32} className="animate-spin" color="var(--text-secondary)" />
      </div>
    );
  }

  // Filter logs
  const filteredLogs = logs.filter((log) => {
    const searchStr = search.toLowerCase();
    return (
      log.action.toLowerCase().includes(searchStr) ||
      log.actor.toLowerCase().includes(searchStr) ||
      log.entity.toLowerCase().includes(searchStr) ||
      log.entity_id.toLowerCase().includes(searchStr) ||
      JSON.stringify(log.metadata).toLowerCase().includes(searchStr)
    );
  });

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'left', position: 'relative' }}>
      {/* Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 600 }}>System Audit Log</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Immutable records of database inserts, API calls, Gemini agent triages, and delivery status changes.
          </p>
        </div>
        <button onClick={() => fetchLogs(true)} className="btn btn-secondary btn-sm">
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {/* Filter */}
      <div className="card" style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ flex: 1, position: 'relative' }}>
          <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
          <input
            type="text"
            className="form-input"
            placeholder="Search audit trail (e.g. email status, CASE_CREATED, case ID)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: '38px' }}
          />
        </div>
      </div>

      {/* Table */}
      <div className="table-container">
        {filteredLogs.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No audit records found.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Actor</th>
                <th>Action Event</th>
                <th>Entity Type</th>
                <th>Entity Reference ID</th>
                <th>Result Status</th>
                <th style={{ textAlign: 'right' }}>Metadata</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log, index) => (
                <tr
                  key={index}
                  onClick={() => setSelectedLog(log)}
                  style={{ cursor: 'pointer' }}
                >
                  <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {formatDateTime(log.timestamp)}
                  </td>
                  <td style={{ fontWeight: 500 }}>{log.actor}</td>
                  <td>
                    <code style={{ fontSize: '11px', color: 'var(--text-primary)' }}>{log.action}</code>
                  </td>
                  <td>{log.entity}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>
                        {log.entity_id.substring(0, 18)}...
                      </span>
                      <button
                        onClick={(e) => handleCopyId(e, log.entity_id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          color: 'var(--text-muted)',
                          padding: '2px',
                        }}
                      >
                        {copiedId === log.entity_id ? <Check size={12} color="var(--color-success)" /> : <Copy size={12} />}
                      </button>
                    </div>
                  </td>
                  <td>
                    <span className={`badge ${log.status === 'success' || log.status === 'delivered' || log.status === 'recovered' ? 'badge-success' : log.status === 'failed' ? 'badge-error' : 'badge-warning'}`}>
                      {log.status}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button className="btn btn-ghost btn-sm" style={{ padding: '4px 6px' }}>
                      <FileJson size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Audit Detail Drawer */}
      {selectedLog && (
        <div
          style={{
            position: 'fixed',
            right: 0,
            top: 0,
            width: '460px',
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

          {/* Header */}
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
              <History size={18} color="var(--color-info)" />
              <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Event Payload Context</h3>
            </div>
            <button
              onClick={() => setSelectedLog(null)}
              className="btn btn-ghost btn-sm"
              style={{ padding: '6px' }}
            >
              <X size={16} />
            </button>
          </div>

          {/* Content */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Meta */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Event Timestamp</span>
                <span>{formatDateTime(selectedLog.timestamp)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Actor</span>
                <span style={{ fontWeight: 500 }}>{selectedLog.actor}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Action</span>
                <code>{selectedLog.action}</code>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Entity</span>
                <span>{selectedLog.entity}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Entity ID</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{selectedLog.entity_id}</span>
              </div>
            </div>

            <div style={{ height: '1px', backgroundColor: 'var(--border-color)' }}></div>

            {/* Metadata JSON */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Metadata Payload JSON
              </span>
              <pre
                style={{
                  backgroundColor: 'var(--bg-primary)',
                  border: '1px solid var(--border-color)',
                  padding: '16px',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '11px',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-secondary)',
                  overflowX: 'auto',
                  lineHeight: '1.5',
                }}
              >
                {JSON.stringify(selectedLog.metadata, null, 2)}
              </pre>
            </div>

          </div>
        </div>
      )}
    </div>
  );
};
