import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
  const qc = useQueryClient();
  const { data: entries } = useQuery({ queryKey: ['pipeline'], queryFn: api.listPipeline });
  const { data: owners } = useQuery({ queryKey: ['owners'], queryFn: api.listOwners });
  const ownerById = new Map((owners ?? []).map((o: any) => [o.id, o]));

  const [entry, setEntry] = useState({ owner_id: '', status: 'lead', notes: '', next_followup: '' });
  const createM = useMutation({
    mutationFn: () =>
      api.createPipeline({
        owner_id: Number(entry.owner_id),
        status: entry.status,
        notes: entry.notes || undefined,
        next_followup: entry.next_followup || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pipeline'] });
      setEntry({ owner_id: '', status: 'lead', notes: '', next_followup: '' });
    },
  });
  const fld: React.CSSProperties = {
    padding: '8px 10px', background: 'var(--ef-navy-700)', border: '1px solid var(--ef-border)',
    borderRadius: 6, color: 'var(--ef-text-primary)', fontSize: 13,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Pipeline</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>Owner negotiations</h1>
      </header>

      <div className="card" style={{ padding: 16 }}>
        <div className="eyebrow" style={{ marginBottom: 12 }}>Add pipeline entry</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 2fr 1fr auto', gap: 10, alignItems: 'end' }}>
          <div>
            <label style={{ fontSize: 11, color: 'var(--ef-text-secondary)', display: 'block', marginBottom: 4 }}>Owner</label>
            <select style={{ ...fld, width: '100%' }} value={entry.owner_id} onChange={(e) => setEntry((s) => ({ ...s, owner_id: e.target.value }))}>
              <option value="">Select owner…</option>
              {(owners ?? []).map((o: any) => <option key={o.id} value={o.id}>{o.name}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 11, color: 'var(--ef-text-secondary)', display: 'block', marginBottom: 4 }}>Status</label>
            <select style={{ ...fld, width: '100%' }} value={entry.status} onChange={(e) => setEntry((s) => ({ ...s, status: e.target.value }))}>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 11, color: 'var(--ef-text-secondary)', display: 'block', marginBottom: 4 }}>Notes</label>
            <input style={{ ...fld, width: '100%' }} value={entry.notes} onChange={(e) => setEntry((s) => ({ ...s, notes: e.target.value }))} />
          </div>
          <div>
            <label style={{ fontSize: 11, color: 'var(--ef-text-secondary)', display: 'block', marginBottom: 4 }}>Next follow-up</label>
            <input type="date" style={{ ...fld, width: '100%' }} value={entry.next_followup} onChange={(e) => setEntry((s) => ({ ...s, next_followup: e.target.value }))} />
          </div>
          <button
            disabled={!entry.owner_id || createM.isPending}
            onClick={() => createM.mutate()}
            style={{ ...fld, cursor: entry.owner_id ? 'pointer' : 'not-allowed', border: '1px solid var(--ef-orange-500)', background: 'rgba(232,114,42,0.15)', fontWeight: 600, opacity: entry.owner_id ? 1 : 0.5, whiteSpace: 'nowrap' }}
          >
            {createM.isPending ? 'Adding…' : 'Add'}
          </button>
        </div>
        {createM.isError && <div style={{ fontSize: 12, color: '#F49389', marginTop: 8 }}>{(createM.error as Error).message}</div>}
      </div>
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
