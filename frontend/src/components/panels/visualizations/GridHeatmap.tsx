import React from 'react';
import ReactECharts from 'echarts-for-react';

interface GridHeatmapProps {
  panelId: string;
}

export const GridHeatmap: React.FC<GridHeatmapProps> = ({ panelId }) => {
  const seed = parseInt(panelId.replace('p', ''), 10) || 1;
  const hours = ['12a', '2a', '4a', '6a', '8a', '10a', '12p', '2p', '4p', '6p', '8p', '10p'];
  const days = ['Sat', 'Fri', 'Thu', 'Wed', 'Tue', 'Mon', 'Sun'];

  const data = [];
  for (let i = 0; i < 7; i++) {
    for (let j = 0; j < 12; j++) {
      // Deterministic pseudo-random based on indices and seed
      const val = Math.floor(Math.abs(Math.sin(i * j * seed)) * 10);
      data.push([j, i, val]);
    }
  }

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
          Last Sync: 14:10:22
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
      </div>
    </div>
  );
};
