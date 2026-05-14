import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

const STATUS_TONE: Record<string, string> = {
  not_started: '#5A6577',
  in_progress: '#F39C12',
  at_risk: '#E74C3C',
  complete: '#2ECC71',
};

export default function MilestonesPage() {
  const { data: items } = useQuery({ queryKey: ['milestones'], queryFn: api.listMilestones });
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Milestones</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>Project timeline</h1>
      </header>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {(items ?? []).map((m: any) => (
          <div key={m.id} className="card" style={{ padding: 16, display: 'grid', gridTemplateColumns: '24px 1fr 120px 120px', gap: 14, alignItems: 'center' }}>
            <span style={{ width: 12, height: 12, borderRadius: 999, background: STATUS_TONE[m.status] ?? '#5A6577', justifySelf: 'center' }} />
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{m.title}</div>
              {m.description && <div style={{ fontSize: 12, color: 'var(--ef-text-secondary)', marginTop: 2 }}>{m.description}</div>}
            </div>
            <div className="mono" style={{ fontSize: 12, color: 'var(--ef-text-secondary)' }}>{m.target_date ?? '—'}</div>
            <div className="eyebrow" style={{ color: STATUS_TONE[m.status] ?? '#5A6577' }}>{m.status.replace(/_/g, ' ')}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
