import React from 'react';
import ReactECharts from 'echarts-for-react';
import { useSignalStore } from '@/stores';

interface RadarChartProps {
  panelId: string;
}

export const RadarChart: React.FC<RadarChartProps> = ({ panelId }) => {
  const { signals } = useSignalStore();
  
  // Find the latest signal targeting this panel
  const relevantSignal = [...signals]
    .reverse()
    .find(s => s.target_panel_ids?.includes(panelId));

  const generateData = () => {
    if (relevantSignal && relevantSignal.metrics) {
      const m = relevantSignal.metrics;
      // Map extracted metrics to radar dimensions
      return [
        m.compute || 50,
        m.intelligence || m.sensors || 50,
        m.energy || m.range || 50,
        m.safety || 50,
        m.cost || 50,
        m.ux || 50
      ];
    }
    // Fallback to pseudo-random if no signal found
    const seed = parseInt(panelId.replace('p', ''), 10) || 1;
    return [
      80 + Math.sin(seed) * 10,
      60 + Math.cos(seed) * 10,
      70 + Math.sin(seed * 2) * 10,
      85 + Math.cos(seed * 0.5) * 10,
      75 + Math.sin(seed * 1.5) * 10,
      90 + Math.cos(seed * 3) * 10,
    ];
  };

  const chartData = generateData();

  const option = {
    tooltip: {
      backgroundColor: 'rgba(15, 15, 35, 0.9)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff', fontSize: 10 },
    },
    radar: {
      indicator: [
        { name: 'Compute', max: 100 },
        { name: 'Sensors', max: 100 },
        { name: 'Range', max: 100 },
        { name: 'Efficiency', max: 100 },
        { name: 'Comfort', max: 100 },
        { name: 'Price', max: 100 }
      ],
      splitNumber: 4,
      axisName: { color: 'rgba(255,255,255,0.4)', fontSize: 9 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
    },
    series: [
      {
        name: 'Competitor Matrix',
        type: 'radar',
        data: [
          {
            value: chartData,
            name: 'Intelligence Signal (Latest)',
            itemStyle: { color: '#8b5cf6' },
            areaStyle: { color: 'rgba(139, 92, 246, 0.3)' },
            lineStyle: { type: 'solid', width: 2 }
          }
        ]
      }
    ]
  };

  return (
    <div className="w-full h-full relative flex flex-col p-1">
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
