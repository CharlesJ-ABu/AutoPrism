import { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  DatabaseZap,
  ExternalLink,
  FilePlus2,
  LockKeyhole,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
} from 'lucide-react';

import { formatDate, safeHostname, shortHash, slugify } from '../../lib/format';
import {
  api,
  type CollectionJob,
  type HumanAction,
  type PanelView,
  type SourceDefinition,
  type SourceDiscoveryCandidate,
  type SourceDiscoveryRun,
  type SourcePool,
} from '../../lib/v2-api';
import { Button, Drawer, LoadingState, Status } from '../../components/ui';

type OperationsTab = 'sources' | 'discovery' | 'jobs' | 'actions';

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
  const [discoveryRuns, setDiscoveryRuns] = useState<SourceDiscoveryRun[]>([]);
  const [jobs, setJobs] = useState<CollectionJob[]>([]);
  const [actions, setActions] = useState<HumanAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');
  const [complianceConfirmed, setComplianceConfirmed] = useState(false);
  const [discoveryConfirmed, setDiscoveryConfirmed] = useState(false);
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
  const [discoveryForm, setDiscoveryForm] = useState({
    pool_id: '',
    query: '',
    api_key: '',
    search_engine_id: '',
  });

  const sourceById = useMemo(
    () => new Map(sources.map((source) => [source.id, source])),
    [sources],
  );
  const discoveryPool = useMemo(
    () => pools.find((pool) => pool.id === discoveryForm.pool_id),
    [discoveryForm.pool_id, pools],
  );

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [nextPools, nextSources, nextRuns, nextJobs, nextActions] = await Promise.all([
        api.listSourcePools(),
        api.listSources(),
        api.listDiscoveryRuns(),
        api.listCollectionJobs(),
        api.listHumanActions(),
      ]);
      setPools(nextPools);
      setSources(nextSources);
      setDiscoveryRuns(nextRuns);
      setJobs(nextJobs);
      setActions(nextActions);
      setSourceForm((current) => ({
        ...current,
        pool_id: current.pool_id || nextPools[0]?.id || '',
      }));
      setDiscoveryForm((current) => ({
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

  const discover = async () => {
    setBusyId('discovery');
    setError('');
    try {
      await api.discoverSources(discoveryForm.pool_id, {
        api_key: discoveryForm.api_key,
        search_engine_id: discoveryForm.search_engine_id,
        ...(discoveryForm.query.trim() ? { query: discoveryForm.query.trim() } : {}),
        limit: 10,
        safe: 'active',
      });
      setDiscoveryForm((current) => ({ ...current, api_key: '' }));
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '搜索发现失败');
    } finally {
      setBusyId('');
    }
  };

  const useCandidate = (
    run: SourceDiscoveryRun,
    candidate: SourceDiscoveryCandidate,
  ) => {
    setSourceForm({
      pool_id: run.pool_id,
      name: candidate.title,
      canonical_url: candidate.url,
      kind: candidate.suggested_kind,
      global_reputation: '',
      topic_authority: '',
    });
    setTab('sources');
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
  const discoveryFormValid = Boolean(
    discoveryForm.pool_id
    && discoveryForm.api_key
    && discoveryForm.search_engine_id
    && (discoveryForm.query.trim() || discoveryPool?.discovery_query)
    && discoveryConfirmed,
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
        <button className={tab === 'discovery' ? 'active' : ''} onClick={() => setTab('discovery')}>搜索发现 · {discoveryRuns.length}</button>
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

      {!loading && tab === 'discovery' && (
        <>
          <section className="drawer-section">
            <div className="drawer-section-title">
              <h3>Google Programmable Search</h3>
              <Status tone="warning"><LockKeyhole size={12} /> EPHEMERAL CREDENTIAL</Status>
            </div>
            <p className="section-help">
              API key 仅用于这一次服务器内存请求，不写入来源池、发现历史、日志或仓库。
              搜索结果只是未注册候选，不代表来源已获授权、符合 robots/条款或具备可信度。
              搜索词会进入不可变审计历史，请勿在其中填写凭证或其他秘密。
            </p>
            <div className="operation-forms discovery-form">
              <label className="field">
                <span>来源池</span>
                <select
                  value={discoveryForm.pool_id}
                  onChange={(event) => setDiscoveryForm({ ...discoveryForm, pool_id: event.target.value })}
                >
                  {pools.map((pool) => <option key={pool.id} value={pool.id}>{pool.name}</option>)}
                </select>
              </label>
              <label className="field">
                <span>搜索词（留空使用来源池冻结查询）</span>
                <input
                  value={discoveryForm.query}
                  placeholder={discoveryPool?.discovery_query ?? '该来源池尚未设置默认查询'}
                  onChange={(event) => setDiscoveryForm({ ...discoveryForm, query: event.target.value })}
                />
              </label>
              <label className="field">
                <span>Search Engine ID（CX）</span>
                <input
                  value={discoveryForm.search_engine_id}
                  autoComplete="off"
                  onChange={(event) => setDiscoveryForm({ ...discoveryForm, search_engine_id: event.target.value })}
                />
              </label>
              <label className="field">
                <span>Google API key（提交成功后清空）</span>
                <input
                  type="password"
                  value={discoveryForm.api_key}
                  autoComplete="new-password"
                  onChange={(event) => setDiscoveryForm({ ...discoveryForm, api_key: event.target.value })}
                />
              </label>
            </div>
            <label className="publish-confirmation">
              <input
                type="checkbox"
                checked={discoveryConfirmed}
                onChange={(event) => setDiscoveryConfirmed(event.target.checked)}
              />
              <ShieldCheck size={15} />
              我确认有权使用该搜索配置，并接受 Google 的配额、条款与 SafeSearch 请求。
            </label>
            <Button
              disabled={!discoveryFormValid || busyId === 'discovery'}
              onClick={() => void discover()}
            >
              <Search size={13} /> 发现候选来源
            </Button>
          </section>

          <section className="drawer-section">
            <h3>不可变发现历史</h3>
            <p className="section-help">
              仅冻结查询、结果及搜索配置哈希；API key 与原始 CX 不被保存。
              “带入注册表单”仍需人工补充声誉、主题权威和合规信息。
            </p>
            {discoveryRuns.length ? (
              <div className="discovery-run-list">
                {discoveryRuns.map((run) => (
                  <article className="discovery-run" key={run.id}>
                    <header>
                      <div>
                        <span className="panel-key">{run.provider}</span>
                        <h4>{run.query}</h4>
                      </div>
                      <div className="discovery-run-meta">
                        <Status tone={run.integrity_valid ? 'ok' : 'danger'}>
                          {run.integrity_valid ? 'HASH VERIFIED' : 'INTEGRITY ERROR'}
                        </Status>
                        <Status tone="neutral">{run.result_count} CANDIDATES</Status>
                        <small>{formatDate(run.completed_at)} · {shortHash(run.result_hash)}</small>
                      </div>
                    </header>
                    {run.candidates.length ? (
                      <div className="source-list">
                        {run.candidates.map((candidate) => (
                          <article className="source-item discovery-candidate" key={candidate.id}>
                            <div>
                              <span className="panel-key">
                                UNREGISTERED · {candidate.suggested_kind} · {candidate.display_host}
                              </span>
                              <h4>{candidate.title}</h4>
                              <p>{candidate.snippet || '搜索服务未返回摘要；系统不会补写。'}</p>
                            </div>
                            <div className="version-actions">
                              <a className="ghost-button" href={candidate.url} target="_blank" rel="noreferrer"><ExternalLink size={13} /> 查看</a>
                              <Button variant="secondary" onClick={() => useCandidate(run, candidate)}><FilePlus2 size={13} /> 带入注册表单</Button>
                            </div>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <div className="panel-empty">
                        本次搜索没有返回可安全保存的候选；系统不会补写或伪造结果。
                      </div>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <div className="panel-empty">尚无发现运行。系统不会伪造候选来源。</div>
            )}
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
