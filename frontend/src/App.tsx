import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar';
import DashboardPage from './pages/DashboardPage';
import MarketResearchPage from './pages/MarketResearchPage';
import ZoneDetailPage from './pages/ZoneDetailPage';
import PipelinePage from './pages/PipelinePage';
import CandidatesPage from './pages/CandidatesPage';
import OwnersPage from './pages/OwnersPage';
import FinancePage from './pages/FinancePage';
import OpsPage from './pages/OpsPage';
import MilestonesPage from './pages/MilestonesPage';
import MeetingsPage from './pages/MeetingsPage';
import DocumentsPage from './pages/DocumentsPage';

export default function App() {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '240px 1fr',
        gap: 20,
        padding: 16,
        minHeight: '100vh',
        maxWidth: 1640,
        margin: '0 auto',
      }}
    >
      <Sidebar />
      <main style={{ minWidth: 0 }}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/market" element={<MarketResearchPage />} />
          <Route path="/market/zone/:slug" element={<ZoneDetailPage />} />
          <Route path="/pipeline" element={<PipelinePage />} />
          <Route path="/candidates" element={<CandidatesPage />} />
          <Route path="/owners" element={<OwnersPage />} />
          <Route path="/finance" element={<FinancePage />} />
          <Route path="/ops" element={<OpsPage />} />
          <Route path="/milestones" element={<MilestonesPage />} />
          <Route path="/meetings" element={<MeetingsPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
        </Routes>
      </main>
    </div>
  );
}
