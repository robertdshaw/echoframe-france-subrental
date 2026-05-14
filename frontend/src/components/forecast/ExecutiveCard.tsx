import { Link } from 'react-router-dom';
import type { ZoneSummary } from '../../api/client';

const VERDICT_TONE = {
  TARGET: { bg: 'rgba(46,204,113,0.12)', border: 'rgba(46,204,113,0.35)', dot: '#2ECC71', text: '#7DEDA9', chip: 'TARGET' },
  WAIT:   { bg: 'rgba(243,156,18,0.12)', border: 'rgba(243,156,18,0.35)', dot: '#F39C12', text: '#FBC56F', chip: 'WAIT' },
  AVOID:  { bg: 'rgba(231,76,60,0.12)',  border: 'rgba(231,76,60,0.35)',  dot: '#E74C3C', text: '#F49389', chip: 'AVOID' },
} as const;

export default function ExecutiveCard({ zone }: { zone: ZoneSummary }) {
  const tone = VERDICT_TONE[zone.verdict ?? 'WAIT'];
  const netPct = zone.expected_net_margin_pct ?? 0;
  const netEur = zone.expected_net_margin_eur ?? 0;

  return (
    <Link
      to={`/market/zone/${zone.slug}`}
      className="card"
      style={{
        display: 'block',
        padding: 22,
        textDecoration: 'none',
        color: 'inherit',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0, left: 0, right: 0, height: 3,
          background: `linear-gradient(90deg, ${tone.dot} 0%, transparent 100%)`,
        }}
      />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            {zone.regulatory_friction === 'high' ? '⚠ high regulatory friction' : `${zone.communes.length} communes`}
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.01em' }}>{zone.name}</div>
          <div style={{ fontSize: 11.5, color: 'var(--ef-text-secondary)', marginTop: 4, lineHeight: 1.45 }}>
            {zone.profile}
          </div>
        </div>
        <div
          style={{
            padding: '4px 10px',
            background: tone.bg,
            border: `1px solid ${tone.border}`,
            borderRadius: 999,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: 0.18,
            color: tone.text,
            whiteSpace: 'nowrap',
          }}
        >
          <span style={{ width: 6, height: 6, borderRadius: 999, background: tone.dot }} />
          {tone.chip}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 24, marginTop: 18, alignItems: 'baseline' }}>
        <div>
          <div className="eyebrow">12-mo net margin</div>
          <div
            className="mono"
            style={{ fontSize: 38, fontWeight: 700, color: tone.dot, lineHeight: 1.05, letterSpacing: '-0.02em' }}
          >
            {netPct >= 0 ? '+' : ''}{netPct.toFixed(1)}%
          </div>
        </div>
        <div>
          <div className="eyebrow">net €/yr</div>
          <div className="mono" style={{ fontSize: 16, fontWeight: 600, color: 'var(--ef-text-primary)' }}>
            €{(netEur / 1000).toFixed(1)}k
          </div>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 10,
          marginTop: 18,
          paddingTop: 14,
          borderTop: '1px solid var(--ef-border)',
        }}
      >
        <div>
          <div className="eyebrow">ADR</div>
          <div className="mono" style={{ fontSize: 13, fontWeight: 600 }}>€{zone.median_adr_eur.toFixed(0)}/n</div>
        </div>
        <div>
          <div className="eyebrow">Occ</div>
          <div className="mono" style={{ fontSize: 13, fontWeight: 600 }}>{zone.median_occupancy_pct.toFixed(0)}%</div>
        </div>
        <div>
          <div className="eyebrow">€/m²</div>
          <div className="mono" style={{ fontSize: 13, fontWeight: 600 }}>€{zone.median_rent_per_m2_eur.toFixed(1)}</div>
        </div>
      </div>
    </Link>
  );
}
