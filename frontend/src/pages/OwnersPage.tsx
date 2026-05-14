import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export default function OwnersPage() {
  const { data: owners } = useQuery({ queryKey: ['owners'], queryFn: api.listOwners });
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Owners</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>Property owner database</h1>
      </header>
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--ef-navy-700)' }}>
              {['Name', 'Email', 'Phone', 'Source', 'Notes'].map((h) => (
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
