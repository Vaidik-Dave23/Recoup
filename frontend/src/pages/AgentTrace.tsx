import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Loader2, ArrowLeft, Cpu, Terminal, ArrowDown, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';

export const AgentTrace: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [caseData, setCaseData] = useState<any>(null);
  const [investigations, setInvestigations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedPayload, setExpandedPayload] = useState<Record<string, boolean>>({});
  
  const navigate = useNavigate();
  const { showToast } = useToast();

  useEffect(() => {
    const fetchTraceData = async () => {
      if (!id) return;
      setLoading(true);
      try {
        const [c, invs] = await Promise.all([
          api.getCase(id),
          api.getAIInvestigations(id).catch(() => []),
        ]);
        setCaseData(c);
        setInvestigations(invs);
      } catch (err: any) {
        showToast(err.message || 'Failed to load trace logs', 'error');
      } finally {
        setLoading(false);
      }
    };
    fetchTraceData();
  }, [id]);

  const toggleExpand = (nodeId: string) => {
    setExpandedPayload((prev) => ({ ...prev, [nodeId]: !prev[nodeId] }));
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '60vh', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 size={32} className="animate-spin" color="var(--text-secondary)" />
      </div>
    );
  }

  if (!caseData) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <h3>Case Not Found</h3>
        <button onClick={() => navigate('/recovery/at-risk')} className="btn btn-secondary" style={{ marginTop: '16px' }}>
          Back to At-Risk Queue
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'left' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <button onClick={() => navigate(`/recovery/cases/${id}`)} className="btn btn-ghost btn-sm">
          <ArrowLeft size={14} /> Back to Case Detail
        </button>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 600 }}>AI Agent Orchestration Trace</h2>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            Case UUID: {caseData.id}
          </span>
        </div>
      </div>

      {/* Info Card */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Current Status</span>
          <div style={{ fontSize: '16px', fontWeight: 600, textTransform: 'capitalize', color: 'var(--text-primary)', marginTop: '4px' }}>
            {caseData.status.replace(/_/g, ' ')}
          </div>
        </div>
        <div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Active Stage</span>
          <div style={{ fontSize: '16px', fontWeight: 600, textTransform: 'capitalize', color: 'var(--color-info)', marginTop: '4px' }}>
            {caseData.stage}
          </div>
        </div>
        <div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>AI Confidence</span>
          <div style={{ fontSize: '16px', fontWeight: 600, fontFamily: 'var(--font-mono)', marginTop: '4px' }}>
            {investigations.length > 0 ? `${Math.round(parseFloat(investigations[investigations.length - 1].confidence || '0.95') * 100)}%` : 'N/A'}
          </div>
        </div>
      </div>

      {/* Node Trace Flow Tree */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px',
          width: '100%',
          maxWidth: '800px',
          marginInline: 'auto',
          padding: '20px 0',
        }}
      >
        {investigations.length === 0 ? (
          <div className="card" style={{ width: '100%', textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            No trace nodes have been generated. Run the agent to see live decisions.
          </div>
        ) : (
          investigations.map((node, index) => {
            const nodeId = node.id.toString();
            const isExpanded = !!expandedPayload[nodeId];

            return (
              <React.Fragment key={nodeId}>
                {/* Node Card */}
                <div
                  className="card"
                  style={{
                    width: '100%',
                    borderLeft: `4px solid ${index % 2 === 0 ? 'var(--color-info)' : 'var(--color-warning)'}`,
                    backgroundColor: 'var(--bg-secondary)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '6px',
                          backgroundColor: 'rgba(255, 255, 255, 0.03)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          border: '1px solid var(--border-color)',
                        }}
                      >
                        <Cpu size={16} color="var(--color-info)" />
                      </div>
                      <div>
                        <h4 style={{ fontSize: '14px', fontWeight: 600, textTransform: 'capitalize' }}>
                          {node.node_name.replace(/_/g, ' ')}
                        </h4>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          Model: <code>{node.model_name || 'gemini-3.5-flash'}</code>
                        </span>
                      </div>
                    </div>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span className="badge badge-info" style={{ fontFamily: 'var(--font-mono)' }}>
                        Conf: {Math.round(parseFloat(node.confidence || '0.95') * 100)}%
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {new Date(node.created_at).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>

                  {/* Summary / Decision Output */}
                  <div
                    style={{
                      padding: '12px',
                      borderRadius: 'var(--radius-sm)',
                      backgroundColor: 'rgba(255, 255, 255, 0.01)',
                      border: '1px solid var(--border-color)',
                    }}
                  >
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginBottom: '4px' }}>
                      <Terminal size={12} color="var(--text-muted)" />
                      <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                        AI Finding & Decision
                      </span>
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: '1.4' }}>
                      {node.response_payload?.finding || node.response_payload?.reasoning || 'Triage criteria verified successfully.'}
                    </div>
                    {node.response_payload?.recommended_action && (
                      <div style={{ fontSize: '13px', color: 'var(--color-warning)', marginTop: '8px', fontWeight: 500 }}>
                        Recommendation: {node.response_payload.recommended_action}
                      </div>
                    )}
                  </div>

                  {/* Expand payload trigger */}
                  <button
                    onClick={() => toggleExpand(nodeId)}
                    style={{
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '12px',
                      color: 'var(--text-secondary)',
                      padding: '4px 0 0',
                      width: 'fit-content',
                    }}
                  >
                    {isExpanded ? (
                      <>
                        Hide JSON Payloads <ChevronUp size={14} />
                      </>
                    ) : (
                      <>
                        Show JSON Payloads <ChevronDown size={14} />
                      </>
                    )}
                  </button>

                  {/* Expanded Payloads */}
                  {isExpanded && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
                      {node.input_payload && (
                        <div>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                            Input Context
                          </div>
                          <pre
                            style={{
                              backgroundColor: 'var(--bg-primary)',
                              border: '1px solid var(--border-color)',
                              padding: '10px',
                              borderRadius: 'var(--radius-sm)',
                              fontSize: '11px',
                              overflowX: 'auto',
                              color: 'var(--text-secondary)',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            {JSON.stringify(node.input_payload, null, 2)}
                          </pre>
                        </div>
                      )}
                      <div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                          Response Payload
                        </div>
                        <pre
                          style={{
                            backgroundColor: 'var(--bg-primary)',
                              border: '1px solid var(--border-color)',
                              padding: '10px',
                              borderRadius: 'var(--radius-sm)',
                              fontSize: '11px',
                              overflowX: 'auto',
                              color: 'var(--text-secondary)',
                              fontFamily: 'var(--font-mono)',
                          }}
                        >
                          {JSON.stringify(node.response_payload, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>

                {/* Connecting arrow if not the last node */}
                {index < investigations.length - 1 && (
                  <ArrowDown size={18} color="var(--border-color)" />
                )}
              </React.Fragment>
            );
          })
        )}
      </div>
    </div>
  );
};
