import { ChevronRight, Database, Fingerprint } from 'lucide-react';

import { safeHostname, formatDate, shortHash } from '../../lib/format';
import type { PanelView } from '../../lib/v2-api';
import { Status } from '../ui';

export function DashboardPanel({
  panel,
  onInspect,
}: {
  panel: PanelView;
  onInspect: () => void;
}) {
  const dslNodes = panel.ui_dsl.type === 'stack'
    ? panel.ui_dsl.children ?? []
    : [panel.ui_dsl];
  const metricNode = dslNodes.find((item) => item.type === 'metric');
  const tableNode = dslNodes.find((item) => item.type === 'table');
  const metricField = metricNode?.field;
  const metricValue = metricField ? panel.data?.[metricField] : undefined;
  const tableField = tableNode?.field ?? 'records';
  const rawRows = panel.data?.[tableField];
  const records = Array.isArray(rawRows)
    ? rawRows.filter(
        (row): row is Record<string, unknown> =>
          typeof row === 'object' && row !== null && !Array.isArray(row),
      )
    : [];
  const columns = tableNode?.columns ?? (records[0] ? Object.keys(records[0]) : []);
  const visibleRecords = records.slice(0, tableNode?.page_size ?? 8);
  const evidence = panel.evidence[0];
  const valid = panel.extraction?.validation.valid === true;

  return (
    <article className="panel-card">
      <div className="panel-header">
        <div className="panel-title-group">
          <span className="panel-node"><Database size={15} /></span>
          <div>
            <span className="panel-key">{panel.key}</span>
            <h2>{panel.title}</h2>
            <p>{panel.description}</p>
          </div>
        </div>
        <button className="inspect-button" onClick={onInspect}>
          证据终端 <ChevronRight size={14} />
        </button>
      </div>
      <div className="metric-row">
        <div className="metric-value">
          {metricValue === undefined || metricValue === null
            ? '—'
            : typeof metricValue === 'number'
              ? metricValue.toLocaleString()
              : String(metricValue)}
        </div>
        <div>
          <strong>{metricNode?.label ?? metricField ?? '未配置指标'}</strong>
          <span>LATEST STRUCTURED OUTPUT</span>
        </div>
        <Status tone={valid ? 'warning' : panel.extraction ? 'danger' : 'neutral'}>
          {valid ? 'UNVERIFIED DATA' : panel.extraction ? 'OUTPUT INVALID' : 'NO EXTRACTION'}
        </Status>
      </div>
      {tableNode && visibleRecords.length > 0 ? (
        <div className="table-wrap">
          <table>
            <thead><tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
            <tbody>
              {visibleRecords.map((record, index) => (
                <tr key={index}>
                  {columns.map((column) => (
                    <td key={column}>
                      {record[column] === undefined || record[column] === null
                        ? <span className="missing-value">未提供</span>
                        : String(record[column])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : tableNode ? (
        <div className="panel-empty">
          该冻结面板尚无结构化记录。系统不会补零或生成演示数据。
        </div>
      ) : null}
      <footer className="panel-footer">
        <span><Database size={13} /> {evidence ? safeHostname(evidence.source_url) : '等待可信采集'}</span>
        <span><Fingerprint size={13} /> {evidence ? shortHash(evidence.artifact_sha256) : '无文件哈希'}</span>
        <span>{evidence ? formatDate(evidence.retrieved_at) : '未抓取'}</span>
        <span>{panel.evidence.length} 个定位片段</span>
      </footer>
    </article>
  );
}
