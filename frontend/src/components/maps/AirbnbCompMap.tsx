import { useEffect, useMemo, useState } from 'react';
import {
  CircleMarker,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
  ZoomControl,
  useMap,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { apiClient } from '../../api/client';

/*
 * Leaflet map of Airbnb comp listings for a zone.
 *
 * Color = ADR band, size ∝ capacity. Each marker pops up the full
 * comp record on click. Falls back to a "no comps available" card
 * when the zone has no seed entries.
 *
 * Zone polygons are not loaded here — the centroid view + a tile
 * layer gives enough geographic context for the MVP. Later: load
 * commune GeoJSON for proper boundary overlays.
 */

interface Props {
  zoneSlug: string;
  zoneCenter: [number, number];
}

interface Comp {
  id: string;
  commune: string;
  adr_eur: number;
  occupancy_pct: number;
  capacity: number;
  type: string;
  amenities: string[];
  source: string;
}

// Commune centroids for the 38 communes in our seed corpus. The
// backend doesn't currently return per-comp lat/lng (the seed only
// carries commune name + ADR), so we look up the centroid client-side.
// Smaller jitter per id keeps overlapping pins separable.
const COMMUNE_CENTROIDS: Record<string, [number, number]> = {
  // Pays de Gex
  Cessy: [46.3203, 6.0786],
  'Ferney-Voltaire': [46.2558, 6.1078],
  Gex: [46.3328, 6.0586],
  'Divonne-les-Bains': [46.3567, 6.1422],
  'Saint-Genis-Pouilly': [46.2433, 6.0231],
  // Annecy & Haute-Savoie Lakeside
  Annecy: [45.8992, 6.1294],
  Talloires: [45.8442, 6.2167],
  'Menthon-Saint-Bernard': [45.8567, 6.2031],
  Sévrier: [45.8633, 6.1467],
  'Veyrier-du-Lac': [45.8825, 6.1731],
  // Greater Lyon
  'Lyon 1er': [45.77, 4.83],
  'Lyon 2e': [45.75, 4.83],
  'Lyon 3e': [45.75, 4.86],
  'Lyon 6e': [45.77, 4.85],
  'Lyon 7e': [45.74, 4.84],
  Villeurbanne: [45.7667, 4.88],
  'Caluire-et-Cuire': [45.7967, 4.8467],
  Bron: [45.7333, 4.91],
  // Grenoble & Isère
  Grenoble: [45.1885, 5.7245],
  Meylan: [45.2167, 5.7833],
  "Saint-Martin-d'Hères": [45.1833, 5.7667],
  Échirolles: [45.1466, 5.7136],
  Vizille: [45.0833, 5.7833],
  // Dijon & Côte-d'Or
  Dijon: [47.322, 5.0415],
  Beaune: [47.025, 4.84],
  Chenôve: [47.2833, 5.0167],
  Talant: [47.3417, 5.0117],
  'Nuits-Saint-Georges': [47.1383, 4.9483],
  // Ski Access
  'La Clusaz': [45.905, 6.4267],
  'Le Grand-Bornand': [45.9417, 6.4283],
  Megève: [45.8567, 6.6172],
  Morzine: [46.18, 6.7081],
  'Les Gets': [46.1583, 6.6717],
  // Geneva Periphery
  Annemasse: [46.195, 6.235],
  'Thonon-les-Bains': [46.3717, 6.4783],
  'Évian-les-Bains': [46.4017, 6.5867],
  'Bons-en-Chablais': [46.2667, 6.3667],
};

// Map an ADR to a colour band. Pegged to the realistic spread we
// see across our French zones (€90 cheap, €250+ premium).
const ADR_BANDS = [
  { max: 100, color: '#2ECC71', label: '< €100' },
  { max: 150, color: '#F39C12', label: '€100 – €150' },
  { max: 200, color: '#E8722A', label: '€150 – €200' },
  { max: 250, color: '#E74C3C', label: '€200 – €250' },
  { max: Infinity, color: '#9B59B6', label: '> €250' },
];

const bandFor = (adr: number) =>
  ADR_BANDS.find((b) => adr < b.max) ?? ADR_BANDS[ADR_BANDS.length - 1];

const jitterFor = (id: string): [number, number] => {
  // Deterministic small offset so co-located comps don't stack.
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = (hash * 31 + id.charCodeAt(i)) | 0;
  const dx = ((hash & 0xff) - 128) / 12800; // ±0.01°
  const dy = (((hash >> 8) & 0xff) - 128) / 12800;
  return [dx, dy];
};

/** Recenters the map when zone changes. */
function MapRefocus({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, map.getZoom());
    setTimeout(() => map.invalidateSize(), 80);
  }, [center, map]);
  return null;
}

export default function AirbnbCompMap({ zoneSlug, zoneCenter }: Props) {
  const [comps, setComps] = useState<Comp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiClient
      .get<Comp[]>(`/api/market/zones/${zoneSlug}/airbnb-comps`)
      .then((r) => {
        if (!cancelled) {
          setComps(r.data);
          setLoading(false);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [zoneSlug]);

  const markers = useMemo(
    () =>
      comps
        .map((c) => {
          const centroid = COMMUNE_CENTROIDS[c.commune];
          if (!centroid) return null;
          const [dx, dy] = jitterFor(c.id);
          return {
            comp: c,
            position: [centroid[0] + dx, centroid[1] + dy] as [number, number],
          };
        })
        .filter((m): m is NonNullable<typeof m> => m !== null),
    [comps],
  );

  if (loading) {
    return (
      <div className="card" style={{ padding: 24, color: 'var(--ef-text-secondary)' }}>
        Loading comps…
      </div>
    );
  }
  if (error) {
    return (
      <div className="card" style={{ padding: 16, color: '#F49389', borderColor: 'rgba(231,76,60,0.4)' }}>
        Comp map unavailable: {error}
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
      <div style={{ position: 'relative', height: 420, width: '100%' }}>
        <MapContainer
          key={zoneSlug}
          center={zoneCenter}
          zoom={11}
          style={{ height: '100%', width: '100%' }}
          zoomControl={false}
          scrollWheelZoom={false}
          attributionControl
        >
          <ZoomControl position="topright" />
          <MapRefocus center={zoneCenter} />
          <TileLayer
            attribution='&copy; <a href="https://carto.com/attributions">CARTO</a> · <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            subdomains={['a', 'b', 'c', 'd']}
          />
          {markers.map(({ comp, position }) => {
            const band = bandFor(comp.adr_eur);
            const radius = Math.min(16, 6 + Math.sqrt(comp.capacity) * 2);
            return (
              <CircleMarker
                key={comp.id}
                center={position}
                radius={radius}
                pathOptions={{
                  color: band.color,
                  weight: 1.5,
                  fillColor: band.color,
                  fillOpacity: 0.65,
                }}
              >
                <Tooltip direction="top" offset={[0, -8]} opacity={1}>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>
                    <strong>{comp.commune}</strong> · €{comp.adr_eur}/n · {comp.occupancy_pct}% occ
                  </div>
                </Tooltip>
                <Popup>
                  <div style={{ minWidth: 200, fontSize: 12 }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>{comp.commune}</div>
                    <div style={{ fontSize: 18, color: band.color, fontWeight: 700, fontFamily: 'JetBrains Mono, monospace' }}>
                      €{comp.adr_eur}/night
                    </div>
                    <div style={{ marginTop: 6, fontSize: 11, color: '#666' }}>
                      {comp.type} · sleeps {comp.capacity} · {comp.occupancy_pct}% occupancy
                    </div>
                    {comp.amenities?.length > 0 && (
                      <div style={{ marginTop: 6, fontSize: 11 }}>
                        {comp.amenities.slice(0, 4).join(' · ')}
                      </div>
                    )}
                    <div style={{ marginTop: 6, fontSize: 10, color: '#999' }}>
                      Source: {comp.source}
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>

        {/* Legend ribbon */}
        <div
          style={{
            position: 'absolute',
            bottom: 10,
            left: 10,
            zIndex: 401,
            background: 'rgba(11, 20, 38, 0.92)',
            border: '1px solid var(--ef-border)',
            borderRadius: 8,
            padding: '10px 12px',
            fontSize: 11,
            color: 'var(--ef-text-primary)',
            backdropFilter: 'blur(4px)',
          }}
        >
          <div
            style={{
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: 0.14,
              textTransform: 'uppercase',
              color: 'var(--ef-text-secondary)',
              marginBottom: 6,
            }}
          >
            ADR / night (EUR)
          </div>
          {ADR_BANDS.map((b) => (
            <div
              key={b.label}
              style={{ display: 'flex', alignItems: 'center', gap: 6, lineHeight: 1.7 }}
            >
              <span
                style={{
                  width: 11,
                  height: 11,
                  borderRadius: '50%',
                  background: b.color,
                  border: '1.5px solid rgba(255,255,255,0.7)',
                }}
              />
              <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{b.label}</span>
            </div>
          ))}
          <div
            style={{
              marginTop: 6,
              paddingTop: 6,
              borderTop: '1px dashed var(--ef-border)',
              fontSize: 10,
              color: 'var(--ef-text-muted)',
            }}
          >
            Circle size ∝ √capacity
          </div>
        </div>
      </div>

      <div
        style={{
          padding: '10px 16px',
          fontSize: 11,
          color: 'var(--ef-text-muted)',
          borderTop: '1px solid var(--ef-border)',
        }}
      >
        {markers.length} comp{markers.length === 1 ? '' : 's'} plotted · click any pin for details
      </div>
    </div>
  );
}
