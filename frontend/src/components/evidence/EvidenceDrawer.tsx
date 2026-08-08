import { Download, ExternalLink, FileJson2, ShieldCheck } from 'lucide-react';

import { formatDate } from '../../lib/format';
import { api, type PanelView } from '../../lib/v2-api';
import { TrustWorkspace } from '../../features/trust/TrustWorkspace';
import { Drawer, Status } from '../ui';

export function EvidenceDrawer({
  panel,
  onClose,
}: {
  panel: PanelView;
  onClose: () => void;
}) {
  return (
    <Drawer
      eyebrow={<><ShieldCheck size={12} /> EVIDENCE TRACE TERMINAL</>}
      title={panel.title}
      onClose={onClose}
      wide
    >
      <section className="drawer-section">
        <div className="drawer-section-title">
          <h3>冻结契约</h3>
          <Status tone={!panel.extraction ? 'neutral' : panel.extraction.validation.valid ? 'ok' : 'danger'}>
            {!panel.extraction
              ? 'NOT RUN'
              : panel.extraction.validation.valid
                ? 'OUTPUT VALIDATED'
                : 'OUTPUT INVALID'}
          </Status>
        </div>
        <dl className="detail-list">
          <div><dt>面板版本</dt><dd>v{panel.version}</dd></div>
          <div><dt>模板类型</dt><dd>{panel.template_kind}</dd></div>
          <div><dt>抽取引擎</dt><dd>{panel.extraction ? `${panel.extraction.provider} / ${panel.extraction.model}` : '尚无抽取运行'}</dd></div>
          <div><dt>提示词版本</dt><dd>{panel.extraction_prompt_version}</dd></div>
          <div><dt>输入哈希</dt><dd className="mono break">{panel.extraction?.input_hash ?? '尚无输入哈希'}</dd></div>
        </dl>
      </section>

      <section className="drawer-section">
        <div className="drawer-section-title">
          <h3>本次抽取引用片段</h3>
          <Status tone={panel.evidence.length ? 'info' : 'neutral'}>
            {panel.evidence.length} FRAGMENTS
          </Status>
        </div>
        {panel.evidence.length ? (
          <div className="evidence-stack">
            {panel.evidence.map((evidence, index) => (
              <article className="evidence-item" key={evidence.fragment_id}>
                <header>
                  <strong>定位片段 {index + 1}</strong>
                  <span className="mono">{evidence.locator_type}</span>
                </header>
                <dl className="detail-list compact">
                  <div><dt>定位器</dt><dd className="mono break">{JSON.stringify(evidence.locator)}</dd></div>
                  <div><dt>抓取时间</dt><dd>{formatDate(evidence.retrieved_at)}</dd></div>
                  <div><dt>发布时间</dt><dd>{evidence.published_at ? formatDate(evidence.published_at) : '来源未提供'}</dd></div>
                  <div><dt>媒体类型</dt><dd>{evidence.artifact_media_type}</dd></div>
                  <div><dt>原始字节</dt><dd>{evidence.artifact_byte_size.toLocaleString()} bytes</dd></div>
                  <div><dt>文件 SHA-256</dt><dd className="mono break">{evidence.artifact_sha256}</dd></div>
                  <div><dt>文本 SHA-256</dt><dd className="mono break">{evidence.text_sha256 ?? '片段未提供文本哈希'}</dd></div>
                </dl>
                <div className="drawer-actions">
                  <a className="secondary-button" href={evidence.source_url} target="_blank" rel="noreferrer">
                    <ExternalLink size={15} /> 打开来源
                  </a>
                  <a className="primary-button" href={api.artifactUrl(evidence.artifact_id)}>
                    <Download size={15} /> 下载原始文件
                  </a>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="panel-empty">
            {panel.extraction
              ? '本次抽取没有返回引用片段，因此不能据此标记为可信。'
              : '尚无抽取运行；冻结 Schema 存在，但没有可展示的抽取血缘。'}
          </div>
        )}
      </section>

      <TrustWorkspace panelVersionKey={panel.id} />

      <section className="drawer-section code-section">
        <h3><FileJson2 size={14} /> JSON Schema</h3>
        <pre>{JSON.stringify(panel.data_schema, null, 2)}</pre>
        <h3><FileJson2 size={14} /> UI DSL</h3>
        <pre>{JSON.stringify(panel.ui_dsl, null, 2)}</pre>
      </section>
    </Drawer>
  );
}
