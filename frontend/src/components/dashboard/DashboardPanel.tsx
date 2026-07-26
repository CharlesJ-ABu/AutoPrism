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
  const records = Array.isArray(panel.data?.records) ? panel.data.records : [];
  const columns = panel.ui_dsl.children?.find((item) => item.type === 'table')?.columns
    ?? (records[0] ? Object.keys(records[0]) : []);
  const visibleRecords = records.slice(0, 8);
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
          {panel.data?.record_count === undefined
            ? '—'
            : Number(panel.data.record_count).toLocaleString()}
        </div>
        <div>
          <strong>数据库记录</strong>
          <span>LATEST IMMUTABLE SNAPSHOT</span>
        </div>
        <Status tone={valid ? 'ok' : panel.extraction ? 'warning' : 'neutral'}>
          {valid ? 'SCHEMA VALID' : panel.extraction ? 'VALIDATION ISSUE' : 'NO EXTRACTION'}
        </Status>
      </div>
      {visibleRecords.length > 0 ? (
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
      ) : (
        <div className="panel-empty">
          该冻结面板尚无结构化记录。系统不会补零或生成演示数据。
        </div>
      )}
      <footer className="panel-footer">
        <span><Database size={13} /> {evidence ? safeHostname(evidence.source_url) : '等待可信采集'}</span>
        <span><Fingerprint size={13} /> {evidence ? shortHash(evidence.artifact_sha256) : '无文件哈希'}</span>
        <span>{evidence ? formatDate(evidence.retrieved_at) : '未抓取'}</span>
        <span>{panel.evidence.length} 个定位片段</span>
      </footer>
    </article>
  );
}
