import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Loader2, ArrowLeft, Play, Mail, Terminal } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';
import { formatCurrency } from '../lib/currency';

export const CaseDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [caseData, setCaseData] = useState<any>(null);
  const [investigations, setInvestigations] = useState<any[]>([]);
  const [actions, setActions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [agentRunning, setAgentRunning] = useState(false);
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [outcomeAmount, setOutcomeAmount] = useState<number>(0);
  const [outcomeNotes, setOutcomeNotes] = useState('');
  const [showOutcomeForm, setShowOutcomeForm] = useState(false);
  const [isRecoveredVal, setIsRecoveredVal] = useState(true);
  const [outcomeSubmitting, setOutcomeSubmitting] = useState(false);

  const fetchAllDetails = async (quiet = false) => {
    if (!id) return;
    if (!quiet) setLoading(true);
    try {
      const [c, invs, acts] = await Promise.all([
        api.getCase(id),
        api.getAIInvestigations(id).catch(() => []),
        api.getRecoveryActions(id).catch(() => []),
      ]);
      const caseVal = c as any;
      setCaseData(caseVal);
      if (caseVal && typeof caseVal.amount_at_risk === 'number') {
        setOutcomeAmount(caseVal.amount_at_risk / 100);
      }
      setInvestigations(invs);
      setActions(acts);
    } catch (err: any) {
      showToast(err.message || 'Failed to load case details', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitOutcome = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || actions.length === 0) return;
    setOutcomeSubmitting(true);
    try {
      const latestAction = actions[actions.length - 1];
      await api.createOutcome({
        case_id: id,
        action_id: latestAction.id,
        recovered: isRecoveredVal,
        amount_recovered: isRecoveredVal ? Math.round(Number(outcomeAmount) * 100) : 0,
        notes: outcomeNotes || (isRecoveredVal ? 'Manual recovery recorded' : 'Manual failure recorded'),
      });
      showToast('Outcome recorded successfully!', 'success');
      setShowOutcomeForm(false);
      setOutcomeNotes('');
      await fetchAllDetails(true);
    } catch (err: any) {
      showToast(err.message || 'Failed to record outcome', 'error');
    } finally {
      setOutcomeSubmitting(false);
    }
  };

  useEffect(() => {
    fetchAllDetails();
  }, [id]);

  const handleRunAgent = async () => {
    if (!id) return;
    setAgentRunning(true);
    try {
      const res: any = await api.runAgent(id);
      showToast(`Agent executed successfully! Result: ${res.escalated ? 'Escalated' : 'Action Created'}`, 'success');
      await fetchAllDetails(true);
    } catch (err: any) {
      showToast(err.message || 'Error running recovery agent', 'error');
    } finally {
      setAgentRunning(false);
    }
  };

  const handleResumeAgent = async () => {
    if (!id) return;
    setAgentRunning(true);
    try {
      await api.resumeAgent(id);
      showToast(`Agent resumed successfully!`, 'success');
      await fetchAllDetails(true);
    } catch (err: any) {
      showToast(err.message || 'Error resuming recovery agent', 'error');
    } finally {
      setAgentRunning(false);
    }
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
        <h3 style={{ color: 'var(--text-primary)' }}>Case Not Found</h3>
        <button onClick={() => navigate('/recovery/at-risk')} className="btn btn-secondary" style={{ marginTop: '16px' }}>
          Back to At-Risk Queue
        </button>
      </div>
    );
  }



  const formattedDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  };

  // Find latest investigation node recommendation
  const latestInv = investigations[investigations.length - 1];
  const recommendedAction = latestInv?.response_payload?.recommended_action || latestInv?.response_payload?.recommendation || 'No recommendation recorded yet';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'left' }}>
      {/* Back button & Title */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button onClick={() => navigate('/recovery/at-risk')} className="btn btn-ghost btn-sm">
            <ArrowLeft size={14} /> Back to Queue
          </button>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
                Case {caseData.id.substring(0, 18)}...
              </h2>
              <span className={`badge ${caseData.stage === 'recovered' ? 'badge-success' : caseData.stage === 'escalated' ? 'badge-error' : 'badge-info'}`}>
                {caseData.stage}
              </span>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Created: {formattedDate(caseData.created_at)}
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleResumeAgent}
            disabled={caseData.status !== 'in_progress' || agentRunning}
            className="btn btn-secondary"
          >
            Resume Agent
          </button>
          <button
            onClick={handleRunAgent}
            disabled={caseData.status !== 'in_progress' || agentRunning}
            className="btn btn-primary"
          >
            {agentRunning ? (
              <>
                <Loader2 size={14} className="animate-spin" /> Orchestrating Agent...
              </>
            ) : (
              <>
                <Play size={14} fill="currentColor" /> Run AI Agent
              </>
            )}
          </button>
        </div>
      </div>

      {/* Grid Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        
        {/* Left Column (Details, Financials, Timeline) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Financial Impact Card */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Financial Impact
            </h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Amount at Risk</span>
                <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-error)' }}>
                  {formatCurrency(caseData.amount_at_risk, caseData.currency)}
                </div>
              </div>
              <div style={{ height: '32px', width: '1px', backgroundColor: 'var(--border-color)' }}></div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Recovered Amount</span>
                <div style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-success)' }}>
                  {formatCurrency(caseData.financial_impact || 0, caseData.currency)}
                </div>
              </div>
            </div>
          </div>

          {/* Payment & Order Summary */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Payment Context Details
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Payment ID (UUID)</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                  {caseData.payment_id || 'N/A'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Case Type</span>
                <span style={{ textTransform: 'capitalize' }}>
                  {caseData.case_type.replace(/_/g, ' ')}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Failure Reason</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                  <code>{caseData.failure_reason}</code>
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Status</span>
                <span className={`badge ${caseData.status === 'recovered' ? 'badge-success' : caseData.status === 'escalated' ? 'badge-error' : 'badge-info'}`}>
                  {caseData.status.replace(/_/g, ' ')}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Dunning Attempts</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                  {caseData.attempt_count}
                </span>
              </div>
            </div>
          </div>

          {/* Record Recovery Outcome Card */}
          {caseData.status === 'in_progress' && actions.length > 0 && (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
                Record Recovery Outcome
              </h3>
              
              {!showOutcomeForm ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0, lineHeight: '1.4' }}>
                    Manually log the recovery result for this case based on customer response or direct payment validation.
                  </p>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => {
                        setIsRecoveredVal(true);
                        setShowOutcomeForm(true);
                      }}
                      className="btn btn-primary"
                      style={{ flex: 1, backgroundColor: 'var(--color-success)', borderColor: 'var(--color-success)', color: '#fff', fontSize: '12px', padding: '8px' }}
                    >
                      Mark as Recovered
                    </button>
                    <button
                      onClick={() => {
                        setIsRecoveredVal(false);
                        setShowOutcomeForm(true);
                      }}
                      className="btn btn-secondary"
                      style={{ flex: 1, borderColor: 'var(--color-error)', color: 'var(--color-error)', fontSize: '12px', padding: '8px' }}
                    >
                      Mark Attempt Failed
                    </button>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleSubmitOutcome} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: isRecoveredVal ? 'var(--color-success)' : 'var(--color-error)' }}>
                    Recording: {isRecoveredVal ? 'SUCCESSFUL RECOVERY' : 'FAILED RECOVERY ATTEMPT'}
                  </div>

                  {isRecoveredVal && (
                    <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label className="form-label" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Recovered Amount ({caseData.currency})</label>
                      <input
                        type="number"
                        step="0.01"
                        className="form-input"
                        required
                        value={outcomeAmount}
                        onChange={(e) => setOutcomeAmount(parseFloat(e.target.value) || 0)}
                        style={{ fontSize: '13px', padding: '8px' }}
                      />
                    </div>
                  )}

                  <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <label className="form-label" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Internal Outcome Notes</label>
                    <textarea
                      className="form-input"
                      rows={2}
                      placeholder="Optional details..."
                      value={outcomeNotes}
                      onChange={(e) => setOutcomeNotes(e.target.value)}
                      style={{ fontSize: '13px', padding: '8px', resize: 'vertical' }}
                    />
                  </div>

                  <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                    <button
                      type="button"
                      onClick={() => setShowOutcomeForm(false)}
                      className="btn btn-secondary btn-sm"
                      style={{ flex: 1, fontSize: '11px' }}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={outcomeSubmitting}
                      className="btn btn-primary btn-sm"
                      style={{ flex: 1, fontSize: '11px' }}
                    >
                      {outcomeSubmitting ? 'Saving...' : 'Save Outcome'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* Lifecycle Timeline */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Case Recovery Stage Timeline
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingLeft: '8px', borderLeft: '1px solid var(--border-color)' }}>
              
              {/* Created */}
              <div style={{ position: 'relative', paddingLeft: '16px' }}>
                <div style={{ position: 'absolute', left: '-13px', top: '4px', width: '9px', height: '9px', borderRadius: '50%', backgroundColor: 'var(--color-success)', border: '2px solid var(--bg-secondary)' }} />
                <div style={{ fontSize: '12px' }}>
                  <div style={{ fontWeight: 500 }}>Failed Payment Detected</div>
                  <span style={{ color: 'var(--text-secondary)' }}>{formattedDate(caseData.created_at)}</span>
                </div>
              </div>

              {/* AI Triage */}
              {investigations.length > 0 && (
                <div style={{ position: 'relative', paddingLeft: '16px' }}>
                  <div style={{ position: 'absolute', left: '-13px', top: '4px', width: '9px', height: '9px', borderRadius: '50%', backgroundColor: 'var(--color-info)', border: '2px solid var(--bg-secondary)' }} />
                  <div style={{ fontSize: '12px' }}>
                    <div style={{ fontWeight: 500 }}>AI Investigation Triage & Strategy Node</div>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      Confidence: {Math.round(parseFloat(latestInv?.confidence || '0.95') * 100)}%
                    </span>
                  </div>
                </div>
              )}

              {/* Action sent */}
              {actions.length > 0 && (
                <div style={{ position: 'relative', paddingLeft: '16px' }}>
                  <div style={{ position: 'absolute', left: '-13px', top: '4px', width: '9px', height: '9px', borderRadius: '50%', backgroundColor: 'var(--color-warning)', border: '2px solid var(--bg-secondary)' }} />
                  <div style={{ fontSize: '12px' }}>
                    <div style={{ fontWeight: 500 }}>Recovery Action Dispatched ({actions[0].action_type})</div>
                    <span style={{ color: 'var(--text-secondary)' }}>Status: {actions[0].status}</span>
                  </div>
                </div>
              )}

              {/* Resolved / Resolved outcome */}
              {caseData.status !== 'in_progress' && (
                <div style={{ position: 'relative', paddingLeft: '16px' }}>
                  <div style={{ position: 'absolute', left: '-13px', top: '4px', width: '9px', height: '9px', borderRadius: '50%', backgroundColor: caseData.status === 'recovered' ? 'var(--color-success)' : 'var(--color-error)', border: '2px solid var(--bg-secondary)' }} />
                  <div style={{ fontSize: '12px' }}>
                    <div style={{ fontWeight: 500 }}>Case Resolution reached ({caseData.status})</div>
                    <span style={{ color: 'var(--text-secondary)' }}>{formattedDate(caseData.updated_at)}</span>
                  </div>
                </div>
              )}

            </div>
          </div>

        </div>

        {/* Right Column (Agent Trace & Recovery Action Previews) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Next Recommended Action Panel */}
          <div
            className="card"
            style={{
              backgroundColor: 'rgba(99, 102, 241, 0.03)',
              borderColor: 'var(--color-info-border)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={16} color="var(--color-info)" />
              <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-info)' }}>
                AI Recommendation Engine
              </h3>
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>
                {recommendedAction}
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: '1.4' }}>
                Based on Gemini's assessment of card declined code and customer billing data.
              </p>
            </div>
          </div>

          {/* AI Investigation Trace Preview */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                AI Agent Trace Steps
              </h3>
              <Link to={`/recovery/cases/${id}/trace`} className="btn btn-secondary btn-sm">
                View Trace Graph
              </Link>
            </div>
            
            {investigations.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                No investigation trace nodes recorded. Click "Run AI Agent" to initiate.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {investigations.slice(-3).reverse().map((inv) => (
                  <div
                    key={inv.id}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: 'rgba(255, 255, 255, 0.01)',
                      border: '1px solid var(--border-color)',
                      fontSize: '13px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>
                        Node: {inv.node_name.replace(/_/g, ' ')}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {inv.model_name || 'gemini'}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      Finding: {inv.response_payload?.finding || inv.response_payload?.reasoning || 'Executed triage node'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recovery Actions Preview */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Dunning Actions Sent
              </h3>
              <Link to={`/recovery/cases/${id}/actions`} className="btn btn-secondary btn-sm">
                View Actions Log
              </Link>
            </div>

            {actions.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                No dunning messages dispatched yet.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {actions.slice(-3).reverse().map((act) => (
                  <div
                    key={act.id}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-md)',
                      backgroundColor: 'rgba(255, 255, 255, 0.01)',
                      border: '1px solid var(--border-color)',
                      fontSize: '13px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Mail size={14} color="var(--text-muted)" />
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontWeight: 500 }}>
                          {act.action_type.toUpperCase()} ({act.channel})
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {act.subject || 'Dunning reminder'}
                        </span>
                      </div>
                    </div>
                    <span className={`badge ${act.status === 'delivered' || act.status === 'sent' ? 'badge-success' : 'badge-warning'}`}>
                      {act.status}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
};
