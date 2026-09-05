import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  Loader2, ArrowLeft, Play, Mail, Terminal, CheckCircle2, 
  ExternalLink, ShieldCheck, RefreshCw, ChevronDown, ChevronUp, AlertOctagon, Sparkles
} from 'lucide-react';
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
  const [verifyingPayment, setVerifyingPayment] = useState(false);
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [outcomeAmount, setOutcomeAmount] = useState<number>(0);
  const [outcomeNotes, setOutcomeNotes] = useState('');
  const [showManualOverride, setShowManualOverride] = useState(false);
  const [showOutcomeForm, setShowOutcomeForm] = useState(false);
  const [isRecoveredVal, setIsRecoveredVal] = useState(true);
  const [outcomeSubmitting, setOutcomeSubmitting] = useState(false);

  // Reference for previous status to detect when case transitions to recovered
  const prevStatusRef = useRef<string | null>(null);

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

      // Check if newly recovered
      if (prevStatusRef.current === 'in_progress' && caseVal?.status === 'recovered') {
        showToast('Payment verified on Razorpay! Revenue successfully recovered.', 'success');
      }
      prevStatusRef.current = caseVal?.status;
    } catch (err: any) {
      if (!quiet) showToast(err.message || 'Failed to load case details', 'error');
    } finally {
      if (!quiet) setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllDetails();
  }, [id]);

  // Live Auto-Polling for Background Agent & Razorpay Payment Link completion
  useEffect(() => {
    if (!caseData || caseData.status !== 'in_progress') return;

    const interval = setInterval(async () => {
      // If an action with a Razorpay link is active, automatically invoke verifyPayment on each poll tick
      const hasSentLink = actions.some(
        (a) => (a.status === 'sent' || a.status === 'delivered') && a.provider_ref?.includes('rzp_link:')
      );

      if (hasSentLink && id) {
        try {
          await api.verifyPayment(id);
        } catch {
          // Ignore transient background verification errors
        }
      }
      await fetchAllDetails(true);
    }, 1800);

    return () => clearInterval(interval);
  }, [caseData?.status, actions, id]);

  const handleManualVerify = async () => {
    if (!id) return;
    setVerifyingPayment(true);
    try {
      const res = await api.verifyPayment(id);
      if (res.sync_result?.synced && res.sync_result?.link_status === 'paid') {
        showToast('Razorpay payment verified! Case is now RECOVERED.', 'success');
      } else {
        showToast(`Razorpay status: ${res.sync_result?.link_status || 'Waiting for customer payment'}`, 'info');
      }
      await fetchAllDetails(true);
    } catch (err: any) {
      showToast(err.message || 'Failed to verify payment', 'error');
    } finally {
      setVerifyingPayment(false);
    }
  };

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

  // Find latest investigation nodes & payloads
  const triageInv = investigations.find((i) => i.node_name === 'triage');
  const strategyInv = investigations.find((i) => i.node_name === 'strategize');
  const contentInv = investigations.find((i) => i.node_name === 'generate_content');
  const escalateInv = investigations.find((i) => i.node_name === 'escalate');
  const latestInv = investigations[investigations.length - 1];

  let paymentLinkUrl = contentInv?.response_payload?.payment_link_url || null;
  if (!paymentLinkUrl && actions[0]?.provider_ref?.includes('rzp_link:')) {
    const rawRef = actions[0].provider_ref.split('rzp_link:')[1].trim().split(' ')[0];
    if (rawRef.startsWith('order_')) {
      paymentLinkUrl = `/pay/${rawRef}`;
    } else {
      paymentLinkUrl = `https://rzp.io/i/${rawRef}`;
    }
  }
  if (paymentLinkUrl && paymentLinkUrl.includes('api.razorpay.com/v1/checkout/hosted') && paymentLinkUrl.includes('order_id=')) {
    const match = paymentLinkUrl.match(/order_id=([^&]+)/);
    if (match && match[1]) {
      paymentLinkUrl = `/pay/${match[1]}`;
    }
  }

  const isEscalated = caseData.status === 'escalated' || Boolean(escalateInv);
  const isRecovered = caseData.status === 'recovered';
  const hasActionsSent = actions.some((a) => a.status === 'sent' || a.status === 'delivered');

  const strategyConfidence = strategyInv?.confidence ? Math.round(parseFloat(strategyInv.confidence) * 100) : null;
  const recommendedAction = latestInv?.response_payload?.recommended_action || latestInv?.response_payload?.recommendation || latestInv?.response_payload?.action_type || 'Email Dunning with Razorpay Link';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'left' }}>
      
      {/* Header & Title */}
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
              <span className={`badge ${isRecovered ? 'badge-success' : isEscalated ? 'badge-error' : 'badge-info'}`}>
                {caseData.stage.toUpperCase()}
              </span>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Created: {formattedDate(caseData.created_at)}
            </span>
          </div>
        </div>

        {/* Quick Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {caseData.status === 'in_progress' && hasActionsSent && (
            <button
              onClick={handleManualVerify}
              disabled={verifyingPayment}
              className="btn btn-secondary btn-sm"
              title="Poll Razorpay Test API immediately"
            >
              {verifyingPayment ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <RefreshCw size={13} />
              )}
              Verify Razorpay Payment
            </button>
          )}

          {caseData.status === 'in_progress' && (
            <button
              onClick={handleRunAgent}
              disabled={agentRunning}
              className="btn btn-primary btn-sm"
            >
              {agentRunning ? (
                <>
                  <Loader2 size={13} className="animate-spin" /> Running Agent...
                </>
              ) : (
                <>
                  <Play size={13} fill="currentColor" /> Re-run Agent
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Hero: Automated End-to-End Recovery Flow Tracker */}
      <div
        className="card"
        style={{
          background: isRecovered 
            ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(5, 150, 105, 0.03) 100%)'
            : isEscalated 
            ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.06) 0%, rgba(185, 28, 28, 0.02) 100%)'
            : 'linear-gradient(135deg, rgba(99, 102, 241, 0.06) 0%, rgba(16, 185, 129, 0.04) 100%)',
          borderColor: isRecovered ? 'var(--color-success-border)' : isEscalated ? 'var(--color-error-border)' : 'var(--color-info-border)',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          padding: '20px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={18} color={isRecovered ? 'var(--color-success)' : 'var(--color-primary)'} />
            <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
              Automated End-to-End Recovery Pipeline
            </h3>
          </div>
          {isRecovered ? (
            <span className="badge badge-success" style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <CheckCircle2 size={12} /> REVENUE RECOVERED
            </span>
          ) : isEscalated ? (
            <span className="badge badge-error" style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <AlertOctagon size={12} /> ESCALATED TO HUMAN REVIEW
            </span>
          ) : (
            <span className="badge badge-info" style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Loader2 size={12} className="animate-spin" /> LIVE AUTONOMOUS PROGRESSION
            </span>
          )}
        </div>

        {/* Step Progression Chain */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px' }}>
          
          {/* 1. Failure Detected */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', fontSize: '12px' }}>
            <CheckCircle2 size={15} color="var(--color-success)" style={{ flexShrink: 0 }} />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontWeight: 600 }}>Failure Detected</span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{caseData.failure_reason}</span>
            </div>
          </div>

          {/* 2. Case Created */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', fontSize: '12px' }}>
            <CheckCircle2 size={15} color="var(--color-success)" style={{ flexShrink: 0 }} />
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontWeight: 600 }}>Case Created</span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>At-risk {formatCurrency(caseData.amount_at_risk, caseData.currency)}</span>
            </div>
          </div>

          {/* 3. Triage */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', fontSize: '12px' }}>
            {triageInv ? (
              <CheckCircle2 size={15} color="var(--color-success)" style={{ flexShrink: 0 }} />
            ) : !isEscalated ? (
              <Loader2 size={15} className="animate-spin" color="var(--color-info)" style={{ flexShrink: 0 }} />
            ) : (
              <div style={{ width: '15px', height: '15px', borderRadius: '50%', border: '2px dashed var(--text-muted)', flexShrink: 0 }} />
            )}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontWeight: 600 }}>Gemini Triage</span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                {triageInv?.response_payload?.category || (caseData.status === 'in_progress' ? 'Diagnosing...' : 'Pending')}
              </span>
            </div>
          </div>

          {/* 4. Strategy */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', fontSize: '12px' }}>
            {strategyInv ? (
              <CheckCircle2 size={15} color="var(--color-success)" style={{ flexShrink: 0 }} />
            ) : triageInv && !isEscalated ? (
              <Loader2 size={15} className="animate-spin" color="var(--color-info)" style={{ flexShrink: 0 }} />
            ) : (
              <div style={{ width: '15px', height: '15px', borderRadius: '50%', border: '2px dashed var(--text-muted)', flexShrink: 0 }} />
            )}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontWeight: 600 }}>Strategy Engine</span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                {strategyInv?.response_payload?.action_type || (triageInv && caseData.status === 'in_progress' ? 'Strategizing...' : 'Pending')}
              </span>
            </div>
          </div>

          {/* 5. Confidence Gate / Guardrail */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', fontSize: '12px' }}>
            {isEscalated ? (
              <ShieldCheck size={15} color="var(--color-error)" style={{ flexShrink: 0 }} />
            ) : strategyInv ? (
              <ShieldCheck size={15} color="var(--color-success)" style={{ flexShrink: 0 }} />
            ) : triageInv ? (
              <Loader2 size={15} className="animate-spin" color="var(--color-info)" style={{ flexShrink: 0 }} />
            ) : (
              <div style={{ width: '15px', height: '15px', borderRadius: '50%', border: '2px dashed var(--text-muted)', flexShrink: 0 }} />
            )}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontWeight: 600 }}>Confidence Gate</span>
              <span style={{ fontSize: '10px', color: isEscalated ? 'var(--color-error)' : 'var(--text-muted)' }}>
                {isEscalated ? 'Policy Escalation' : strategyInv ? `${strategyConfidence || 95}% Passed` : 'Pending'}
              </span>
            </div>
          </div>

          {!isEscalated ? (
            <>
              {/* 6. Content Generated */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', fontSize: '12px' }}>
                {contentInv ? (
                  <CheckCircle2 size={15} color="var(--color-success)" style={{ flexShrink: 0 }} />
                ) : strategyInv ? (
                  <Loader2 size={15} className="animate-spin" color="var(--color-info)" style={{ flexShrink: 0 }} />
                ) : (
                  <div style={{ width: '15px', height: '15px', borderRadius: '50%', border: '2px dashed var(--text-muted)', flexShrink: 0 }} />
                )}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontWeight: 600 }}>Content Drafted</span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    {contentInv ? 'AI Personalized' : strategyInv ? 'Drafting...' : 'Pending'}
                  </span>
                </div>
              </div>

              {/* 7. Payment Link Created */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', fontSize: '12px' }}>
                {paymentLinkUrl ? (
                  <CheckCircle2 size={15} color="var(--color-success)" style={{ flexShrink: 0 }} />
                ) : contentInv ? (
                  <Loader2 size={15} className="animate-spin" color="var(--color-info)" style={{ flexShrink: 0 }} />
                ) : (
                  <div style={{ width: '15px', height: '15px', borderRadius: '50%', border: '2px dashed var(--text-muted)', flexShrink: 0 }} />
                )}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontWeight: 600 }}>Razorpay Link</span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    {paymentLinkUrl ? 'Test Mode Active' : contentInv ? 'Creating Link...' : 'Pending'}
                  </span>
                </div>
              </div>

              {/* 8. Email Sent */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', fontSize: '12px' }}>
                {hasActionsSent ? (
                  <CheckCircle2 size={15} color="var(--color-success)" style={{ flexShrink: 0 }} />
                ) : contentInv ? (
                  <Loader2 size={15} className="animate-spin" color="var(--color-info)" style={{ flexShrink: 0 }} />
                ) : (
                  <div style={{ width: '15px', height: '15px', borderRadius: '50%', border: '2px dashed var(--text-muted)', flexShrink: 0 }} />
                )}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontWeight: 600 }}>Email Dispatched</span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    {hasActionsSent ? 'Delivered via SMTP' : contentInv ? 'Dispatching...' : 'Pending'}
                  </span>
                </div>
              </div>

              {/* 9. Payment Verified */}
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px', 
                padding: '8px 10px', 
                borderRadius: '6px', 
                backgroundColor: isRecovered ? 'rgba(16, 185, 129, 0.12)' : 'var(--bg-secondary)', 
                border: isRecovered ? '1px solid var(--color-success)' : '1px solid var(--border-color)', 
                fontSize: '12px' 
              }}>
                {isRecovered ? (
                  <CheckCircle2 size={15} color="var(--color-success)" style={{ flexShrink: 0 }} />
                ) : hasActionsSent ? (
                  <Loader2 size={15} className="animate-spin" color="var(--color-info)" style={{ flexShrink: 0 }} />
                ) : (
                  <div style={{ width: '15px', height: '15px', borderRadius: '50%', border: '2px dashed var(--text-muted)', flexShrink: 0 }} />
                )}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontWeight: 600 }}>Payment Verified</span>
                  <span style={{ fontSize: '10px', color: isRecovered ? 'var(--color-success)' : 'var(--text-muted)' }}>
                    {isRecovered ? 'Razorpay Verified' : hasActionsSent ? 'Awaiting Payment...' : 'Pending'}
                  </span>
                </div>
              </div>

              {/* 10. Revenue Recovered */}
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px', 
                padding: '8px 10px', 
                borderRadius: '6px', 
                backgroundColor: isRecovered ? 'rgba(16, 185, 129, 0.15)' : 'var(--bg-secondary)', 
                border: isRecovered ? '1px solid var(--color-success)' : '1px solid var(--border-color)', 
                fontSize: '12px' 
              }}>
                {isRecovered ? (
                  <CheckCircle2 size={15} color="var(--color-success)" style={{ flexShrink: 0 }} />
                ) : (
                  <div style={{ width: '15px', height: '15px', borderRadius: '50%', border: '2px dashed var(--text-muted)', flexShrink: 0 }} />
                )}
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontWeight: 600, color: isRecovered ? 'var(--color-success)' : 'var(--text-primary)' }}>
                    {isRecovered ? `${formatCurrency(caseData.financial_impact || caseData.amount_at_risk, caseData.currency)} Recovered` : 'Revenue Target'}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    {isRecovered ? 'Ledger Synced' : formatCurrency(caseData.amount_at_risk, caseData.currency)}
                  </span>
                </div>
              </div>
            </>
          ) : (
            /* Escalated Branch Indicator */
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px', borderRadius: '6px', backgroundColor: 'rgba(239, 68, 68, 0.08)', border: '1px solid var(--color-error)', fontSize: '12px', gridColumn: 'span 3' }}>
              <AlertOctagon size={16} color="var(--color-error)" style={{ flexShrink: 0 }} />
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontWeight: 600, color: 'var(--color-error)' }}>Escalation Handoff Generated</span>
                <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                  Hard decline policy automatically blocked dunning and transferred case to support team queue.
                </span>
              </div>
            </div>
          )}

        </div>

        {/* Live Payment Link Callout for Test Mode Demo */}
        {paymentLinkUrl && !isRecovered && (
          <div style={{ 
            marginTop: '4px', 
            padding: '10px 14px', 
            borderRadius: '6px', 
            backgroundColor: 'rgba(99, 102, 241, 0.05)', 
            border: '1px solid rgba(99, 102, 241, 0.2)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '10px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Mail size={16} color="var(--color-primary)" />
              <div style={{ fontSize: '12px' }}>
                <strong>Recovery Email Sent:</strong> Check your inbox or complete the payment via the test link below:
              </div>
            </div>
            <a
              href={paymentLinkUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary btn-sm"
              style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}
            >
              Open Razorpay Checkout <ExternalLink size={12} />
            </a>
          </div>
        )}

      </div>

      {/* Grid Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        
        {/* Left Column (Details, Financials, Timeline) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Financial Impact Card */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
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
            <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
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

          {/* Lifecycle Timeline */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
              Case Recovery Stage Timeline
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingLeft: '8px', borderLeft: '1px solid var(--border-color)' }}>
              
              {/* Created */}
              <div style={{ position: 'relative', paddingLeft: '16px' }}>
                <div style={{ position: 'absolute', left: '-13px', top: '4px', width: '9px', height: '9px', borderRadius: '50%', backgroundColor: 'var(--color-success)', border: '2px solid var(--bg-secondary)' }} />
                <div style={{ fontSize: '12px' }}>
                  <div style={{ fontWeight: 500 }}>Failed Payment Detected & Case Seeded</div>
                  <span style={{ color: 'var(--text-secondary)' }}>{formattedDate(caseData.created_at)}</span>
                </div>
              </div>

              {/* AI Triage */}
              {investigations.length > 0 && (
                <div style={{ position: 'relative', paddingLeft: '16px' }}>
                  <div style={{ position: 'absolute', left: '-13px', top: '4px', width: '9px', height: '9px', borderRadius: '50%', backgroundColor: 'var(--color-info)', border: '2px solid var(--bg-secondary)' }} />
                  <div style={{ fontSize: '12px' }}>
                    <div style={{ fontWeight: 500 }}>AI Investigation Triage & Strategy Execution</div>
                    <span style={{ color: 'var(--text-secondary)' }}>
                      Confidence Score: {strategyConfidence || 95}%
                    </span>
                  </div>
                </div>
              )}

              {/* Action sent */}
              {actions.length > 0 && (
                <div style={{ position: 'relative', paddingLeft: '16px' }}>
                  <div style={{ position: 'absolute', left: '-13px', top: '4px', width: '9px', height: '9px', borderRadius: '50%', backgroundColor: 'var(--color-warning)', border: '2px solid var(--bg-secondary)' }} />
                  <div style={{ fontSize: '12px' }}>
                    <div style={{ fontWeight: 500 }}>Recovery Action Dispatched ({actions[0].action_type.toUpperCase()})</div>
                    <span style={{ color: 'var(--text-secondary)' }}>Status: {actions[0].status}</span>
                  </div>
                </div>
              )}

              {/* Resolved / Resolved outcome */}
              {caseData.status !== 'in_progress' && (
                <div style={{ position: 'relative', paddingLeft: '16px' }}>
                  <div style={{ position: 'absolute', left: '-13px', top: '4px', width: '9px', height: '9px', borderRadius: '50%', backgroundColor: isRecovered ? 'var(--color-success)' : 'var(--color-error)', border: '2px solid var(--bg-secondary)' }} />
                  <div style={{ fontSize: '12px' }}>
                    <div style={{ fontWeight: 500 }}>
                      {isRecovered ? 'Payment Verified & Revenue Recovered' : `Case Resolution Reached (${caseData.status})`}
                    </div>
                    <span style={{ color: 'var(--text-secondary)' }}>{formattedDate(caseData.updated_at)}</span>
                  </div>
                </div>
              )}

            </div>
          </div>

          {/* Admin / Manual Override (Debug Accordion) */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <button
              onClick={() => setShowManualOverride(!showManualOverride)}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'none',
                border: 'none',
                color: 'var(--text-secondary)',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                padding: 0,
              }}
            >
              <span>ADMIN & MANUAL OVERRIDE (DEBUG)</span>
              {showManualOverride ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {showManualOverride && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingTop: '8px', borderTop: '1px solid var(--border-color)' }}>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                  Controls for manually forcing outcomes or resuming the LangGraph retry agent without waiting for customer actions.
                </p>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={handleResumeAgent}
                    disabled={caseData.status !== 'in_progress' || agentRunning}
                    className="btn btn-secondary btn-sm"
                    style={{ flex: 1 }}
                  >
                    Resume Retry Loop
                  </button>
                  <button
                    onClick={() => {
                      setIsRecoveredVal(true);
                      setShowOutcomeForm(true);
                    }}
                    disabled={caseData.status !== 'in_progress' || actions.length === 0}
                    className="btn btn-primary btn-sm"
                    style={{ flex: 1, backgroundColor: 'var(--color-success)', borderColor: 'var(--color-success)' }}
                  >
                    Force Recover
                  </button>
                </div>

                {showOutcomeForm && (
                  <form onSubmit={handleSubmitOutcome} style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '8px' }}>
                    <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label className="form-label" style={{ fontSize: '11px' }}>Recovered Amount ({caseData.currency})</label>
                      <input
                        type="number"
                        step="0.01"
                        className="form-input"
                        required
                        value={outcomeAmount}
                        onChange={(e) => setOutcomeAmount(parseFloat(e.target.value) || 0)}
                        style={{ fontSize: '12px', padding: '6px' }}
                      />
                    </div>
                    <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label className="form-label" style={{ fontSize: '11px' }}>Notes</label>
                      <input
                        type="text"
                        className="form-input"
                        value={outcomeNotes}
                        placeholder="Manual debug note"
                        onChange={(e) => setOutcomeNotes(e.target.value)}
                        style={{ fontSize: '12px', padding: '6px' }}
                      />
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button type="button" onClick={() => setShowOutcomeForm(false)} className="btn btn-secondary btn-sm" style={{ flex: 1 }}>
                        Cancel
                      </button>
                      <button type="submit" disabled={outcomeSubmitting} className="btn btn-primary btn-sm" style={{ flex: 1 }}>
                        {outcomeSubmitting ? 'Saving...' : 'Save'}
                      </button>
                    </div>
                  </form>
                )}
              </div>
            )}
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
              <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-info)', margin: 0 }}>
                AI Recommendation Engine
              </h3>
            </div>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)' }}>
                {recommendedAction}
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: '1.4' }}>
                {strategyInv?.response_payload?.reasoning || triageInv?.response_payload?.summary || "Automated diagnosis determined optimal dunning path."}
              </p>
            </div>
          </div>

          {/* AI Investigation Trace Preview */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
                AI Agent Trace Steps
              </h3>
              <Link to={`/recovery/cases/${id}/trace`} className="btn btn-secondary btn-sm">
                View Full Graph
              </Link>
            </div>
            
            {investigations.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                No investigation trace nodes recorded yet.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {investigations.slice(-4).reverse().map((inv) => (
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
                      {inv.response_payload?.summary || inv.response_payload?.reasoning || inv.response_payload?.finding || 'Executed node successfully'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recovery Actions Preview */}
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '13px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', margin: 0 }}>
                Recovery Actions Dispatched
              </h3>
              <Link to={`/recovery/cases/${id}/actions`} className="btn btn-secondary btn-sm">
                View Actions Log
              </Link>
            </div>

            {actions.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '16px 0' }}>
                {isEscalated ? 'No customer message dispatched (Case escalated).' : 'No recovery messages dispatched yet.'}
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
