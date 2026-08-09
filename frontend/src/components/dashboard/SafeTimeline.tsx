import { formatDate } from '../../lib/format';
import type { UiDslNode } from '../../lib/v2-api';

export function SafeTimeline({
  node,
  rows,
}: {
  node: UiDslNode;
  rows: Record<string, unknown>[];
}) {
  const timeField = node.time_field ?? '';
  const titleField = node.title_field ?? '';
  const valueField = node.value_field;
  const limit = typeof node.max_items === 'number' ? node.max_items : 20;
  const items = rows
    .map((row, index) => ({
      index,
      time: row[timeField],
      title: row[titleField],
      value: valueField ? row[valueField] : undefined,
    }))
    .filter((item): item is typeof item & { time: string; title: string } => (
      typeof item.time === 'string'
      && Number.isFinite(Date.parse(item.time))
      && typeof item.title === 'string'
      && item.title.trim().length > 0
    ))
    .sort(
      (left, right) => (
        Date.parse(left.time) - Date.parse(right.time) || left.index - right.index
      ),
    )
    .slice(-limit);

  if (!items.length) {
    return (
      <div className="panel-empty">
        时间线字段没有可验证的日期记录，未生成占位事件。
      </div>
    );
  }

  return (
    <section className="safe-timeline" aria-label={node.label ?? '证据时间线'}>
      <header>
        <strong>{node.label ?? '证据时间线'}</strong>
        <span>{items.length} STORED EVENTS</span>
      </header>
      <ol>
        {items.map((item) => (
          <li key={`${item.time}-${item.index}`}>
            <time dateTime={item.time}>{formatDate(item.time)}</time>
            <strong>{item.title}</strong>
            {item.value !== undefined && item.value !== null && <span>{String(item.value)}</span>}
          </li>
        ))}
      </ol>
    </section>
  );
}
