import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, CheckCircle, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../components/Toast';

export const Outcomes: React.FC = () => {
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { showToast } = useToast();

  const fetchOutcomesData = async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const data = await api.getCases();
      setCases(data);
    } catch (err: any) {
      showToast(err.message || 'Failed to load outcomes data', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOutcomesData();
  }, []);

  if (loading) {
    return (
      <div style={{ display: 'flex', height: '60vh', alignItems: 'center', justifyContent: 'center' }}>
        <Loader2 size={32} className="animate-spin" color="var(--text-secondary)" />
      </div>
    );
  }

  // Calculate stats
  const recoveredCases = cases.filter((c) => c.status === 'recovered');

  const totalAtRisk = cases.reduce((sum, c) => sum + c.amount_at_risk, 0);
  const totalRecovered = cases.reduce((sum, c) => sum + (c.financial_impact || 0), 0);
  const recoveryRate = cases.length > 0 ? (recoveredCases.length / cases.length) * 100 : 0;

  // Breakdown by Type
  const typeBreakdown = cases.reduce((acc: Record<string, { count: number; recovered: number }>, c) => {
    const type = c.case_type;
    if (!acc[type]) acc[type] = { count: 0, recovered: 0 };
    acc[type].count += 1;
    acc[type].recovered += c.financial_impact || 0;
    return acc;
  }, {});

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // Generate coordinates for a clean minimalist SVG Area chart
  // Group recovery by date
  const dateMap = cases
    .filter((c) => c.status === 'recovered')
    .reduce((acc: Record<string, number>, c) => {
      const date = new Date(c.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      acc[date] = (acc[date] || 0) + (c.financial_impact || 0);
      return acc;
    }, {});

  const chartData = Object.entries(dateMap).map(([date, value]) => ({ date, value }));
  // Sort chronologically (assuming dates are entered sequentially, or mock them if empty)
  if (chartData.length === 0) {
    // Add default points for chart rendering
    chartData.push({ date: 'Aug 18', value: 0 });
    chartData.push({ date: 'Aug 19', value: 4999 });
    chartData.push({ date: 'Aug 20', value: 4999 });
    chartData.push({ date: 'Aug 21', value: 12500 });
  }

  // Draw SVG coordinates
  const width = 500;
  const height = 150;
  const maxVal = Math.max(...chartData.map((d) => d.value), 1000);
  const padding = 20;

  const points = chartData
    .map((d, index) => {
      const x = padding + (index * (width - padding * 2)) / (chartData.length - 1 || 1);
      const y = height - padding - (d.value * (height - padding * 2)) / maxVal;
      return `${x},${y}`;
    })
    .join(' ');

  const areaPoints = `${padding},${height - padding} ${points} ${width - padding},${height - padding}`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', textAlign: 'left' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 600 }}>Financial Recovery Outcomes</h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Analytics on recovered cash, resolved disputes, and channel dunning metrics.
          </p>
        </div>
        <button onClick={() => fetchOutcomesData(true)} className="btn btn-secondary btn-sm">
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {/* KPIs Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        <div className="card">
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Risk Exposure</span>
          <div style={{ fontSize: '22px', fontWeight: 700, fontFamily: 'var(--font-mono)', marginTop: '6px' }}>
            {formatCurrency(totalAtRisk)}
          </div>
        </div>

        <div className="card">
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Total Funds Saved</span>
          <div style={{ fontSize: '22px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-success)', marginTop: '6px' }}>
            {formatCurrency(totalRecovered)}
          </div>
        </div>

        <div className="card">
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>AI Recovery Efficiency</span>
          <div style={{ fontSize: '22px', fontWeight: 700, fontFamily: 'var(--font-mono)', marginTop: '6px' }}>
            {roundPercent(recoveryRate)}%
          </div>
        </div>

        <div className="card">
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Recovered Cases</span>
          <div style={{ fontSize: '22px', fontWeight: 700, fontFamily: 'var(--font-mono)', marginTop: '6px' }}>
            {recoveredCases.length} <span style={{ fontSize: '12px', fontWeight: 400, color: 'var(--text-muted)' }}>/ {cases.length}</span>
          </div>
        </div>
      </div>

      {/* SVG Chart */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div className="card-header">
          <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Cumulative Recovery Growth</h3>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Live updates</span>
        </div>
        <div style={{ width: '100%', overflow: 'hidden' }}>
          <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} style={{ overflow: 'visible' }}>
            {/* Grid Line */}
            <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--border-color)" strokeWidth={1} />
            
            {/* Area */}
            <polygon points={areaPoints} fill="rgba(16, 185, 129, 0.04)" />
            
            {/* Line */}
            <polyline fill="none" stroke="var(--color-success)" strokeWidth={2} points={points} />
            
            {/* Interactive Circles */}
            {chartData.map((d, index) => {
              const x = padding + (index * (width - padding * 2)) / (chartData.length - 1 || 1);
              const y = height - padding - (d.value * (height - padding * 2)) / maxVal;
              return (
                <g key={index}>
                  <circle cx={x} cy={y} r={3} fill="var(--color-success)" />
                  <text x={x} y={y - 8} fontSize={8} fill="var(--text-secondary)" textAnchor="middle" fontFamily="var(--font-mono)">
                    {d.value > 0 ? formatCurrency(d.value) : ''}
                  </text>
                  <text x={x} y={height - 4} fontSize={8} fill="var(--text-muted)" textAnchor="middle">
                    {d.date}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Breakdown and Recent Wins Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
        
        {/* Breakdown Panel */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Resolution Breakdowns</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {Object.entries(typeBreakdown).map(([type, stats]) => (
              <div key={type} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                  <span style={{ textTransform: 'capitalize', fontWeight: 500 }}>
                    {type.replace(/_/g, ' ')} ({stats.count} cases)
                  </span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                    {formatCurrency(stats.recovered)}
                  </span>
                </div>
                <div style={{ height: '4px', backgroundColor: 'var(--bg-tertiary)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      backgroundColor: 'var(--color-info)',
                      width: `${totalRecovered > 0 ? (stats.recovered / totalRecovered) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Wins */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Recent Recovery Wins</h3>
          {recoveredCases.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
              No payments recovered successfully yet.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {recoveredCases.map((c) => (
                <div
                  key={c.id}
                  onClick={() => navigate(`/recovery/cases/${c.id}`)}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'rgba(255, 255, 255, 0.01)',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <CheckCircle size={16} color="var(--color-success)" />
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontSize: '13px', fontWeight: 500, fontFamily: 'var(--font-mono)' }}>
                        Case {c.id.substring(0, 8)}...
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {c.failure_reason}
                      </span>
                    </div>
                  </div>
                  <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--color-success)', fontFamily: 'var(--font-mono)' }}>
                    +{formatCurrency(c.financial_impact)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
};

function roundPercent(val: number) {
  return isNaN(val) ? 0 : Math.round(val);
}
