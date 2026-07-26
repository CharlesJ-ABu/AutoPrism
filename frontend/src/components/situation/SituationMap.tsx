import { Crosshair, Globe2, Map, ShieldCheck } from 'lucide-react';

import type { PanelView } from '../../lib/v2-api';
import { Panel, Status } from '../ui';

type GeoPoint = {
  lat: number;
  lng: number;
  label: string;
};

function verifiedPoints(panels: PanelView[]): GeoPoint[] {
  const points: GeoPoint[] = [];
  for (const panel of panels) {
    for (const evidence of panel.evidence) {
      const locator = evidence.locator;
      const lat = Number(locator.latitude ?? locator.lat);
      const lng = Number(locator.longitude ?? locator.lng);
      if (
        Number.isFinite(lat)
        && Number.isFinite(lng)
        && lat >= -90
        && lat <= 90
        && lng >= -180
        && lng <= 180
      ) {
        points.push({ lat, lng, label: panel.title });
      }
    }
  }
  return points;
}

export function SituationMap({ panels }: { panels: PanelView[] }) {
  const points = verifiedPoints(panels);
  return (
    <Panel className="situation-map">
      <header className="situation-header">
        <div>
          <span className="eyebrow"><Globe2 size={12} /> VERIFIED SITUATION LAYER</span>
          <h2>全球证据态势</h2>
        </div>
        <div className="map-mode" aria-label="地图模式">
          <button className="active"><Globe2 size={13} /> 3D GRID</button>
          <button disabled title="地理证据不足时不生成战术点位"><Map size={13} /> 2D TACTICAL</button>
        </div>
      </header>
      <div className="globe-stage" aria-label={`已验证地理证据 ${points.length} 个`}>
        <div className="globe-orbit orbit-one" />
        <div className="globe-orbit orbit-two" />
        <div className="globe-core">
          <div className="globe-grid" />
          {points.slice(0, 24).map((point, index) => (
            <span
              className="verified-map-point"
              key={`${point.lat}-${point.lng}-${index}`}
              style={{
                left: `${((point.lng + 180) / 360) * 100}%`,
                top: `${((90 - point.lat) / 180) * 100}%`,
              }}
              title={point.label}
            />
          ))}
        </div>
        <div className="map-readout">
          <Crosshair size={15} />
          <div>
            <strong>{points.length} VERIFIED GEO NODES</strong>
            <span>
              {points.length
                ? '仅显示数据库证据定位器中的明确坐标'
                : '当前证据没有明确坐标；系统未推断或伪造位置'}
            </span>
          </div>
          <Status tone={points.length ? 'ok' : 'neutral'}>
            <ShieldCheck size={12} /> {points.length ? 'TRACEABLE' : 'NO GEO EVIDENCE'}
          </Status>
        </div>
      </div>
    </Panel>
  );
}
