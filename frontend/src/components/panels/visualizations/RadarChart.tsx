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
    return null;
  };

  const chartData = generateData();
  if (!chartData) {
    return (
      <div className="h-full min-h-[120px] flex items-center justify-center px-4 text-center text-white/20 text-[10px] tracking-widest uppercase">
        暂无可验证的雷达指标
      </div>
    );
  }

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
          Snapshot: {new Date(relevantSignal.created_at).toLocaleString()}
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
      </div>
    </div>
  );
};
