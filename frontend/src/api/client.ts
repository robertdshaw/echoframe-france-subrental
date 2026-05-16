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

export interface LandlordOffer {
  target_margin_pct: number;
  max_rent_offer_monthly_eur: number | null;
  vs_asking_rent_eur: number | null;
  vs_official_market_pct: number | null;
  interpretation: string;
}

export interface PropertyScore {
  property_id: number | null;
  commune: string;
  zone_slug: string | null;
  type: string | null;
  size_m2: number | null;
  asking_rent_monthly_eur: number | null;
  official_market_rent_monthly_eur: number | null;
  official_rent_eur_per_m2: number | null;
  zone_adr_eur: number | null;
  zone_occupancy_pct: number | null;
  margin: {
    gross_revenue_annual_eur: number;
    net_margin_annual_eur: number;
    net_margin_pct: number;
  } | null;
  spread_multiple: number | null;
  dpe_class: string | null;
  commune_f_plus_g_pct: number | null;
  dpe_letting_blocked: boolean;
  regulatory_friction: string;
  verdict: 'TARGET' | 'WAIT' | 'AVOID' | 'INSUFFICIENT_DATA';
  landlord_offer: LandlordOffer | null;
  rent_provenance: string;
  data_gaps: string[];
  rank?: number;
}

export interface RankedResponse {
  n_properties: number;
  top_5: PropertyScore[];
  all: PropertyScore[];
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
  createOwner: (body: Record<string, unknown>) =>
    apiClient.post('/api/owners', body).then((r) => r.data),
  deleteOwner: (id: number) =>
    apiClient.delete(`/api/owners/${id}`).then((r) => r.data),
  createOwnerProperty: (ownerId: number, body: Record<string, unknown>) =>
    apiClient.post(`/api/owners/${ownerId}/properties`, body).then((r) => r.data),
  listProperties: () =>
    apiClient.get('/api/properties').then((r) => r.data),
  deleteProperty: (id: number) =>
    apiClient.delete(`/api/properties/${id}`).then((r) => r.data),
  scoreAdhoc: (body: Record<string, unknown>) =>
    apiClient.post<PropertyScore>('/api/properties/score', body).then((r) => r.data),
  rankedProperties: () =>
    apiClient.get<RankedResponse>('/api/properties/ranked').then((r) => r.data),
  createPipeline: (body: Record<string, unknown>) =>
    apiClient.post('/api/pipeline/owners', body).then((r) => r.data),
  pipelineOverview: () => apiClient.get('/api/pipeline/overview').then((r) => r.data),
  listPipeline: () => apiClient.get('/api/pipeline/owners').then((r) => r.data),
  financeSummary: () => apiClient.get('/api/finance/summary').then((r) => r.data),
  pnl: () => apiClient.get('/api/finance/pnl').then((r) => r.data),
  listMilestones: () => apiClient.get('/api/milestones').then((r) => r.data),
  listMeetings: () => apiClient.get('/api/meetings').then((r) => r.data),
  listDocuments: () => apiClient.get('/api/documents').then((r) => r.data),
};
