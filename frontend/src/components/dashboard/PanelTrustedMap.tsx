import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { Crosshair, LoaderCircle, MapPinned, RefreshCw, ShieldCheck } from 'lucide-react';

import type { TrustedMapFeature, UiDslNode } from '../../lib/v2-api';
import { Button, Status } from '../ui';

const TrustedTacticalMap = lazy(() => import('../situation/TrustedTacticalMap'));

export function PanelTrustedMap({
  node,
  features,
  loading,
  error,
  onRetry,
  onInspect,
}: {
  node: UiDslNode;
  features: TrustedMapFeature[];
  loading: boolean;
  error: string;
  onRetry: () => void;
  onInspect: () => void;
}) {
  const limit = Number.isInteger(node.max_features)
    ? Math.min(100, Math.max(1, node.max_features as number))
    : 24;
  const visibleFeatures = useMemo(() => features.slice(0, limit), [features, limit]);
  const hiddenCount = Math.max(0, features.length - visibleFeatures.length);
  const showIndex = node.show_index !== false;
  const [selected, setSelected] = useState<TrustedMapFeature>();
  const statusTone = error ? 'danger' : loading ? 'info' : visibleFeatures.length ? 'ok' : 'neutral';
  const statusLabel = error ? 'ERROR' : loading ? 'LOADING' : visibleFeatures.length ? 'REPLAYED' : 'EMPTY';

  useEffect(() => {
    if (selected && !visibleFeatures.some((feature) => feature.id === selected.id)) {
      setSelected(undefined);
    }
  }, [selected, visibleFeatures]);

  return (
    <section className="panel-trusted-map" aria-label={node.label ?? '面板可信地图'}>
      <header>
        <div>
          <span className="eyebrow"><MapPinned size={11} /> TRUSTED MAP DSL · CURRENT L2 ONLY</span>
          <strong>{node.label ?? '当前可信地理洞察'}</strong>
        </div>
        <Status tone={statusTone}>
          <ShieldCheck size={11} /> {statusLabel}
        </Status>
      </header>

      <div className="panel-map-stage">
        {!loading && !error && visibleFeatures.length > 0 && (
          <Suspense fallback={(
            <div className="panel-map-state"><LoaderCircle className="spin" /> 正在初始化 2D 可信地图…</div>
          )}>
            <TrustedTacticalMap
              features={visibleFeatures}
              mapStyle="cyber"
              selectedId={selected?.id}
              onSelect={setSelected}
            />
          </Suspense>
        )}
        {loading && (
          <div className="panel-map-state"><LoaderCircle className="spin" /> 正在重放当前可信要素…</div>
        )}
        {!loading && error && (
          <div className="panel-map-state panel-map-error">
            <strong>可信地图加载失败</strong>
            <span>{error}</span>
            <Button variant="secondary" onClick={onRetry}><RefreshCw size={12} /> 重试</Button>
          </div>
        )}
        {!loading && !error && visibleFeatures.length === 0 && (
          <div className="panel-map-state">
            <ShieldCheck size={20} />
            <strong>该面板暂无当前可信地理要素</strong>
            <span>只读取 trusted-insight-map-v1；不会把未验证坐标或标签直接上图。</span>
          </div>
        )}
        {selected && (
          <aside className="panel-map-selection">
            <span>{selected.display_type}</span>
            <strong>{selected.title}</strong>
            <small>{selected.label} · {selected.observation_ids.length} 个输入观测</small>
            <button type="button" onClick={onInspect}><Crosshair size={11} /> 打开该面板证据链</button>
          </aside>
        )}
      </div>

      {showIndex && visibleFeatures.length > 0 && (
        <div className="panel-map-index" aria-label="面板可信地图要素">
          {visibleFeatures.map((feature) => (
            <button
              type="button"
              className={selected?.id === feature.id ? 'active' : ''}
              key={feature.id}
              onClick={() => setSelected(feature)}
            >
              <span>{feature.display_type}</span>
              <strong>{feature.label}</strong>
            </button>
          ))}
        </div>
      )}
      <footer>
        <span>{visibleFeatures.length} / {features.length} CURRENT FEATURES</span>
        <span>{hiddenCount ? `${hiddenCount} 个超出冻结显示上限` : '无客户端推断或补点'}</span>
      </footer>
    </section>
  );
}
