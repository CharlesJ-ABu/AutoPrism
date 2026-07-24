const API_BASE = '/api/v2';

export interface DashboardListItem {
  id: string;
  key: string;
  title: string;
  description: string;
  latest_version: { id: string; version: number; state: string } | null;
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

export interface PanelView {
  id: string;
  key: string;
  version: number;
  title: string;
  description: string;
  data_schema: Record<string, unknown>;
  template_kind: string;
  ui_dsl: { children?: Array<{ type: string; columns?: string[] }> };
  extraction_prompt_version: string;
  data: { record_count?: number; records?: Array<Record<string, unknown>> } | null;
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
  version: { id: string; version: number; state: string };
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
    request(`/dashboards/${id}/versions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  artifactUrl: (id: string) => `${API_BASE}/evidence/artifacts/${id}`,
};
