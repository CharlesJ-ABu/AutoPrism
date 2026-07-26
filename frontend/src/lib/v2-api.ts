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
  artifactUrl: (id: string) => `${API_BASE}/evidence/artifacts/${id}`,
};
