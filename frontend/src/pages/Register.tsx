import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Eye, EyeOff, Loader2, Lock, Mail, User, Briefcase } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';

interface RegisterProps {
  onRegisterSuccess: (user: any) => void;
}

export const Register: React.FC<RegisterProps> = ({ onRegisterSuccess }) => {
  const [businessName, setBusinessName] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { showToast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!businessName || !name || !email || !password || !confirmPassword) {
      showToast('Please fill in all fields', 'error');
      return;
    }

    if (password.length < 8) {
      showToast('Password must be at least 8 characters long', 'error');
      return;
    }

    if (password !== confirmPassword) {
      showToast('Passwords do not match', 'error');
      return;
    }

    setLoading(true);
    try {
      const response = await api.register({
        name,
        email,
        password,
        business_name: businessName,
      });
      
      onRegisterSuccess(response.user);
      showToast('Merchant account registered successfully!', 'success');
      navigate('/dashboard');
    } catch (error: any) {
      showToast(error.message || 'Registration failed. Try again.', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-primary)',
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '440px',
          padding: '32px',
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 600, marginBottom: '6px' }}>Create Recoup Account</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Set up your autonomous AI dunning loop in minutes
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="form-group" style={{ marginBottom: '12px' }}>
            <label className="form-label">Business Name</label>
            <div style={{ position: 'relative' }}>
              <Briefcase
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '12px', top: '13px' }}
              />
              <input
                type="text"
                className="form-input"
                placeholder="Acme Corp"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                style={{ paddingLeft: '38px' }}
                required
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: '12px' }}>
            <label className="form-label">Contact Name</label>
            <div style={{ position: 'relative' }}>
              <User
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '12px', top: '13px' }}
              />
              <input
                type="text"
                className="form-input"
                placeholder="Vaidik Dave"
                value={name}
                onChange={(e) => setName(e.target.value)}
                style={{ paddingLeft: '38px' }}
                required
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: '12px' }}>
            <label className="form-label">Work Email</label>
            <div style={{ position: 'relative' }}>
              <Mail
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '12px', top: '13px' }}
              />
              <input
                type="email"
                className="form-input"
                placeholder="you@acme.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{ paddingLeft: '38px' }}
                required
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: '12px' }}>
            <label className="form-label">Password (Min 8 chars)</label>
            <div style={{ position: 'relative' }}>
              <Lock
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '12px', top: '13px' }}
              />
              <input
                type={showPassword ? 'text' : 'password'}
                className="form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingLeft: '38px', paddingRight: '40px' }}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '12px',
                  top: '12px',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: '16px' }}>
            <label className="form-label">Confirm Password</label>
            <div style={{ position: 'relative' }}>
              <Lock
                size={16}
                color="var(--text-muted)"
                style={{ position: 'absolute', left: '12px', top: '13px' }}
              />
              <input
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                style={{ paddingLeft: '38px' }}
                required
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary" style={{ padding: '10px' }} disabled={loading}>
            {loading ? <Loader2 size={16} className="animate-spin" /> : 'Create Account'}
          </button>
        </form>

        <div style={{ marginTop: '24px', textAlign: 'center', fontSize: '13px', color: 'var(--text-secondary)' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
};
