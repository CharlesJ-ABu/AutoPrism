import React from 'react';
import ReactECharts from 'echarts-for-react';
import { useSignalStore } from '@/stores';

interface GridHeatmapProps {
  panelId: string;
}

export const GridHeatmap: React.FC<GridHeatmapProps> = ({ panelId }) => {
  const signal = useSignalStore((state) =>
    [...state.signals].reverse().find((item) => item.target_panel_ids?.includes(panelId))
  );
  const heatmap = signal?.metrics?.heatmap;
  if (!signal || !Array.isArray(heatmap)) {
    return (
      <div className="h-full min-h-[120px] flex items-center justify-center px-4 text-center text-white/20 text-[10px] tracking-widest uppercase">
        暂无可验证的热力图数据
      </div>
    );
  }
  const hours = ['12a', '2a', '4a', '6a', '8a', '10a', '12p', '2p', '4p', '6p', '8p', '10p'];
  const days = ['Sat', 'Fri', 'Thu', 'Wed', 'Tue', 'Mon', 'Sun'];

  const data = heatmap
    .filter((item: unknown) => Array.isArray(item) && item.length === 3)
    .map((item: [number, number, number]) => item);

  const option = {
    tooltip: {
      position: 'top',
      backgroundColor: 'rgba(15, 15, 35, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff', fontSize: 10 },
    },
    grid: {
      top: 10,
      bottom: 20,
      left: 30,
      right: 10
    },
    xAxis: {
      type: 'category',
      data: hours,
      splitArea: { show: true },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: 'rgba(255,255,255,0.3)', fontSize: 8 }
    },
    yAxis: {
      type: 'category',
      data: days,
      splitArea: { show: true },
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: 'rgba(255,255,255,0.3)', fontSize: 8 }
    },
    visualMap: {
      min: 0,
      max: 10,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: -10,
      show: false,
      inRange: {
        color: ['#1e1b4b', '#4c1d95', '#7c3aed', '#c026d3', '#e11d48']
      }
    },
    series: [
      {
        name: 'Density',
        type: 'heatmap',
        data: data,
        label: { show: false },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        itemStyle: {
          borderColor: '#0f0f23',
          borderWidth: 1
        }
      }
    ]
  };

  return (
    <div className="w-full h-full relative p-2 flex flex-col">
      <div className="flex justify-between items-center mb-1 px-1">
        <span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
          Snapshot: {new Date(signal.created_at).toLocaleString()}
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
      </div>
    </div>
  );
};
