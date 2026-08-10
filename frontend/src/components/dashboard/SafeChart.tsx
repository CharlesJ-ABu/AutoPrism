import type { UiDslNode } from '../../lib/v2-api';

const WIDTH = 600;
const HEIGHT = 180;
const PAD_X = 24;
const PAD_Y = 18;

const SERIES_COLORS = [
  '#22d3ee',
  '#c084fc',
  '#2dd4bf',
  '#fb7185',
  '#f59e0b',
  '#60a5fa',
  '#a3e635',
  '#f472b6',
  '#818cf8',
  '#34d399',
  '#f97316',
  '#e879f9',
];

const xKey = (value: string | number) => `${typeof value}:${String(value)}`;

export function SafeChart({ node, rows }: { node: UiDslNode; rows: Record<string, unknown>[] }) {
  const limit = typeof node.max_points === 'number' ? node.max_points : 80;
  const seriesLimit = typeof node.max_series === 'number' ? node.max_series : 6;
  const xField = node.x_field ?? '';
  const yField = node.y_field ?? '';
  const seriesField = node.series_field;
  const validPoints = rows
    .map((row, rowIndex) => ({
      x: row[xField],
      y: row[yField],
      series: seriesField ? row[seriesField] : yField,
      rowIndex,
    }))
    .filter((item): item is {
      x: string | number;
      y: number;
      series: string | number;
      rowIndex: number;
    } => (
      (typeof item.x === 'string' || typeof item.x === 'number')
      && typeof item.y === 'number'
      && Number.isFinite(item.y)
      && (typeof item.series === 'string' || typeof item.series === 'number')
    ))
    .map((item) => ({ ...item, series: String(item.series) }));

  const boundedPoints = validPoints.slice(0, limit);
  const allSeries = [...new Set(boundedPoints.map((point) => point.series))];
  const visibleSeries = allSeries.slice(0, seriesLimit);
  const visibleSeriesSet = new Set(visibleSeries);
  const points = boundedPoints.filter((point) => visibleSeriesSet.has(point.series));

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
  const xValues = [...new Map(points.map((point) => [xKey(point.x), point.x])).values()];
  const xIndexes = new Map(xValues.map((value, index) => [xKey(value), index]));
  const xPosition = (value: string | number) => (
    PAD_X + (
      xValues.length === 1
        ? usableWidth / 2
        : (xIndexes.get(xKey(value)) ?? 0) * usableWidth / (xValues.length - 1)
    )
  );
  const seriesCoordinates = visibleSeries.map((series) => ({
    series,
    color: SERIES_COLORS[visibleSeries.indexOf(series) % SERIES_COLORS.length],
    points: points
      .filter((point) => point.series === series)
      .map((point) => ({
        ...point,
        px: xPosition(point.x),
        py: yPosition(point.y),
      })),
  }));
  const baseline = yPosition(0);
  const clipped = validPoints.length > boundedPoints.length;
  const hiddenSeriesCount = allSeries.length - visibleSeries.length;

  return (
    <figure className="safe-chart" aria-label={node.label ?? `${yField} 图表`}>
      <figcaption>
        <strong>{node.label ?? yField}</strong>
        <span>
          {variant.toUpperCase()} · {points.length} REAL POINTS
          {seriesField ? ` · ${visibleSeries.length} SERIES` : ''}
        </span>
      </figcaption>
      {seriesField && (
        <div className="chart-legend" aria-label={`按 ${seriesField} 分组`}>
          {seriesCoordinates.map((group) => (
            <span key={group.series}>
              <i style={{ backgroundColor: group.color }} />{group.series}
            </span>
          ))}
          {hiddenSeriesCount > 0 && <em>另有 {hiddenSeriesCount} 个序列未显示（契约上限）</em>}
        </div>
      )}
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img">
        <title>{node.label ?? `${yField} by ${xField}`}</title>
        <line
          x1={PAD_X}
          y1={baselineVariant ? baseline : HEIGHT - PAD_Y}
          x2={WIDTH - PAD_X}
          y2={baselineVariant ? baseline : HEIGHT - PAD_Y}
          className="chart-axis"
        />
        {variant === 'bar' ? seriesCoordinates.flatMap((group, seriesIndex) => {
          const slotWidth = usableWidth / Math.max(xValues.length, 1);
          const width = Math.max(2, Math.min(22, slotWidth * 0.68 / visibleSeries.length));
          return group.points.map((point) => {
            const offset = (seriesIndex - (visibleSeries.length - 1) / 2) * width;
            return (
              <rect
                key={`${group.series}-${point.rowIndex}`}
                x={point.px + offset - width / 2}
                y={Math.min(point.py, baseline)}
                width={width}
                height={Math.abs(baseline - point.py)}
                className="chart-bar"
                style={{ fill: group.color, fillOpacity: 0.55 }}
              >
                <title>{group.series} · {String(point.x)} · {point.y}</title>
              </rect>
            );
          });
        }) : seriesCoordinates.map((group) => {
          const path = group.points
            .map((point, index) => `${index ? 'L' : 'M'}${point.px},${point.py}`)
            .join(' ');
          const firstPoint = group.points[0];
          const lastPoint = group.points[group.points.length - 1];
          return (
            <g key={group.series}>
              {variant === 'area' && firstPoint && lastPoint && (
                <path
                  d={`${path} L${lastPoint.px},${baseline} L${firstPoint.px},${baseline} Z`}
                  className="chart-area"
                  style={{ fill: group.color, fillOpacity: 0.14 }}
                />
              )}
              <path d={path} className="chart-line" style={{ stroke: group.color }} />
              {group.points.map((point) => (
                <circle
                  key={`${group.series}-${point.rowIndex}`}
                  cx={point.px}
                  cy={point.py}
                  r="3"
                  className="chart-point"
                  style={{ fill: group.color }}
                >
                  <title>{group.series} · {String(point.x)} · {point.y}</title>
                </circle>
              ))}
            </g>
          );
        })}
      </svg>
      <div className="chart-scale">
        <span>X · {xField}</span>
        <span>MIN {dataMinimum.toLocaleString()} · MAX {dataMaximum.toLocaleString()}</span>
        <span>Y · {yField}</span>
      </div>
      {(clipped || hiddenSeriesCount > 0) && (
        <p className="chart-limit-note">
          已按冻结 DSL 上限显示；未聚合、未插值、未生成缺失点。
          {clipped ? ` ${validPoints.length - boundedPoints.length} 个超出点数上限。` : ''}
        </p>
      )}
    </figure>
  );
}
