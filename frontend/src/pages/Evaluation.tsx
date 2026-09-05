import React, { useEffect, useState, useRef } from 'react';
import {
  Play,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  TrendingUp,
  BarChart3,
  Cpu,
  Sparkles,
  Info,
  Clock,
  Layers,
  FileSpreadsheet,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';
import { formatCurrency } from '../lib/currency';

interface ScenarioStats {
  cases: number;
  valid_evaluations: number;
  api_errors: number;
  policy_overrides: number;
  decision_accuracy: number | null;
  escalation_rate: number | null;
  simulated_amount_at_risk_inr: number;
  simulated_amount_recovered_inr: number;
  simulated_recovery_rate_by_amount: number;
}

interface BenchmarkSummary {
  benchmark: string;
  generated_at: string;
  seed: number;
  cases: number;
  valid_evaluations: number;
  api_errors: number;
  policy_overrides: number;
  valid_evaluation_rate: number;
  confidence_threshold: number;
  decision_accuracy: number | null;
  escalation_rate: number | null;
  error_rate: number;
  simulated_amount_at_risk_inr: number;
  simulated_amount_recovered_inr: number;
  simulated_recovery_rate_by_amount: number;
  scenario_breakdown: Record<string, ScenarioStats>;
  important_note: string;
}

export const Evaluation: React.FC = () => {
  const [summary, setSummary] = useState<BenchmarkSummary | null>(null);
  const [latestFileName, setLatestFileName] = useState<string | null>(null);
  const [latestDate, setLatestDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [progress, setProgress] = useState({ completed: 0, total: 500, percent: 0, elapsed: 0 });
  const [historyRuns, setHistoryRuns] = useState<any[]>([]);
  const { showToast } = useToast();
  const pollIntervalRef = useRef<any>(null);

  const fetchLatest = async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const [res, runs] = await Promise.all([
        api.getLatestEvaluation(),
        api.getEvaluationRuns().catch(() => []),
      ]);
      if (res.has_result && res.summary) {
        setSummary(res.summary);
        setLatestFileName(res.file_name || null);
        setLatestDate(res.created_at || res.summary.generated_at || null);
      } else {
        setSummary(null);
      }
      setHistoryRuns(runs);
    } catch (err: any) {
      if (!quiet) showToast(err.message || 'Failed to load evaluation results', 'error');
    } finally {
      if (!quiet) setLoading(false);
    }
  };

  useEffect(() => {
    fetchLatest();
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleStartEvaluation = async (casesCount: number = 500) => {
    if (evaluating) return;
    setEvaluating(true);
    setProgress({ completed: 0, total: casesCount, percent: 0, elapsed: 0 });

    try {
      const runRes = await api.runEvaluation({ n: casesCount, concurrency: 8 });
      setActiveRunId(runRes.run_id);
      showToast(`Started synthetic evaluation of ${casesCount} cases...`, 'info');

      // Begin polling status
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

      pollIntervalRef.current = setInterval(async () => {
        try {
          const statusRes = await api.getEvaluationStatus(runRes.run_id);
          setProgress({
            completed: statusRes.completed,
            total: statusRes.total,
            percent: statusRes.progress_percentage,
            elapsed: statusRes.elapsed_seconds,
          });

          if (statusRes.status === 'completed') {
            clearInterval(pollIntervalRef.current);
            setEvaluating(false);
            if (statusRes.summary) {
              setSummary(statusRes.summary);
              setLatestDate(statusRes.completed_at || new Date().toISOString());
            } else {
              await fetchLatest(true);
            }
            showToast('500-Payment evaluation completed successfully!', 'success');
          } else if (statusRes.status === 'failed') {
            clearInterval(pollIntervalRef.current);
            setEvaluating(false);
            showToast(`Evaluation failed: ${statusRes.error || 'Unknown error'}`, 'error');
          }
        } catch {
          // ignore transient poll error
        }
      }, 1000);
    } catch (err: any) {
      setEvaluating(false);
      showToast(err.message || 'Failed to start evaluation run', 'error');
    }
  };

  const getScenarioLabel = (key: string) => {
    switch (key) {
      case 'hard_decline':
        return 'Hard Decline (Stolen / Fraud)';
      case 'soft_decline':
        return 'Soft Decline (Insufficient Funds)';
      case 'abandoned_checkout':
        return 'Abandoned Checkout';
      case 'overdue_invoice':
        return 'Overdue B2B Invoice (30+ Days)';
      default:
        return key.replace(/_/g, ' ').toUpperCase();
    }
  };

  const getScenarioGroundTruth = (key: string) => {
    return key === 'hard_decline' ? 'Escalate (Human Review)' : 'Automate (Email Recovery)';
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'left' }}>
      
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Cpu size={22} color="var(--color-primary, #6366f1)" />
            <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              500-Payment AI Evaluation
            </h2>
            <span className="badge badge-info" style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Sparkles size={11} /> Synthetic Benchmark
            </span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px', maxWidth: '750px', lineHeight: '1.4' }}>
            Large-scale benchmark evaluating the Gemini triage and strategy models against deterministic ground truth,
            strict policy guardrails, and customer response simulation across 500 failure events.
          </p>
        </div>

        {/* Primary CTA */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={() => fetchLatest(false)}
            disabled={evaluating || loading}
            className="btn btn-secondary btn-sm"
            title="Refresh latest results"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button
            onClick={() => handleStartEvaluation(500)}
            disabled={evaluating}
            className="btn btn-primary"
            style={{
              padding: '10px 20px',
              fontSize: '13px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 14px rgba(99, 102, 241, 0.25)',
            }}
          >
            {evaluating ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Evaluating... ({progress.completed}/{progress.total})
              </>
            ) : (
              <>
                <Play size={16} fill="currentColor" />
                Run 500-Payment Evaluation
              </>
            )}
          </button>
        </div>
      </div>

      {/* Synthetic Benchmark Safety & Isolation Alert */}
      <div
        style={{
          backgroundColor: 'rgba(99, 102, 241, 0.05)',
          border: '1px solid rgba(99, 102, 241, 0.2)',
          borderRadius: '8px',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
        }}
      >
        <Info size={18} color="var(--color-primary, #6366f1)" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
          <strong style={{ color: 'var(--text-primary)' }}>Synthetic Benchmark Isolation:</strong> This evaluation operates exclusively on deterministic synthetic payment data.
          No real customer payments, Razorpay Payment Links, emails, or live recovery transactions are triggered during this benchmark.
          Recovered amounts reflect <em>Simulated Amount Recovered</em> based on calibrated recovery probability models.
        </div>
      </div>

      {/* Live Evaluation Progress Card */}
      {evaluating && (
        <div
          className="card"
          style={{
            padding: '20px',
            border: '1px solid var(--color-primary, #6366f1)',
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(17, 24, 39, 0.8) 100%)',
            display: 'flex',
            flexDirection: 'column',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Loader2 size={18} className="animate-spin" color="var(--color-primary, #6366f1)" />
              <strong style={{ fontSize: '14px', color: '#fff' }}>Running 500-Payment Evaluation...</strong>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '16px' }}>
              <span>
                <Clock size={13} style={{ display: 'inline', marginRight: '4px' }} />
                {progress.elapsed.toFixed(1)}s elapsed
              </span>
              <span style={{ fontWeight: 600, color: 'var(--color-primary, #6366f1)' }}>
                {progress.completed} / {progress.total} evaluated ({progress.percent}%)
              </span>
            </div>
          </div>

          {/* Progress Bar */}
          <div style={{ width: '100%', height: '8px', backgroundColor: 'rgba(255, 255, 255, 0.08)', borderRadius: '4px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${progress.percent}%`,
                height: '100%',
                backgroundColor: 'var(--color-primary, #6366f1)',
                transition: 'width 0.3s ease',
                borderRadius: '4px',
              }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
            <span>Concurrent Gemini triage & strategy workers active (x8) {activeRunId ? `[${activeRunId}]` : ''}</span>
            <span>Policy guardrails active</span>
          </div>
        </div>
      )}

      {/* Main Results View */}
      {loading && !evaluating ? (
        <div style={{ display: 'flex', height: '40vh', alignItems: 'center', justifyContent: 'center' }}>
          <Loader2 size={32} className="animate-spin" color="var(--text-secondary)" />
        </div>
      ) : !summary ? (
        <div className="card" style={{ padding: '60px 20px', textAlign: 'center' }}>
          <BarChart3 size={48} color="var(--text-muted)" style={{ margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
            No evaluation has been run yet
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '420px', margin: '0 auto 20px' }}>
            Click the button below to execute the 500-payment synthetic benchmark and evaluate the Gemini recovery decision engine.
          </p>
          <button
            onClick={() => handleStartEvaluation(500)}
            className="btn btn-primary"
            style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}
          >
            <Play size={15} fill="currentColor" /> Run 500-Payment Evaluation
          </button>
        </div>
      ) : (
        <>
          {/* Top Metric Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '14px' }}>
            
            {/* 1. Cases Evaluated */}
            <div className="card" style={{ padding: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Total Evaluated
                </span>
                <Layers size={16} color="var(--color-info)" />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-primary)' }}>
                {summary.cases}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                {summary.valid_evaluations} Valid ({((summary.valid_evaluation_rate || 1) * 100).toFixed(1)}%)
              </div>
            </div>

            {/* 2. Decision Accuracy */}
            <div className="card" style={{ padding: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Decision Accuracy
                </span>
                <CheckCircle2 size={16} color="var(--color-success)" />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-success)' }}>
                {summary.decision_accuracy !== null ? `${(summary.decision_accuracy * 100).toFixed(1)}%` : 'N/A'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Ground truth alignment rate
              </div>
            </div>

            {/* 3. Escalation Rate */}
            <div className="card" style={{ padding: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Escalation Rate
                </span>
                <ShieldCheck size={16} color="var(--color-warning)" />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--color-warning)' }}>
                {summary.escalation_rate !== null ? `${(summary.escalation_rate * 100).toFixed(1)}%` : 'N/A'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                {summary.policy_overrides} Policy Guardrail Blocks
              </div>
            </div>

            {/* 4. Simulated Amount At Risk */}
            <div className="card" style={{ padding: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Simulated At Risk
                </span>
                <AlertTriangle size={16} color="var(--color-error)" />
              </div>
              <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)' }}>
                {formatCurrency(summary.simulated_amount_at_risk_inr * 100, 'INR')}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                Across 4 failure profiles
              </div>
            </div>

            {/* 5. Simulated Amount Recovered */}
            <div
              className="card"
              style={{
                padding: '16px',
                background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(17, 24, 39, 0.6) 100%)',
                borderColor: 'var(--color-success-border, rgba(16, 185, 129, 0.3))',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', color: 'var(--color-success)', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>
                  Simulated Recovered
                </span>
                <TrendingUp size={16} color="var(--color-success)" />
              </div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: 'var(--color-success)' }}>
                {formatCurrency(summary.simulated_amount_recovered_inr * 100, 'INR')}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-success)', marginTop: '4px', fontWeight: 600 }}>
                {((summary.simulated_recovery_rate_by_amount || 0) * 100).toFixed(1)}% Simulated Recovery Rate
              </div>
            </div>

          </div>

          {/* Scenario Breakdown Section */}
          <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                  Scenario Breakdown & Policy Guardrail Verification
                </h3>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                  Comparing Gemini decisions and guardrail enforcement across 4 distinct payment failure classes.
                </p>
              </div>
              {latestDate && (
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Generated: {new Date(latestDate).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                  {latestFileName ? ` (${latestFileName})` : ''}
                </span>
              )}
            </div>

            {/* Scenario Table */}
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '10px 12px', fontWeight: 600 }}>Failure Scenario</th>
                    <th style={{ padding: '10px 12px', fontWeight: 600 }}>Ground Truth</th>
                    <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'center' }}>Cases</th>
                    <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'center' }}>Decision Accuracy</th>
                    <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'center' }}>Escalation Rate</th>
                    <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'right' }}>Simulated At-Risk</th>
                    <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'right' }}>Simulated Recovered</th>
                    <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'right' }}>Simulated Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.scenario_breakdown &&
                    Object.entries(summary.scenario_breakdown).map(([key, sc]) => (
                      <tr
                        key={key}
                        style={{
                          borderBottom: '1px solid var(--border-color)',
                          backgroundColor: key === 'hard_decline' ? 'rgba(239, 68, 68, 0.02)' : 'transparent',
                        }}
                      >
                        <td style={{ padding: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span>{getScenarioLabel(key)}</span>
                            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                              {key}
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: '12px' }}>
                          <span
                            className={`badge ${
                              key === 'hard_decline' ? 'badge-error' : 'badge-info'
                            }`}
                            style={{ fontSize: '10px' }}
                          >
                            {getScenarioGroundTruth(key)}
                          </span>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          <strong>{sc.cases}</strong>
                          {sc.api_errors > 0 && (
                            <span style={{ fontSize: '10px', color: 'var(--color-error)', display: 'block' }}>
                              ({sc.api_errors} err)
                            </span>
                          )}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          <span style={{ color: 'var(--color-success)', fontWeight: 600 }}>
                            {sc.decision_accuracy !== null ? `${(sc.decision_accuracy * 100).toFixed(1)}%` : 'N/A'}
                          </span>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'center' }}>
                          <span style={{ fontWeight: 600, color: sc.escalation_rate && sc.escalation_rate > 0 ? 'var(--color-warning)' : 'var(--text-secondary)' }}>
                            {sc.escalation_rate !== null ? `${(sc.escalation_rate * 100).toFixed(1)}%` : '0.0%'}
                          </span>
                        </td>
                        <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>
                          {formatCurrency(sc.simulated_amount_at_risk_inr * 100, 'INR')}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'right', fontFamily: 'var(--font-mono)', color: 'var(--color-success)', fontWeight: 600 }}>
                          {formatCurrency(sc.simulated_amount_recovered_inr * 100, 'INR')}
                        </td>
                        <td style={{ padding: '12px', textAlign: 'right', fontWeight: 700, color: 'var(--color-success)' }}>
                          {((sc.simulated_recovery_rate_by_amount || 0) * 100).toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Narrative / Methodology Visual Pipeline */}
          <div
            className="card"
            style={{
              padding: '20px',
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
              <Zap size={16} color="var(--color-primary, #6366f1)" />
              <h3 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                Buildathon Demonstration Architecture
              </h3>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
              <div style={{ padding: '12px', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Step 1: Ingestion</span>
                <h4 style={{ fontSize: '13px', fontWeight: 600, margin: '4px 0', color: 'var(--text-primary)' }}>500 Synthetic Cases</h4>
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: 0 }}>Deterministic failure distribution across cards, UPI & bank transfers.</p>
              </div>

              <div style={{ padding: '12px', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Step 2: AI Reasoning</span>
                <h4 style={{ fontSize: '13px', fontWeight: 600, margin: '4px 0', color: 'var(--text-primary)' }}>Gemini Triage & Strategy</h4>
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: 0 }}>Identical prompt pipeline used in live production recovery.</p>
              </div>

              <div style={{ padding: '12px', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Step 3: Guardrails</span>
                <h4 style={{ fontSize: '13px', fontWeight: 600, margin: '4px 0', color: 'var(--text-primary)' }}>Policy Enforcement</h4>
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: 0 }}>Hard declines (stolen cards) 100% intercepted & escalated.</p>
              </div>

              <div style={{ padding: '12px', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>Step 4: Simulation</span>
                <h4 style={{ fontSize: '13px', fontWeight: 600, margin: '4px 0', color: 'var(--text-primary)' }}>Simulated Response</h4>
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: 0 }}>Empirical customer recovery probabilities evaluated.</p>
              </div>

              <div style={{ padding: '12px', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
                <span style={{ fontSize: '10px', color: 'var(--color-success)', textTransform: 'uppercase', fontWeight: 700 }}>Step 5: Validation</span>
                <h4 style={{ fontSize: '13px', fontWeight: 600, margin: '4px 0', color: 'var(--color-success)' }}>Live Proof of Recovery</h4>
                <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: 0 }}>Follow up with 1 real live Fault Lab Razorpay test-mode transaction.</p>
              </div>
            </div>
          </div>

          {/* Historical Batch Runs */}
          {historyRuns.length > 0 && (
            <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <FileSpreadsheet size={15} color="var(--text-secondary)" />
                <h4 style={{ fontSize: '13px', fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>
                  Historical Batch Benchmark Artifacts ({historyRuns.length})
                </h4>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {historyRuns.map((r, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '6px 10px',
                      borderRadius: '6px',
                      backgroundColor: 'var(--bg-secondary)',
                      border: '1px solid var(--border-color)',
                      fontSize: '11px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                    }}
                  >
                    <span style={{ fontFamily: 'var(--font-mono)' }}>{r.file_name}</span>
                    <span style={{ color: 'var(--color-success)', fontWeight: 600 }}>
                      {((r.simulated_recovery_rate || 0) * 100).toFixed(1)}% Rec
                    </span>
                    <span style={{ color: 'var(--text-muted)' }}>
                      {new Date(r.created_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

    </div>
  );
};
