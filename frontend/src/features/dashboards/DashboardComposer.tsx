import { useState } from 'react';
import { Archive, RefreshCw, Sparkles, X } from 'lucide-react';

import { slugify } from '../../lib/format';
import { api, type DashboardProposal } from '../../lib/v2-api';
import { Button, IconButton, Status } from '../../components/ui';

export function DashboardComposer({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: (dashboardId: string) => void;
}) {
  const [title, setTitle] = useState('');
  const [provider, setProvider] = useState('openai-compatible');
  const [model, setModel] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [proposalText, setProposalText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const propose = async () => {
    setBusy(true);
    setError('');
    try {
      const proposal = await api.proposeDashboard({
        title,
        provider,
        model: model || undefined,
        base_url: baseUrl || undefined,
        api_key: apiKey || undefined,
      });
      setProposalText(JSON.stringify(proposal, null, 2));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '生成失败');
    } finally {
      setBusy(false);
    }
  };

  const saveDraft = async () => {
    setBusy(true);
    setError('');
    try {
      const proposal = JSON.parse(proposalText) as DashboardProposal;
      const key = slugify(proposal.title || title);
      const dashboard = await api.createDashboard({
        key: `${key}-${Date.now().toString(36)}`,
        title: proposal.title || title,
        description: proposal.description || '',
      });
      await api.createDashboardVersion(dashboard.id, {
        state: 'draft',
        research_brief: { title, source: 'llm_proposal' },
        generation_model: proposal._generation?.model,
        generation_prompt_version: 'dashboard-design-v1',
        panels: proposal.panels.map((panel) => ({
          ...panel,
          template_kind: 'ui_dsl',
          extraction_prompt_version: '1',
          model_settings: {},
        })),
      });
      setApiKey('');
      onSaved(dashboard.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '保存失败');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="composer" role="dialog" aria-modal="true" aria-label="新建情报主面板">
        <div className="drawer-header">
          <div>
            <span className="eyebrow"><Sparkles size={12} /> LLM DASHBOARD DESIGNER</span>
            <h2>从课题生成主面板草稿</h2>
          </div>
          <IconButton aria-label="关闭新建面板" onClick={onClose}><X size={18} /></IconButton>
        </div>
        <div className="composer-grid">
          <label className="field span-2"><span>课题标题</span><input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="例如：全球人形机器人产业链" /></label>
          <label className="field"><span>模型供应商</span><select value={provider} onChange={(event) => setProvider(event.target.value)}><option value="openai-compatible">OpenAI Compatible</option><option value="google">Google Gemini</option></select></label>
          <label className="field"><span>模型</span><input value={model} onChange={(event) => setModel(event.target.value)} placeholder="组织默认模型" /></label>
          <label className="field"><span>API Base URL</span><input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="使用后端默认配置" /></label>
          <label className="field"><span>临时 API Key</span><input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder="仅发送本次请求，不写入版本" /></label>
        </div>
        <div className="credential-notice">
          <Status tone="warning">EPHEMERAL CREDENTIAL</Status>
          临时 Key 只用于本次设计请求。加密凭证库尚未实现，因此不会保存。
        </div>
        <div className="composer-toolbar">
          <Button disabled={!title || busy} onClick={() => void propose()}>
            <RefreshCw size={15} className={busy ? 'spin' : ''} /> 生成设计
          </Button>
          <span>生成后可人工编辑结构化 Schema、UI DSL 与提示词</span>
        </div>
        <textarea className="json-editor" value={proposalText} onChange={(event) => setProposalText(event.target.value)} placeholder="LLM 生成的组件、JSON Schema、UI DSL、提示词会显示在这里…" />
        {error && <div className="error-banner">{error}</div>}
        <div className="composer-actions">
          <Button onClick={onClose}>取消</Button>
          <Button variant="primary" disabled={!proposalText || busy} onClick={() => void saveDraft()}>
            <Archive size={15} /> 保存为草稿版本
          </Button>
        </div>
      </div>
    </div>
  );
}
