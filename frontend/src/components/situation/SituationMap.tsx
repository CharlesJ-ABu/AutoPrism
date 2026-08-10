import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Crosshair,
  FileSearch,
  Globe2,
  ListFilter,
  LoaderCircle,
  Map,
  RefreshCw,
  Search,
  ShieldCheck,
  X,
} from 'lucide-react';

import type {
  TrustedMapFeature,
  TrustedMapResponse,
} from '../../lib/v2-api';
import { Button, Panel, Status } from '../ui';
import type { MapStyle } from './TrustedGlobeMap';

const TrustedGlobeMap = lazy(() => import('./TrustedGlobeMap'));
const TrustedTacticalMap = lazy(() => import('./TrustedTacticalMap'));

type MapMode = 'globe' | 'tactical';
type MapDisplayType = TrustedMapFeature['display_type'];

interface SituationMapProps {
  response?: TrustedMapResponse;
  loading: boolean;
  error: string;
  onRetry: () => void;
  onInspectPanel: (panelVersionKey: string) => void;
}

function geometryLabel(feature: TrustedMapFeature) {
  if (feature.geometry.type === 'Point') {
    const [longitude, latitude] = feature.geometry.coordinates;
    return `${latitude.toFixed(4)}°, ${longitude.toFixed(4)}°`;
  }
  if (feature.geometry.type === 'LineString') {
    const [[startLng, startLat], [endLng, endLat]] = feature.geometry.coordinates;
    return `${startLat.toFixed(2)}, ${startLng.toFixed(2)} → ${endLat.toFixed(2)}, ${endLng.toFixed(2)}`;
  }
  return `${feature.geometry.coordinates[0].length - 1} 个边界节点`;
}

export function SituationMap({
  response,
  loading,
  error,
  onRetry,
  onInspectPanel,
}: SituationMapProps) {
  const [mode, setMode] = useState<MapMode>('globe');
  const [mapStyle, setMapStyle] = useState<MapStyle>('cyber');
  const [selected, setSelected] = useState<TrustedMapFeature>();
  const [query, setQuery] = useState('');
  const [displayType, setDisplayType] = useState<'ALL' | MapDisplayType>('ALL');
  const [indexOpen, setIndexOpen] = useState(false);
  const features = response?.features ?? [];
  const stats = response?.stats;
  const filtering = displayType !== 'ALL' || query.trim().length > 0;
  const availableTypes = useMemo(
    () => [...new Set(features.map((feature) => feature.display_type))].sort(),
    [features],
  );
  const filteredFeatures = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    return features.filter((feature) => (
      (displayType === 'ALL' || feature.display_type === displayType)
      && (
        !needle
        || feature.title.toLocaleLowerCase().includes(needle)
        || feature.label.toLocaleLowerCase().includes(needle)
        || feature.summary.toLocaleLowerCase().includes(needle)
      )
    ));
  }, [displayType, features, query]);

  useEffect(() => {
    if (selected && !filteredFeatures.some((feature) => feature.id === selected.id)) {
      setSelected(undefined);
    }
  }, [filteredFeatures, selected]);

  useEffect(() => {
    if (displayType !== 'ALL' && !availableTypes.includes(displayType)) {
      setDisplayType('ALL');
    }
  }, [availableTypes, displayType]);

  const selectFeature = (feature: TrustedMapFeature) => {
    setSelected(feature);
    setIndexOpen(false);
  };

  const engine = mode === 'globe' ? (
    <TrustedGlobeMap
      features={filteredFeatures}
      mapStyle={mapStyle}
      selectedId={selected?.id}
      onSelect={selectFeature}
    />
  ) : (
    <TrustedTacticalMap
      features={filteredFeatures}
      mapStyle={mapStyle}
      selectedId={selected?.id}
      onSelect={selectFeature}
    />
  );

  return (
    <Panel className="situation-map trusted-situation-map">
      <header className="situation-header">
        <div>
          <span className="eyebrow"><Globe2 size={12} /> TRUSTED INSIGHT MAP · V1</span>
          <h2>全球可信洞察态势</h2>
        </div>
        <div className="map-toolbar">
          <div className="map-style-switch" aria-label="地图风格">
            {(['industrial', 'cyber', 'ghost'] as const).map((style) => (
              <button
                className={mapStyle === style ? 'active' : ''}
                key={style}
                onClick={() => setMapStyle(style)}
              >
                {style}
              </button>
            ))}
          </div>
          <div className="map-mode" aria-label="地图模式">
            <button className={mode === 'globe' ? 'active' : ''} onClick={() => setMode('globe')}>
              <Globe2 size={13} /> 3D GLOBE
            </button>
            <button className={mode === 'tactical' ? 'active' : ''} onClick={() => setMode('tactical')}>
              <Map size={13} /> 2D TACTICAL
            </button>
          </div>
        </div>
      </header>

      <div className="trusted-map-stage" aria-label={`当前显示可信地图要素 ${filteredFeatures.length} 个，共 ${features.length} 个`}>
        <Suspense fallback={(
          <div className="map-engine-loading"><LoaderCircle className="spin" /> 正在初始化地图引擎…</div>
        )}>
          {engine}
        </Suspense>

        {!loading && !error && features.length === 0 && (
          <div className="map-empty-overlay">
            <ShieldCheck size={25} />
            <strong>当前没有可上图的可信洞察</strong>
            <span>只接受 geo-scope-v1 坐标证据与当前 ELIGIBLE 的 L2 输入；系统不会推断或散布装饰点位。</span>
          </div>
        )}
        {!loading && !error && features.length > 0 && filteredFeatures.length === 0 && (
          <div className="map-empty-overlay">
            <Search size={25} />
            <strong>没有符合当前筛选的可信洞察</strong>
            <span>筛选不会改变或隐藏底层历史；清除条件即可恢复全部 {features.length} 个当前可信要素。</span>
            <Button variant="secondary" onClick={() => { setQuery(''); setDisplayType('ALL'); }}>
              清除筛选
            </Button>
          </div>
        )}
        {loading && (
          <div className="map-empty-overlay"><LoaderCircle className="spin" /><strong>正在重放可信地图契约</strong></div>
        )}
        {error && (
          <div className="map-empty-overlay map-error-overlay">
            <FileSearch size={24} />
            <strong>地图可信数据加载失败</strong>
            <span>{error}</span>
            <Button variant="secondary" onClick={onRetry}><RefreshCw size={13} /> 重试</Button>
          </div>
        )}

        {!loading && !error && features.length > 0 && (
          <div className="map-data-controls" aria-label="可信地图筛选">
            <label>
              <Search size={13} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="检索标题、地点或摘要"
                aria-label="检索可信地图要素"
              />
            </label>
            <select
              value={displayType}
              onChange={(event) => setDisplayType(event.target.value as 'ALL' | MapDisplayType)}
              aria-label="按地图要素类型筛选"
            >
              <option value="ALL">全部类型</option>
              {availableTypes.map((type) => <option key={type} value={type}>{type}</option>)}
            </select>
            <button
              className={indexOpen ? 'active' : ''}
              onClick={() => setIndexOpen((value) => !value)}
              aria-expanded={indexOpen}
            >
              <ListFilter size={13} /> 索引 {filteredFeatures.length}
            </button>
          </div>
        )}

        {indexOpen && filteredFeatures.length > 0 && (
          <aside className="map-feature-index" aria-label="可信地图要素索引">
            <header>
              <span><ListFilter size={12} /> CURRENT FEATURE INDEX</span>
              <button onClick={() => setIndexOpen(false)} aria-label="关闭要素索引"><X size={13} /></button>
            </header>
            <ol>
              {filteredFeatures.map((feature) => (
                <li key={feature.id}>
                  <button onClick={() => selectFeature(feature)}>
                    <span>{feature.display_type}</span>
                    <strong>{feature.title}</strong>
                    <small>{feature.label} · {feature.observation_ids.length} 个输入观测</small>
                  </button>
                </li>
              ))}
            </ol>
          </aside>
        )}

        {selected && (
          <aside className="map-insight-card" aria-label="地图洞察详情">
            <button className="map-card-close" onClick={() => setSelected(undefined)} aria-label="关闭洞察详情"><X size={14} /></button>
            <span className="eyebrow"><Crosshair size={11} /> {selected.display_type}</span>
            <h3>{selected.title}</h3>
            <strong>{selected.label}</strong>
            <p>{selected.summary}</p>
            <dl>
              <div><dt>坐标契约</dt><dd>{geometryLabel(selected)}</dd></div>
              <div><dt>输入观测</dt><dd>{selected.observation_ids.length}</dd></div>
              <div><dt>地图契约</dt><dd>{selected.contract_version}</dd></div>
            </dl>
            <Status tone="ok"><ShieldCheck size={12} /> CURRENT ELIGIBLE</Status>
            {selected.panel_version_keys[0] && (
              <Button
                variant="secondary"
                onClick={() => onInspectPanel(selected.panel_version_keys[0])}
              >
                <Box size={13} /> 打开完整证据链
              </Button>
            )}
          </aside>
        )}
      </div>

      <div className="map-readout trusted-map-readout">
        <Crosshair size={15} />
        <div>
          <strong>{filteredFeatures.length} / {features.length} CURRENT TRUSTED FEATURES</strong>
          <span>{stats ? `${stats.current_insights} 个当前洞察 · ${stats.without_geography} 个缺少坐标 · ${stats.stale_or_invalid_insights} 个已失效` : '等待可信地图响应'}</span>
        </div>
        <Status tone={filteredFeatures.length ? 'ok' : 'neutral'}>
          <ShieldCheck size={12} /> {features.length
            ? filtering ? 'FILTERED REPLAY' : 'REPLAYED'
            : 'EMPTY BY CONTRACT'}
        </Status>
      </div>
    </Panel>
  );
}
