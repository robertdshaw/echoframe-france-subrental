import axios from 'axios';

const baseURL =
  (import.meta as unknown as { env: Record<string, string | undefined> }).env
    .VITE_API_URL ?? 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL,
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.response.use(
  (r) => r,
  (err) => {
    const message =
      (err.response?.data?.error?.message as string | undefined) ?? err.message;
    return Promise.reject(new Error(message));
  },
);

export interface ZoneSummary {
  slug: string;
  name: string;
  profile: string;
  communes: string[];
  center: [number, number];
  radius_km: number;
  median_adr_eur: number;
  median_rent_per_m2_eur: number;
  median_occupancy_pct: number;
  regulatory_friction: string;
  expected_net_margin_eur: number | null;
  expected_net_margin_pct: number | null;
  verdict: 'TARGET' | 'WAIT' | 'AVOID' | null;
}

export interface MarginWaterfallLine {
  key: string;
  label: string;
  value_eur: number;
  note: string;
  source: string;
}

export interface MarginResponse {
  gross_revenue_annual_eur: number;
  net_revenue_annual_eur: number;
  landlord_costs_annual_eur: number;
  operating_costs_annual_eur: number;
  taxable_base_eur: number;
  tax_eur: number;
  net_margin_annual_eur: number;
  net_margin_pct_of_revenue: number;
  waterfall: MarginWaterfallLine[];
  regime_used: string;
  notes: string[];
}

export const api = {
  listZones: () => apiClient.get<ZoneSummary[]>('/api/zones').then((r) => r.data),
  getZoneForecast: (slug: string) =>
    apiClient.get(`/api/zones/${slug}/forecast`).then((r) => r.data),
  margin: (body: Record<string, unknown>) =>
    apiClient.post<MarginResponse>('/api/margin', body).then((r) => r.data),
  signalsFeed: (zone?: string) =>
    apiClient.get('/api/signals/feed', { params: { zone } }).then((r) => r.data),
  regulation: () => apiClient.get('/api/signals/regulation').then((r) => r.data),
  spread: (slug: string) =>
    apiClient.get(`/api/market/zones/${slug}/spread`).then((r) => r.data),
  airbnbComps: (slug: string) =>
    apiClient.get(`/api/market/zones/${slug}/airbnb-comps`).then((r) => r.data),
  rentalComps: (slug: string) =>
    apiClient.get(`/api/market/zones/${slug}/rental-comps`).then((r) => r.data),
  narrative: (slug: string) =>
    apiClient.get(`/api/narrative/${slug}`).then((r) => r.data),
  // Operational
  listOwners: () => apiClient.get('/api/owners').then((r) => r.data),
  pipelineOverview: () => apiClient.get('/api/pipeline/overview').then((r) => r.data),
  listPipeline: () => apiClient.get('/api/pipeline/owners').then((r) => r.data),
  financeSummary: () => apiClient.get('/api/finance/summary').then((r) => r.data),
  pnl: () => apiClient.get('/api/finance/pnl').then((r) => r.data),
  listMilestones: () => apiClient.get('/api/milestones').then((r) => r.data),
  listMeetings: () => apiClient.get('/api/meetings').then((r) => r.data),
  listDocuments: () => apiClient.get('/api/documents').then((r) => r.data),
};
