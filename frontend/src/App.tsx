import { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  Archive,
  CheckCircle2,
  ChevronRight,
  Cpu,
  Database,
  Download,
  ExternalLink,
  FileJson2,
  Fingerprint,
  Layers3,
  Plus,
  Radio,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';

import {
  api,
  type DashboardListItem,
  type DashboardProposal,
  type DashboardView,
  type PanelView,
} from './lib/v2-api';

const shortHash = (value: string) => `${value.slice(0, 10)}…${value.slice(-8)}`;
const formatDate = (value: string) =>
  new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value));

function App() {
  const [dashboards, setDashboards] = useState<DashboardListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [view, setView] = useState<DashboardView>();
  const [selectedPanel, setSelectedPanel] = useState<PanelView>();
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [composerOpen, setComposerOpen] = useState(false);

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
        setView(await api.getDashboardView(id, dashboard.latest_version.version));
      } else {
        setView(undefined);
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
    if (!item.latest_version) return;
    setLoading(true);
    try {
      setView(await api.getDashboardView(item.id, item.latest_version.version));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '加载失败');
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
        <button className="primary-button wide" onClick={() => setComposerOpen(true)}>
          <Plus size={16} /> 新建情报主面板
        </button>
        <label className="search-box">
          <Search size={15} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索已保存面板" />
        </label>
        <div className="section-label">主面板</div>
        <nav className="dashboard-list">
          {visibleDashboards.map((item) => (
            <button
              className={`dashboard-link ${selectedId === item.id ? 'active' : ''}`}
              key={item.id}
              onClick={() => void selectDashboard(item)}
            >
              <span className="dashboard-icon"><Database size={15} /></span>
              <span><strong>{item.title}</strong><small>版本 {item.latest_version?.version ?? '—'}</small></span>
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
        <header className="topbar">
          <div>
            <div className="eyebrow"><Radio size={12} /> AUTOMOTIVE INTELLIGENCE / VERIFIED DATA LAYER</div>
            <h1>{view?.dashboard.title ?? '选择主面板'}</h1>
            <p>{view?.dashboard.description}</p>
          </div>
          <div className="topbar-actions">
            <span className="system-pill"><Activity size={14} /> EVIDENCE NODE ONLINE</span>
            {view && <span className="version-pill"><Archive size={14} /> 冻结版本 {view.version.version}</span>}
            <button className="icon-button" aria-label="刷新" onClick={() => void loadDashboards(selectedId)}>
              <RefreshCw size={17} className={loading ? 'spin' : ''} />
            </button>
          </div>
        </header>

        {error && <div className="error-banner">{error}</div>}
        {loading && !view ? <div className="empty-state">正在读取可审计快照…</div> : null}

        {view && (
          <>
            <section className="audit-strip">
              <div><CheckCircle2 /><span><small>SCHEMA STATUS</small><strong>{view.panels.filter((panel) => panel.extraction?.validation.valid).length}/{view.panels.length} 校验通过</strong></span></div>
              <div><Fingerprint /><span><small>PROVENANCE</small><strong>{view.panels.filter((panel) => panel.evidence.length).length} 条完整证据链</strong></span></div>
              <div><FileJson2 /><span><small>FROZEN CONTRACT</small><strong>JSON Schema + UI DSL</strong></span></div>
              <div><Cpu /><span><small>COMPUTE ENGINE</small><strong>确定性映射与核算</strong></span></div>
            </section>

            <section className="panel-grid">
              {view.panels.map((panel) => (
                <PanelCard key={panel.id} panel={panel} onInspect={() => setSelectedPanel(panel)} />
              ))}
            </section>
          </>
        )}
      </main>

      {selectedPanel && <EvidenceDrawer panel={selectedPanel} onClose={() => setSelectedPanel(undefined)} />}
      {composerOpen && (
        <DashboardComposer
          onClose={() => setComposerOpen(false)}
          onSaved={(id) => {
            setComposerOpen(false);
            void loadDashboards(id);
          }}
        />
      )}
    </div>
  );
}

function PanelCard({ panel, onInspect }: { panel: PanelView; onInspect: () => void }) {
  const records = Array.isArray(panel.data?.records) ? panel.data.records : [];
  const columns = panel.ui_dsl.children?.find((item) => item.type === 'table')?.columns
    ?? (records[0] ? Object.keys(records[0]) : []);
  const visibleRecords = records.slice(0, 8);
  const evidence = panel.evidence[0];
  return (
    <article className="panel-card">
      <div className="panel-header">
        <div className="panel-title-group">
          <span className="panel-node"><Database size={15} /></span>
          <div>
            <span className="panel-key">{panel.key}</span>
            <h2>{panel.title}</h2>
            <p>{panel.description}</p>
          </div>
        </div>
        <button className="inspect-button" onClick={onInspect}>溯源终端 <ChevronRight size={14} /></button>
      </div>
      <div className="metric-row">
        <div className="metric-value">{Number(panel.data?.record_count ?? 0).toLocaleString()}</div>
        <div><strong>官方记录</strong><span>LATEST IMMUTABLE SNAPSHOT</span></div>
        <span className={`status-badge ${panel.extraction?.validation.valid ? 'ok' : ''}`}>
          {panel.extraction?.validation.valid ? 'VALID' : 'PENDING'}
        </span>
      </div>
      <div className="table-wrap">
        <table>
          <thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
          <tbody>
            {visibleRecords.map((record, index) => (
              <tr key={index}>
                {columns.map((column) => <td key={column}>{String(record[column] ?? '—')}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <footer className="panel-footer">
        <span><Database size={13} /> {evidence ? new URL(evidence.source_url).hostname : '等待采集'}</span>
        <span><Fingerprint size={13} /> {evidence ? shortHash(evidence.artifact_sha256) : '—'}</span>
        <span>{evidence ? formatDate(evidence.retrieved_at) : '—'}</span>
      </footer>
    </article>
  );
}

function EvidenceDrawer({ panel, onClose }: { panel: PanelView; onClose: () => void }) {
  const evidence = panel.evidence[0];
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(event) => event.stopPropagation()}>
        <div className="drawer-header">
          <div><span className="eyebrow"><ShieldCheck size={12} /> EVIDENCE TRACE TERMINAL</span><h2>{panel.title}</h2></div>
          <button className="icon-button" onClick={onClose}><X size={18} /></button>
        </div>
        <section className="drawer-section">
          <h3>冻结契约</h3>
          <dl className="detail-list">
            <div><dt>面板版本</dt><dd>v{panel.version}</dd></div>
            <div><dt>模板类型</dt><dd>{panel.template_kind}</dd></div>
            <div><dt>抽取引擎</dt><dd>{panel.extraction?.provider} / {panel.extraction?.model}</dd></div>
            <div><dt>提示词版本</dt><dd>{panel.extraction_prompt_version}</dd></div>
            <div><dt>输入哈希</dt><dd className="mono">{panel.extraction?.input_hash}</dd></div>
          </dl>
        </section>
        {evidence && (
          <section className="drawer-section">
            <h3>原始证据</h3>
            <dl className="detail-list">
              <div><dt>定位器</dt><dd className="mono">{evidence.locator_type} {JSON.stringify(evidence.locator)}</dd></div>
              <div><dt>抓取时间</dt><dd>{formatDate(evidence.retrieved_at)}</dd></div>
              <div><dt>媒体类型</dt><dd>{evidence.artifact_media_type}</dd></div>
              <div><dt>原始字节</dt><dd>{evidence.artifact_byte_size.toLocaleString()} bytes</dd></div>
              <div><dt>文件 SHA-256</dt><dd className="mono break">{evidence.artifact_sha256}</dd></div>
              <div><dt>文本 SHA-256</dt><dd className="mono break">{evidence.text_sha256}</dd></div>
            </dl>
            <div className="drawer-actions">
              <a className="secondary-button" href={evidence.source_url} target="_blank" rel="noreferrer">
                <ExternalLink size={15} /> 打开官方来源
              </a>
              <a className="primary-button" href={api.artifactUrl(evidence.artifact_id)}>
                <Download size={15} /> 下载原始文件
              </a>
            </div>
          </section>
        )}
        <section className="drawer-section code-section">
          <h3>JSON Schema</h3>
          <pre>{JSON.stringify(panel.data_schema, null, 2)}</pre>
          <h3>UI DSL</h3>
          <pre>{JSON.stringify(panel.ui_dsl, null, 2)}</pre>
        </section>
      </aside>
    </div>
  );
}

function DashboardComposer({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: (dashboardId: string) => void;
}) {
  const [title, setTitle] = useState('');
  const [provider, setProvider] = useState('openai-compatible');
  const [model, setModel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [proposalText, setProposalText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const propose = async () => {
    setBusy(true);
    setError('');
    try {
      const proposal = await api.proposeDashboard({
        title,
        provider,
        model: model || undefined,
        base_url: baseUrl || undefined,
        api_key: apiKey || undefined,
      });
      setProposalText(JSON.stringify(proposal, null, 2));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '生成失败');
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    setBusy(true);
    setError('');
    try {
      const proposal = JSON.parse(proposalText) as DashboardProposal;
      const key = slugify(proposal.title || title);
      const dashboard = await api.createDashboard({
        key: `${key}-${Date.now().toString(36)}`,
        title: proposal.title || title,
        description: proposal.description || '',
      });
      await api.createDashboardVersion(dashboard.id, {
        state: 'draft',
        research_brief: { title, source: 'llm_proposal' },
        generation_model: proposal._generation?.model,
        generation_prompt_version: 'dashboard-design-v1',
        panels: proposal.panels.map((panel) => ({
          ...panel,
          template_kind: 'ui_dsl',
          extraction_prompt_version: '1',
          model_settings: {},
        })),
      });
      onSaved(dashboard.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '保存失败');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="composer">
        <div className="drawer-header">
          <div><span className="eyebrow"><Sparkles size={12} /> LLM DASHBOARD DESIGNER</span><h2>从课题生成主面板</h2></div>
          <button className="icon-button" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="composer-grid">
          <label className="field span-2"><span>课题标题</span><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="例如：全球人形机器人产业链" /></label>
          <label className="field"><span>模型供应商</span><select value={provider} onChange={(event) => setProvider(event.target.value)}><option value="openai-compatible">OpenAI Compatible</option><option value="google">Google Gemini</option></select></label>
          <label className="field"><span>模型</span><input value={model} onChange={(event) => setModel(event.target.value)} placeholder="组织默认模型" /></label>
          <label className="field"><span>API Base URL</span><input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="使用后端默认配置" /></label>
          <label className="field"><span>临时 API Key</span><input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="不会写入面板版本" /></label>
        </div>
        <div className="composer-toolbar">
          <button className="secondary-button" disabled={!title || busy} onClick={() => void propose()}><RefreshCw size={15} /> 生成设计</button>
          <span>生成后可直接编辑完整结构化文件</span>
        </div>
        <textarea className="json-editor" value={proposalText} onChange={(event) => setProposalText(event.target.value)} placeholder="LLM 生成的组件、JSON Schema、UI DSL、提示词会显示在这里…" />
        {error && <div className="error-banner">{error}</div>}
        <div className="composer-actions">
          <button className="secondary-button" onClick={onClose}>取消</button>
          <button className="primary-button" disabled={!proposalText || busy} onClick={() => void save()}><Archive size={15} /> 保存冻结版本</button>
        </div>
      </div>
    </div>
  );
}

function slugify(value: string) {
  return value
    .normalize('NFKD')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || 'dashboard';
}

export default App;
