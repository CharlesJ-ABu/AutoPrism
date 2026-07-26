import { useEffect, useState } from 'react';
import {
  Archive,
  CheckCircle2,
  Code2,
  FileEdit,
  GitBranch,
  History,
  ShieldAlert,
} from 'lucide-react';

import { formatDate } from '../../lib/format';
import {
  api,
  type DashboardVersionDetail,
  type DashboardVersionSummary,
} from '../../lib/v2-api';
import { Button, Drawer, LoadingState, Status } from '../../components/ui';

type SaveState = 'draft' | 'published';

function editablePayload(detail: DashboardVersionDetail) {
  return {
    state: 'draft',
    research_brief: {
      ...detail.research_brief,
      based_on_version: detail.version,
    },
    generation_model: detail.generation_model,
    generation_prompt_version: detail.generation_prompt_version,
    panels: detail.panels.map((panel) => ({
      key: panel.key,
      title: panel.title,
      description: panel.description,
      data_schema: panel.data_schema,
      template_kind: panel.template_kind,
      ui_dsl: panel.ui_dsl,
      component_code: panel.component_code,
      visualization_contract: panel.visualization_contract,
      extraction_prompt: panel.extraction_prompt,
      extraction_prompt_version: panel.extraction_prompt_version,
      model_settings: panel.model_settings,
      source_pool_id: panel.source_pool_id,
    })),
  };
}

export function VersionManagerDrawer({
  dashboardId,
  dashboardTitle,
  viewedVersion,
  onClose,
  onOpenVersion,
  onCreated,
}: {
  dashboardId: string;
  dashboardTitle: string;
  viewedVersion: number;
  onClose: () => void;
  onOpenVersion: (version: number) => Promise<void>;
  onCreated: () => Promise<void>;
}) {
  const [versions, setVersions] = useState<DashboardVersionSummary[]>([]);
  const [editorText, setEditorText] = useState('');
  const [sourceVersion, setSourceVersion] = useState<number>();
  const [publishConfirmed, setPublishConfirmed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const loadHistory = async () => {
    setLoading(true);
    setError('');
    try {
      setVersions(await api.listDashboardVersions(dashboardId));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '版本历史加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadHistory();
  }, [dashboardId]);

  const beginRevision = async (version: number) => {
    setBusy(true);
    setError('');
    try {
      const detail = await api.getDashboardVersion(dashboardId, version);
      setSourceVersion(version);
      setEditorText(JSON.stringify(editablePayload(detail), null, 2));
      setPublishConfirmed(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '版本内容加载失败');
    } finally {
      setBusy(false);
    }
  };

  const save = async (state: SaveState) => {
    setBusy(true);
    setError('');
    try {
      const payload = JSON.parse(editorText) as Record<string, unknown>;
      payload.state = state;
      await api.createDashboardVersion(dashboardId, payload);
      setEditorText('');
      setSourceVersion(undefined);
      setPublishConfirmed(false);
      await loadHistory();
      await onCreated();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '新版本保存失败');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Drawer
      eyebrow={<><History size={12} /> IMMUTABLE VERSION CONTROL</>}
      title={`${dashboardTitle} · 版本管理`}
      onClose={onClose}
      wide
    >
      <section className="drawer-section">
        <div className="drawer-section-title">
          <h3>不可变版本历史</h3>
          <Status tone="info">{versions.length} VERSIONS</Status>
        </div>
        <p className="section-help">
          历史版本只能读取。任何编辑都会创建包含完整 Schema、UI DSL、组件源码、
          提示词和模型设置的新版本。
        </p>
        {loading ? (
          <LoadingState label="正在读取版本历史…" />
        ) : (
          <div className="version-list">
            {versions.map((version) => (
              <article
                className={`version-item ${viewedVersion === version.version ? 'active' : ''}`}
                key={version.id}
              >
                <div className="version-sequence"><GitBranch size={14} /> v{version.version}</div>
                <div className="version-copy">
                  <strong>{version.state.toUpperCase()}</strong>
                  <span>{formatDate(version.created_at)} · {version.panel_count} 个子面板</span>
                  <small>
                    {version.generation_model
                      ? `${version.generation_model} / ${version.generation_prompt_version ?? '未标注提示词版本'}`
                      : '人工或确定性模板版本'}
                  </small>
                </div>
                <div className="version-actions">
                  <Button
                    variant="ghost"
                    disabled={busy || viewedVersion === version.version}
                    onClick={() => void onOpenVersion(version.version)}
                  >
                    查看
                  </Button>
                  <Button disabled={busy} onClick={() => void beginRevision(version.version)}>
                    <FileEdit size={13} /> 基于此版本修订
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {sourceVersion && (
        <section className="drawer-section">
          <div className="drawer-section-title">
            <h3>从 v{sourceVersion} 创建新版本</h3>
            <Status tone="warning">APPEND ONLY</Status>
          </div>
          <div className="contract-notice">
            <Code2 size={16} />
            <span>
              <code>custom_react</code> 源码可以冻结并校验哈希，但隔离编译/运行尚未实现；
              当前客户端不会执行用户组件代码。
            </span>
          </div>
          <textarea
            aria-label="版本 JSON 编辑器"
            className="json-editor version-editor"
            value={editorText}
            onChange={(event) => setEditorText(event.target.value)}
          />
          <label className="publish-confirmation">
            <input
              type="checkbox"
              checked={publishConfirmed}
              onChange={(event) => setPublishConfirmed(event.target.checked)}
            />
            <ShieldAlert size={15} />
            我确认发布会创建新的冻结版本，历史版本保持不变。
          </label>
          <div className="composer-actions version-save-actions">
            <Button disabled={busy || !editorText} onClick={() => void save('draft')}>
              <Archive size={14} /> 保存新草稿
            </Button>
            <Button
              variant="primary"
              disabled={busy || !editorText || !publishConfirmed}
              onClick={() => void save('published')}
            >
              <CheckCircle2 size={14} /> 冻结并发布新版本
            </Button>
          </div>
        </section>
      )}

      {error && <div className="error-banner">{error}</div>}
    </Drawer>
  );
}
