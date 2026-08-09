import type { UiDslNode } from '../../lib/v2-api';

const WIDTH = 600;
const HEIGHT = 180;
const PAD_X = 24;
const PAD_Y = 18;

export function SafeChart({ node, rows }: { node: UiDslNode; rows: Record<string, unknown>[] }) {
  const limit = typeof node.max_points === 'number' ? node.max_points : 80;
  const xField = node.x_field ?? '';
  const yField = node.y_field ?? '';
  const points = rows
    .map((row) => ({ x: row[xField], y: row[yField] }))
    .filter((item): item is { x: string | number; y: number } => (
      (typeof item.x === 'string' || typeof item.x === 'number')
      && typeof item.y === 'number'
      && Number.isFinite(item.y)
    ))
    .slice(0, limit);

  if (!points.length) {
    return (
      <div className="panel-empty">
        图表字段没有可呈现的真实数值，未生成补点或趋势。
      </div>
    );
  }

  const values = points.map((point) => point.y);
  const dataMinimum = Math.min(...values);
  const dataMaximum = Math.max(...values);
  const variant = node.variant ?? 'line';
  const baselineVariant = variant === 'bar' || variant === 'area';
  const minimum = Math.min(dataMinimum, ...(baselineVariant ? [0] : []));
  const maximum = Math.max(dataMaximum, ...(baselineVariant ? [0] : []));
  const span = maximum - minimum;
  const usableWidth = WIDTH - PAD_X * 2;
  const usableHeight = HEIGHT - PAD_Y * 2;
  const yPosition = (value: number) => (
    PAD_Y + (span === 0 ? usableHeight / 2 : (maximum - value) * usableHeight / span)
  );
  const coordinates = points.map((point, index) => ({
    ...point,
    px: PAD_X + (
      points.length === 1
        ? usableWidth / 2
        : index * usableWidth / (points.length - 1)
    ),
    py: yPosition(point.y),
  }));
  const path = coordinates
    .map((point, index) => `${index ? 'L' : 'M'}${point.px},${point.py}`)
    .join(' ');
  const baseline = yPosition(0);
  const lastPoint = coordinates[coordinates.length - 1];

  return (
    <figure className="safe-chart" aria-label={node.label ?? `${yField} 图表`}>
      <figcaption>
        <strong>{node.label ?? yField}</strong>
        <span>{variant.toUpperCase()} · {points.length} REAL POINTS</span>
      </figcaption>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img">
        <title>{node.label ?? `${yField} by ${xField}`}</title>
        <line
          x1={PAD_X}
          y1={baselineVariant ? baseline : HEIGHT - PAD_Y}
          x2={WIDTH - PAD_X}
          y2={baselineVariant ? baseline : HEIGHT - PAD_Y}
          className="chart-axis"
        />
        {variant === 'bar' ? coordinates.map((point, index) => {
          const width = Math.max(4, usableWidth / Math.max(points.length, 1) * 0.62);
          return (
            <rect
              key={`${String(point.x)}-${index}`}
              x={point.px - width / 2}
              y={Math.min(point.py, baseline)}
              width={width}
              height={Math.abs(baseline - point.py)}
              className="chart-bar"
            />
          );
        }) : (
          <>
            {variant === 'area' && (
              <path
                d={`${path} L${lastPoint.px},${baseline} L${coordinates[0].px},${baseline} Z`}
                className="chart-area"
              />
            )}
            <path d={path} className="chart-line" />
            {coordinates.map((point, index) => (
              <circle
                key={`${String(point.x)}-${index}`}
                cx={point.px}
                cy={point.py}
                r="3"
                className="chart-point"
              />
            ))}
          </>
        )}
      </svg>
      <div className="chart-scale">
        <span>X · {xField}</span>
        <span>MIN {dataMinimum.toLocaleString()} · MAX {dataMaximum.toLocaleString()}</span>
        <span>Y · {yField}</span>
      </div>
    </figure>
  );
}
