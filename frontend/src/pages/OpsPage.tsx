import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';

const fetcher = (path: string) => () => apiClient.get(path).then((r) => r.data);

export default function OpsPage() {
  const { data: cleaning } = useQuery({ queryKey: ['ops-cleaning'], queryFn: fetcher('/api/ops/cleaning') });
  const { data: maintenance } = useQuery({ queryKey: ['ops-maint'], queryFn: fetcher('/api/ops/maintenance') });
  const { data: tasks } = useQuery({ queryKey: ['ops-tasks'], queryFn: fetcher('/api/ops/tasks') });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Operations</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>Cleaning · Maintenance · Tasks</h1>
      </header>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
        <Column title="Cleaning schedule" items={cleaning ?? []} render={(c: any) => (
          <>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Property #{c.property_id}</div>
            <div style={{ fontSize: 12, color: 'var(--ef-text-secondary)' }}>{c.schedule_date} · {c.cleaner_name ?? 'unassigned'}</div>
          </>
        )} empty="No cleaning scheduled." />
        <Column title="Maintenance tickets" items={maintenance ?? []} render={(t: any) => (
          <>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{t.title}</div>
            <div style={{ fontSize: 12, color: 'var(--ef-text-secondary)' }}>{t.status} · {t.priority}</div>
          </>
        )} empty="No maintenance tickets." />
        <Column title="Operational tasks" items={tasks ?? []} render={(t: any) => (
          <>
            <div style={{ fontSize: 13, fontWeight: 600 }}>{t.title}</div>
            <div style={{ fontSize: 12, color: 'var(--ef-text-secondary)' }}>{t.assignee ?? '—'} · {t.due_date ?? 'no due'}</div>
          </>
        )} empty="No tasks." />
      </div>
    </div>
  );
}

function Column({ title, items, render, empty }: { title: string; items: any[]; render: (i: any) => React.ReactNode; empty: string }) {
  return (
    <div className="card" style={{ padding: 14, minHeight: 300 }}>
      <div className="eyebrow">{title} · {items.length}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
        {items.length === 0 ? (
          <div style={{ color: 'var(--ef-text-muted)', fontSize: 12 }}>{empty}</div>
        ) : (
          items.map((i, idx) => (
            <div key={i.id ?? idx} style={{ padding: 10, borderRadius: 6, background: 'var(--ef-navy-700)', border: '1px solid var(--ef-border)' }}>
              {render(i)}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
