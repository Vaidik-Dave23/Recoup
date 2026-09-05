import React, { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { CheckCircle2, ShieldCheck, AlertCircle, Loader2, CreditCard, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import { formatCurrency } from '../lib/currency';

declare global {
  interface Window {
    Razorpay: any;
  }
}

export const PayCheckout: React.FC = () => {
  const { orderId } = useParams<{ orderId: string }>();
  const [checkoutInfo, setCheckoutInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPaid, setIsPaid] = useState(false);
  const [paymentDetails, setPaymentDetails] = useState<any>(null);
  const [sdkReady, setSdkReady] = useState(false);
  const hasAutoOpened = useRef(false);

  useEffect(() => {
    // Dynamically inject Razorpay Checkout script
    if (!window.Razorpay) {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      script.onload = () => setSdkReady(true);
      script.onerror = () => setError('Failed to load Razorpay Checkout SDK');
      document.body.appendChild(script);
    } else {
      setSdkReady(true);
    }
  }, []);

  useEffect(() => {
    if (!orderId) return;
    const fetchInfo = async () => {
      setLoading(true);
      try {
        const info = await api.getCheckoutInfo(orderId);
        setCheckoutInfo(info);
        if (info.status === 'paid' || (info.amount_paid && info.amount_paid > 0)) {
          setIsPaid(true);
        }
      } catch (err: any) {
        setError(err.message || 'Order could not be loaded');
      } finally {
        setLoading(false);
      }
    };
    fetchInfo();
  }, [orderId]);

  const launchRazorpay = () => {
    if (!window.Razorpay || !checkoutInfo) return;

    const options = {
      key: checkoutInfo.key_id,
      amount: checkoutInfo.amount,
      currency: checkoutInfo.currency || 'INR',
      name: 'Recoup Recovery',
      description: checkoutInfo.description || 'Invoice Recovery Payment',
      order_id: checkoutInfo.order_id,
      prefill: {
        name: checkoutInfo.customer_name || 'Customer',
        email: checkoutInfo.customer_email || '',
      },
      theme: {
        color: '#6366f1',
      },
      handler: function (response: any) {
        setIsPaid(true);
        setPaymentDetails(response);
      },
      modal: {
        ondismiss: function () {
          // Modal closed
        },
      },
    };

    const rzp = new window.Razorpay(options);
    rzp.on('payment.failed', function (resp: any) {
      setError(`Payment failed: ${resp.error?.description || 'Authorization failed'}`);
    });
    rzp.open();
  };

  // Auto-launch checkout modal once when data and SDK are ready
  useEffect(() => {
    if (sdkReady && checkoutInfo && !isPaid && !hasAutoOpened.current) {
      hasAutoOpened.current = true;
      const timer = setTimeout(() => {
        launchRazorpay();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [sdkReady, checkoutInfo, isPaid]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-primary, #090d16)' }}>
        <div style={{ textAlign: 'center' }}>
          <Loader2 size={36} className="animate-spin" color="var(--color-primary, #6366f1)" />
          <p style={{ marginTop: '16px', color: 'var(--text-secondary, #9ca3af)', fontSize: '14px' }}>Loading secure checkout...</p>
        </div>
      </div>
    );
  }

  if (error && !checkoutInfo) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-primary, #090d16)', padding: '20px' }}>
        <div className="card" style={{ maxWidth: '440px', width: '100%', textAlign: 'center', padding: '32px' }}>
          <AlertCircle size={40} color="var(--color-error, #ef4444)" style={{ margin: '0 auto 16px' }} />
          <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary, #fff)', marginBottom: '8px' }}>Checkout Unavailable</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary, #9ca3af)', marginBottom: '24px' }}>{error}</p>
          <Link to="/" className="btn btn-secondary" style={{ width: '100%', display: 'inline-block' }}>
            Return to Recoup
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', backgroundColor: 'var(--bg-primary, #090d16)', padding: '20px' }}>
      <div
        className="card"
        style={{
          maxWidth: '460px',
          width: '100%',
          padding: '32px',
          boxShadow: '0 20px 25px -5px rgba(0,0,0,0.5), 0 10px 10px -5px rgba(0,0,0,0.4)',
          borderRadius: '12px',
          textAlign: 'center',
          border: '1px solid var(--border-color, #1f2937)',
        }}
      >
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 12px', borderRadius: '9999px', background: 'rgba(99, 102, 241, 0.12)', border: '1px solid rgba(99, 102, 241, 0.3)', color: '#818cf8', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', marginBottom: '16px' }}>
          <ShieldCheck size={13} /> Razorpay Test Mode
        </div>

        <h1 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary, #fff)', marginBottom: '6px' }}>
          {isPaid ? 'Payment Confirmed' : 'Invoice Payment Recovery'}
        </h1>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary, #9ca3af)', marginBottom: '24px' }}>
          {checkoutInfo?.description || 'Complete your transaction securely via Razorpay Test Mode'}
        </p>

        {isPaid ? (
          <div style={{ animation: 'fadeIn 0.4s ease-in-out' }}>
            <div style={{ width: '64px', height: '64px', borderRadius: '50%', backgroundColor: 'rgba(16, 185, 129, 0.15)', border: '2px solid var(--color-success, #10b981)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <CheckCircle2 size={36} color="var(--color-success, #10b981)" />
            </div>
            
            <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--color-success, #10b981)', marginBottom: '8px' }}>
              Payment Completed!
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary, #9ca3af)', marginBottom: '20px', lineHeight: '1.5' }}>
              Thank you! Your payment has been authorized in Razorpay Test Mode. Recoup AI has automatically verified this transaction and marked the recovery case as complete.
            </p>

            <div style={{ backgroundColor: 'var(--bg-secondary, #111827)', border: '1px solid var(--border-color, #1f2937)', borderRadius: '8px', padding: '16px', textAlign: 'left', fontSize: '12px', marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-secondary, #9ca3af)' }}>Amount Paid:</span>
                <span style={{ fontWeight: 600, color: '#fff' }}>{formatCurrency(checkoutInfo?.amount || 0, checkoutInfo?.currency || 'INR')}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ color: 'var(--text-secondary, #9ca3af)' }}>Order ID:</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{orderId}</span>
              </div>
              {paymentDetails?.razorpay_payment_id && (
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary, #9ca3af)' }}>Payment Ref:</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-success, #10b981)' }}>{paymentDetails.razorpay_payment_id}</span>
                </div>
              )}
            </div>

            <Link to="/dashboard" className="btn btn-primary" style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
              <span>Back to Dashboard</span> <ArrowRight size={14} />
            </Link>
          </div>
        ) : (
          <div>
            <div style={{ backgroundColor: 'var(--bg-secondary, #111827)', border: '1px solid var(--border-color, #1f2937)', borderRadius: '8px', padding: '20px', marginBottom: '20px' }}>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary, #9ca3af)', marginBottom: '4px', letterSpacing: '0.05em' }}>
                Amount Due
              </div>
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-primary, #fff)' }}>
                {formatCurrency(checkoutInfo?.amount || 0, checkoutInfo?.currency || 'INR')}
              </div>
            </div>

            <div style={{ textAlign: 'left', fontSize: '12px', display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid var(--border-color, #1f2937)' }}>
                <span style={{ color: 'var(--text-secondary, #9ca3af)' }}>Order ID:</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{orderId}</span>
              </div>
              {checkoutInfo?.customer_name && (
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '6px', borderBottom: '1px solid var(--border-color, #1f2937)' }}>
                  <span style={{ color: 'var(--text-secondary, #9ca3af)' }}>Customer:</span>
                  <span>{checkoutInfo.customer_name}</span>
                </div>
              )}
              {checkoutInfo?.customer_email && (
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary, #9ca3af)' }}>Email:</span>
                  <span>{checkoutInfo.customer_email}</span>
                </div>
              )}
            </div>

            <button
              onClick={launchRazorpay}
              disabled={!sdkReady}
              className="btn btn-primary"
              style={{ width: '100%', padding: '12px 20px', fontSize: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
            >
              <CreditCard size={16} /> Pay with Razorpay (Test Mode)
            </button>

            <p style={{ fontSize: '11px', color: 'var(--text-secondary, #9ca3af)', marginTop: '16px' }}>
              ⚡ Simulated payment in Razorpay sandbox. No actual funds are transferred.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
