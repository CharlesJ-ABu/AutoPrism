import { useEffect, useMemo, useState } from 'react';
import {
  Bot,
  CheckCircle2,
  DatabaseZap,
  Fingerprint,
  KeyRound,
  Quote,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
} from 'lucide-react';

import { Button, Drawer, EmptyState, LoadingState, Status } from '../../components/ui';
import { formatDate, shortHash } from '../../lib/format';
import {
  api,
  type EvidenceInterpretation,
  type MetricObservation,
  type ResearchAction,
  type ResearchActionState,
  type ResearchRun,
  type SourcePool,
} from '../../lib/v2-api';

const STATE_TONE: Record<ResearchActionState, 'ok' | 'warning' | 'danger' | 'neutral' | 'info'> = {
  proposed: 'neutral',
  authorized: 'warning',
  started: 'info',
  completed: 'ok',
  queued: 'ok',
  blocked: 'warning',
  failed: 'danger',
  missing: 'danger',
};

function actionTitle(action: ResearchAction) {
  if (action.action_type === 'discover') {
    return String(action.specification.query ?? '无效的搜索提案');
  }
  return String(action.specification.source_name ?? action.specification.source_key ?? '无效的采集提案');
}

function actionPurpose(action: ResearchAction) {
  return String(action.specification.purpose ?? '模型未提供动作目的');
}

export function ResearchDrawer({ onClose }: { onClose: () => void }) {
  const [pools, setPools] = useState<SourcePool[]>([]);
  const [runs, setRuns] = useState<ResearchRun[]>([]);
  const [trustedObservations, setTrustedObservations] = useState<MetricObservation[]>([]);
  const [interpretations, setInterpretations] = useState<EvidenceInterpretation[]>([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');
  const [authorized, setAuthorized] = useState<Record<string, boolean>>({});
  const [searchCredentials, setSearchCredentials] = useState({ api_key: '', search_engine_id: '' });
  const [selectedObservationIds, setSelectedObservationIds] = useState<string[]>([]);
  const [interpretationForm, setInterpretationForm] = useState({
    title: '',
    question: '',
    api_key: '',
  });
  const [form, setForm] = useState({
    source_pool_id: '',
    title: '',
    objective: '',
    constraints: '{}',
    provider: 'openai-compatible',
    model: 'gpt-4o',
    base_url: 'https://api.openai.com/v1',
    api_key: '',
  });

  const selectedRun = useMemo(
    () => runs.find((run) => run.id === selectedRunId) ?? runs[0],
    [runs, selectedRunId],
  );

  const load = async (preferredRunId?: string) => {
    setLoading(true);
    setError('');
    try {
      const [nextPools, nextRuns, nextObservations, nextInterpretations] = await Promise.all([
        api.listSourcePools(),
        api.listResearchRuns(),
        api.listTrustedObservations(),
        api.listInterpretations(),
      ]);
      setPools(nextPools);
      setRuns(nextRuns);
      setTrustedObservations(nextObservations);
      setInterpretations(nextInterpretations);
      const nextRunId = preferredRunId ?? selectedRunId ?? nextRuns[0]?.id ?? '';
      setSelectedRunId(nextRunId);
      setForm((current) => ({
        ...current,
        source_pool_id: current.source_pool_id || nextPools[0]?.id || '',
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'AI 研究工作区加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const createPlan = async () => {
    setBusyId('plan');
    setError('');
    try {
      const constraints = JSON.parse(form.constraints) as unknown;
      if (!constraints || Array.isArray(constraints) || typeof constraints !== 'object') {
        throw new Error('研究约束必须是 JSON 对象');
      }
      const run = await api.createResearchRun({
        source_pool_id: form.source_pool_id,
        title: form.title,
        objective: form.objective,
        constraints: constraints as Record<string, unknown>,
        provider: form.provider,
        model: form.model,
        ...(form.base_url.trim() ? { base_url: form.base_url.trim() } : {}),
        ...(form.api_key ? { api_key: form.api_key } : {}),
      });
      setForm((current) => ({ ...current, api_key: '', title: '', objective: '' }));
      await load(run.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '研究计划生成失败');
    } finally {
      setBusyId('');
    }
  };

  const executeAction = async (action: ResearchAction) => {
    setBusyId(action.id);
    setError('');
    try {
      if (action.action_type === 'discover') {
        await api.executeResearchDiscovery(action.id, {
          api_key: searchCredentials.api_key,
          search_engine_id: searchCredentials.search_engine_id,
          authorization_confirmed: authorized[action.id] === true,
        });
        setSearchCredentials((current) => ({ ...current, api_key: '' }));
      } else {
        await api.executeResearchCollection(action.id, {
          authorization_confirmed: authorized[action.id] === true,
        });
      }
      setAuthorized((current) => ({ ...current, [action.id]: false }));
      await load(selectedRun?.id);
    } catch (reason) {
      await load(selectedRun?.id);
      setError(reason instanceof Error ? reason.message : '研究动作执行失败');
    } finally {
      setBusyId('');
    }
  };

  const createInterpretation = async () => {
    setBusyId('interpretation');
    setError('');
    try {
      const created = await api.createInterpretation({
        title: interpretationForm.title,
        question: interpretationForm.question,
        observation_ids: selectedObservationIds,
        created_by: 'local-user-self-attested',
        provider: form.provider,
        model: form.model,
        ...(form.base_url.trim() ? { base_url: form.base_url.trim() } : {}),
        ...(interpretationForm.api_key ? { api_key: interpretationForm.api_key } : {}),
      });
      setInterpretationForm({ title: '', question: '', api_key: '' });
      setSelectedObservationIds([]);
      await load(selectedRun?.id);
      setInterpretations((current) => current.some((item) => item.id === created.id)
        ? current
        : [created, ...current]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '证据绑定解读生成失败');
    } finally {
      setBusyId('');
    }
  };

  const toggleObservation = (observationId: string) => {
    setSelectedObservationIds((current) => current.includes(observationId)
      ? current.filter((item) => item !== observationId)
      : [...current, observationId]);
  };

  const formValid = Boolean(
    form.source_pool_id && form.title.trim().length >= 3
    && form.objective.trim().length >= 10 && form.provider && form.model,
  );
  const interpretationValid = Boolean(
    selectedObservationIds.length
    && interpretationForm.title.trim().length >= 3
    && interpretationForm.question.trim().length >= 10,
  );

  return (
    <Drawer
      eyebrow={<><Bot size={12} /> LLM RESEARCH ORCHESTRATOR</>}
      title="AI 可信研究工作区"
      onClose={onClose}
      wide
    >
      <section className="drawer-section research-boundary">
        <div className="drawer-section-title">
          <h3>职责边界</h3>
          <Status tone="warning"><ShieldAlert size={12} /> PLAN ≠ FACT</Status>
        </div>
        <p className="section-help">
          LLM 读取数据库中的来源池，提出检索词、采集顺序、分析目标和解读问题；
          它不能声称已经检索、采集或验证，也不能直接生成权威数值。每个外部动作仍需你逐项授权，
          搜索、抓取、内容哈希、跨源验证与计算由受控工具执行并留下不可变记录。
        </p>
      </section>

      <section className="drawer-section research-plan-form">
        <div className="drawer-section-title">
          <h3><Sparkles size={13} /> 发起研究</h3>
          <Status tone="info"><KeyRound size={12} /> EPHEMERAL MODEL KEY</Status>
        </div>
        <div className="research-form-grid">
          <label className="field"><span>来源池</span><select value={form.source_pool_id} onChange={(event) => setForm({ ...form, source_pool_id: event.target.value })}>{pools.map((pool) => <option key={pool.id} value={pool.id}>{pool.name}</option>)}</select></label>
          <label className="field"><span>研究标题</span><input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="例如：2026 Q2 新能源车交付研究" /></label>
          <label className="field research-span-2"><span>研究目标</span><textarea value={form.objective} onChange={(event) => setForm({ ...form, objective: event.target.value })} placeholder="说明需要全面收集什么、比较什么，以及希望解读的决策问题。" /></label>
          <label className="field research-span-2"><span>边界与约束（JSON 对象）</span><textarea className="research-json" value={form.constraints} onChange={(event) => setForm({ ...form, constraints: event.target.value })} /></label>
          <label className="field"><span>模型提供方</span><select value={form.provider} onChange={(event) => setForm({ ...form, provider: event.target.value })}><option value="openai-compatible">OpenAI Compatible</option><option value="gemini">Gemini</option></select></label>
          <label className="field"><span>模型</span><input value={form.model} onChange={(event) => setForm({ ...form, model: event.target.value })} /></label>
          <label className="field"><span>API Base</span><input value={form.base_url} onChange={(event) => setForm({ ...form, base_url: event.target.value })} /></label>
          <label className="field"><span>临时模型 API Key（留空使用服务端配置）</span><input type="password" value={form.api_key} onChange={(event) => setForm({ ...form, api_key: event.target.value })} autoComplete="off" /></label>
        </div>
        <p className="credential-hint">临时模型 Key 只进入本次请求，不写入研究计划、数据库或来源配置。</p>
        <Button variant="primary" disabled={!formValid || busyId === 'plan'} onClick={() => void createPlan()}><Sparkles size={14} /> {busyId === 'plan' ? '正在生成冻结计划…' : '让 LLM 制定研究计划'}</Button>
      </section>

      <section className="drawer-section interpretation-workspace">
        <div className="drawer-section-title">
          <h3><Quote size={13} /> 证据绑定解读</h3>
          <Status tone="warning">MODEL NARRATIVE · NOT TRUST STATE</Status>
        </div>
        <p className="section-help">
          只把当前仍通过可信策略的数据库观测交给模型。输入证据、评估 ID、提示词和输出均冻结哈希；
          模型只能复制已引用数值，不能计算新数值，也不能把文字解读升级为可信事实。
        </p>
        {trustedObservations.length ? (
          <div className="interpretation-input-list">
            {trustedObservations.map((observation) => (
              <label key={observation.id} className="interpretation-input">
                <input
                  type="checkbox"
                  checked={selectedObservationIds.includes(observation.id)}
                  onChange={() => toggleObservation(observation.id)}
                />
                <span>
                  <strong>{observation.metric_key}</strong>
                  <small>
                    {String(observation.normalized_value.value)} {observation.unit ?? observation.currency ?? ''}
                    {' · '}{shortHash(observation.id)}
                  </small>
                </span>
                <Status tone="ok">CURRENT ELIGIBLE</Status>
              </label>
            ))}
          </div>
        ) : (
          <div className="panel-empty">当前没有可用于模型解读的可信观测；系统不会退回未验证数据或生成示例。</div>
        )}
        <div className="research-form-grid interpretation-form">
          <label className="field"><span>解读标题</span><input value={interpretationForm.title} onChange={(event) => setInterpretationForm({ ...interpretationForm, title: event.target.value })} placeholder="例如：已验证交付数据的差异解读" /></label>
          <label className="field"><span>临时模型 API Key</span><input type="password" value={interpretationForm.api_key} onChange={(event) => setInterpretationForm({ ...interpretationForm, api_key: event.target.value })} autoComplete="off" /></label>
          <label className="field research-span-2"><span>需要模型回答的问题</span><textarea value={interpretationForm.question} onChange={(event) => setInterpretationForm({ ...interpretationForm, question: event.target.value })} placeholder="仅根据选中的可信观测，说明可以得出什么、不能得出什么。" /></label>
        </div>
        <Button variant="primary" disabled={!interpretationValid || busyId === 'interpretation'} onClick={() => void createInterpretation()}>
          <Quote size={14} /> {busyId === 'interpretation' ? '正在校验并冻结解读…' : `生成证据绑定解读 · ${selectedObservationIds.length} INPUTS`}
        </Button>
      </section>

      {error && <div className="error-banner">{error}</div>}
      {loading && <LoadingState label="正在读取冻结研究历史…" />}

      {!loading && runs.length === 0 && (
        <EmptyState title="尚无研究计划" description="选择一个已有来源池并描述目标；模型只会生成待授权计划，不会伪装已完成研究。" />
      )}

      {!loading && runs.length > 0 && (
        <>
          <nav className="research-run-switcher" aria-label="研究历史">
            {runs.map((run) => <button key={run.id} className={selectedRun?.id === run.id ? 'active' : ''} onClick={() => setSelectedRunId(run.id)}><strong>{run.title}</strong><small>{formatDate(run.created_at)}</small></button>)}
            <Button variant="ghost" onClick={() => void load(selectedRun?.id)}><RefreshCw size={13} /> 刷新</Button>
          </nav>

          {selectedRun?.plan && (
            <>
              <section className="drawer-section research-plan-summary">
                <div className="drawer-section-title">
                  <h3>冻结研究计划</h3>
                  <Status tone={selectedRun.plan.integrity_valid ? 'ok' : 'danger'}><Fingerprint size={12} /> {selectedRun.plan.integrity_valid ? 'HASH VERIFIED' : 'INTEGRITY FAILED'}</Status>
                </div>
                <h4>{selectedRun.title}</h4>
                <p>{selectedRun.plan.document.summary}</p>
                <div className="research-hash-row"><span>{selectedRun.plan.provider} / {selectedRun.plan.model}</span><code>INPUT {shortHash(selectedRun.plan.input_hash)} · OUTPUT {shortHash(selectedRun.plan.output_hash)}</code></div>
                <div className="research-question-grid">
                  <div><strong>研究问题</strong>{selectedRun.plan.document.research_questions.map((item) => <p key={item}>• {item}</p>)}</div>
                  <div><strong>解读问题</strong>{selectedRun.plan.document.interpretation_questions.map((item) => <p key={item}>• {item}</p>)}</div>
                </div>
                <div className="research-targets">
                  {selectedRun.plan.document.analysis_targets.map((target) => <article key={target.key}><span>{target.key}</span><strong>{target.question}</strong><p>{target.evidence_expectation}</p><small>{target.requires_cross_source ? 'REQUIRES CROSS-SOURCE' : 'SINGLE SOURCE ALLOWED'} · {target.expected_fields.join(' / ')}</small></article>)}
                </div>
                <div className="research-limitations"><strong>模型声明的限制</strong>{selectedRun.plan.document.limitations.map((item) => <span key={item}>{item}</span>)}</div>
              </section>

              <section className="drawer-section">
                <div className="drawer-section-title"><h3>待授权工具动作 · {selectedRun.actions.length}</h3><Status tone="warning">逐项人工门禁</Status></div>
                {selectedRun.actions.some((action) => action.action_type === 'discover' && !['completed', 'queued'].includes(action.current_state)) && (
                  <div className="research-search-credentials">
                    <label className="field"><span>Google Search API Key（临时）</span><input type="password" value={searchCredentials.api_key} onChange={(event) => setSearchCredentials({ ...searchCredentials, api_key: event.target.value })} autoComplete="off" /></label>
                    <label className="field"><span>Search Engine ID（CX）</span><input value={searchCredentials.search_engine_id} onChange={(event) => setSearchCredentials({ ...searchCredentials, search_engine_id: event.target.value })} /></label>
                  </div>
                )}
                <div className="research-action-list">
                  {selectedRun.actions.map((action) => {
                    const terminal = ['completed', 'queued'].includes(action.current_state);
                    const discoveryReady = action.action_type !== 'discover' || Boolean(searchCredentials.api_key && searchCredentials.search_engine_id);
                    return <article key={action.id} className="research-action"><header><span className="panel-key">#{action.ordinal + 1} · {action.action_type === 'discover' ? 'SEARCH DISCOVERY' : 'REGISTERED COLLECTION'}</span><Status tone={STATE_TONE[action.current_state]}>{action.current_state.toUpperCase()}</Status></header><h4>{actionTitle(action)}</h4><p>{actionPurpose(action)}</p>{action.collection_job && <small>COLLECTION JOB {shortHash(action.collection_job.id)} · {action.collection_job.state.toUpperCase()}</small>} {!terminal && <><label className="publish-confirmation"><input type="checkbox" checked={authorized[action.id] === true} onChange={(event) => setAuthorized({ ...authorized, [action.id]: event.target.checked })} /><CheckCircle2 size={14} />我授权执行这一项外部动作，并接受合规策略在受限时暂停。</label><Button disabled={!authorized[action.id] || !discoveryReady || busyId === action.id || !selectedRun.plan?.integrity_valid} onClick={() => void executeAction(action)}>{action.action_type === 'discover' ? <Search size={13} /> : <DatabaseZap size={13} />} {busyId === action.id ? '执行中…' : action.action_type === 'discover' ? '执行受控搜索' : '创建采集任务'}</Button></>}</article>;
                  })}
                </div>
              </section>
            </>
          )}
        </>
      )}

      {!loading && interpretations.length > 0 && (
        <section className="drawer-section interpretation-history">
          <div className="drawer-section-title"><h3>冻结解读历史 · {interpretations.length}</h3><Status tone="neutral">APPEND ONLY</Status></div>
          {interpretations.map((item) => (
            <article key={item.id} className="interpretation-card">
              <header>
                <div><span className="panel-key">{item.provider} / {item.model}</span><h4>{item.title}</h4></div>
                <Status tone={!item.integrity_valid ? 'danger' : item.currently_grounded ? 'ok' : 'warning'}>
                  {!item.integrity_valid ? 'HASH FAILED' : item.currently_grounded ? 'CURRENTLY GROUNDED' : 'HISTORICAL · INPUT STALE'}
                </Status>
              </header>
              <p className="interpretation-question">{item.question}</p>
              <p>{item.output.summary}</p>
              <div className="interpretation-claims">
                {item.output.claims.map((claim, index) => (
                  <div key={`${item.id}-${index}`}>
                    <strong>CLAIM {index + 1}</strong>
                    <p>{claim.statement}</p>
                    <small>{claim.observation_ids.map(shortHash).join(' · ')} · {claim.limitation}</small>
                  </div>
                ))}
              </div>
              <footer><code>INPUT {shortHash(item.input_hash)} · OUTPUT {shortHash(item.output_hash)}</code><span>{formatDate(item.created_at)}</span></footer>
            </article>
          ))}
        </section>
      )}
    </Drawer>
  );
}
