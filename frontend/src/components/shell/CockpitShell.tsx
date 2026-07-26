import type { ReactNode } from 'react';
import {
  Activity,
  Archive,
  ChevronRight,
  Database,
  Layers3,
  History,
  Plus,
  Radio,
  RefreshCw,
  Search,
} from 'lucide-react';

import type { DashboardListItem } from '../../lib/v2-api';
import { Button, IconButton } from '../ui';

export type Perspective = 'all' | 'market' | 'product' | 'supply';

const PERSPECTIVES: Array<{ id: Perspective; label: string }> = [
  { id: 'all', label: '全量情报' },
  { id: 'market', label: '市场与政策' },
  { id: 'product', label: '产品与技术' },
  { id: 'supply', label: '供应链与合规' },
];

export function CockpitShell({
  dashboards,
  visibleDashboards,
  selectedId,
  query,
  onQueryChange,
  onDashboardSelect,
  onCreate,
  perspective,
  onPerspectiveChange,
  title,
  description,
  version,
  loading,
  onRefresh,
  onManageVersions,
  children,
}: {
  dashboards: DashboardListItem[];
  visibleDashboards: DashboardListItem[];
  selectedId?: string;
  query: string;
  onQueryChange: (value: string) => void;
  onDashboardSelect: (dashboard: DashboardListItem) => void;
  onCreate: () => void;
  perspective: Perspective;
  onPerspectiveChange: (perspective: Perspective) => void;
  title: string;
  description?: string;
  version?: number;
  loading: boolean;
  onRefresh: () => void;
  onManageVersions?: () => void;
  children: ReactNode;
}) {
  return (
    <div className="app-shell">
      <div className="nebula nebula-one" />
      <div className="nebula nebula-two" />
      <div className="grid-field" />
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Layers3 size={20} /></div>
          <div><strong>AutoPrism</strong><span>INTELLIGENCE EVIDENCE OS · V2</span></div>
        </div>
        <Button variant="primary" wide onClick={onCreate}>
          <Plus size={16} /> 新建情报主面板
        </Button>
        <label className="search-box">
          <Search size={15} />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="搜索已保存面板"
          />
        </label>
        <div className="section-label">主面板 · {dashboards.length}</div>
        <nav className="dashboard-list" aria-label="主面板">
          {visibleDashboards.map((item) => (
            <button
              className={`dashboard-link ${selectedId === item.id ? 'active' : ''}`}
              key={item.id}
              onClick={() => onDashboardSelect(item)}
            >
              <span className="dashboard-icon"><Database size={15} /></span>
              <span>
                <strong>{item.title}</strong>
                <small>版本 {item.latest_version?.version ?? '—'} · {item.latest_version?.state ?? 'empty'}</small>
              </span>
              <ChevronRight size={14} />
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="live-dot" />
          <div><strong>LOCAL TRUST NODE · ONLINE</strong><span>原始证据内容寻址存储</span></div>
        </div>
      </aside>

      <main className="workspace">
        <div className="mission-bar">
          <div className="mission-brand"><Radio size={13} /> VERIFIED INTELLIGENCE COCKPIT</div>
          <nav className="perspective-switcher" aria-label="情报视角">
            {PERSPECTIVES.map((item) => (
              <button
                aria-pressed={perspective === item.id}
                className={perspective === item.id ? 'active' : ''}
                key={item.id}
                onClick={() => onPerspectiveChange(item.id)}
              >
                {item.label}
              </button>
            ))}
          </nav>
          <span className="system-pill"><Activity size={14} /> EVIDENCE NODE ONLINE</span>
        </div>

        <header className="topbar">
          <div>
            <div className="eyebrow"><Radio size={12} /> AUTOMOTIVE INTELLIGENCE / VERIFIED DATA LAYER</div>
            <h1>{title}</h1>
            {description && <p>{description}</p>}
          </div>
          <div className="topbar-actions">
            {version && <span className="version-pill"><Archive size={14} /> 当前版本 {version}</span>}
            {version && onManageVersions && (
              <Button onClick={onManageVersions}>
                <History size={14} /> 版本与编辑
              </Button>
            )}
            <IconButton aria-label="刷新数据" onClick={onRefresh}>
              <RefreshCw size={17} className={loading ? 'spin' : ''} />
            </IconButton>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
