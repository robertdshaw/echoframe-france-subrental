import { useQuery } from '@tanstack/react-query';
import { api, type ZoneSummary } from '../api/client';
import ExecutiveCard from '../components/forecast/ExecutiveCard';

export default function DashboardPage() {
  const { data: zones, isLoading, error } = useQuery({
    queryKey: ['zones'],
    queryFn: api.listZones,
  });

  const sorted = (zones ?? [])
    .slice()
    .sort((a, b) => (b.expected_net_margin_pct ?? -99) - (a.expected_net_margin_pct ?? -99));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Executive overview</div>
        <h1 style={{ fontSize: 28, fontWeight: 700, marginTop: 4, marginBottom: 4 }}>
          The Call · seven zones in priority order
        </h1>
        <p style={{ fontSize: 14, color: 'var(--ef-text-secondary)', maxWidth: 720 }}>
          Each card shows the 12-month expected net margin from the
          model, with a verdict (target / wait / avoid) that synthesises
          the margin, regulatory friction, and current regime. Click any
          card to drill into the six narrative panels for that zone.
        </p>
      </header>

      {isLoading && (
        <div className="card" style={{ padding: 32, textAlign: 'center', color: 'var(--ef-text-secondary)' }}>
          Loading zone forecasts…
        </div>
      )}
      {error && (
        <div
          className="card"
          style={{
            padding: 16,
            border: '1px solid rgba(231,76,60,0.4)',
            color: '#F49389',
            background: 'rgba(231,76,60,0.08)',
          }}
        >
          Could not load forecasts: {(error as Error).message}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(330px, 1fr))', gap: 16 }}>
        {sorted.map((z: ZoneSummary) => (
          <ExecutiveCard key={z.slug} zone={z} />
        ))}
      </div>

      <section className="card" style={{ padding: 20 }}>
        <div className="eyebrow">Today's priorities</div>
        <ol style={{ marginTop: 10, paddingLeft: 18, color: 'var(--ef-text-secondary)', lineHeight: 1.7, fontSize: 13 }}>
          <li>
            <strong style={{ color: 'var(--ef-text-primary)' }}>Annecy</strong> — confirm second
            T2 walkthrough and validate rental comps against AirROI.
          </li>
          <li>
            <strong style={{ color: 'var(--ef-text-primary)' }}>Pipeline</strong> — Sophie Marchand
            negotiation due for follow-up; lease draft pending.
          </li>
          <li>
            <strong style={{ color: 'var(--ef-text-primary)' }}>Ops</strong> — finalise cleaning
            contracts for Pays de Gex + Annecy before activation.
          </li>
        </ol>
      </section>
    </div>
  );
}
