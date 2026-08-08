import { useCallback, useEffect, useMemo, useState } from 'react';
import { BadgeCheck, Calculator, CheckCircle2, GitCompareArrows, History, UserCheck } from 'lucide-react';

import { formatDate, safeHostname } from '../../lib/format';
import {
  api,
  type CalculationRun,
  type L2Insight,
  type MetricObservation,
  type ObservationRevision,
  type ReviewCase,
  type ReviewDecision,
  type TrustAssessment,
  type ValidationRun,
} from '../../lib/v2-api';
import { Button, EmptyState, ErrorState, LoadingState, Status } from '../../components/ui';
import { ObservationLineageTrace } from './ObservationLineage';

type TrustTab = 'observations' | 'calculations' | 'validations' | 'reviews' | 'eligibility';

const stateTone = (state: string) => {
  if (state === 'verified' || state === 'passed' || state === 'approved') return 'ok';
  if (state === 'rejected' || state === 'conflict') return 'danger';
  if (state === 'unverified' || state === 'needs_review' || state === 'needs_information') {
    return 'warning';
  }
  return 'neutral';
};

const jsonValue = (value: unknown) => JSON.stringify(value, null, 2);

export function TrustWorkspace({ panelVersionKey }: { panelVersionKey: string }) {
  const [tab, setTab] = useState<TrustTab>('observations');
  const [observations, setObservations] = useState<MetricObservation[]>([]);
  const [revisions, setRevisions] = useState<ObservationRevision[]>([]);
  const [calculations, setCalculations] = useState<CalculationRun[]>([]);
  const [validations, setValidations] = useState<ValidationRun[]>([]);
  const [reviews, setReviews] = useState<ReviewCase[]>([]);
  const [assessments, setAssessments] = useState<TrustAssessment[]>([]);
  const [insights, setInsights] = useState<L2Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [
        nextObservations,
        nextRevisions,
        nextCalculations,
        nextValidations,
        nextReviews,
        nextAssessments,
        nextInsights,
      ] =
        await Promise.all([
          api.listObservations(panelVersionKey),
          api.listObservationRevisions(panelVersionKey),
          api.listCalculations(panelVersionKey),
          api.listValidations(panelVersionKey),
          api.listReviews(panelVersionKey),
          api.listTrustAssessments(panelVersionKey),
          api.listInsights(),
        ]);
      setObservations(nextObservations);
      setRevisions(nextRevisions);
      setCalculations(nextCalculations);
      setValidations(nextValidations);
      setReviews(nextReviews);
      setAssessments(nextAssessments);
      setInsights(nextInsights);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '可信链读取失败');
    } finally {
      setLoading(false);
    }
  }, [panelVersionKey]);

  useEffect(() => {
    void load();
  }, [load]);

  const supersededIds = useMemo(
    () => new Set(revisions.map((revision) => revision.original_observation_id)),
    [revisions],
  );

  if (loading) return <LoadingState label="正在重建观测、计算、验证与审核链…" />;
  if (error) return <ErrorState message={error} onRetry={() => void load()} />;

  return (
    <section className="drawer-section trust-workspace">
      <div className="drawer-section-title">
        <h3>可信度工作区</h3>
        <div className="trust-summary">
          <Status tone={assessments.some((item) => item.currently_eligible) ? 'ok' : 'warning'}>
            {assessments.filter((item) => item.currently_eligible).length} ELIGIBLE
          </Status>
          <Status tone={reviews.some((item) => !item.latest_decision) ? 'warning' : 'neutral'}>
            {reviews.filter((item) => !item.latest_decision).length} OPEN REVIEW
          </Status>
        </div>
      </div>
      <p className="trust-boundary">
        Schema 合法、证据已引用、验证通过和人工批准是不同状态。这里展示真实运行记录；未建立可信晋级证明的观测仍保持 UNVERIFIED。
      </p>
      <nav className="drawer-tabs trust-tabs" aria-label="可信度工作区">
        <button className={tab === 'observations' ? 'active' : ''} onClick={() => setTab('observations')}>
          <History size={14} /> INFO · {observations.length}
        </button>
        <button className={tab === 'calculations' ? 'active' : ''} onClick={() => setTab('calculations')}>
          <Calculator size={14} /> 计算 · {calculations.length}
        </button>
        <button className={tab === 'validations' ? 'active' : ''} onClick={() => setTab('validations')}>
          <GitCompareArrows size={14} /> 验证 · {validations.length}
        </button>
        <button className={tab === 'reviews' ? 'active' : ''} onClick={() => setTab('reviews')}>
          <UserCheck size={14} /> 审核 · {reviews.length}
        </button>
        <button className={tab === 'eligibility' ? 'active' : ''} onClick={() => setTab('eligibility')}>
          <BadgeCheck size={14} /> 资格/L2 · {assessments.length}
        </button>
      </nav>

      {tab === 'observations' && (
        <ObservationWorkspace
          observations={observations}
          revisions={revisions}
          supersededIds={supersededIds}
          onChanged={load}
        />
      )}
      {tab === 'calculations' && (
        <CalculationWorkspace observations={observations} runs={calculations} onChanged={load} />
      )}
      {tab === 'validations' && (
        <ValidationWorkspace observations={observations} runs={validations} onChanged={load} />
      )}
      {tab === 'reviews' && <ReviewWorkspace cases={reviews} onChanged={load} />}
      {tab === 'eligibility' && (
        <EligibilityWorkspace
          observations={observations}
          validations={validations}
          assessments={assessments}
          insights={insights}
          onChanged={load}
        />
      )}
    </section>
  );
}

function ObservationWorkspace({
  observations,
  revisions,
  supersededIds,
  onChanged,
}: {
  observations: MetricObservation[];
  revisions: ObservationRevision[];
  supersededIds: Set<string>;
  onChanged: () => Promise<void>;
}) {
  const [editing, setEditing] = useState<MetricObservation | null>(null);
  const [rawValue, setRawValue] = useState('');
  const [normalizedValue, setNormalizedValue] = useState('');
  const [reason, setReason] = useState('');
  const [actor, setActor] = useState('');
  const [evidenceConfirmed, setEvidenceConfirmed] = useState(false);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const beginRevision = (observation: MetricObservation) => {
    setEditing(observation);
    setRawValue(jsonValue(observation.raw_value));
    setNormalizedValue(jsonValue(observation.normalized_value));
    setReason('');
    setActor('');
    setEvidenceConfirmed(false);
    setError('');
  };

  const submitRevision = async () => {
    if (!editing) return;
    setSaving(true);
    setError('');
    try {
      const evidenceClaims = editing.lineage.evidence_refs.reduce<Record<string, string[]>>(
        (claims, reference) => {
          const ids = claims[reference.claim_key] ?? [];
          if (!ids.includes(reference.fragment.fragment_id)) {
            ids.push(reference.fragment.fragment_id);
          }
          claims[reference.claim_key] = ids;
          return claims;
        },
        {},
      );
      await api.reviseObservation(editing.id, {
        raw_value: JSON.parse(rawValue) as Record<string, unknown>,
        normalized_value: JSON.parse(normalizedValue) as Record<string, unknown>,
        reason,
        revised_by: actor,
        evidence_claims: evidenceClaims,
      });
      setEditing(null);
      await onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '修订失败');
    } finally {
      setSaving(false);
    }
  };

  if (!observations.length) {
    return (
      <EmptyState
        title="还没有 INFO 观测"
        description="先在“采集与处理”的成功快照上运行结构化抽取；系统不会补默认值。"
      />
    );
  }
  return (
    <div className="trust-stack">
      {editing && (
        <div className="trust-form">
          <div className="drawer-section-title">
            <h4>追加观测修订</h4>
            <Status tone="warning">IMMUTABLE REPLACEMENT</Status>
          </div>
          <p>原记录不会修改；提交后创建一条 UNVERIFIED 替代记录，并保留原因与操作者。</p>
          <label>原始值 JSON<textarea value={rawValue} onChange={(event) => setRawValue(event.target.value)} /></label>
          <label>归一化值 JSON<textarea value={normalizedValue} onChange={(event) => setNormalizedValue(event.target.value)} /></label>
          <label>修订原因<input value={reason} onChange={(event) => setReason(event.target.value)} /></label>
          <label>操作者（当前为自我声明，认证尚未接入）<input value={actor} onChange={(event) => setActor(event.target.value)} /></label>
          <label className="checkbox-line">
            <input
              type="checkbox"
              checked={evidenceConfirmed}
              onChange={(event) => setEvidenceConfirmed(event.target.checked)}
            />
            我已逐项确认当前冻结证据声明支持本次修订；该记录仍保持 UNVERIFIED，当前策略不会自动晋级。
          </label>
          {error && <p className="form-error">{error}</p>}
          <div className="drawer-actions">
            <Button variant="secondary" onClick={() => setEditing(null)}>取消</Button>
            <Button disabled={saving || !reason.trim() || !actor.trim() || !evidenceConfirmed} onClick={() => void submitRevision()}>
              {saving ? '正在追加…' : '创建替代记录'}
            </Button>
          </div>
        </div>
      )}
      {observations.map((observation) => {
        const isSuperseded = supersededIds.has(observation.id);
        return (
          <article className="trust-record" key={observation.id}>
            <header>
              <div>
                <span className="mono">{observation.metric_key}</span>
                <strong>{String(observation.normalized_value.value ?? '未提供')}</strong>
                <small>{observation.unit ?? '单位未提供'}</small>
              </div>
              <div className="trust-record-statuses">
                <Status tone={isSuperseded ? 'neutral' : stateTone(observation.trust_state)}>
                  {isSuperseded ? 'SUPERSEDED' : observation.trust_state.toUpperCase()}
                </Status>
              </div>
            </header>
            <dl className="detail-list compact">
              <div><dt>观测 ID</dt><dd className="mono break">{observation.id}</dd></div>
              <div><dt>原始值</dt><dd className="mono break">{jsonValue(observation.raw_value)}</dd></div>
              <div><dt>归一化值</dt><dd className="mono break">{jsonValue(observation.normalized_value)}</dd></div>
              <div><dt>单位 / 币种</dt><dd>{observation.unit ?? '单位未提供'} / {observation.currency ?? '币种未提供'}</dd></div>
              <div><dt>维度</dt><dd className="mono break">{jsonValue(observation.dimensions)}</dd></div>
              <div><dt>记录时间</dt><dd>{formatDate(observation.created_at)}</dd></div>
            </dl>
            <ObservationLineageTrace observation={observation} />
            <div className="drawer-actions">
              <Button variant="secondary" disabled={isSuperseded} onClick={() => beginRevision(observation)}>
                {isSuperseded ? '已被替代' : '创建修订'}
              </Button>
            </div>
          </article>
        );
      })}
      {revisions.length > 0 && (
        <div className="lineage-list">
          <h4>修订替代链</h4>
          {revisions.map((revision) => (
            <div key={revision.id}>
              <Status tone="info">{revision.metric_key}</Status>
              <span className="mono">{revision.original_observation_id.slice(0, 8)} → {revision.replacement_observation_id.slice(0, 8)}</span>
              <p>{revision.reason} · {revision.revised_by} · {formatDate(revision.created_at)}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ObservationSelector({
  observations,
  selected,
  onChange,
}: {
  observations: MetricObservation[];
  selected: string[];
  onChange: (ids: string[]) => void;
}) {
  return (
    <div className="observation-selector">
      {observations.map((observation) => (
        <label key={observation.id}>
          <input
            type="checkbox"
            checked={selected.includes(observation.id)}
            onChange={(event) => onChange(
              event.target.checked
                ? [...selected, observation.id]
                : selected.filter((id) => id !== observation.id),
            )}
          />
          <span>{observation.metric_key} · {String(observation.normalized_value.value ?? '未提供')} {observation.unit ?? ''}</span>
          <small>
            {observation.id.slice(0, 8)} · {
              observation.lineage.evidence_refs[0]
                ? safeHostname(observation.lineage.evidence_refs[0].fragment.source_url)
                : '观测级来源未绑定'
            }
          </small>
        </label>
      ))}
    </div>
  );
}

function CalculationWorkspace({
  observations,
  runs,
  onChanged,
}: {
  observations: MetricObservation[];
  runs: CalculationRun[];
  onChanged: () => Promise<void>;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [operation, setOperation] = useState('add');
  const [metricKey, setMetricKey] = useState('');
  const [unit, setUnit] = useState('');
  const [weights, setWeights] = useState('');
  const [unitPlan, setUnitPlan] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    setSaving(true);
    setError('');
    try {
      const parameters: Record<string, unknown> = {};
      if (operation === 'weighted_average') {
        const parsedWeights = weights
          .split(',')
          .map((value) => value.trim())
          .filter(Boolean)
          .map(Number);
        if (
          parsedWeights.length !== selected.length
          || parsedWeights.some((value) => !Number.isFinite(value))
        ) {
          throw new Error('权重必须与输入一一对应，并且都是有限数字');
        }
        parameters.weights = parsedWeights;
      }
      if (operation === 'multiply' || operation === 'divide') {
        const parsedPlan = JSON.parse(unitPlan) as unknown;
        if (
          typeof parsedPlan !== 'object'
          || parsedPlan === null
          || Array.isArray(parsedPlan)
          || Object.keys(parsedPlan).length === 0
        ) {
          throw new Error('单位计划必须是非空 JSON 对象');
        }
        parameters.unit_plan = parsedPlan;
      }
      await api.calculate({
        operation,
        input_observation_ids: selected,
        output_metric_key: metricKey,
        output_unit: unit || null,
        parameters,
      });
      setSelected([]);
      setMetricKey('');
      await onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '计算失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="trust-stack">
      <div className="trust-form">
        <h4>确定性计算计划</h4>
        <p>只选择数据库已有观测；数学由后端 Decimal 引擎执行，模型不参与计算。</p>
        <ObservationSelector observations={observations} selected={selected} onChange={setSelected} />
        <label>运算<select value={operation} onChange={(event) => setOperation(event.target.value)}>
          <option value="add">相加</option><option value="subtract">相减</option>
          <option value="multiply">相乘</option><option value="divide">相除</option>
          <option value="percent_change">百分比变化</option><option value="weighted_average">加权平均</option>
        </select></label>
        <label>输出指标键<input value={metricKey} onChange={(event) => setMetricKey(event.target.value)} /></label>
        <label>输出单位（必须显式）<input value={unit} onChange={(event) => setUnit(event.target.value)} /></label>
        {operation === 'weighted_average' && <label>权重（按输入顺序，逗号分隔）<input value={weights} onChange={(event) => setWeights(event.target.value)} /></label>}
        {(operation === 'multiply' || operation === 'divide') && <label>单位计划 JSON<textarea value={unitPlan} onChange={(event) => setUnitPlan(event.target.value)} placeholder='{"operation":"vehicle_per_day"}' /></label>}
        {error && <p className="form-error">{error}</p>}
        <Button disabled={saving || !selected.length || !metricKey.trim() || !unit.trim()} onClick={() => void submit()}>
          {saving ? '正在执行…' : '执行并冻结计算运行'}
        </Button>
      </div>
      {runs.length ? runs.map((run) => (
        <article className="trust-record" key={run.id}>
          <header><strong>{run.output_metric_key}</strong><Status tone="info">{run.operation}</Status></header>
          <dl className="detail-list compact">
            <div><dt>结果</dt><dd>{jsonValue(run.result)}</dd></div>
            <div><dt>输入</dt><dd className="mono break">{run.input_observation_ids.join(', ')}</dd></div>
            <div><dt>引擎</dt><dd>{run.engine_version}</dd></div>
            <div><dt>重放哈希</dt><dd className="mono break">{run.replay_hash}</dd></div>
          </dl>
        </article>
      )) : <EmptyState title="没有计算运行" description="选择已有观测并显式建立计算计划。" />}
    </div>
  );
}

function ValidationWorkspace({
  observations,
  runs,
  onChanged,
}: {
  observations: MetricObservation[];
  runs: ValidationRun[];
  onChanged: () => Promise<void>;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [absolute, setAbsolute] = useState('');
  const [relative, setRelative] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    setSaving(true);
    setError('');
    try {
      await api.validateObservations({
        observation_ids: selected,
        absolute_tolerance: absolute,
        relative_tolerance: relative,
      });
      setSelected([]);
      await onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '验证失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="trust-stack">
      <div className="trust-form">
        <h4>跨独立来源验证</h4>
        <p>必须具有相同指标、单位、币种、期间、地域和维度；同一来源的重复记录不会通过。</p>
        <ObservationSelector observations={observations} selected={selected} onChange={setSelected} />
        <label>绝对容差<input inputMode="decimal" value={absolute} onChange={(event) => setAbsolute(event.target.value)} /></label>
        <label>相对容差（例如 0.01）<input inputMode="decimal" value={relative} onChange={(event) => setRelative(event.target.value)} /></label>
        {error && <p className="form-error">{error}</p>}
        <Button disabled={saving || !selected.length || !absolute.trim() || !relative.trim()} onClick={() => void submit()}>
          {saving ? '正在验证…' : '运行跨源验证'}
        </Button>
      </div>
      {runs.length ? runs.map((run) => (
        <article className="trust-record" key={run.id}>
          <header><strong>{run.rule_version}</strong><Status tone={stateTone(run.state)}>{run.state.toUpperCase()}</Status></header>
          <dl className="detail-list compact">
            <div><dt>容差</dt><dd>{jsonValue(run.tolerance)}</dd></div>
            <div><dt>结果</dt><dd>{jsonValue(run.result)}</dd></div>
            <div><dt>观测</dt><dd className="mono break">{run.observation_ids.join(', ')}</dd></div>
          </dl>
        </article>
      )) : <EmptyState title="没有验证运行" description="显式选择真实观测和容差后运行；不足两个独立来源会进入人工审核。" />}
    </div>
  );
}

function ReviewWorkspace({ cases, onChanged }: { cases: ReviewCase[]; onChanged: () => Promise<void> }) {
  const [editing, setEditing] = useState<ReviewCase | null>(null);
  const [outcome, setOutcome] = useState<ReviewDecision['outcome']>('needs_information');
  const [actor, setActor] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async () => {
    if (!editing) return;
    setSaving(true);
    setError('');
    try {
      await api.decideReview(editing.id, {
        outcome,
        decision: { rationale: reason },
        decided_by: actor,
        ...(editing.latest_decision ? { supersedes_id: editing.latest_decision.id } : {}),
      });
      setEditing(null);
      await onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '审核提交失败');
    } finally {
      setSaving(false);
    }
  };

  if (!cases.length) return <EmptyState title="没有人工审核案件" description="冲突或独立来源不足的验证运行会自动创建不可变审核案件。" />;
  return (
    <div className="trust-stack">
      {editing && (
        <div className="trust-form">
          <h4>{editing.latest_decision ? '追加替代审核决定' : '记录首个审核决定'}</h4>
          <p>操作者当前由请求自我声明；认证主体尚未接入，因此 UI 不会把此决定显示为身份已验证。</p>
          <label>结果<select value={outcome} onChange={(event) => setOutcome(event.target.value as ReviewDecision['outcome'])}>
            <option value="approved">批准</option><option value="rejected">拒绝</option><option value="needs_information">需要补充信息</option>
          </select></label>
          <label>理由<input value={reason} onChange={(event) => setReason(event.target.value)} /></label>
          <label>操作者（自我声明）<input value={actor} onChange={(event) => setActor(event.target.value)} /></label>
          {error && <p className="form-error">{error}</p>}
          <div className="drawer-actions">
            <Button variant="secondary" onClick={() => setEditing(null)}>取消</Button>
            <Button disabled={saving || !reason.trim() || !actor.trim()} onClick={() => void submit()}>
              {saving ? '正在追加…' : '冻结审核决定'}
            </Button>
          </div>
        </div>
      )}
      {cases.map((item) => (
        <article className="trust-record" key={item.id}>
          <header>
            <strong>{item.reason_codes.join(' · ')}</strong>
            <Status tone={item.latest_decision ? stateTone(item.latest_decision.outcome) : 'warning'}>
              {item.latest_decision?.outcome.toUpperCase() ?? 'OPEN'}
            </Status>
          </header>
          <dl className="detail-list compact">
            <div><dt>案件 ID</dt><dd className="mono break">{item.id}</dd></div>
            <div><dt>验证运行</dt><dd className="mono break">{item.validation_run_id ?? '未关联'}</dd></div>
            <div><dt>观测</dt><dd className="mono break">{item.observation_ids.join(', ')}</dd></div>
          </dl>
          {item.decisions.map((decision) => (
            <div className="review-decision" key={decision.id}>
              <CheckCircle2 size={14} />
              <span>{decision.outcome} · {decision.decided_by} · {formatDate(decision.created_at)}</span>
              <small>{String(decision.decision.rationale ?? '未提供理由')}</small>
            </div>
          ))}
          <Button variant="secondary" onClick={() => { setEditing(item); setError(''); }}>
            {item.latest_decision ? '追加替代决定' : '进入人工审核'}
          </Button>
        </article>
      ))}
    </div>
  );
}

function EligibilityWorkspace({
  observations,
  validations,
  assessments,
  insights,
  onChanged,
}: {
  observations: MetricObservation[];
  validations: ValidationRun[];
  assessments: TrustAssessment[];
  insights: L2Insight[];
  onChanged: () => Promise<void>;
}) {
  const [validationByObservation, setValidationByObservation] = useState<Record<string, string>>({});
  const [selected, setSelected] = useState<string[]>([]);
  const [actor, setActor] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState('');

  const latestByObservation = useMemo(() => {
    const output = new Map<string, TrustAssessment>();
    assessments.forEach((assessment) => {
      if (!output.has(assessment.observation_id)) output.set(assessment.observation_id, assessment);
    });
    return output;
  }, [assessments]);
  const eligibleObservations = observations.filter(
    (observation) => latestByObservation.get(observation.id)?.currently_eligible,
  );
  const observationIds = new Set(observations.map((item) => item.id));
  const panelInsights = insights.filter((insight) =>
    insight.inputs.some((input) => observationIds.has(input.observation_id)),
  );

  const assess = async (observation: MetricObservation) => {
    setSaving(`assessment:${observation.id}`);
    setError('');
    try {
      const validationId = validationByObservation[observation.id];
      await api.assessObservation({
        observation_id: observation.id,
        ...(validationId ? { validation_run_id: validationId } : {}),
      });
      await onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : '资格评估失败');
    } finally {
      setSaving('');
    }
  };

  const createInsight = async () => {
    setSaving('insight');
    setError('');
    try {
      await api.createInsight({ observation_ids: selected, created_by: actor });
      setSelected([]);
      await onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'L2 摘要创建失败');
    } finally {
      setSaving('');
    }
  };

  return (
    <div className="trust-stack">
      <div className="trust-form">
        <h4>Append-only 可信资格评估</h4>
        <p>
          评估会重放原始文件与片段哈希、检查当前修订头、验证状态、独立来源数和计算记录。
          它创建新评估，不修改观测；人工批准不能覆盖冲突验证。
        </p>
        {observations.length ? observations.map((observation) => {
          const candidates = validations.filter((run) => run.observation_ids.includes(observation.id));
          const latest = latestByObservation.get(observation.id);
          return (
            <div className="eligibility-row" key={observation.id}>
              <div>
                <strong>{observation.metric_key}</strong>
                <small>{observation.id.slice(0, 8)} · {String(observation.normalized_value.value ?? '未提供')} {observation.unit ?? ''}</small>
              </div>
              <select
                aria-label={`${observation.metric_key} 的验证运行`}
                value={validationByObservation[observation.id] ?? ''}
                onChange={(event) => setValidationByObservation((current) => ({
                  ...current,
                  [observation.id]: event.target.value,
                }))}
              >
                <option value="">未选择验证（将记录不合格）</option>
                {candidates.map((run) => (
                  <option key={run.id} value={run.id}>{run.state} · {run.id.slice(0, 8)}</option>
                ))}
              </select>
              <Status tone={latest?.currently_eligible ? 'ok' : 'warning'}>
                {latest ? (latest.currently_eligible ? 'ELIGIBLE' : 'INELIGIBLE') : 'NOT ASSESSED'}
              </Status>
              <Button
                variant="secondary"
                disabled={saving === `assessment:${observation.id}`}
                onClick={() => void assess(observation)}
              >
                {saving === `assessment:${observation.id}` ? '评估中…' : '运行评估'}
              </Button>
            </div>
          );
        }) : <EmptyState title="没有可评估观测" description="先从成功快照执行结构化抽取。" />}
      </div>

      {assessments.length > 0 && (
        <div className="lineage-list">
          <h4>资格评估历史</h4>
          {assessments.map((assessment) => (
            <div key={assessment.id}>
              <Status tone={assessment.currently_eligible ? 'ok' : 'warning'}>
                {assessment.currently_eligible ? 'CURRENT ELIGIBLE' : 'INELIGIBLE / STALE'}
              </Status>
              <span>{assessment.metric_key} · {assessment.policy_version}</span>
              <p>{assessment.reason_codes.join(' · ')} · {formatDate(assessment.created_at)}</p>
              <p className="mono break">{jsonValue(assessment.details)}</p>
            </div>
          ))}
        </div>
      )}

      <div className="trust-form">
        <h4>存储输入限定的 L2 摘要</h4>
        <p>
          只允许选择当前 ELIGIBLE 观测。输出是确定性证据摘要，不浏览、不补事实、不预测，也不执行模型数学。
        </p>
        {eligibleObservations.length ? (
          <ObservationSelector observations={eligibleObservations} selected={selected} onChange={setSelected} />
        ) : (
          <EmptyState
            title="L2 当前不可用"
            description="当前面板没有通过 trust-eligibility-v1 的修订头；系统不会用 UNVERIFIED 数据生成洞察。"
          />
        )}
        <label>创建者（当前为自我声明）<input value={actor} onChange={(event) => setActor(event.target.value)} /></label>
        {error && <p className="form-error">{error}</p>}
        <Button
          disabled={saving === 'insight' || !selected.length || !actor.trim()}
          onClick={() => void createInsight()}
        >
          {saving === 'insight' ? '正在冻结…' : '生成并冻结 L2 证据摘要'}
        </Button>
      </div>

      {panelInsights.length ? panelInsights.map((insight) => (
        <article className="trust-record" key={insight.id}>
          <header><strong>{insight.title}</strong><Status tone="ok">STORED INPUTS</Status></header>
          <p className="insight-summary">{insight.output.summary}</p>
          <dl className="detail-list compact">
            <div><dt>输入哈希</dt><dd className="mono break">{insight.input_hash}</dd></div>
            <div><dt>引擎</dt><dd>{insight.engine_version}</dd></div>
            <div><dt>契约版本</dt><dd>{insight.prompt_version}</dd></div>
            <div><dt>输入观测</dt><dd className="mono break">{insight.inputs.map((item) => item.observation_id).join(', ')}</dd></div>
            <div><dt>创建者</dt><dd>{insight.created_by}（自我声明）</dd></div>
          </dl>
        </article>
      )) : <EmptyState title="没有 L2 历史" description="只有满足当前资格策略的观测集合才能创建记录。" />}
    </div>
  );
}
