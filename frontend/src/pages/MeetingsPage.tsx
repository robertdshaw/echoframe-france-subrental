import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import AddRecordForm from '../components/AddRecordForm';

const TAG_TONE: Record<string, string> = { malmo: '#7AA7FF', cessy: '#F7A76B', remote: '#A8B2C1' };

export default function MeetingsPage() {
  const { data: items } = useQuery({ queryKey: ['meetings'], queryFn: api.listMeetings });
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Meetings</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>Malmö ↔ Cessy sync notes</h1>
      </header>
      <AddRecordForm
        title="Log a meeting"
        postPath="/api/meetings"
        invalidate={['meetings']}
        listFields={['attendees']}
        fields={[
          { name: 'title', label: 'Title', type: 'text', required: true },
          { name: 'meeting_date', label: 'Date', type: 'date', required: true },
          {
            name: 'location_tag',
            label: 'Location',
            type: 'select',
            options: ['malmo', 'cessy', 'remote'],
          },
          { name: 'attendees', label: 'Attendees (comma-sep)', type: 'text', placeholder: 'Rob, Bertrand' },
          { name: 'notes_md', label: 'Notes', type: 'text' },
        ]}
        defaults={{ location_tag: 'remote' }}
      />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {(items ?? []).map((m: any) => (
          <article key={m.id} className="card" style={{ padding: 18 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
              <h2 style={{ fontSize: 16, fontWeight: 600 }}>{m.title}</h2>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: 11 }}>
                <span className="mono" style={{ color: 'var(--ef-text-muted)' }}>{m.meeting_date}</span>
                <span className="eyebrow" style={{ padding: '2px 8px', borderRadius: 4, background: 'rgba(255,255,255,0.04)', color: TAG_TONE[m.location_tag] }}>
                  {m.location_tag}
                </span>
              </div>
            </div>
            {m.notes_md && (
              <pre style={{ marginTop: 12, fontSize: 12.5, color: 'var(--ef-text-secondary)', whiteSpace: 'pre-wrap', fontFamily: 'inherit', lineHeight: 1.55 }}>
                {m.notes_md}
              </pre>
            )}
            {Array.isArray(m.action_items) && m.action_items.length > 0 && (
              <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px dashed var(--ef-border)' }}>
                <div className="eyebrow">Action items</div>
                <ul style={{ margin: '8px 0 0', paddingLeft: 20, fontSize: 13 }}>
                  {m.action_items.map((a: any, i: number) => (
                    <li key={i}>
                      {a.text} <span style={{ color: 'var(--ef-text-muted)' }}>· {a.assignee} · {a.due}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
