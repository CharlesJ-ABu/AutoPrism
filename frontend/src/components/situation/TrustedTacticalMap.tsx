import { ArcLayer, PolygonLayer, ScatterplotLayer } from '@deck.gl/layers';
import DeckGL from '@deck.gl/react';
import { useMemo } from 'react';

import type { TrustedMapFeature } from '../../lib/v2-api';
import type { MapStyle } from './TrustedGlobeMap';

interface TrustedTacticalMapProps {
  features: TrustedMapFeature[];
  mapStyle: MapStyle;
  selectedId?: string;
  onSelect: (feature: TrustedMapFeature) => void;
}

const COLORS: Record<TrustedMapFeature['display_type'], [number, number, number, number]> = {
  MARKER: [34, 211, 238, 220],
  HOTSPOT: [251, 113, 133, 230],
  RIPPLE: [167, 139, 250, 225],
  FLOW: [45, 212, 191, 220],
  COMPARISON: [245, 158, 11, 225],
  SHIELD_UP: [96, 165, 250, 225],
  ZONE: [192, 132, 252, 180],
};

const DEFAULT_VIEW = {
  longitude: 20,
  latitude: 18,
  zoom: 1.15,
  minZoom: 0,
  maxZoom: 15,
  pitch: 0,
  bearing: 0,
};

const geometryPositions = (feature: TrustedMapFeature): Array<[number, number]> => {
  if (feature.geometry.type === 'Point') return [feature.geometry.coordinates];
  if (feature.geometry.type === 'LineString') return feature.geometry.coordinates;
  return feature.geometry.coordinates.flat();
};

const fittedView = (features: TrustedMapFeature[]) => {
  const positions = features.flatMap(geometryPositions);
  if (!positions.length) return DEFAULT_VIEW;
  const longitudes = positions.map(([longitude]) => longitude);
  const latitudes = positions.map(([, latitude]) => latitude);
  const west = Math.min(...longitudes);
  const east = Math.max(...longitudes);
  const south = Math.min(...latitudes);
  const north = Math.max(...latitudes);
  const span = Math.max(east - west, (north - south) * 1.7);
  const zoom = span === 0
    ? 4
    : Math.max(.5, Math.min(7, Math.log2(360 / Math.max(1, span * 3.2))));
  return {
    ...DEFAULT_VIEW,
    longitude: (west + east) / 2,
    latitude: (south + north) / 2,
    zoom,
  };
};

export default function TrustedTacticalMap({
  features,
  mapStyle,
  selectedId,
  onSelect,
}: TrustedTacticalMapProps) {
  const points = features.filter((feature) => feature.geometry.type === 'Point');
  const lines = features.filter((feature) => feature.geometry.type === 'LineString');
  const zones = features.filter((feature) => feature.geometry.type === 'Polygon');
  const initialViewState = useMemo(() => fittedView(features), [features]);
  const layers = useMemo(() => [
    new PolygonLayer<TrustedMapFeature>({
      id: `trusted-zones-${mapStyle}`,
      data: zones,
      getPolygon: (feature) => (feature.geometry as {
        coordinates: Array<Array<[number, number]>>;
      }).coordinates[0],
      pickable: true,
      stroked: true,
      filled: true,
      getFillColor: (feature) => COLORS[feature.display_type],
      getLineColor: (feature) => [
        ...COLORS[feature.display_type].slice(0, 3),
        feature.id === selectedId ? 255 : 180,
      ] as [number, number, number, number],
      getLineWidth: (feature) => feature.id === selectedId ? 3 : 1,
      lineWidthMinPixels: 1,
      onClick: ({ object }) => object && onSelect(object),
    }),
    new ArcLayer<TrustedMapFeature>({
      id: `trusted-lines-${mapStyle}`,
      data: lines,
      pickable: true,
      getSourcePosition: (feature) => (feature.geometry as { coordinates: [[number, number], [number, number]] }).coordinates[0],
      getTargetPosition: (feature) => (feature.geometry as { coordinates: [[number, number], [number, number]] }).coordinates[1],
      getSourceColor: (feature) => COLORS[feature.display_type],
      getTargetColor: [255, 255, 255, 150],
      getWidth: (feature) => feature.id === selectedId ? 5 : 2.5,
      widthMinPixels: 2,
      onClick: ({ object }) => object && onSelect(object),
    }),
    new ScatterplotLayer<TrustedMapFeature>({
      id: `trusted-points-${mapStyle}`,
      data: points,
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 100],
      getPosition: (feature) => (feature.geometry as { coordinates: [number, number] }).coordinates,
      getFillColor: (feature) => COLORS[feature.display_type],
      getLineColor: [255, 255, 255, 180],
      stroked: true,
      filled: true,
      getRadius: (feature) => feature.id === selectedId ? 100000 : 65000,
      radiusMinPixels: 5,
      radiusMaxPixels: 28,
      lineWidthMinPixels: 1,
      onClick: ({ object }) => object && onSelect(object),
    }),
  ], [lines, mapStyle, onSelect, points, selectedId, zones]);

  return (
    <div className={`trusted-map-engine tactical-${mapStyle}`}>
      <div className="tactical-grid" aria-hidden="true" />
      <DeckGL
        layers={layers}
        initialViewState={initialViewState}
        controller
        getTooltip={({ object }) => object && (object as TrustedMapFeature).label}
      />
    </div>
  );
}
