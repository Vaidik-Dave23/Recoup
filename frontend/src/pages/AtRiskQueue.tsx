import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Search, Play, RefreshCw, Eye } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';
import { formatCurrency } from '../lib/currency';

export const AtRiskQueue: React.FC = () => {
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedStage, setSelectedStage] = useState('all');
  const [selectedReason, setSelectedReason] = useState('all');
  const [agentRunningMap, setAgentRunningMap] = useState<Record<string, boolean>>({});
  
  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchCases = async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const data = await api.getCases();
      setCases(data);
    } catch (err: any) {
      showToast(err.message || 'Failed to fetch recovery cases', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  const handleRunAgent = async (e: React.MouseEvent, caseId: string) => {
    e.stopPropagation(); // prevent navigation to detail page
    setAgentRunningMap((prev) => ({ ...prev, [caseId]: true }));
    try {
      const res: any = await api.runAgent(caseId);
      showToast(`Agent executed. Recommendation: ${res.strategy?.recommendation || 'Retry'}`, 'success');
      await fetchCases(true); // reload list silently
    } catch (err: any) {
      showToast(err.message || 'Agent failed to run', 'error');
    } finally {
      setAgentRunningMap((prev) => ({ ...prev, [caseId]: false }));
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '60vh', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 size={32} className="animate-spin" color="var(--text-secondary)" />
      </div>
    );
  }

  // Get unique stages and reasons for dropdown filters
  const stages = ['all', ...Array.from(new Set(cases.map((c) => c.stage)))];
  const reasons = ['all', ...Array.from(new Set(cases.map((c) => c.failure_reason)))];

  // Filtering
  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      c.id.toLowerCase().includes(search.toLowerCase()) ||
      c.failure_reason.toLowerCase().includes(search.toLowerCase()) ||
      c.case_type.toLowerCase().includes(search.toLowerCase());
    
    const matchesStage = selectedStage === 'all' || c.stage === selectedStage;
    const matchesReason = selectedReason === 'all' || c.failure_reason === selectedReason;

    return matchesSearch && matchesStage && matchesReason;
  });

  // Calculate Exposure
  const totalExposure = filteredCases
    .filter((c) => c.status === 'in_progress')
    .reduce((sum, c) => sum + c.amount_at_risk, 0);



  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Title & Total Exposure Banner */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div style={{ textAlign: 'left' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 600 }}>At-Risk Exposure Queue</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Failed payments, overdue invoices, and shopping carts flagged for AI agent intervention.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Active Exposure
            </span>
            <div style={{ fontSize: '22px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-error)' }}>
              {formatCurrency(totalExposure)}
            </div>
          </div>
          <button onClick={() => fetchCases(true)} className="btn btn-secondary" style={{ padding: '10px 14px' }}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div
        className="card"
        style={{
          display: 'flex',
          gap: '16px',
          padding: '16px',
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
        {/* Search */}
        <div style={{ flex: 1, minWidth: '240px', position: 'relative' }}>
          <Search
            size={16}
            color="var(--text-muted)"
            style={{ position: 'absolute', left: '12px', top: '12px' }}
          />
          <input
            type="text"
            className="form-input"
            placeholder="Search by Case ID, type, or reason..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: '38px', paddingRight: '12px' }}
          />
        </div>

        {/* Stage Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Stage:</span>
          <select
            value={selectedStage}
            onChange={(e) => setSelectedStage(e.target.value)}
            className="form-input"
            style={{ width: '130px', padding: '8px 12px', fontSize: '13px' }}
          >
            {stages.map((st) => (
              <option key={st} value={st}>
                {st}
              </option>
            ))}
          </select>
        </div>

        {/* Reason Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Reason:</span>
          <select
            value={selectedReason}
            onChange={(e) => setSelectedReason(e.target.value)}
            className="form-input"
            style={{ width: '180px', padding: '8px 12px', fontSize: '13px' }}
          >
            {reasons.map((rn) => (
              <option key={rn} value={rn}>
                {rn.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Table */}
      <div className="table-container">
        {filteredCases.length === 0 ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No failed payments found matching the selected filters.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Case Reference</th>
                <th>Type</th>
                <th>Failure Reason</th>
                <th>Amount At Risk</th>
                <th>Stage</th>
                <th>Status</th>
                <th style={{ textAlign: 'center' }}>Attempts</th>
                <th>Last Update</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCases.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => navigate(`/recovery/cases/${c.id}`)}
                  style={{ cursor: 'pointer' }}
                >
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 500, fontSize: '12px' }}>
                    {c.id.substring(0, 13)}...
                  </td>
                  <td style={{ textTransform: 'capitalize' }}>
                    {c.case_type.replace(/_/g, ' ')}
                  </td>
                  <td style={{ color: 'var(--text-secondary)' }}>
                    <code>{c.failure_reason}</code>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    {formatCurrency(c.amount_at_risk)}
                  </td>
                  <td>
                    <span className={`badge ${c.stage === 'recovered' ? 'badge-success' : c.stage === 'escalated' ? 'badge-error' : 'badge-info'}`}>
                      <span className="badge-dot" />
                      {c.stage}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${c.status === 'recovered' ? 'badge-success' : c.status === 'escalated' ? 'badge-error' : c.status === 'closed' ? 'badge-warning' : 'badge-info'}`}>
                      {c.status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)' }}>{c.attempt_count}</td>
                  <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {new Date(c.updated_at).toLocaleDateString()}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/recovery/cases/${c.id}`);
                        }}
                        className="btn btn-secondary btn-sm"
                        title="View Case Detail"
                      >
                        <Eye size={12} />
                      </button>
                      <button
                        onClick={(e) => handleRunAgent(e, c.id)}
                        disabled={c.status !== 'in_progress' || agentRunningMap[c.id]}
                        className="btn btn-primary btn-sm"
                        title="Run AI Agent"
                      >
                        {agentRunningMap[c.id] ? (
                          <Loader2 size={12} className="animate-spin" />
                        ) : (
                          <Play size={12} fill="currentColor" />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
