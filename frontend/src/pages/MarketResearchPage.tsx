import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export default function MarketResearchPage() {
  const { data: zones } = useQuery({ queryKey: ['zones'], queryFn: api.listZones });
  const sorted = (zones ?? []).slice().sort((a, b) => (b.expected_net_margin_pct ?? 0) - (a.expected_net_margin_pct ?? 0));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Market research</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>Cross-zone comparison</h1>
        <p style={{ fontSize: 13, color: 'var(--ef-text-secondary)', maxWidth: 720 }}>
          Zones ranked by 12-month net margin. Click into any zone for the six
          narrative panels — Where to source, When to act, What you'll earn,
          Versus alternatives, Geography, Signals.
        </p>
      </header>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--ef-navy-700)' }}>
              {['Zone', 'Net margin', 'ADR', 'Occ', '€/m²', 'Friction', 'Verdict', ''].map((h) => (
                <th key={h} className="eyebrow" style={{ padding: '12px 14px', textAlign: 'left', color: 'var(--ef-slate-400)' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((z) => (
              <tr key={z.slug} style={{ borderTop: '1px solid var(--ef-border)' }}>
                <td style={{ padding: '12px 14px' }}>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{z.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--ef-text-muted)' }}>{z.communes.length} communes</div>
                </td>
                <td className="mono" style={{ padding: '12px 14px', color: (z.expected_net_margin_pct ?? 0) >= 12 ? '#2ECC71' : (z.expected_net_margin_pct ?? 0) >= 6 ? '#F39C12' : '#E74C3C' }}>
                  {(z.expected_net_margin_pct ?? 0).toFixed(1)}%
                </td>
                <td className="mono" style={{ padding: '12px 14px' }}>€{z.median_adr_eur}/n</td>
                <td className="mono" style={{ padding: '12px 14px' }}>{z.median_occupancy_pct}%</td>
                <td className="mono" style={{ padding: '12px 14px' }}>€{z.median_rent_per_m2_eur}</td>
                <td style={{ padding: '12px 14px', fontSize: 12, color: z.regulatory_friction === 'high' ? '#F49389' : 'var(--ef-text-secondary)' }}>{z.regulatory_friction}</td>
                <td style={{ padding: '12px 14px', fontSize: 11, fontWeight: 700, color: z.verdict === 'TARGET' ? '#2ECC71' : z.verdict === 'WAIT' ? '#F39C12' : '#E74C3C' }}>{z.verdict}</td>
                <td style={{ padding: '12px 14px' }}>
                  <Link to={`/market/zone/${z.slug}`} style={{ color: 'var(--ef-orange-500)', fontSize: 12 }}>open →</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
