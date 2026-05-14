import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Map,
  GitBranch,
  Users,
  Wallet,
  Wrench,
  CheckCircle2,
  FileText,
  Calendar,
} from 'lucide-react';

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/market', label: 'Market Research', icon: Map },
  { to: '/pipeline', label: 'Pipeline', icon: GitBranch },
  { to: '/owners', label: 'Owners', icon: Users },
  { to: '/finance', label: 'Finance', icon: Wallet },
  { to: '/ops', label: 'Operations', icon: Wrench },
  { to: '/milestones', label: 'Milestones', icon: CheckCircle2 },
  { to: '/meetings', label: 'Meetings', icon: Calendar },
  { to: '/documents', label: 'Documents', icon: FileText },
];

export default function Sidebar() {
  return (
    <nav
      className="card scrollbar-thin"
      style={{
        position: 'sticky',
        top: 16,
        padding: 12,
        height: 'calc(100vh - 32px)',
        overflowY: 'auto',
      }}
    >
      <div style={{ padding: '8px 12px 18px' }}>
        <div
          className="mono"
          style={{
            fontSize: 11,
            color: 'var(--ef-orange-500)',
            letterSpacing: 0.18,
            textTransform: 'uppercase',
            fontWeight: 700,
          }}
        >
          EchoFrame
        </div>
        <div style={{ fontSize: 14, color: 'var(--ef-text-primary)', fontWeight: 600, marginTop: 2 }}>
          France · Subrental
        </div>
        <div style={{ fontSize: 11, color: 'var(--ef-text-secondary)', marginTop: 2 }}>
          150 km radius · Cessy
        </div>
      </div>
      {NAV.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          style={({ isActive }) => ({
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 12px',
            marginBottom: 2,
            borderRadius: 8,
            color: isActive ? '#FFFFFF' : 'var(--ef-text-secondary)',
            background: isActive ? 'rgba(232,114,42,0.12)' : 'transparent',
            borderLeft: isActive ? '3px solid var(--ef-orange-500)' : '3px solid transparent',
            fontSize: 13,
            fontWeight: isActive ? 600 : 500,
            textDecoration: 'none',
            transition: 'background 120ms ease, color 120ms ease',
          })}
        >
          <Icon size={16} />
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
