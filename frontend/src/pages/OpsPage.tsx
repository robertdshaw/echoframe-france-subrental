import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import AddRecordForm from '../components/AddRecordForm';

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
      <AddRecordForm
        title="Schedule cleaning"
        postPath="/api/ops/cleaning"
        invalidate={['ops-cleaning']}
        fields={[
          { name: 'property_id', label: 'Property #', type: 'number', required: true },
          { name: 'schedule_date', label: 'Date', type: 'date', required: true },
          { name: 'cleaner_name', label: 'Cleaner', type: 'text' },
          { name: 'status', label: 'Status', type: 'select', options: ['scheduled', 'done', 'cancelled'] },
          { name: 'notes', label: 'Notes', type: 'text' },
        ]}
        defaults={{ status: 'scheduled' }}
      />
      <AddRecordForm
        title="Open maintenance ticket"
        postPath="/api/ops/maintenance"
        invalidate={['ops-maint']}
        fields={[
          { name: 'property_id', label: 'Property #', type: 'number', required: true },
          { name: 'title', label: 'Title', type: 'text', required: true },
          { name: 'description', label: 'Description', type: 'text' },
          { name: 'priority', label: 'Priority', type: 'select', options: ['low', 'medium', 'high'] },
          { name: 'status', label: 'Status', type: 'select', options: ['open', 'in_progress', 'resolved'] },
        ]}
        defaults={{ priority: 'medium', status: 'open' }}
      />
      <AddRecordForm
        title="Add operational task"
        postPath="/api/ops/tasks"
        invalidate={['ops-tasks']}
        fields={[
          { name: 'title', label: 'Title', type: 'text', required: true },
          { name: 'assignee', label: 'Assignee', type: 'text' },
          { name: 'due_date', label: 'Due', type: 'date' },
          { name: 'status', label: 'Status', type: 'select', options: ['todo', 'doing', 'done', 'blocked'] },
        ]}
        defaults={{ status: 'todo' }}
      />
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
