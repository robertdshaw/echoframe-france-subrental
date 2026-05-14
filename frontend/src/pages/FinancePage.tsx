import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';

export default function FinancePage() {
  const { data: summary } = useQuery({ queryKey: ['fin-summary'], queryFn: api.financeSummary });
  const { data: pnl } = useQuery({ queryKey: ['pnl'], queryFn: api.pnl });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
      <header>
        <div className="eyebrow" style={{ color: 'var(--ef-orange-500)' }}>Finance</div>
        <h1 style={{ fontSize: 26, fontWeight: 700, marginTop: 4 }}>Budget · Revenue · P&L</h1>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <Kpi label="Budget" value={summary?.budget_total_eur ?? 0} />
        <Kpi label="Revenue YTD" value={summary?.revenue_ytd_eur ?? 0} accent="#2ECC71" />
        <Kpi label="Expenses YTD" value={summary?.expense_ytd_eur ?? 0} accent="#E74C3C" />
        <Kpi label="Net YTD" value={summary?.net_ytd_eur ?? 0} accent="#E8722A" />
      </div>

      <div className="card" style={{ padding: 18 }}>
        <div className="eyebrow">Monthly P&L</div>
        {!pnl?.by_month?.length ? (
          <div style={{ color: 'var(--ef-text-secondary)', marginTop: 12, fontSize: 13 }}>
            No financial entries yet. Add revenue + expenses via POST /api/finance/revenue and /expenses.
          </div>
        ) : (
          <table style={{ width: '100%', marginTop: 12, borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ color: 'var(--ef-text-muted)' }}>
                {['Month', 'Revenue', 'Expense', 'Net'].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '6px 8px', fontWeight: 500 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pnl.by_month.map((m: any) => (
                <tr key={m.month} style={{ borderTop: '1px solid var(--ef-border)' }}>
                  <td className="mono" style={{ padding: 8 }}>{m.month}</td>
                  <td className="mono" style={{ padding: 8, color: '#2ECC71' }}>€{m.revenue.toLocaleString()}</td>
                  <td className="mono" style={{ padding: 8, color: '#E74C3C' }}>€{m.expense.toLocaleString()}</td>
                  <td className="mono" style={{ padding: 8, fontWeight: 700 }}>€{m.net.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Kpi({ label, value, accent }: { label: string; value: number; accent?: string }) {
  return (
    <div className="card" style={{ padding: 16 }}>
      <div className="eyebrow">{label}</div>
      <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: accent ?? 'var(--ef-text-primary)', marginTop: 4 }}>
        €{value.toLocaleString()}
      </div>
    </div>
  );
}
