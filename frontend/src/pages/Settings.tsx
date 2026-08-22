import React, { useEffect, useState } from 'react';
import { Loader2, Settings as SettingsIcon, Users, User, Mail, Key } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';

interface SettingsProps {
  user: any;
  onUserUpdate: (profile: any) => void;
}

export const Settings: React.FC<SettingsProps> = ({ user, onUserUpdate }) => {
  const [activeTab, setActiveTab] = useState<'merchant' | 'users' | 'profile'>('merchant');
  const [merchant, setMerchant] = useState<any>(null);
  const [teamUsers, setTeamUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Editable fields
  const [merchantName, setMerchantName] = useState('');
  const [businessName, setBusinessName] = useState('');

  const { showToast } = useToast();

  const fetchSettingsData = async () => {
    setLoading(true);
    try {
      const [m, usersList] = await Promise.all([
        api.getMerchant() as Promise<any>,
        api.getMerchantUsers().catch(() => []),
      ]);
      setMerchant(m);
      setTeamUsers(usersList);
      
      setMerchantName(m.name || '');
      setBusinessName(m.business_name || '');
    } catch (err: any) {
      showToast(err.message || 'Failed to load settings', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettingsData();
  }, []);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await api.updateMerchant({
        name: merchantName,
        business_name: businessName,
      }) as any;
      setMerchant((prev: any) => ({ ...prev, ...updated }));
      
      // Update global user state in App.tsx
      const meProfile = await api.getMe();
      onUserUpdate(meProfile);
      
      showToast('Settings saved successfully', 'success');
    } catch (err: any) {
      showToast(err.message || 'Failed to save merchant settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '60vh', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 size={32} className="animate-spin" color="var(--text-secondary)" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'left' }}>
      {/* Title */}
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: 600 }}>System Configuration</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
          Manage your business credentials, team access, and dunning retry channel integration statuses.
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
        <button
          onClick={() => setActiveTab('merchant')}
          className={`btn ${activeTab === 'merchant' ? 'btn-primary' : 'btn-ghost'} btn-sm`}
        >
          <SettingsIcon size={14} /> Merchant Settings
        </button>
        <button
          onClick={() => setActiveTab('users')}
          className={`btn ${activeTab === 'users' ? 'btn-primary' : 'btn-ghost'} btn-sm`}
        >
          <Users size={14} /> Team & Access ({teamUsers.length})
        </button>
        <button
          onClick={() => setActiveTab('profile')}
          className={`btn ${activeTab === 'profile' ? 'btn-primary' : 'btn-ghost'} btn-sm`}
        >
          <User size={14} /> My Profile
        </button>
      </div>

      {/* Tab Content */}
      <div style={{ marginTop: '8px' }}>
        {/* Tab 1: Merchant Settings */}
        {activeTab === 'merchant' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* Form */}
            <form onSubmit={handleUpdateProfile} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '600px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Business Profile</h3>
              
              <div className="form-group">
                <label className="form-label">Merchant Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={merchantName}
                  onChange={(e) => setMerchantName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Registered Business Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={businessName}
                  onChange={(e) => setBusinessName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Plan Level</label>
                <input
                  type="text"
                  className="form-input"
                  value={merchant?.plan.toUpperCase()}
                  style={{ textTransform: 'uppercase', color: 'var(--text-muted)', cursor: 'not-allowed' }}
                  disabled
                />
              </div>

              <button type="submit" disabled={saving} className="btn btn-primary" style={{ width: 'fit-content', alignSelf: 'flex-start' }}>
                {saving ? <Loader2 size={14} className="animate-spin" /> : 'Save Changes'}
              </button>
            </form>

            {/* Dunning Integration Channels */}
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Dunning Integration Channels</h3>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
                {/* Channel 1: Email */}
                <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Mail size={16} color="var(--color-info)" />
                      <span style={{ fontWeight: 600 }}>Email (SMTP)</span>
                    </div>
                    <span className={`badge ${merchant?.channels?.email?.configured ? 'badge-success' : 'badge-warning'}`}>
                      {merchant?.channels?.email?.status}
                    </span>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Dispatches recovery dunning notices via Gmail / Custom SMTP server coordinates.
                  </p>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Provider: {merchant?.channels?.email?.provider}
                  </div>
                </div>

                {/* Channel 2: Twilio SMS */}
                <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Mail size={16} color="var(--color-warning)" />
                      <span style={{ fontWeight: 600 }}>SMS (Twilio)</span>
                    </div>
                    <span className={`badge ${merchant?.channels?.sms?.configured ? 'badge-success' : 'badge-error'}`}>
                      {merchant?.channels?.sms?.status}
                    </span>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Sends SMS text reminders directly to mobile customer phones to nudge retry payments.
                  </p>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Provider: {merchant?.channels?.sms?.provider}
                  </div>
                </div>

                {/* Channel 3: Razorpay Retry */}
                <div style={{ border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Key size={16} color="var(--color-success)" />
                      <span style={{ fontWeight: 600 }}>Razorpay Client</span>
                    </div>
                    <span className={`badge ${merchant?.channels?.razorpay_retry?.configured ? 'badge-success' : 'badge-error'}`}>
                      {merchant?.channels?.razorpay_retry?.status}
                    </span>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Auto-sends trigger transactions directly to the Razorpay checkout endpoint on dunning intervals.
                  </p>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Provider: {merchant?.channels?.razorpay_retry?.provider}
                  </div>
                </div>

              </div>
            </div>

          </div>
        )}

        {/* Tab 2: Team Members */}
        {activeTab === 'users' && (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Team Member</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Account Created</th>
                  <th>Last login</th>
                </tr>
              </thead>
              <tbody>
                {teamUsers.map((teamUser) => (
                  <tr key={teamUser.id}>
                    <td style={{ fontWeight: 600 }}>{teamUser.name}</td>
                    <td style={{ color: 'var(--text-secondary)' }}>{teamUser.email}</td>
                    <td>
                      <span className="badge badge-info" style={{ textTransform: 'uppercase', fontSize: '10px' }}>
                        {teamUser.role}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${teamUser.status === 'active' ? 'badge-success' : 'badge-error'}`}>
                        {teamUser.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {new Date(teamUser.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {teamUser.last_login_at ? new Date(teamUser.last_login_at).toLocaleString() : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 3: Profile Settings */}
        {activeTab === 'profile' && (
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '600px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600 }}>My Operator Details</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Name</span>
                <span>{user?.name}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Operator Email</span>
                <span>{user?.email}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>System Role</span>
                <span style={{ textTransform: 'uppercase', fontWeight: 500 }}>{user?.role}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ color: 'var(--text-muted)' }}>User UUID</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-secondary)' }}>{user?.id}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
