import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, ShieldCheck, Cpu, RefreshCcw, Landmark } from 'lucide-react';

export const Home: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-primary)',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '60px 24px',
        textAlign: 'center',
      }}
    >
      {/* Brand Header */}
      <header
        style={{
          width: '100%',
          maxWidth: '1000px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '80px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontWeight: 700, fontSize: '20px', letterSpacing: '-0.03em' }}>Recoup</span>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={() => navigate('/login')} className="btn btn-secondary btn-sm">
            Sign In
          </button>
          <button onClick={() => navigate('/register')} className="btn btn-primary btn-sm">
            Get Started
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ width: '100%', maxWidth: '900px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {/* Hero Section */}
        <div style={{ marginBottom: '60px' }}>
          <h1
            style={{
              fontSize: '48px',
              lineHeight: '1.1',
              fontWeight: 700,
              letterSpacing: '-0.04em',
              marginBottom: '20px',
              maxWidth: '750px',
              marginInline: 'auto',
            }}
          >
            Agentic Revenue Recovery for Modern Merchants
          </h1>
          <p
            style={{
              fontSize: '16px',
              color: 'var(--text-secondary)',
              maxWidth: '560px',
              marginInline: 'auto',
              marginBottom: '32px',
              lineHeight: '1.6',
            }}
          >
            Recoup orchestrates autonomous agents that detect failed payments, decide on personalized recovery strategies, and execute dunning actions through live channels.
          </p>
          <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
            <button onClick={() => navigate('/register')} className="btn btn-primary" style={{ padding: '12px 24px', fontSize: '14px' }}>
              Start Recovering Revenue <ArrowRight size={16} />
            </button>
            <button onClick={() => navigate('/login')} className="btn btn-secondary" style={{ padding: '12px 24px', fontSize: '14px' }}>
              Sign In to Control Center
            </button>
          </div>
        </div>

        {/* The Recovery Loop Visualizer */}
        <div
          style={{
            width: '100%',
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            padding: '40px',
            marginBottom: '80px',
            position: 'relative',
          }}
        >
          <h3 style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '24px' }}>
            Active Autonomous Recovery Loop
          </h3>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              maxWidth: '680px',
              marginInline: 'auto',
              position: 'relative',
              flexWrap: 'wrap',
              gap: '24px',
            }}
          >
            {/* Step 1: Detect */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '120px' }}>
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-error-bg)',
                  border: '1px solid var(--color-error-border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '12px',
                }}
              >
                <ShieldCheck size={20} color="var(--color-error)" />
              </div>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>At Risk</span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Payment Failed</span>
            </div>

            <ArrowRight size={18} color="var(--border-color)" style={{ marginTop: '-20px' }} />

            {/* Step 2: Decide */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '120px' }}>
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-info-bg)',
                  border: '1px solid var(--color-info-border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '12px',
                }}
              >
                <Cpu size={20} color="var(--color-info)" />
              </div>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>AI Agent</span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Triage & Strategize</span>
            </div>

            <ArrowRight size={18} color="var(--border-color)" style={{ marginTop: '-20px' }} />

            {/* Step 3: Act */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '120px' }}>
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-warning-bg)',
                  border: '1px solid var(--color-warning-border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '12px',
                }}
              >
                <RefreshCcw size={20} color="var(--color-warning)" />
              </div>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>Recovery Action</span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Email / SMS / Retry</span>
            </div>

            <ArrowRight size={18} color="var(--border-color)" style={{ marginTop: '-20px' }} />

            {/* Step 4: Recovered */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '120px' }}>
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-success-bg)',
                  border: '1px solid var(--color-success-border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '12px',
                }}
              >
                <Landmark size={20} color="var(--color-success)" />
              </div>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>Recovered</span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Funds Restored</span>
            </div>
          </div>
        </div>

        {/* Value Prop Columns */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '32px', textAlign: 'left', width: '100%', marginBottom: '80px' }}>
          <div>
            <h4 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '8px' }}>Detect Failures In Real Time</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.5' }}>
              Listen directly to Razorpay payment events. Overdue invoices and abandoned checkouts are triaged instantly.
            </p>
          </div>
          <div>
            <h4 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '8px' }}>Contextual Decision Engine</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.5' }}>
              Gemini LLM checks customer histories and declination reasoning (e.g. stolen card vs bank timeout) before executing recovery channels.
            </p>
          </div>
          <div>
            <h4 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '8px' }}>Dunning & Auto-Retry Loop</h4>
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', lineHeight: '1.5' }}>
              Executes smart communications and hooks back to Razorpay payments to trigger automated transaction retries.
            </p>
          </div>
        </div>

        {/* Proof of Value Summary */}
        <div style={{ display: 'flex', justifyContent: 'space-around', width: '100%', borderTop: '1px solid var(--border-color)', paddingTop: '40px', color: 'var(--text-secondary)' }}>
          <div>
            <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>94%</div>
            <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>AI Triage Confidence</div>
          </div>
          <div>
            <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>&lt; 3 min</div>
            <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Mean Recovery Initiation</div>
          </div>
          <div>
            <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>INR 4,999</div>
            <div style={{ fontSize: '12px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Real-time Case Testing</div>
          </div>
        </div>
      </main>
    </div>
  );
};
