import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

const CATEGORIES = ['contract', 'template', 'legal', 'compliance', 'other'] as const;

export default function DocumentsPage() {
  const { data: docs } = useQuery({ queryKey: ['documents'], queryFn: api.listDocuments });
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Documents</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>Contracts · templates · legal</h1>
      </header>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 14 }}>
        {CATEGORIES.map((c) => {
          const items = (docs ?? []).filter((d: any) => d.category === c);
          return (
            <div key={c} className="card" style={{ padding: 14, minHeight: 200 }}>
              <div className="eyebrow">{c} · {items.length}</div>
              <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {items.length === 0 ? (
                  <div style={{ color: 'var(--ef-text-muted)', fontSize: 12 }}>No documents in this category.</div>
                ) : (
                  items.map((d: any) => (
                    <div key={d.id} style={{ padding: 10, borderRadius: 6, background: 'var(--ef-navy-700)', fontSize: 13 }}>
                      {d.title}
                    </div>
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
