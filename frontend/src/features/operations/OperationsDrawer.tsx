import { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  DatabaseZap,
  ExternalLink,
  FilePlus2,
  LockKeyhole,
  Play,
  RefreshCw,
  ShieldCheck,
} from 'lucide-react';

import { formatDate, safeHostname, slugify } from '../../lib/format';
import {
  api,
  type CollectionJob,
  type HumanAction,
  type PanelView,
  type SourceDefinition,
  type SourcePool,
} from '../../lib/v2-api';
import { Button, Drawer, LoadingState, Status } from '../../components/ui';

type OperationsTab = 'sources' | 'jobs' | 'actions';

export function OperationsDrawer({
  panels,
  onClose,
  onExtractionComplete,
}: {
  panels: PanelView[];
  onClose: () => void;
  onExtractionComplete: () => Promise<void>;
}) {
  const [tab, setTab] = useState<OperationsTab>('sources');
  const [pools, setPools] = useState<SourcePool[]>([]);
  const [sources, setSources] = useState<SourceDefinition[]>([]);
  const [jobs, setJobs] = useState<CollectionJob[]>([]);
  const [actions, setActions] = useState<HumanAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');
  const [complianceConfirmed, setComplianceConfirmed] = useState(false);
  const [extractionPanelId, setExtractionPanelId] = useState(panels[0]?.id ?? '');
  const [extractionResult, setExtractionResult] = useState('');
  const [poolForm, setPoolForm] = useState({ name: '', topic: '' });
  const [sourceForm, setSourceForm] = useState({
    pool_id: '',
    name: '',
    canonical_url: '',
    kind: 'api',
    global_reputation: '',
    topic_authority: '',
  });

  const sourceById = useMemo(
    () => new Map(sources.map((source) => [source.id, source])),
    [sources],
  );

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [nextPools, nextSources, nextJobs, nextActions] = await Promise.all([
        api.listSourcePools(),
        api.listSources(),
        api.listCollectionJobs(),
        api.listHumanActions(),
      ]);
      setPools(nextPools);
      setSources(nextSources);
      setJobs(nextJobs);
      setActions(nextActions);
      setSourceForm((current) => ({
        ...current,
        pool_id: current.pool_id || nextPools[0]?.id || '',
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '采集工作区加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const createPool = async () => {
    setBusyId('pool');
    setError('');
    try {
      const pool = await api.createSourcePool({
        key: `${slugify(poolForm.name)}-${Date.now().toString(36)}`,
        name: poolForm.name,
        topic: poolForm.topic,
      });
      setPoolForm({ name: '', topic: '' });
      setSourceForm((current) => ({ ...current, pool_id: pool.id }));
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '来源池创建失败');
    } finally {
      setBusyId('');
    }
  };

  const createSource = async () => {
    setBusyId('source');
    setError('');
    try {
      await api.createSource(sourceForm.pool_id, {
        key: `${slugify(sourceForm.name)}-${Date.now().toString(36)}`,
        name: sourceForm.name,
        canonical_url: sourceForm.canonical_url,
        kind: sourceForm.kind,
        global_reputation: Number(sourceForm.global_reputation),
        topic_authority: Number(sourceForm.topic_authority),
      });
      setSourceForm((current) => ({
        ...current,
        name: '',
        canonical_url: '',
        global_reputation: '',
        topic_authority: '',
      }));
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '来源创建失败');
    } finally {
      setBusyId('');
    }
  };

  const collect = async (sourceId: string) => {
    setBusyId(sourceId);
    setError('');
    try {
      await api.collectSource(sourceId);
      setTab('jobs');
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '采集任务创建失败');
    } finally {
      setBusyId('');
    }
  };

  const extract = async (job: CollectionJob) => {
    if (!job.result_snapshot_id || !extractionPanelId) return;
    setBusyId(`extract:${job.id}`);
    setError('');
    setExtractionResult('');
    try {
      const result = await api.runExtraction({
        panel_version_id: extractionPanelId,
        snapshot_id: job.result_snapshot_id,
      });
      setExtractionResult(
        `抽取运行 ${result.run_id} · ${result.observation_ids.length} 个观察值 · ${result.issues.length} 个 Schema 问题`,
      );
      await onExtractionComplete();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '结构化抽取失败');
    } finally {
      setBusyId('');
    }
  };

  const sourceFormValid = Boolean(
    sourceForm.pool_id
    && sourceForm.name
    && sourceForm.canonical_url
    && sourceForm.global_reputation !== ''
    && sourceForm.topic_authority !== '',
  );

  return (
    <Drawer
      eyebrow={<><DatabaseZap size={12} /> COMPLIANT ACQUISITION CONTROL</>}
      title="采集与人工处理工作区"
      onClose={onClose}
      wide
    >
      <nav className="drawer-tabs" aria-label="采集工作区">
        <button className={tab === 'sources' ? 'active' : ''} onClick={() => setTab('sources')}>来源与采集</button>
        <button className={tab === 'jobs' ? 'active' : ''} onClick={() => setTab('jobs')}>任务 · {jobs.length}</button>
        <button className={tab === 'actions' ? 'active' : ''} onClick={() => setTab('actions')}>人工处理 · {actions.filter((item) => item.state === 'open').length}</button>
        <Button variant="ghost" onClick={() => void load()}><RefreshCw size={13} /> 刷新</Button>
      </nav>

      {loading ? <LoadingState label="正在读取采集状态…" /> : null}
      {error && <div className="error-banner">{error}</div>}

      {!loading && tab === 'sources' && (
        <>
          <section className="drawer-section">
            <div className="drawer-section-title">
              <h3>合规边界</h3>
              <Status tone="warning"><LockKeyhole size={12} /> HUMAN GATE</Status>
            </div>
            <p className="section-help">
              仅采集用户有权访问且允许自动访问的内容。条款、robots、频率、登录、
              CAPTCHA 或访问限制会暂停任务并进入人工处理，不允许绕过。
            </p>
            <label className="publish-confirmation">
              <input type="checkbox" checked={complianceConfirmed} onChange={(event) => setComplianceConfirmed(event.target.checked)} />
              <ShieldCheck size={15} />
              我确认本次采集目标已获授权，并接受系统在限制出现时暂停。
            </label>
          </section>

          <section className="drawer-section">
            <h3>已注册来源</h3>
            <div className="source-list">
              {sources.map((source) => (
                <article className="source-item" key={source.id}>
                  <div>
                    <span className="panel-key">{source.kind} · {safeHostname(source.canonical_url)}</span>
                    <h4>{source.name}</h4>
                    <p>
                      全局声誉 {source.global_reputation} · 主题权威 {source.topic_authority}
                      {source.requires_auth ? ' · 需要登录，自动采集将暂停' : ''}
                    </p>
                  </div>
                  <div className="version-actions">
                    <a className="ghost-button" href={source.canonical_url} target="_blank" rel="noreferrer"><ExternalLink size={13} /> 来源</a>
                    <Button
                      disabled={!source.enabled || !complianceConfirmed || busyId === source.id}
                      onClick={() => void collect(source.id)}
                    >
                      <Play size={13} /> 创建采集任务
                    </Button>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="drawer-section operation-forms">
            <div>
              <h3>新建来源池</h3>
              <label className="field"><span>名称</span><input value={poolForm.name} onChange={(event) => setPoolForm({ ...poolForm, name: event.target.value })} /></label>
              <label className="field"><span>研究主题</span><input value={poolForm.topic} onChange={(event) => setPoolForm({ ...poolForm, topic: event.target.value })} /></label>
              <Button disabled={!poolForm.name || !poolForm.topic || busyId === 'pool'} onClick={() => void createPool()}><FilePlus2 size={13} /> 创建来源池</Button>
            </div>
            <div>
              <h3>注册直接来源</h3>
              <label className="field"><span>来源池</span><select value={sourceForm.pool_id} onChange={(event) => setSourceForm({ ...sourceForm, pool_id: event.target.value })}>{pools.map((pool) => <option key={pool.id} value={pool.id}>{pool.name}</option>)}</select></label>
              <label className="field"><span>名称</span><input value={sourceForm.name} onChange={(event) => setSourceForm({ ...sourceForm, name: event.target.value })} /></label>
              <label className="field"><span>官方 URL</span><input value={sourceForm.canonical_url} onChange={(event) => setSourceForm({ ...sourceForm, canonical_url: event.target.value })} /></label>
              <label className="field"><span>类型</span><select value={sourceForm.kind} onChange={(event) => setSourceForm({ ...sourceForm, kind: event.target.value })}><option value="api">API</option><option value="html">HTML</option><option value="pdf">PDF</option><option value="csv">CSV</option><option value="xlsx">Excel</option><option value="rss">RSS</option></select></label>
              <div className="trust-fields">
                <label className="field"><span>全局声誉 0–1（必填）</span><input type="number" min="0" max="1" step="0.1" value={sourceForm.global_reputation} onChange={(event) => setSourceForm({ ...sourceForm, global_reputation: event.target.value })} /></label>
                <label className="field"><span>主题权威 0–1（必填）</span><input type="number" min="0" max="1" step="0.1" value={sourceForm.topic_authority} onChange={(event) => setSourceForm({ ...sourceForm, topic_authority: event.target.value })} /></label>
              </div>
              <Button disabled={!sourceFormValid || busyId === 'source'} onClick={() => void createSource()}><FilePlus2 size={13} /> 注册来源</Button>
            </div>
          </section>
        </>
      )}

      {!loading && tab === 'jobs' && (
        <section className="drawer-section">
          <h3>采集任务</h3>
          <div className="extraction-toolbar">
            <label className="field">
              <span>成功快照的目标冻结面板</span>
              <select value={extractionPanelId} onChange={(event) => setExtractionPanelId(event.target.value)}>
                {panels.map((panel) => <option key={panel.id} value={panel.id}>{panel.title} · v{panel.version}</option>)}
              </select>
            </label>
            <p>
              抽取严格使用所选面板冻结的 Schema、提示词和模型设置。确定性映射由代码执行；
              其他模型使用后端环境配置，缺少凭证时明确失败。
            </p>
          </div>
          {extractionResult && <div className="success-banner">{extractionResult}</div>}
          <div className="timeline-list">
            {jobs.map((job) => {
              const source = sourceById.get(job.source_definition_id);
              return (
                <article key={job.id}>
                  <Status tone={job.state === 'succeeded' ? 'ok' : job.state === 'failed' || job.state === 'blocked' ? 'danger' : 'info'}>{job.state.toUpperCase()}</Status>
                  <div>
                    <strong>{source?.name ?? job.source_definition_id}</strong>
                    <span>{formatDate(job.requested_at)} · 尝试 {job.attempt_count}/{job.max_attempts}</span>
                    <small>{job.result_snapshot_id ? `快照 ${job.result_snapshot_id}` : JSON.stringify(job.error)}</small>
                    {job.state === 'succeeded' && job.result_snapshot_id && (
                      <Button
                        disabled={!extractionPanelId || busyId === `extract:${job.id}`}
                        onClick={() => void extract(job)}
                      >
                        <DatabaseZap size={13} /> 运行结构化抽取
                      </Button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}

      {!loading && tab === 'actions' && (
        <section className="drawer-section">
          <h3>人工处理请求</h3>
          {actions.length ? <div className="timeline-list">{actions.map((action) => <article key={action.id}><Status tone={action.state === 'open' ? 'warning' : 'neutral'}>{action.state.toUpperCase()}</Status><div><strong>{action.reason_code}</strong><span>{action.instructions}</span><small>{formatDate(action.created_at)}</small></div></article>)}</div> : <div className="panel-empty"><AlertTriangle size={16} /> 当前没有人工处理请求。</div>}
        </section>
      )}
    </Drawer>
  );
}
