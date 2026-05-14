import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

const STATUSES = ['lead', 'contact', 'negotiation', 'signed', 'active'] as const;

const STATUS_LABEL = {
  lead: 'Lead',
  contact: 'Contact',
  negotiation: 'Negotiation',
  signed: 'Signed',
  active: 'Active',
} as const;

export default function PipelinePage() {
  const { data: entries } = useQuery({ queryKey: ['pipeline'], queryFn: api.listPipeline });
  const { data: owners } = useQuery({ queryKey: ['owners'], queryFn: api.listOwners });
  const ownerById = new Map((owners ?? []).map((o: any) => [o.id, o]));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Pipeline</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>Owner negotiations</h1>
      </header>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
        {STATUSES.map((s) => {
          const items = (entries ?? []).filter((e: any) => e.status === s);
          return (
            <div key={s} className="card" style={{ padding: 14, minHeight: 320 }}>
              <div className="eyebrow" style={{ marginBottom: 10 }}>{STATUS_LABEL[s]} · {items.length}</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {items.map((e: any) => {
                  const o: any = ownerById.get(e.owner_id);
                  return (
                    <div key={e.id} style={{ padding: 10, borderRadius: 6, background: 'var(--ef-navy-700)', border: '1px solid var(--ef-border)' }}>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{o?.name ?? `Owner #${e.owner_id}`}</div>
                      {e.notes && <div style={{ fontSize: 11, color: 'var(--ef-text-secondary)', marginTop: 4 }}>{e.notes}</div>}
                      {e.next_followup && (
                        <div style={{ fontSize: 11, color: 'var(--ef-orange-300)', marginTop: 6 }}>follow-up: {e.next_followup}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
