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

export interface SourceDiscoveryCandidate {
  id: string;
  ordinal: number;
  title: string;
  url: string;
  url_sha256: string;
  display_host: string;
  snippet: string;
  mime_type: string | null;
  suggested_kind: 'html' | 'pdf' | 'csv' | 'xlsx' | 'rss';
  created_at: string;
}

export interface SourceDiscoveryRun {
  id: string;
  pool_id: string;
  provider: 'google-programmable-search-v1';
  query: string;
  provider_config_hash: string;
  result_count: number;
  result_hash: string;
  integrity_valid: boolean;
  requested_at: string;
  completed_at: string;
  candidates: SourceDiscoveryCandidate[];
}

export interface SourceRefreshSchedule {
  id: string;
  source_definition_id: string;
  mode: 'manual' | 'interval';
  interval_minutes: number | null;
  authorization_attested: boolean;
  actor_label: string;
  supersedes_id: string | null;
  created_at: string;
  current: boolean;
}

export interface ScheduleDispatch {
  id: string;
  schedule_id: string;
  source_definition_id: string;
  bucket_key: string;
  due_at: string;
  observed_at: string;
  outcome: 'queued' | 'skipped' | 'failed';
  reason_code: string;
  collection_job_id: string | null;
}

export type ResearchActionState =
  | 'proposed'
  | 'authorized'
  | 'started'
  | 'completed'
  | 'queued'
  | 'blocked'
  | 'failed'
  | 'missing';

export interface ResearchActionEvent {
  id: string;
  event_type: Exclude<ResearchActionState, 'missing'>;
  actor_label: string;
  details: Record<string, unknown>;
  predecessor_id: string | null;
  created_at: string;
}

export interface ResearchAction {
  id: string;
  run_id: string;
  plan_id: string;
  ordinal: number;
  action_type: 'discover' | 'collect';
  specification: Record<string, unknown>;
  requires_authorization: boolean;
  created_at: string;
  current_state: ResearchActionState;
  events: ResearchActionEvent[];
  collection_job: CollectionJob | null;
}

export interface ResearchPlanDocument {
  summary: string;
  research_questions: string[];
  discovery_actions: Array<{ query: string; purpose: string; limit: number }>;
  collection_actions: Array<{ source_key: string; purpose: string }>;
  analysis_targets: Array<{
    key: string;
    question: string;
    expected_fields: string[];
    evidence_expectation: string;
    requires_cross_source: boolean;
  }>;
  interpretation_questions: string[];
  limitations: string[];
}

export interface ResearchRun {
  id: string;
  source_pool_id: string;
  title: string;
  objective: string;
  constraints: Record<string, unknown>;
  actor_label: string;
  created_at: string;
  plan: {
    id: string;
    provider: string;
    model: string;
    prompt_version: string;
    system_prompt_sha256: string;
    input_hash: string;
    input_manifest: Record<string, unknown>;
    output_hash: string;
    document: ResearchPlanDocument;
    action_count: number;
    model_metadata: Record<string, unknown>;
    integrity_valid: boolean;
    created_at: string;
  } | null;
  actions: ResearchAction[];
}

export interface EvidenceInterpretation {
  id: string;
  title: string;
  question: string;
  provider: string;
  model: string;
  prompt_version: 'evidence-bound-interpretation-v1';
  system_prompt_sha256: string;
  input_hash: string;
  input_manifest: Record<string, unknown>;
  output_hash: string;
  output: {
    summary: string;
    claims: Array<{
      statement: string;
      observation_ids: string[];
      trust_assessment_ids: string[];
      reasoning: string;
      limitation: string;
    }>;
    limitations: string[];
  };
  input_count: number;
  created_by: string;
  created_at: string;
  integrity_valid: boolean;
  currently_grounded: boolean;
  inputs: Array<{
    ordinal: number;
    observation_id: string;
    trust_assessment_id: string;
    currently_eligible: boolean;
  }>;
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

export type ObservationLineageState =
  | 'direct'
  | 'derived'
  | 'legacy_unverified'
  | 'incomplete';

export type ObservationOriginKind =
  | 'extraction'
  | 'revision'
  | 'calculation'
  | 'conversion'
  | 'legacy';

export interface ObservationExtractionRun {
  id: string;
  panel_version_id: string;
  snapshot_id: string;
  provider: string;
  model: string;
  prompt_version: string;
  input_hash: string;
  validation: {
    valid: boolean;
    issues: Array<{ path: string; message: string }>;
    [key: string]: unknown;
  };
  input_manifest: {
    status: 'frozen_header_present' | 'legacy_unreplayable';
    input_count: number | null;
    frozen_count: number | null;
    manifest_hash: string | null;
  };
  output_record_ordinal: number;
  field_path: string;
  match_method: 'direct_write' | 'backfill_exact';
  created_at: string;
}

export interface ExtractionInputManifest {
  extraction_run_id: string;
  status: 'frozen_manifest_present' | 'legacy_unreplayable';
  input_count: number | null;
  frozen_count: number | null;
  manifest_hash: string | null;
  inputs: Array<{
    ordinal: number;
    evidence_fragment_id: string;
    snapshot_id: string;
    source_key: string;
    source_url: string;
    retrieved_at: string;
    locator_type: string;
    locator: Record<string, unknown>;
    extracted_text: string | null;
    extracted_text_sha256: string;
    manifest_entry_hash: string;
    artifact_id: string;
    artifact_sha256: string;
    artifact_byte_size: number;
    artifact_media_type: string;
  }>;
}

export interface ObservationEvidenceFragment {
  fragment_id: string;
  locator_type: string;
  locator: Record<string, unknown>;
  text: string | null;
  text_sha256: string | null;
  snapshot_id: string;
  source_definition_id: string | null;
  source_key: string;
  source_url: string;
  retrieved_at: string;
  published_at: string | null;
  artifact_id: string;
  artifact_sha256: string;
  artifact_byte_size: number;
  artifact_media_type: string;
}

export interface ObservationEvidenceRef {
  association_id: string;
  ordinal: number;
  role: 'primary' | 'supporting' | 'dimension' | 'calculation_input';
  claim_key: string;
  field_path: string;
  fragment: ObservationEvidenceFragment;
}

export interface ObservationLineage {
  state: ObservationLineageState;
  origin: {
    kind: ObservationOriginKind;
    extraction_run: ObservationExtractionRun | null;
    parent_observation_ids: string[];
    revision_id: string | null;
    calculation_run_id: string | null;
    conversion_run_id: string | null;
  };
  evidence_refs: ObservationEvidenceRef[];
  evidence_set_complete: boolean;
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
  numeric: {
    value: string;
    uncertainty_kind: 'exact' | 'bounded' | 'unknown';
    absolute_error: string | null;
    uncertainty_basis: Record<string, unknown>;
    evidence_count: number;
  } | null;
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
  lineage: ObservationLineage;
  /** Compatibility-only singular citation. New UI must use lineage.evidence_refs. */
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

export interface ConversionRun {
  id: string;
  output_observation_id: string;
  output_metric_key: string;
  input_observation_id: string;
  input_trust_assessment_id: string;
  kind: 'unit' | 'currency';
  fx_rate_observation_id: string | null;
  registry_version: string;
  engine_version: string;
  plan: Record<string, unknown>;
  input_snapshot: Record<string, unknown>;
  result: Record<string, unknown>;
  replay_hash: string;
  created_at: string;
}

export interface UnitRegistry {
  version: string;
  units: Array<{
    code: string;
    dimension: string;
    semantic_kind: string;
    scale_to_base: string;
  }>;
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

export interface TrustAssessment {
  id: string;
  observation_id: string;
  metric_key: string;
  validation_run_id: string | null;
  calculation_run_id: string | null;
  conversion_run_id: string | null;
  review_decision_id: string | null;
  eligible: boolean;
  currently_eligible: boolean;
  reason_codes: string[];
  policy_version: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface L2Insight {
  id: string;
  title: string;
  input_hash: string;
  engine_version: string;
  prompt_version: string;
  output: {
    summary?: string;
    items?: Array<Record<string, unknown>>;
    limitations?: string[];
  };
  created_by: string;
  created_at: string;
  inputs: Array<{
    ordinal: number;
    observation_id: string;
    trust_assessment_id: string;
  }>;
}

export type TrustedMapGeometry =
  | { type: 'Point'; coordinates: [number, number] }
  | { type: 'LineString'; coordinates: [[number, number], [number, number]] }
  | { type: 'Polygon'; coordinates: Array<Array<[number, number]>> };

export interface TrustedMapFeature {
  id: string;
  contract_version: 'trusted-insight-map-v1';
  insight_id: string;
  title: string;
  summary: string;
  display_type:
    | 'MARKER'
    | 'HOTSPOT'
    | 'RIPPLE'
    | 'FLOW'
    | 'COMPARISON'
    | 'SHIELD_UP'
    | 'ZONE';
  label: string;
  geometry: TrustedMapGeometry;
  observation_ids: string[];
  trust_assessment_ids: string[];
  panel_version_keys: string[];
  input_hash: string;
  engine_version: string;
  prompt_version: string;
  created_at: string;
}

export interface TrustedMapResponse {
  contract_version: 'trusted-insight-map-v1';
  features: TrustedMapFeature[];
  stats: {
    scanned_insights: number;
    current_insights: number;
    stale_or_invalid_insights: number;
    unsupported_contract_insights: number;
    without_geography: number;
    replay_mismatch_insights: number;
  };
}

export interface Evidence {
  fragment_id: string;
  locator_type: string;
  locator: Record<string, unknown>;
  text_sha256: string | null;
  source_url: string;
  retrieved_at: string;
  published_at: string | null;
  artifact_id: string;
  artifact_sha256: string;
  artifact_byte_size: number;
  artifact_media_type: string;
}

export interface UiDslNode {
  type: 'stack' | 'metric' | 'table' | 'chart' | 'timeline' | 'provenance';
  field?: string;
  label?: string;
  unit?: string;
  columns?: string[];
  page_size?: number;
  variant?: 'line' | 'bar' | 'area';
  x_field?: string;
  y_field?: string;
  series_field?: string;
  max_points?: number;
  max_series?: number;
  time_field?: string;
  title_field?: string;
  value_field?: string;
  max_items?: number;
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
  template_kind: 'ui_dsl' | 'custom_react';
  ui_dsl: UiDslNode;
  component_code: string | null;
  component_code_sha256: string | null;
  visualization_contract: Record<string, unknown>;
  extraction_prompt_version: string;
  data: Record<string, unknown> | null;
  data_state: 'not_run' | 'invalid' | 'unverified';
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
  discoverSources: (
    poolId: string,
    payload: {
      api_key: string;
      search_engine_id: string;
      query?: string;
      limit?: number;
      safe?: 'active' | 'off';
    },
  ) =>
    request<SourceDiscoveryRun>(`/sources/pools/${poolId}/discover`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listDiscoveryRuns: () =>
    request<SourceDiscoveryRun[]>('/sources/discovery-runs'),
  listRefreshSchedules: () =>
    request<SourceRefreshSchedule[]>('/sources/refresh-schedules'),
  createRefreshSchedule: (
    sourceId: string,
    payload: {
      mode: 'manual' | 'interval';
      interval_minutes?: number;
      authorization_confirmed: boolean;
    },
  ) =>
    request<SourceRefreshSchedule>(`/sources/${sourceId}/refresh-schedules`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listScheduleDispatches: () =>
    request<ScheduleDispatch[]>('/sources/schedule-dispatches'),
  listResearchRuns: () => request<ResearchRun[]>('/research/runs'),
  listInterpretations: () =>
    request<EvidenceInterpretation[]>('/research/interpretations'),
  createInterpretation: (payload: {
    title: string;
    question: string;
    observation_ids: string[];
    created_by: string;
    provider?: string;
    model?: string;
    base_url?: string;
    api_key?: string;
  }) =>
    request<EvidenceInterpretation>('/research/interpretations', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createResearchRun: (payload: {
    source_pool_id: string;
    title: string;
    objective: string;
    constraints: Record<string, unknown>;
    provider?: string;
    model?: string;
    base_url?: string;
    api_key?: string;
  }) =>
    request<ResearchRun>('/research/runs', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  executeResearchDiscovery: (
    actionId: string,
    payload: {
      api_key: string;
      search_engine_id: string;
      authorization_confirmed: boolean;
    },
  ) =>
    request<ResearchAction>(`/research/actions/${actionId}/discover`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  executeResearchCollection: (
    actionId: string,
    payload: { authorization_confirmed: boolean },
  ) =>
    request<ResearchAction>(`/research/actions/${actionId}/collect`, {
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
  getExtractionInputs: (runId: string) =>
    request<ExtractionInputManifest>(`/extractions/${runId}/inputs`),
  listObservations: (panelVersionKey: string) =>
    request<MetricObservation[]>(
      `/evidence/observations?panel_version_key=${encodeURIComponent(panelVersionKey)}`,
    ),
  listTrustedObservations: () =>
    request<MetricObservation[]>('/evidence/observations?trusted_only=true&limit=100'),
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
      evidence_fragment_ids?: string[];
      evidence_claims?: Record<string, string[]>;
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
    output_quantum: string;
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
  getUnitRegistry: () => request<UnitRegistry>('/verification/unit-registry'),
  listConversions: (panelVersionKey: string) =>
    request<ConversionRun[]>(
      `/verification/conversions?panel_version_key=${encodeURIComponent(panelVersionKey)}`,
    ),
  convert: (payload: {
    input_observation_id: string;
    kind: 'unit' | 'currency';
    output_metric_key: string;
    output_quantum: string;
    to_unit?: string;
    to_currency?: string;
    fx_rate_observation_id?: string;
  }) =>
    request<{
      observation_id: string;
      conversion_run_id: string;
      result: Record<string, unknown>;
      replay_hash: string;
    }>('/verification/conversions', {
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
  listTrustAssessments: (panelVersionKey: string) =>
    request<TrustAssessment[]>(
      `/verification/assessments?panel_version_key=${encodeURIComponent(panelVersionKey)}`,
    ),
  assessObservation: (payload: {
    observation_id: string;
    validation_run_id?: string;
  }) =>
    request<TrustAssessment>('/verification/assessments', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listInsights: () => request<L2Insight[]>('/insights'),
  listMapFeatures: (panelVersionKeys: string[]) => {
    const params = new URLSearchParams({ limit: '200' });
    panelVersionKeys.forEach((key) => params.append('panel_version_key', key));
    return request<TrustedMapResponse>(`/insights/map-features?${params.toString()}`);
  },
  createInsight: (payload: { observation_ids: string[]; created_by: string }) =>
    request<L2Insight>('/insights', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  artifactUrl: (id: string) => `${API_BASE}/evidence/artifacts/${id}`,
};
