const API_BASE = '/api/v2';

export interface DashboardListItem {
  id: string;
  key: string;
  title: string;
  description: string;
  latest_version: { id: string; version: number; state: string } | null;
}

export interface DashboardVersionRecord {
  id: string;
  dashboard_id: string;
  version: number;
  state: 'draft' | 'published' | 'archived';
  research_brief: Record<string, unknown>;
  generation_model: string | null;
  generation_prompt_version: string | null;
  created_at: string;
}

export interface DashboardVersionSummary extends DashboardVersionRecord {
  panel_count: number;
}

export interface PanelVersionDefinition {
  id: string;
  panel_id: string;
  key: string;
  version: number;
  title: string;
  description: string;
  data_schema: Record<string, unknown>;
  template_kind: 'ui_dsl' | 'custom_react';
  ui_dsl: Record<string, unknown>;
  component_code: string | null;
  component_code_sha256: string | null;
  visualization_contract: Record<string, unknown>;
  extraction_prompt: string;
  extraction_prompt_version: string;
  model_settings: Record<string, unknown>;
  source_pool_id: string | null;
  created_at: string;
}

export interface DashboardVersionDetail extends DashboardVersionRecord {
  panels: PanelVersionDefinition[];
}

export interface SourcePool {
  id: string;
  key: string;
  name: string;
  topic: string;
  dashboard_version_key: string | null;
  discovery_query: string | null;
  settings: Record<string, unknown>;
  created_at: string;
}

export interface SourceDefinition {
  id: string;
  pool_id: string;
  key: string;
  name: string;
  canonical_url: string;
  kind: 'html' | 'pdf' | 'csv' | 'xlsx' | 'rss' | 'api';
  enabled: boolean;
  requires_auth: boolean;
  credential_reference: string | null;
  robots_url: string | null;
  terms_url: string | null;
  global_reputation: number;
  topic_authority: number;
  refresh_policy: Record<string, unknown>;
  request_config: Record<string, unknown>;
  parser_config: Record<string, unknown>;
  created_at: string;
}

export interface CollectionJob {
  id: string;
  source_definition_id: string;
  idempotency_key: string;
  state: 'queued' | 'running' | 'succeeded' | 'failed' | 'blocked' | 'cancelled';
  attempt_count: number;
  max_attempts: number;
  policy_result: Record<string, unknown>;
  result_snapshot_id: string | null;
  error: Record<string, unknown>;
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface HumanAction {
  id: string;
  collection_job_id: string;
  reason_code: string;
  instructions: string;
  context: Record<string, unknown>;
  state: 'open' | 'resolved' | 'dismissed';
  created_at: string;
  resolved_at: string | null;
}

export interface MetricObservation {
  id: string;
  panel_version_key: string;
  schema_version: string;
  metric_key: string;
  raw_value: Record<string, unknown>;
  normalized_value: Record<string, unknown>;
  unit: string | null;
  currency: string | null;
  observed_at: string | null;
  period_start: string | null;
  period_end: string | null;
  geographic_scope: Record<string, unknown>;
  dimensions: Record<string, unknown>;
  extraction_model: string | null;
  extraction_prompt_version: string | null;
  confidence: number | null;
  trust_state: 'unverified' | 'verified' | 'rejected' | 'legacy_unverified';
  supersedes_id: string | null;
  created_at: string;
  evidence: {
    fragment_id: string;
    locator_type: string;
    locator: Record<string, unknown>;
    text: string | null;
    text_sha256: string | null;
    snapshot_id: string;
    source_url: string;
    retrieved_at: string;
    published_at: string | null;
    artifact_id: string;
    artifact_sha256: string;
  };
}

export interface ObservationRevision {
  id: string;
  original_observation_id: string;
  replacement_observation_id: string;
  metric_key: string;
  reason: string;
  revised_by: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface CalculationRun {
  id: string;
  output_observation_id: string;
  output_metric_key: string;
  operation: string;
  input_observation_ids: string[];
  parameters: Record<string, unknown>;
  result: Record<string, unknown>;
  engine_version: string;
  replay_hash: string;
  created_at: string;
}

export interface ValidationRun {
  id: string;
  comparison_key: string;
  observation_ids: string[];
  rule_version: string;
  tolerance: { absolute?: string; relative?: string };
  result: {
    minimum?: string | null;
    maximum?: string | null;
    spread?: string | null;
    relative_spread?: string | null;
  };
  state: 'pending' | 'passed' | 'conflict' | 'needs_review' | 'rejected';
  created_at: string;
}

export interface ReviewDecision {
  id: string;
  supersedes_id: string | null;
  outcome: 'approved' | 'rejected' | 'needs_information';
  decision: Record<string, unknown>;
  decided_by: string;
  created_at: string;
}

export interface ReviewCase {
  id: string;
  validation_run_id: string | null;
  observation_ids: string[];
  reason_codes: string[];
  created_at: string;
  decisions: ReviewDecision[];
  latest_decision: ReviewDecision | null;
}

export interface Evidence {
  fragment_id: string;
  locator_type: string;
  locator: Record<string, unknown>;
  text_sha256: string;
  source_url: string;
  retrieved_at: string;
  published_at: string | null;
  artifact_id: string;
  artifact_sha256: string;
  artifact_byte_size: number;
  artifact_media_type: string;
}

export interface UiDslNode {
  type: 'stack' | 'metric' | 'table' | 'provenance';
  field?: string;
  label?: string;
  unit?: string;
  columns?: string[];
  page_size?: number;
  children?: UiDslNode[];
  [key: string]: unknown;
}

export interface PanelView {
  id: string;
  key: string;
  version: number;
  title: string;
  description: string;
  data_schema: Record<string, unknown>;
  template_kind: string;
  ui_dsl: UiDslNode;
  extraction_prompt_version: string;
  data: Record<string, unknown> | null;
  extraction: {
    id: string;
    provider: string;
    model: string;
    input_hash: string;
    validation: { valid: boolean; issues: unknown[] };
    created_at: string;
  } | null;
  evidence: Evidence[];
}

export interface DashboardView {
  dashboard: DashboardListItem;
  version: DashboardVersionRecord;
  panels: PanelView[];
}

interface ProposalPanel {
  key: string;
  title: string;
  description: string;
  data_schema: Record<string, unknown>;
  visualization_contract: Record<string, unknown>;
  ui_dsl: Record<string, unknown>;
  extraction_prompt: string;
  source_discovery_query?: string;
}

export interface DashboardProposal {
  title: string;
  description: string;
  panels: ProposalPanel[];
  _generation?: { provider: string; model: string };
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.body ? { 'Content-Type': 'application/json' } : {}),
      ...options?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail));
  }
  return response.json() as Promise<T>;
}

export const api = {
  listDashboards: () => request<DashboardListItem[]>('/dashboards'),
  getDashboardView: (id: string, version: number) =>
    request<DashboardView>(`/dashboards/${id}/versions/${version}/view`),
  proposeDashboard: (payload: Record<string, unknown>) =>
    request<DashboardProposal>('/dashboards/propose', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createDashboard: (payload: Record<string, unknown>) =>
    request<DashboardListItem>('/dashboards', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createDashboardVersion: (id: string, payload: Record<string, unknown>) =>
    request<DashboardVersionDetail>(`/dashboards/${id}/versions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listDashboardVersions: (id: string) =>
    request<DashboardVersionSummary[]>(`/dashboards/${id}/versions`),
  getDashboardVersion: (id: string, version: number) =>
    request<DashboardVersionDetail>(`/dashboards/${id}/versions/${version}`),
  listSourcePools: () => request<SourcePool[]>('/sources/pools'),
  createSourcePool: (payload: Record<string, unknown>) =>
    request<SourcePool>('/sources/pools', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listSources: () => request<SourceDefinition[]>('/sources'),
  createSource: (poolId: string, payload: Record<string, unknown>) =>
    request<SourceDefinition>(`/sources/pools/${poolId}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  collectSource: (sourceId: string) =>
    request<CollectionJob>(`/sources/${sourceId}/collect`, { method: 'POST' }),
  listCollectionJobs: () => request<CollectionJob[]>('/sources/jobs'),
  listHumanActions: () => request<HumanAction[]>('/sources/actions'),
  runExtraction: (payload: { panel_version_id: string; snapshot_id: string }) =>
    request<{ run_id: string; observation_ids: string[]; issues: Array<{ path: string; message: string }> }>(
      '/extractions',
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    ),
  listObservations: (panelVersionKey: string) =>
    request<MetricObservation[]>(
      `/evidence/observations?panel_version_key=${encodeURIComponent(panelVersionKey)}`,
    ),
  listObservationRevisions: (panelVersionKey: string) =>
    request<ObservationRevision[]>(
      `/evidence/revisions?panel_version_key=${encodeURIComponent(panelVersionKey)}`,
    ),
  reviseObservation: (
    observationId: string,
    payload: {
      raw_value: Record<string, unknown>;
      normalized_value: Record<string, unknown>;
      reason: string;
      revised_by: string;
      evidence_fragment_id?: string;
      unit?: string | null;
      currency?: string | null;
      dimensions?: Record<string, unknown>;
      geographic_scope?: Record<string, unknown>;
      metadata?: Record<string, unknown>;
    },
  ) =>
    request<ObservationRevision>(`/evidence/observations/${observationId}/revisions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listCalculations: (panelVersionKey: string) =>
    request<CalculationRun[]>(
      `/verification/calculations?panel_version_key=${encodeURIComponent(panelVersionKey)}`,
    ),
  calculate: (payload: {
    operation: string;
    input_observation_ids: string[];
    output_metric_key: string;
    output_unit: string | null;
    parameters: Record<string, unknown>;
  }) =>
    request<{
      observation_id: string;
      calculation_run_id: string;
      result: Record<string, unknown>;
      replay_hash: string;
    }>('/verification/calculate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listValidations: (panelVersionKey: string) =>
    request<ValidationRun[]>(
      `/verification/validations?panel_version_key=${encodeURIComponent(panelVersionKey)}`,
    ),
  validateObservations: (payload: {
    observation_ids: string[];
    absolute_tolerance: string;
    relative_tolerance: string;
  }) =>
    request<{
      validation_run_id: string;
      state: ValidationRun['state'];
      result: ValidationRun['result'];
      review_case_id: string | null;
    }>('/verification/validate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listReviews: (panelVersionKey: string) =>
    request<ReviewCase[]>(
      `/verification/reviews?panel_version_key=${encodeURIComponent(panelVersionKey)}`,
    ),
  decideReview: (
    caseId: string,
    payload: {
      outcome: ReviewDecision['outcome'];
      decision: Record<string, unknown>;
      decided_by: string;
      supersedes_id?: string;
    },
  ) =>
    request<ReviewDecision & { review_case_id: string }>(
      `/verification/reviews/${caseId}/decisions`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      },
    ),
  artifactUrl: (id: string) => `${API_BASE}/evidence/artifacts/${id}`,
};
