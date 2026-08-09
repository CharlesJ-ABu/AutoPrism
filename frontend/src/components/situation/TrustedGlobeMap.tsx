import { useEffect, useMemo, useRef, useState } from 'react';
import Globe from 'react-globe.gl';

import type { TrustedMapFeature } from '../../lib/v2-api';

export type MapStyle = 'industrial' | 'cyber' | 'ghost';

interface TrustedMapEngineProps {
  features: TrustedMapFeature[];
  mapStyle: MapStyle;
  selectedId?: string;
  onSelect: (feature: TrustedMapFeature) => void;
}

const FEATURE_COLORS: Record<TrustedMapFeature['display_type'], string> = {
  MARKER: '#22d3ee',
  HOTSPOT: '#fb7185',
  RIPPLE: '#a78bfa',
  FLOW: '#2dd4bf',
  COMPARISON: '#f59e0b',
  SHIELD_UP: '#60a5fa',
  ZONE: '#c084fc',
};

function useElementSize() {
  const hostRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 1, height: 1 });
  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;
    const update = () => setSize({ width: host.clientWidth, height: host.clientHeight });
    update();
    const observer = new ResizeObserver(update);
    observer.observe(host);
    return () => observer.disconnect();
  }, []);
  return { hostRef, size };
}

export default function TrustedGlobeMap({
  features,
  mapStyle,
  selectedId,
  onSelect,
}: TrustedMapEngineProps) {
  const globeRef = useRef<any>(null);
  const { hostRef, size } = useElementSize();
  const pointFeatures = useMemo(
    () => features.filter((feature) => feature.geometry.type === 'Point'),
    [features],
  );
  const lineFeatures = useMemo(
    () => features.filter((feature) => feature.geometry.type === 'LineString'),
    [features],
  );
  const zoneFeatures = useMemo(
    () => features.filter((feature) => feature.geometry.type === 'Polygon'),
    [features],
  );
  const rings = useMemo(
    () => pointFeatures.filter(
      (feature) => feature.display_type === 'HOTSPOT' || feature.display_type === 'RIPPLE',
    ),
    [pointFeatures],
  );

  useEffect(() => {
    const controls = globeRef.current?.controls?.();
    if (!controls) return;
    controls.autoRotate = true;
    controls.autoRotateSpeed = mapStyle === 'ghost' ? 0.12 : 0.24;
    controls.enableDamping = true;
  }, [mapStyle]);

  const atmosphere = mapStyle === 'industrial'
    ? '#3b82f6'
    : mapStyle === 'ghost'
      ? '#64748b'
      : '#8b5cf6';

  return (
    <div className="trusted-map-engine" ref={hostRef}>
      <Globe
        ref={globeRef}
        width={size.width}
        height={size.height}
        globeImageUrl="/evidence-grid.svg"
        backgroundColor="rgba(0,0,0,0)"
        atmosphereColor={atmosphere}
        atmosphereAltitude={0.18}
        pointsData={pointFeatures}
        pointLat={(feature: object) => (feature as TrustedMapFeature).geometry.type === 'Point'
          ? (feature as TrustedMapFeature & { geometry: { coordinates: [number, number] } }).geometry.coordinates[1]
          : 0}
        pointLng={(feature: object) => (feature as TrustedMapFeature).geometry.type === 'Point'
          ? (feature as TrustedMapFeature & { geometry: { coordinates: [number, number] } }).geometry.coordinates[0]
          : 0}
        pointColor={(feature: object) => FEATURE_COLORS[(feature as TrustedMapFeature).display_type]}
        pointAltitude={(feature: object) => (feature as TrustedMapFeature).id === selectedId ? 0.19 : 0.11}
        pointRadius={(feature: object) => (feature as TrustedMapFeature).id === selectedId ? 0.8 : 0.48}
        pointLabel={(feature: object) => (feature as TrustedMapFeature).label}
        onPointClick={(feature: object) => onSelect(feature as TrustedMapFeature)}
        arcsData={lineFeatures}
        arcStartLat={(feature: object) => ((feature as TrustedMapFeature).geometry as { coordinates: [[number, number], [number, number]] }).coordinates[0][1]}
        arcStartLng={(feature: object) => ((feature as TrustedMapFeature).geometry as { coordinates: [[number, number], [number, number]] }).coordinates[0][0]}
        arcEndLat={(feature: object) => ((feature as TrustedMapFeature).geometry as { coordinates: [[number, number], [number, number]] }).coordinates[1][1]}
        arcEndLng={(feature: object) => ((feature as TrustedMapFeature).geometry as { coordinates: [[number, number], [number, number]] }).coordinates[1][0]}
        arcColor={(feature: object) => FEATURE_COLORS[(feature as TrustedMapFeature).display_type]}
        arcStroke={(feature: object) => (feature as TrustedMapFeature).id === selectedId ? 0.8 : 0.42}
        arcDashLength={0.46}
        arcDashGap={0.16}
        arcDashAnimateTime={2200}
        onArcClick={(feature: object) => onSelect(feature as TrustedMapFeature)}
        ringsData={rings}
        ringLat={(feature: object) => ((feature as TrustedMapFeature).geometry as { coordinates: [number, number] }).coordinates[1]}
        ringLng={(feature: object) => ((feature as TrustedMapFeature).geometry as { coordinates: [number, number] }).coordinates[0]}
        ringColor={(feature: object) => () => FEATURE_COLORS[(feature as TrustedMapFeature).display_type]}
        ringMaxRadius={5}
        ringPropagationSpeed={1.4}
        ringRepeatPeriod={1700}
        polygonsData={zoneFeatures}
        polygonGeoJsonGeometry={(feature: object) => (feature as TrustedMapFeature).geometry as any}
        polygonCapColor={(feature: object) => `${FEATURE_COLORS[(feature as TrustedMapFeature).display_type]}55`}
        polygonSideColor={(feature: object) => `${FEATURE_COLORS[(feature as TrustedMapFeature).display_type]}22`}
        polygonStrokeColor={(feature: object) => FEATURE_COLORS[(feature as TrustedMapFeature).display_type]}
        polygonLabel={(feature: object) => (feature as TrustedMapFeature).label}
        onPolygonClick={(feature: object) => onSelect(feature as TrustedMapFeature)}
      />
    </div>
  );
}
