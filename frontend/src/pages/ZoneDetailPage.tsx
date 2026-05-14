import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export default function ZoneDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const { data: forecast } = useQuery({ queryKey: ['zoneForecast', slug], queryFn: () => api.getZoneForecast(slug!) });
  const { data: spread } = useQuery({ queryKey: ['spread', slug], queryFn: () => api.spread(slug!) });
  const { data: signals } = useQuery({ queryKey: ['signals', slug], queryFn: () => api.signalsFeed(slug) });
  const { data: narrative } = useQuery({ queryKey: ['narrative', slug], queryFn: () => api.narrative(slug!) });

  if (!forecast) {
    return <div className="card" style={{ padding: 32, color: 'var(--ef-text-secondary)' }}>Loading zone…</div>;
  }

  const z = forecast.zone;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
      <header className="card" style={{ padding: 22 }}>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>The Call · {z.regulatory_friction} regulatory friction</div>
        <h1 style={{ fontSize: 28, fontWeight: 700, marginTop: 6 }}>{z.name}</h1>
        <p style={{ fontSize: 13, color: 'var(--ef-text-secondary)', marginTop: 4 }}>{z.profile}</p>
        <div style={{ marginTop: 18, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 14 }}>
          <Stat label="12-mo net margin" value={`${(z.expected_net_margin_pct ?? 0).toFixed(1)}%`} accent />
          <Stat label="Net €/yr" value={`€${((z.expected_net_margin_eur ?? 0)/1000).toFixed(1)}k`} />
          <Stat label="ADR" value={`€${z.median_adr_eur}/n`} />
          <Stat label="Occupancy" value={`${z.median_occupancy_pct}%`} />
          <Stat label="Verdict" value={z.verdict ?? '—'} />
        </div>
      </header>

      {narrative?.narrative && (
        <section className="card" style={{ padding: 22 }}>
          <div className="eyebrow">Executive briefing · {narrative.model}</div>
          <div style={{ marginTop: 12, fontSize: 14, lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
            {narrative.narrative}
          </div>
        </section>
      )}

      <Section number="01" eyebrow="Where to source" title="Airbnb-to-landlord spread by commune">
        <div className="card" style={{ padding: 18 }}>
          {!spread?.by_commune?.length ? (
            <div style={{ color: 'var(--ef-text-secondary)', fontSize: 13 }}>No comp pairs yet for this zone.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ color: 'var(--ef-text-muted)' }}>
                  {['Commune', 'Airbnb / yr', 'Rental / yr', 'Spread', '×'].map((h) => (
                    <th key={h} style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {spread.by_commune.map((r: any) => (
                  <tr key={r.commune} style={{ borderTop: '1px solid var(--ef-border)' }}>
                    <td style={{ padding: '8px' }}>{r.commune}</td>
                    <td className="mono" style={{ padding: '8px' }}>€{r.airbnb_annual_eur.toLocaleString()}</td>
                    <td className="mono" style={{ padding: '8px' }}>€{r.rental_annual_eur.toLocaleString()}</td>
                    <td className="mono" style={{ padding: '8px', color: r.spread_eur > 0 ? '#2ECC71' : '#E74C3C', fontWeight: 600 }}>
                      €{r.spread_eur.toLocaleString()}
                    </td>
                    <td className="mono" style={{ padding: '8px' }}>{r.spread_multiple?.toFixed(2)}×</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Section>

      <Section number="02" eyebrow="Forecast trajectory" title="6 / 12 / 24-month posterior bands">
        <div className="card" style={{ padding: 18, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {forecast.forecasts.map((h: any) => (
            <div key={h.horizon_months}>
              <div className="eyebrow">{h.horizon_months}-month</div>
              <div className="mono" style={{ fontSize: 22, fontWeight: 700, marginTop: 4, color: h.median_change_pct >= 0 ? '#2ECC71' : '#E74C3C' }}>
                {h.median_change_pct >= 0 ? '+' : ''}{h.median_change_pct.toFixed(1)}%
              </div>
              <div className="mono" style={{ fontSize: 11, color: 'var(--ef-text-muted)', marginTop: 4 }}>
                80% band {h.ci_80.lower.toFixed(1)}% / {h.ci_80.upper.toFixed(1)}%
              </div>
              <div style={{ fontSize: 11, color: 'var(--ef-text-muted)', marginTop: 2 }}>
                P(positive) = {(h.p_positive * 100).toFixed(0)}%
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section number="03" eyebrow="Signals" title="News + regulation feed">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {(signals ?? []).slice(0, 8).map((s: any) => (
            <div key={s.id} className="card" style={{ padding: 14 }}>
              <div style={{ fontSize: 11, color: 'var(--ef-text-muted)', marginBottom: 4 }}>
                {s.source} · {s.date} · {s.category}
              </div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>{s.headline}</div>
              {s.section_influence && (
                <div style={{ fontSize: 11, color: 'var(--ef-orange-300)', marginTop: 6 }}>→ feeds {s.section_influence}</div>
              )}
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="eyebrow">{label}</div>
      <div className="mono" style={{ fontSize: 18, fontWeight: 700, color: accent ? 'var(--ef-orange-500)' : 'var(--ef-text-primary)', marginTop: 4 }}>
        {value}
      </div>
    </div>
  );
}

function Section({ number, eyebrow, title, children }: { number: string; eyebrow: string; title: string; children: React.ReactNode }) {
  return (
    <section>
      <div style={{ display: 'flex', gap: 14, alignItems: 'baseline', marginBottom: 12 }}>
        <span className="mono" style={{ color: 'var(--ef-orange-500)', fontSize: 13, fontWeight: 700 }}>{number}</span>
        <div style={{ flex: 1, borderTop: '1px solid var(--ef-border)', paddingTop: 8 }}>
          <div className="eyebrow">{eyebrow}</div>
          <h2 style={{ fontSize: 17, fontWeight: 700, marginTop: 2 }}>{title}</h2>
        </div>
      </div>
      {children}
    </section>
  );
}
