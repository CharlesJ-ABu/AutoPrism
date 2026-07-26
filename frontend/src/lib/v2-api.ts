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
  artifactUrl: (id: string) => `${API_BASE}/evidence/artifacts/${id}`,
};
