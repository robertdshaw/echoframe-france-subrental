import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';

/*
 * Reusable "add a record" card. One component, dropped into every
 * operational page (finance / ops / milestones / meetings / documents)
 * so Rob + Bertrand can enter real data instead of seed.
 *
 * Fields are declared per page. Numbers are cast, blank optionals are
 * dropped, and `listFields` are comma-split into arrays (meeting
 * attendees). On success it invalidates the page's query keys so the
 * list refreshes immediately.
 */

export type FieldType = 'text' | 'number' | 'date' | 'select' | 'textarea';

export interface FieldSpec {
  name: string;
  label: string;
  type?: FieldType;
  options?: string[];
  required?: boolean;
  placeholder?: string;
}

interface Props {
  title: string;
  postPath: string;
  fields: FieldSpec[];
  invalidate: string[];
  listFields?: string[];
  defaults?: Record<string, string>;
}

const FIELD: React.CSSProperties = {
  width: '100%',
  padding: '8px 10px',
  background: 'var(--ef-navy-700)',
  border: '1px solid var(--ef-border)',
  borderRadius: 6,
  color: 'var(--ef-text-primary)',
  fontSize: 13,
};

export default function AddRecordForm({
  title,
  postPath,
  fields,
  invalidate,
  listFields = [],
  defaults = {},
}: Props) {
  const qc = useQueryClient();
  const init = Object.fromEntries(
    fields.map((f) => [f.name, defaults[f.name] ?? '']),
  );
  const [form, setForm] = useState<Record<string, string>>(init);
  const set = (k: string, v: string) => setForm((s) => ({ ...s, [k]: v }));

  const mut = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = {};
      for (const f of fields) {
        const raw = form[f.name];
        if (raw === '' || raw == null) continue;
        if (listFields.includes(f.name)) {
          body[f.name] = raw.split(',').map((s) => s.trim()).filter(Boolean);
        } else if (f.type === 'number') {
          body[f.name] = Number(raw);
        } else {
          body[f.name] = raw;
        }
      }
      return apiClient.post(postPath, body).then((r) => r.data);
    },
    onSuccess: () => {
      invalidate.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
      setForm(init);
    },
  });

  const missingRequired = fields.some(
    (f) => f.required && !String(form[f.name] ?? '').trim(),
  );

  return (
    <div className="card" style={{ padding: 16 }}>
      <div className="eyebrow" style={{ marginBottom: 12 }}>{title}</div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${Math.min(fields.length, 4)}, 1fr) auto`,
          gap: 10,
          alignItems: 'end',
        }}
      >
        {fields.map((f) => (
          <div key={f.name} style={{ minWidth: 0 }}>
            <label
              style={{
                fontSize: 11,
                color: 'var(--ef-text-secondary)',
                display: 'block',
                marginBottom: 4,
              }}
            >
              {f.label}
              {f.required && <span style={{ color: 'var(--ef-orange-500)' }}> *</span>}
            </label>
            {f.type === 'select' ? (
              <select style={FIELD} value={form[f.name]} onChange={(e) => set(f.name, e.target.value)}>
                <option value="">—</option>
                {(f.options ?? []).map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            ) : f.type === 'textarea' ? (
              <input
                style={FIELD}
                value={form[f.name]}
                placeholder={f.placeholder}
                onChange={(e) => set(f.name, e.target.value)}
              />
            ) : (
              <input
                style={FIELD}
                type={f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : 'text'}
                value={form[f.name]}
                placeholder={f.placeholder}
                onChange={(e) => set(f.name, e.target.value)}
              />
            )}
          </div>
        ))}
        <button
          disabled={missingRequired || mut.isPending}
          onClick={() => mut.mutate()}
          style={{
            ...FIELD,
            width: 'auto',
            cursor: missingRequired ? 'not-allowed' : 'pointer',
            border: '1px solid var(--ef-orange-500)',
            background: 'rgba(232,114,42,0.15)',
            fontWeight: 600,
            opacity: missingRequired ? 0.5 : 1,
            whiteSpace: 'nowrap',
          }}
        >
          {mut.isPending ? 'Adding…' : 'Add'}
        </button>
      </div>
      {mut.isError && (
        <div style={{ fontSize: 12, color: '#F49389', marginTop: 8 }}>
          {(mut.error as Error).message}
        </div>
      )}
      {mut.isSuccess && (
        <div style={{ fontSize: 12, color: '#2ECC71', marginTop: 8 }}>Saved.</div>
      )}
    </div>
  );
}
