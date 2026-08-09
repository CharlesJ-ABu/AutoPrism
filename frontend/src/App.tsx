import { useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, Cpu, FileJson2, Fingerprint } from 'lucide-react';

import { DashboardPanel } from './components/dashboard/DashboardPanel';
import { EvidenceDrawer } from './components/evidence/EvidenceDrawer';
import { CockpitShell, type Perspective } from './components/shell/CockpitShell';
import { SituationMap } from './components/situation/SituationMap';
import { EmptyState, ErrorState, LoadingState } from './components/ui';
import { DashboardComposer } from './features/dashboards/DashboardComposer';
import { VersionManagerDrawer } from './features/dashboards/VersionManagerDrawer';
import { OperationsDrawer } from './features/operations/OperationsDrawer';
import {
  api,
  type DashboardListItem,
  type DashboardView,
  type PanelView,
  type TrustedMapResponse,
} from './lib/v2-api';

const PERSPECTIVE_TERMS: Record<Exclude<Perspective, 'all'>, string[]> = {
  market: ['market', 'make', 'sales', 'price', 'policy', 'rating'],
  product: ['model', 'technology', 'battery', 'software', 'safety', 'rating'],
  supply: ['supply', 'source', 'risk', 'compliance', 'logistics', 'material'],
};

function belongsToPerspective(panel: PanelView, perspective: Perspective) {
  if (perspective === 'all') return true;
  const haystack = `${panel.key} ${panel.title} ${panel.description}`.toLowerCase();
  return PERSPECTIVE_TERMS[perspective].some((term) => haystack.includes(term));
}

function App() {
  const [dashboards, setDashboards] = useState<DashboardListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [view, setView] = useState<DashboardView>();
  const [mapResponse, setMapResponse] = useState<TrustedMapResponse>();
  const [mapLoading, setMapLoading] = useState(false);
  const [mapError, setMapError] = useState('');
  const [selectedPanel, setSelectedPanel] = useState<PanelView>();
  const [query, setQuery] = useState('');
  const [perspective, setPerspective] = useState<Perspective>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [composerOpen, setComposerOpen] = useState(false);
  const [versionManagerOpen, setVersionManagerOpen] = useState(false);
  const [operationsOpen, setOperationsOpen] = useState(false);
  const mapLoadGeneration = useRef(0);
  const overlayOpen = Boolean(
    selectedPanel || composerOpen || versionManagerOpen || operationsOpen,
  );

  useEffect(() => {
    if (!overlayOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [overlayOpen]);

  const loadMapFeatures = async (panels: PanelView[]) => {
    const generation = mapLoadGeneration.current + 1;
    mapLoadGeneration.current = generation;
    setMapLoading(true);
    setMapError('');
    setMapResponse(undefined);
    try {
      const response = await api.listMapFeatures(panels.map((panel) => panel.id));
      if (mapLoadGeneration.current === generation) setMapResponse(response);
    } catch (reason) {
      if (mapLoadGeneration.current === generation) {
        setMapResponse(undefined);
        setMapError(reason instanceof Error ? reason.message : '地图加载失败');
      }
    } finally {
      if (mapLoadGeneration.current === generation) setMapLoading(false);
    }
  };

  const loadDashboards = async (preferredId?: string) => {
    setLoading(true);
    setError('');
    try {
      const items = await api.listDashboards();
      setDashboards(items);
      const id = preferredId ?? selectedId ?? items[0]?.id;
      setSelectedId(id);
      const dashboard = items.find((item) => item.id === id);
      if (dashboard?.latest_version) {
        const nextView = await api.getDashboardView(id, dashboard.latest_version.version);
        setView(nextView);
        void loadMapFeatures(nextView.panels);
      } else {
        mapLoadGeneration.current += 1;
        setView(undefined);
        setMapResponse(undefined);
        setMapLoading(false);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDashboards();
  }, []);

  const selectDashboard = async (item: DashboardListItem) => {
    setSelectedId(item.id);
    setSelectedPanel(undefined);
    setError('');
    if (!item.latest_version) {
      mapLoadGeneration.current += 1;
      setView(undefined);
      setMapResponse(undefined);
      setMapLoading(false);
      return;
    }
    setLoading(true);
    try {
      const nextView = await api.getDashboardView(item.id, item.latest_version.version);
      setView(nextView);
      void loadMapFeatures(nextView.panels);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const openDashboardVersion = async (dashboardId: string, version: number) => {
    setLoading(true);
    setError('');
    setSelectedPanel(undefined);
    try {
      const nextView = await api.getDashboardView(dashboardId, version);
      setView(nextView);
      void loadMapFeatures(nextView.panels);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '版本加载失败');
    } finally {
      setLoading(false);
    }
  };

  const visibleDashboards = useMemo(
    () =>
      dashboards.filter((item) =>
        `${item.title} ${item.description}`.toLowerCase().includes(query.toLowerCase()),
      ),
    [dashboards, query],
  );

  const visiblePanels = useMemo(
    () => view?.panels.filter((panel) => belongsToPerspective(panel, perspective)) ?? [],
    [perspective, view],
  );

  const validPanelCount = view?.panels.filter(
    (panel) => panel.extraction?.validation.valid === true,
  ).length ?? 0;
  const evidenceFragmentCount = view?.panels.reduce(
    (count, panel) => count + panel.evidence.length,
    0,
  ) ?? 0;

  return (
    <CockpitShell
      dashboards={dashboards}
      visibleDashboards={visibleDashboards}
      selectedId={selectedId}
      query={query}
      onQueryChange={setQuery}
      onDashboardSelect={(item) => void selectDashboard(item)}
      onCreate={() => {
        setSelectedPanel(undefined);
        setVersionManagerOpen(false);
        setOperationsOpen(false);
        setComposerOpen(true);
      }}
      perspective={perspective}
      onPerspectiveChange={setPerspective}
      title={view?.dashboard.title ?? '选择可信情报主面板'}
      description={view?.dashboard.description}
      version={view?.version.version}
      loading={loading}
      onRefresh={() => void loadDashboards(selectedId)}
      onManageVersions={view ? () => {
        setSelectedPanel(undefined);
        setComposerOpen(false);
        setOperationsOpen(false);
        setVersionManagerOpen(true);
      } : undefined}
      onManageOperations={() => {
        setSelectedPanel(undefined);
        setComposerOpen(false);
        setVersionManagerOpen(false);
        setOperationsOpen(true);
      }}
      overlayOpen={overlayOpen}
    >
      {error && <ErrorState message={error} onRetry={() => void loadDashboards(selectedId)} />}
      {loading && !view && <LoadingState />}

      {!loading && !error && dashboards.length === 0 && (
        <EmptyState
          title="尚无主面板"
          description="新建主面板后，系统会保存冻结契约；没有数据时不会填充演示数值。"
        />
      )}

      {view && (
        <>
          <SituationMap
            response={mapResponse}
            loading={mapLoading}
            error={mapError}
            onRetry={() => void loadMapFeatures(view.panels)}
            onInspectPanel={(panelVersionKey) => {
              const panel = view.panels.find((item) => item.id === panelVersionKey);
              if (panel) setSelectedPanel(panel);
            }}
          />
          <section className="audit-strip" aria-label="可信度摘要">
            <div>
              <CheckCircle2 />
              <span><small>SCHEMA STATUS</small><strong>{validPanelCount}/{view.panels.length} 个面板校验通过</strong></span>
            </div>
            <div>
              <Fingerprint />
              <span><small>PROVENANCE</small><strong>{evidenceFragmentCount} 个证据定位片段</strong></span>
            </div>
            <div>
              <FileJson2 />
              <span><small>VERSION STATE</small><strong>{view.version.state.toUpperCase()} · JSON Schema + UI DSL</strong></span>
            </div>
            <div>
              <Cpu />
              <span><small>COMPUTE POLICY</small><strong>仅确定性代码可形成权威数值</strong></span>
            </div>
          </section>

          {visiblePanels.length ? (
            <section className="panel-grid">
              {visiblePanels.map((panel) => (
                <DashboardPanel
                  key={panel.id}
                  panel={panel}
                  onInspect={() => setSelectedPanel(panel)}
                />
              ))}
            </section>
          ) : (
            <EmptyState
              title="当前视角没有匹配面板"
              description="视角只筛选数据库中的现有面板；系统不会为填满驾驶舱而生成内容。"
            />
          )}
        </>
      )}

      {selectedPanel && (
        <EvidenceDrawer panel={selectedPanel} onClose={() => setSelectedPanel(undefined)} />
      )}
      {composerOpen && (
        <DashboardComposer
          onClose={() => setComposerOpen(false)}
          onSaved={(id) => {
            setComposerOpen(false);
            void loadDashboards(id);
          }}
        />
      )}
      {versionManagerOpen && view && (
        <VersionManagerDrawer
          dashboardId={view.dashboard.id}
          dashboardTitle={view.dashboard.title}
          viewedVersion={view.version.version}
          onClose={() => setVersionManagerOpen(false)}
          onOpenVersion={(version) => openDashboardVersion(view.dashboard.id, version)}
          onCreated={() => loadDashboards(view.dashboard.id)}
        />
      )}
      {operationsOpen && (
        <OperationsDrawer
          panels={view?.panels ?? []}
          onClose={() => setOperationsOpen(false)}
          onExtractionComplete={() => loadDashboards(selectedId)}
        />
      )}
    </CockpitShell>
  );
}

export default App;
