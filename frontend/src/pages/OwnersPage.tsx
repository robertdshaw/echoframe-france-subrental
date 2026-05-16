import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

const FIELD: React.CSSProperties = {
  padding: '8px 10px',
  background: 'var(--ef-navy-700)',
  border: '1px solid var(--ef-border)',
  borderRadius: 6,
  color: 'var(--ef-text-primary)',
  fontSize: 13,
};

export default function OwnersPage() {
  const qc = useQueryClient();
  const { data: owners } = useQuery({ queryKey: ['owners'], queryFn: api.listOwners });
  const [form, setForm] = useState({ name: '', email: '', phone: '', source: '', notes: '' });
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const createM = useMutation({
    mutationFn: () => api.createOwner({ ...form }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['owners'] });
      setForm({ name: '', email: '', phone: '', source: '', notes: '' });
    },
  });
  const deleteM = useMutation({
    mutationFn: (id: number) => api.deleteOwner(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['owners'] }),
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Owners</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>Property owner database</h1>
      </header>

      <div className="card" style={{ padding: 16 }}>
        <div className="eyebrow" style={{ marginBottom: 12 }}>Add owner</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr) auto', gap: 10, alignItems: 'end' }}>
          {(['name', 'email', 'phone', 'source'] as const).map((k) => (
            <div key={k}>
              <label style={{ fontSize: 11, color: 'var(--ef-text-secondary)', display: 'block', marginBottom: 4 }}>
                {k[0].toUpperCase() + k.slice(1)}
              </label>
              <input style={{ ...FIELD, width: '100%' }} value={form[k]} onChange={(e) => set(k, e.target.value)} />
            </div>
          ))}
          <div>
            <label style={{ fontSize: 11, color: 'var(--ef-text-secondary)', display: 'block', marginBottom: 4 }}>Notes</label>
            <input style={{ ...FIELD, width: '100%' }} value={form.notes} onChange={(e) => set('notes', e.target.value)} />
          </div>
          <button
            disabled={!form.name || createM.isPending}
            onClick={() => createM.mutate()}
            style={{
              ...FIELD, cursor: form.name ? 'pointer' : 'not-allowed',
              border: '1px solid var(--ef-orange-500)', background: 'rgba(232,114,42,0.15)',
              fontWeight: 600, opacity: form.name ? 1 : 0.5, whiteSpace: 'nowrap',
            }}
          >
            {createM.isPending ? 'Adding…' : 'Add owner'}
          </button>
        </div>
        {createM.isError && (
          <div style={{ fontSize: 12, color: '#F49389', marginTop: 8 }}>
            {(createM.error as Error).message}
          </div>
        )}
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--ef-navy-700)' }}>
              {['Name', 'Email', 'Phone', 'Source', 'Notes', ''].map((h) => (
                <th key={h} className="eyebrow" style={{ padding: '12px 14px', textAlign: 'left' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(owners ?? []).map((o: any) => (
              <tr key={o.id} style={{ borderTop: '1px solid var(--ef-border)' }}>
                <td style={{ padding: '12px 14px', fontWeight: 600 }}>{o.name}</td>
                <td style={{ padding: '12px 14px', fontSize: 13, color: 'var(--ef-text-secondary)' }}>{o.email ?? '—'}</td>
                <td style={{ padding: '12px 14px', fontSize: 13, color: 'var(--ef-text-secondary)' }} className="mono">{o.phone ?? '—'}</td>
                <td style={{ padding: '12px 14px', fontSize: 12, color: 'var(--ef-text-muted)' }}>{o.source ?? '—'}</td>
                <td style={{ padding: '12px 14px', fontSize: 12, color: 'var(--ef-text-secondary)', maxWidth: 360 }}>{o.notes ?? '—'}</td>
                <td style={{ padding: '12px 14px' }}>
                  <button
                    onClick={() => deleteM.mutate(o.id)}
                    style={{
                      fontSize: 11, padding: '4px 10px', borderRadius: 5,
                      border: '1px solid rgba(231,76,60,0.4)', background: 'transparent',
                      color: '#F49389', cursor: 'pointer',
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
