import { ChevronRight, Database, Fingerprint } from 'lucide-react';

import { safeHostname, formatDate, shortHash } from '../../lib/format';
import type { PanelView } from '../../lib/v2-api';
import { Status } from '../ui';
import { SafeChart } from './SafeChart';
import { SafeTimeline } from './SafeTimeline';
import { CustomReactRuntime } from './CustomReactRuntime';

const flattenDsl = (node: PanelView['ui_dsl']): PanelView['ui_dsl'][] => (
  node.type === 'stack'
    ? (node.children ?? []).flatMap(flattenDsl)
    : [node]
);

const objectRows = (value: unknown) => (
  Array.isArray(value)
    ? value.filter(
        (row): row is Record<string, unknown> => (
          typeof row === 'object' && row !== null && !Array.isArray(row)
        ),
      )
    : []
);

export function DashboardPanel({
  panel,
  onInspect,
}: {
  panel: PanelView;
  onInspect: () => void;
}) {
  const dslNodes = flattenDsl(panel.ui_dsl);
  const metricNode = dslNodes.find((item) => item.type === 'metric');
  const tableNode = dslNodes.find((item) => item.type === 'table');
  const chartNodes = dslNodes.filter((item) => item.type === 'chart');
  const timelineNodes = dslNodes.filter((item) => item.type === 'timeline');
  const metricField = metricNode?.field;
  const metricValue = metricField ? panel.data?.[metricField] : undefined;
  const tableField = tableNode?.field;
  const records = tableField ? objectRows(panel.data?.[tableField]) : [];
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
      {panel.template_kind === 'custom_react' ? (
        <CustomReactRuntime panel={panel} />
      ) : metricNode && <div className="metric-row">
        <div className="metric-value">
          {metricValue === undefined || metricValue === null
            ? '—'
            : typeof metricValue === 'number'
              ? metricValue.toLocaleString()
              : String(metricValue)}
        </div>
        <div>
          <strong>
            {metricNode?.label ?? metricField ?? '未配置指标'}
            {metricNode.unit ? ` · ${metricNode.unit}` : ''}
          </strong>
          <span>LATEST STRUCTURED OUTPUT</span>
        </div>
        <Status tone={valid ? 'warning' : panel.extraction ? 'danger' : 'neutral'}>
          {valid ? 'UNVERIFIED DATA' : panel.extraction ? 'OUTPUT INVALID' : 'NO EXTRACTION'}
        </Status>
      </div>}
      {panel.template_kind === 'ui_dsl' && chartNodes.map((node, index) => (
        <SafeChart
          key={`chart-${node.field}-${index}`}
          node={node}
          rows={objectRows(node.field ? panel.data?.[node.field] : undefined)}
        />
      ))}
      {panel.template_kind === 'ui_dsl' && timelineNodes.map((node, index) => (
        <SafeTimeline
          key={`timeline-${node.field}-${index}`}
          node={node}
          rows={objectRows(node.field ? panel.data?.[node.field] : undefined)}
        />
      ))}
      {panel.template_kind === 'ui_dsl' && tableNode && visibleRecords.length > 0 ? (
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
      ) : panel.template_kind === 'ui_dsl' && tableNode ? (
        <div className="panel-empty">
          该冻结面板尚无结构化记录。系统不会补零或生成演示数据。
        </div>
      ) : null}
      <footer className="panel-footer">
        <span>
          <Database size={13} />
          {evidence ? safeHostname(evidence.source_url) : '等待可信采集'}
        </span>
        <span>
          <Fingerprint size={13} />
          {evidence ? shortHash(evidence.artifact_sha256) : '无文件哈希'}
        </span>
        <span>{evidence ? formatDate(evidence.retrieved_at) : '未抓取'}</span>
        <span>{panel.evidence.length} 个定位片段</span>
      </footer>
    </article>
  );
}
