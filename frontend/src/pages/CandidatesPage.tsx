import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type PropertyScore } from '../api/client';

/*
 * Candidates — the "which flats to pick + what to offer" workspace.
 *
 * Workflow (manual import + auto-score; listings can't be scraped —
 * DataDome): you source a real flat, paste its specs, hit Score to see
 * margin / spread vs official rent / verdict / the back-solved landlord
 * offer on real market data, then Save it to the ranked pool.
 */

const VERDICT_COLOR: Record<string, string> = {
  TARGET: '#2ECC71',
  WAIT: '#F39C12',
  AVOID: '#E74C3C',
  INSUFFICIENT_DATA: '#7F8C9A',
};

const FIELD: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  background: 'var(--ef-navy-700)',
  border: '1px solid var(--ef-border)',
  borderRadius: 6,
  color: 'var(--ef-text-primary)',
  fontSize: 13,
};
const LABEL: React.CSSProperties = {
  fontSize: 11,
  color: 'var(--ef-text-secondary)',
  marginBottom: 4,
  display: 'block',
};

function ScoreCard({ s }: { s: PropertyScore }) {
  const o = s.landlord_offer;
  const m = s.margin;
  return (
    <div className="card" style={{ padding: 16, borderColor: VERDICT_COLOR[s.verdict] }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontWeight: 700, fontSize: 15 }}>
          {s.commune} · {s.type ?? '—'} · {s.size_m2 ?? '?'} m²
        </div>
        <span
          className="mono"
          style={{
            fontSize: 12,
            fontWeight: 700,
            padding: '3px 10px',
            borderRadius: 999,
            color: VERDICT_COLOR[s.verdict],
            border: `1px solid ${VERDICT_COLOR[s.verdict]}`,
          }}
        >
          {s.verdict}
        </span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 14 }}>
        <Stat label="Net margin / yr" value={m ? `€${m.net_margin_annual_eur.toLocaleString()}` : '—'} />
        <Stat label="Net margin %" value={m ? `${m.net_margin_pct}%` : '—'} />
        <Stat label="Spread ×" value={s.spread_multiple ? `${s.spread_multiple}×` : '—'} />
        <Stat label="Zone ADR" value={s.zone_adr_eur ? `€${s.zone_adr_eur}` : '—'} />
        <Stat label="Zone occ" value={s.zone_occupancy_pct ? `${s.zone_occupancy_pct}%` : '—'} />
        <Stat
          label="Official rent"
          value={
            s.official_market_rent_monthly_eur
              ? `€${s.official_market_rent_monthly_eur}/mo`
              : '—'
          }
        />
        <Stat label="DPE F+G in commune" value={s.commune_f_plus_g_pct != null ? `${s.commune_f_plus_g_pct}%` : '—'} />
        <Stat label="Friction" value={s.regulatory_friction} />
        <Stat label="DPE class" value={s.dpe_class ?? '—'} />
      </div>

      <div
        style={{
          marginTop: 14,
          padding: 12,
          borderRadius: 8,
          background: 'rgba(232,114,42,0.08)',
          border: '1px solid rgba(232,114,42,0.3)',
        }}
      >
        <div className="eyebrow" style={{ color: 'var(--ef-orange-300)', marginBottom: 6 }}>
          Offer to landlord (to hold {o?.target_margin_pct ?? 18}% margin)
        </div>
        {o && o.max_rent_offer_monthly_eur != null ? (
          <>
            <div style={{ fontSize: 22, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>
              €{o.max_rent_offer_monthly_eur.toLocaleString()}/mo
            </div>
            <div style={{ fontSize: 12, color: 'var(--ef-text-secondary)', marginTop: 4 }}>
              {o.vs_asking_rent_eur != null && (
                <>€{o.vs_asking_rent_eur.toLocaleString()} vs their asking · </>
              )}
              {o.vs_official_market_pct != null && (
                <>{o.vs_official_market_pct > 0 ? '+' : ''}
                {o.vs_official_market_pct}% vs official market rent</>
              )}
            </div>
            <div style={{ fontSize: 12, color: 'var(--ef-text-primary)', marginTop: 6 }}>
              {o.interpretation}
            </div>
          </>
        ) : (
          <div style={{ fontSize: 13, color: '#F49389' }}>
            {o?.interpretation ?? 'No viable offer at this target margin.'}
          </div>
        )}
      </div>

      {s.dpe_letting_blocked && (
        <div style={{ marginTop: 10, fontSize: 12, color: '#F49389' }}>
          ⚠ DPE class {s.dpe_class} is banned for letting — disqualifying.
        </div>
      )}
      {s.data_gaps.length > 0 && (
        <div style={{ marginTop: 10, fontSize: 11, color: 'var(--ef-text-muted)' }}>
          Gaps: {s.data_gaps.join(' · ')}
        </div>
      )}
      <div style={{ marginTop: 8, fontSize: 10, color: 'var(--ef-text-muted)' }}>
        Rent source: {s.rent_provenance}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--ef-text-muted)', textTransform: 'uppercase', letterSpacing: 0.08 }}>
        {label}
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, marginTop: 2 }}>{value}</div>
    </div>
  );
}

export default function CandidatesPage() {
  const qc = useQueryClient();
  const { data: zones } = useQuery({ queryKey: ['zones'], queryFn: api.listZones });
  const { data: owners } = useQuery({ queryKey: ['owners'], queryFn: api.listOwners });
  const { data: ranked } = useQuery({ queryKey: ['ranked'], queryFn: api.rankedProperties });

  const [form, setForm] = useState({
    commune: '',
    type: 'T2',
    size_m2: '',
    rent_monthly: '',
    charges: '',
    dpe_class: '',
    ownerName: '',
  });
  const [preview, setPreview] = useState<PropertyScore | null>(null);

  const communeOptions = useMemo(() => {
    const out: { zone: string; commune: string }[] = [];
    (zones ?? []).forEach((z: any) =>
      (z.communes ?? []).forEach((c: string) => out.push({ zone: z.name, commune: c })),
    );
    return out;
  }, [zones]);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const scoreM = useMutation({
    mutationFn: () =>
      api.scoreAdhoc({
        commune: form.commune,
        type: form.type,
        size_m2: Number(form.size_m2),
        rent_monthly: Number(form.rent_monthly),
        charges: form.charges ? Number(form.charges) : undefined,
        dpe_class: form.dpe_class || undefined,
      }),
    onSuccess: (d) => setPreview(d),
  });

  const saveM = useMutation({
    mutationFn: async () => {
      const existing = (owners ?? []).find(
        (o: any) => o.name.toLowerCase() === form.ownerName.trim().toLowerCase(),
      );
      let ownerId: number;
      if (existing) {
        ownerId = existing.id as number;
      } else {
        const created = await api.createOwner({
          name: form.ownerName.trim() || `Lead ${form.commune}`,
          source: 'manual import',
        });
        ownerId = created.id as number;
      }
      return api.createOwnerProperty(ownerId, {
        owner_id: ownerId,
        commune: form.commune,
        type: form.type,
        size_m2: Number(form.size_m2),
        rent_monthly: Number(form.rent_monthly),
        charges: form.charges ? Number(form.charges) : undefined,
        dpe_class: form.dpe_class || undefined,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ranked'] });
      qc.invalidateQueries({ queryKey: ['owners'] });
      setPreview(null);
      setForm((f) => ({ ...f, size_m2: '', rent_monthly: '', charges: '', dpe_class: '', ownerName: '' }));
    },
  });

  const canScore = form.commune && form.size_m2 && form.rent_monthly;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Candidates</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>Source · score · rank</h1>
        <p style={{ fontSize: 13, color: 'var(--ef-text-secondary)', marginTop: 6, maxWidth: 760 }}>
          Listings can't be scraped (SeLoger/LeBonCoin are bot-walled). You find a real flat,
          paste its specs, and it's scored on real market data — margin, spread vs the official
          Carte des loyers rent, DPE ban exposure, and the exact rent to offer the landlord.
        </p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 18 }}>
        <div className="card" style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="eyebrow">Import a flat</div>
          <div>
            <label style={LABEL}>Commune</label>
            <select style={FIELD} value={form.commune} onChange={(e) => set('commune', e.target.value)}>
              <option value="">Select commune…</option>
              {communeOptions.map((c) => (
                <option key={`${c.zone}-${c.commune}`} value={c.commune}>
                  {c.commune} ({c.zone})
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label style={LABEL}>Type</label>
              <select style={FIELD} value={form.type} onChange={(e) => set('type', e.target.value)}>
                {['Studio', 'T1', 'T2', 'T3', 'T4', 'Maison'].map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={LABEL}>Size m²</label>
              <input style={FIELD} type="number" value={form.size_m2} onChange={(e) => set('size_m2', e.target.value)} />
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label style={LABEL}>Asking rent €/mo</label>
              <input style={FIELD} type="number" value={form.rent_monthly} onChange={(e) => set('rent_monthly', e.target.value)} />
            </div>
            <div>
              <label style={LABEL}>Charges €/mo</label>
              <input style={FIELD} type="number" value={form.charges} onChange={(e) => set('charges', e.target.value)} />
            </div>
          </div>
          <div>
            <label style={LABEL}>DPE class (optional)</label>
            <select style={FIELD} value={form.dpe_class} onChange={(e) => set('dpe_class', e.target.value)}>
              <option value="">Unknown</option>
              {['A', 'B', 'C', 'D', 'E', 'F', 'G'].map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          <button
            className="btn"
            disabled={!canScore || scoreM.isPending}
            onClick={() => scoreM.mutate()}
            style={{
              padding: '10px', borderRadius: 6, border: '1px solid var(--ef-orange-500)',
              background: 'rgba(232,114,42,0.15)', color: 'var(--ef-text-primary)',
              fontWeight: 600, fontSize: 13, cursor: canScore ? 'pointer' : 'not-allowed',
              opacity: canScore ? 1 : 0.5,
            }}
          >
            {scoreM.isPending ? 'Scoring…' : 'Score on real data'}
          </button>
          {preview && (
            <>
              <div>
                <label style={LABEL}>Owner (existing name or new)</label>
                <input
                  style={FIELD}
                  list="owner-list"
                  value={form.ownerName}
                  onChange={(e) => set('ownerName', e.target.value)}
                  placeholder="e.g. Sophie Marchand"
                />
                <datalist id="owner-list">
                  {(owners ?? []).map((o: any) => (
                    <option key={o.id} value={o.name} />
                  ))}
                </datalist>
              </div>
              <button
                disabled={saveM.isPending}
                onClick={() => saveM.mutate()}
                style={{
                  padding: '10px', borderRadius: 6, border: '1px solid #2ECC71',
                  background: 'rgba(46,204,113,0.15)', color: 'var(--ef-text-primary)',
                  fontWeight: 600, fontSize: 13, cursor: 'pointer',
                }}
              >
                {saveM.isPending ? 'Saving…' : 'Save to candidate pool'}
              </button>
            </>
          )}
          {scoreM.isError && (
            <div style={{ fontSize: 12, color: '#F49389' }}>
              {(scoreM.error as Error).message}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {preview ? (
            <ScoreCard s={preview} />
          ) : (
            <div className="card" style={{ padding: 24, color: 'var(--ef-text-secondary)', fontSize: 13 }}>
              Fill the form and hit <strong>Score on real data</strong> to preview a flat before saving it.
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--ef-border)' }}>
          <div className="eyebrow">Ranked candidate pool · {ranked?.n_properties ?? 0} flats · top 5 highlighted</div>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--ef-navy-700)' }}>
              {['#', 'Commune', 'Type', 'Verdict', 'Net €/yr', 'Spread ×', 'Offer €/mo', 'vs asking'].map((h) => (
                <th key={h} className="eyebrow" style={{ padding: '10px 14px', textAlign: 'left' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(ranked?.all ?? []).map((s: PropertyScore) => {
              const top5 = (s.rank ?? 99) <= 5;
              return (
                <tr
                  key={s.property_id}
                  style={{
                    borderTop: '1px solid var(--ef-border)',
                    background: top5 ? 'rgba(46,204,113,0.06)' : 'transparent',
                  }}
                >
                  <td style={{ padding: '10px 14px', fontWeight: 700 }}>{s.rank}</td>
                  <td style={{ padding: '10px 14px', fontWeight: 600 }}>{s.commune}</td>
                  <td style={{ padding: '10px 14px', fontSize: 13 }}>{s.type ?? '—'}</td>
                  <td style={{ padding: '10px 14px' }}>
                    <span className="mono" style={{ fontSize: 11, fontWeight: 700, color: VERDICT_COLOR[s.verdict] }}>
                      {s.verdict}
                    </span>
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'JetBrains Mono, monospace', fontSize: 13 }}>
                    {s.margin ? `€${s.margin.net_margin_annual_eur.toLocaleString()}` : '—'}
                  </td>
                  <td style={{ padding: '10px 14px', fontSize: 13 }}>
                    {s.spread_multiple ? `${s.spread_multiple}×` : '—'}
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'JetBrains Mono, monospace', fontSize: 13 }}>
                    {s.landlord_offer?.max_rent_offer_monthly_eur
                      ? `€${s.landlord_offer.max_rent_offer_monthly_eur.toLocaleString()}`
                      : '—'}
                  </td>
                  <td style={{ padding: '10px 14px', fontSize: 13, color: 'var(--ef-text-secondary)' }}>
                    {s.landlord_offer?.vs_asking_rent_eur != null
                      ? `€${s.landlord_offer.vs_asking_rent_eur.toLocaleString()}`
                      : '—'}
                  </td>
                </tr>
              );
            })}
            {(ranked?.all ?? []).length === 0 && (
              <tr>
                <td colSpan={8} style={{ padding: 20, color: 'var(--ef-text-muted)', fontSize: 13 }}>
                  No candidates yet — score and save a flat above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
