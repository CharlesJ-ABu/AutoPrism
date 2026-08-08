import {
  Database,
  Download,
  ExternalLink,
  FileSearch,
  GitBranch,
} from 'lucide-react';

import { Status } from '../../components/ui';
import { formatDate, safeHostname } from '../../lib/format';
import {
  api,
  type MetricObservation,
  type ObservationEvidenceRef,
  type ObservationLineageState,
} from '../../lib/v2-api';

const jsonValue = (value: unknown) => JSON.stringify(value, null, 2);

const lineagePresentation: Record<
  ObservationLineageState,
  { label: string; tone: 'ok' | 'info' | 'warning' | 'danger' }
> = {
  direct: { label: 'DIRECT', tone: 'ok' },
  derived: { label: 'DERIVED', tone: 'info' },
  legacy_unverified: { label: 'LEGACY_UNVERIFIED', tone: 'warning' },
  incomplete: { label: 'INCOMPLETE', tone: 'danger' },
};

const originLabel = (observation: MetricObservation) => {
  const { origin } = observation.lineage;
  if (origin.kind === 'extraction') return 'EXTRACTION RUN';
  if (origin.kind === 'revision') return 'MANUAL REVISION';
  if (origin.kind === 'calculation') return 'CALCULATION RUN';
  if (origin.kind === 'conversion') return 'CONVERSION RUN';
  return 'NO DIRECT RUN';
};

const originIdentifier = (observation: MetricObservation) => {
  const { origin } = observation.lineage;
  return origin.extraction_run?.id
    ?? origin.revision_id
    ?? origin.calculation_run_id
    ?? origin.conversion_run_id
    ?? '未关联';
};

const evidenceRoleLabel: Record<ObservationEvidenceRef['role'], string> = {
  primary: 'PRIMARY',
  supporting: 'SUPPORTING',
  dimension: 'DIMENSION',
  calculation_input: 'CALC INPUT',
};

const evidenceClaimPresentation = (reference: ObservationEvidenceRef) => {
  if (reference.role === 'dimension') {
    return { badge: 'DIMENSION CLAIM', label: '维度声明', tone: 'warning' as const };
  }
  if (reference.role === 'calculation_input') {
    return { badge: 'INPUT CLAIM', label: '计算输入声明', tone: 'neutral' as const };
  }
  return { badge: 'METRIC CLAIM', label: '指标声明', tone: 'info' as const };
};

function EvidenceReference({ reference }: { reference: ObservationEvidenceRef }) {
  const { fragment } = reference;
  const claim = evidenceClaimPresentation(reference);
  return (
    <article className="evidence-ref-item">
      <header>
        <div>
          <Status tone={claim.tone}>{claim.badge}</Status>
          <Status tone={reference.role === 'primary' ? 'ok' : 'neutral'}>
            {evidenceRoleLabel[reference.role]}
          </Status>
          <strong>{reference.claim_key}</strong>
        </div>
        <span className="mono">{fragment.locator_type}</span>
      </header>
      <dl className="detail-list compact">
        <div><dt>声明类型</dt><dd>{claim.label}</dd></div>
        <div><dt>声明键</dt><dd className="mono break">{reference.claim_key}</dd></div>
        <div><dt>引用角色</dt><dd>{evidenceRoleLabel[reference.role]}</dd></div>
        <div><dt>字段路径</dt><dd className="mono break">{reference.field_path}</dd></div>
        <div><dt>引用顺序</dt><dd>{reference.ordinal + 1}</dd></div>
        <div><dt>片段 ID</dt><dd className="mono break">{fragment.fragment_id}</dd></div>
        <div><dt>定位器</dt><dd className="mono break">{jsonValue(fragment.locator)}</dd></div>
        <div><dt>来源</dt><dd className="break">{fragment.source_key} · {safeHostname(fragment.source_url)}</dd></div>
        <div><dt>来源定义</dt><dd className="mono break">{fragment.source_definition_id ?? '历史快照未关联来源定义'}</dd></div>
        <div><dt>快照 ID</dt><dd className="mono break">{fragment.snapshot_id}</dd></div>
        <div><dt>抓取时间</dt><dd>{formatDate(fragment.retrieved_at)}</dd></div>
        <div><dt>发布时间</dt><dd>{fragment.published_at ? formatDate(fragment.published_at) : '来源未提供'}</dd></div>
        <div><dt>媒体 / 字节</dt><dd>{fragment.artifact_media_type} · {fragment.artifact_byte_size.toLocaleString()} bytes</dd></div>
        <div><dt>文件 SHA-256</dt><dd className="mono break">{fragment.artifact_sha256}</dd></div>
        <div><dt>文本 SHA-256</dt><dd className="mono break">{fragment.text_sha256 ?? '片段未提供文本哈希'}</dd></div>
      </dl>
      {fragment.text && (
        <details className="evidence-excerpt">
          <summary>查看存储片段文本</summary>
          <pre>{fragment.text}</pre>
        </details>
      )}
      <div className="drawer-actions">
        <a className="secondary-button" href={fragment.source_url} target="_blank" rel="noreferrer">
          <ExternalLink size={14} /> 打开来源
        </a>
        <a className="secondary-button" href={api.artifactUrl(fragment.artifact_id)}>
          <Download size={14} /> 下载原始文件
        </a>
      </div>
    </article>
  );
}

export function ObservationLineageTrace({ observation }: { observation: MetricObservation }) {
  const { lineage } = observation;
  const presentation = lineagePresentation[lineage.state];
  const run = lineage.origin.extraction_run;
  const fragmentCount = new Set(
    lineage.evidence_refs.map((reference) => reference.fragment.fragment_id),
  ).size;

  return (
    <section className="observation-lineage" aria-label={`${observation.metric_key} 的观测血缘`}>
      <div className="lineage-heading">
        <h4><GitBranch size={13} /> 观测血缘</h4>
        <div className="trust-record-statuses">
          <Status tone={presentation.tone}>{presentation.label}</Status>
          <Status tone={lineage.evidence_set_complete ? 'info' : 'danger'}>
            {lineage.evidence_set_complete ? 'EVIDENCE SET COMPLETE' : 'EVIDENCE SET INCOMPLETE'}
          </Status>
        </div>
      </div>

      <div className="lineage-rail">
        <div className="lineage-node">
          <span><FileSearch size={12} /> L1 EVIDENCE</span>
          <strong>{lineage.evidence_refs.length} CLAIMS / {fragmentCount} FRAGMENTS</strong>
          <small>冻结观测级声明与片段集合</small>
        </div>
        <div className="lineage-node">
          <span><Database size={12} /> {originLabel(observation)}</span>
          <strong className="mono break">{originIdentifier(observation)}</strong>
          <small>{lineage.origin.kind.toUpperCase()}</small>
        </div>
        <div className="lineage-node">
          <span>INFO OBSERVATION</span>
          <strong>{observation.metric_key}</strong>
          <small className="mono break">{observation.id}</small>
        </div>
      </div>

      {run && (
        <div className="lineage-run-detail">
          <div className="lineage-detail-heading">
            <strong>直接抽取运行</strong>
            <div className="trust-record-statuses">
              <Status tone={run.validation.valid ? 'ok' : 'danger'}>
                {run.validation.valid ? 'OUTPUT VALIDATED' : 'OUTPUT INVALID'}
              </Status>
              <Status tone={run.input_manifest.status === 'frozen_header_present' ? 'info' : 'warning'}>
                {run.input_manifest.status === 'frozen_header_present'
                  ? 'INPUT MANIFEST FROZEN'
                  : 'INPUT MANIFEST UNREPLAYABLE'}
              </Status>
            </div>
          </div>
          <dl className="detail-list compact">
            <div><dt>ExtractionRun ID</dt><dd className="mono break">{run.id}</dd></div>
            <div><dt>快照 ID</dt><dd className="mono break">{run.snapshot_id}</dd></div>
            <div><dt>输出字段</dt><dd className="mono break">record[{run.output_record_ordinal}] · {run.field_path}</dd></div>
            <div><dt>关联方式</dt><dd>{run.match_method}</dd></div>
            <div><dt>提供方 / 模型</dt><dd>{run.provider} / {run.model}</dd></div>
            <div><dt>提示词版本</dt><dd>{run.prompt_version}</dd></div>
            <div><dt>输入哈希</dt><dd className="mono break">{run.input_hash}</dd></div>
            <div><dt>输入片段数</dt><dd>{run.input_manifest.input_count ?? '—'}</dd></div>
            <div><dt>清单哈希</dt><dd className="mono break">{run.input_manifest.manifest_hash ?? '—'}</dd></div>
            <div><dt>运行时间</dt><dd>{formatDate(run.created_at)}</dd></div>
          </dl>
          {run.validation.issues.length > 0 && (
            <div className="lineage-issues" role="alert">
              {run.validation.issues.map((issue, index) => (
                <p key={`${issue.path}:${index}`}><span className="mono">{issue.path}</span> · {issue.message}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {lineage.origin.parent_observation_ids.length > 0 && (
        <div className="lineage-parent-list">
          <strong>{lineage.origin.kind === 'revision' ? '被替代的父观测' : '确定性运行输入观测'}</strong>
          {lineage.origin.parent_observation_ids.map((id, index) => (
            <span className="mono break" key={`${id}:${index}`}>{index + 1}. {id}</span>
          ))}
        </div>
      )}

      {lineage.state === 'legacy_unverified' && (
        <p className="lineage-alert lineage-alert-warning">
          迁移前记录没有直接运行关联，保持 LEGACY_UNVERIFIED；系统不会反推模型或运行 ID。
        </p>
      )}
      {lineage.state === 'incomplete' && (
        <p className="lineage-alert lineage-alert-danger">
          直接血缘不完整；当前记录不得晋级可信。
        </p>
      )}
      {lineage.state === 'derived' && (
        <p className="lineage-alert lineage-alert-info">
          该值由修订或确定性运行生成，不存在直接 ExtractionRun；请沿父观测查看原始证据。
        </p>
      )}
      {!lineage.evidence_set_complete && (
        <p className="lineage-alert lineage-alert-danger">
          冻结证据集合的声明数量与返回片段不一致；界面不会用兼容字段补齐。
        </p>
      )}

      <div className="lineage-evidence-heading">
        <strong>观测级证据声明</strong>
        <Status tone={lineage.evidence_refs.length ? 'info' : 'warning'}>
          {lineage.evidence_refs.length} CITATIONS · {fragmentCount} FRAGMENTS
        </Status>
      </div>
      {lineage.evidence_refs.length ? (
        <div className="evidence-ref-stack">
          {lineage.evidence_refs.map((reference) => (
            <EvidenceReference key={reference.association_id} reference={reference} />
          ))}
        </div>
      ) : (
        <p className="lineage-alert lineage-alert-warning">
          未绑定观测级证据片段；不会用面板级片段或旧单片段字段代替。
        </p>
      )}
    </section>
  );
}
