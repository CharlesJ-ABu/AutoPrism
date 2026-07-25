import React from 'react';
import ReactECharts from 'echarts-for-react';
import { useSignalStore } from '@/stores';

interface TelemetryGaugeProps {
  panelId: string;
}

export const TelemetryGauge: React.FC<TelemetryGaugeProps> = ({ panelId }) => {
  const signal = useSignalStore((state) =>
    [...state.signals].reverse().find((item) => item.target_panel_ids?.includes(panelId))
  );
  const rawValue = signal?.metrics?.health ?? signal?.metrics?.value ?? signal?.impact_score;
  const value = Number(rawValue);

  if (!signal || !Number.isFinite(value)) {
    return (
      <div className="h-full min-h-[120px] flex items-center justify-center px-4 text-center text-white/20 text-[10px] tracking-widest uppercase">
        暂无可验证的仪表指标
      </div>
    );
  }
  
  const isError = value < 75;

  const option = {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        center: ['50%', '75%'],
        radius: '90%',
        min: 0,
        max: 100,
        splitNumber: 10,
        axisLine: {
          lineStyle: {
            width: 6,
            color: [
              [0.3, '#ef4444'],
              [0.7, '#f59e0b'],
              [1, '#10b981']
            ]
          }
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '12%',
          width: 10,
          offsetCenter: [0, '-60%'],
          itemStyle: { color: 'auto' }
        },
        axisTick: { length: 8, lineStyle: { color: 'auto', width: 1 } },
        splitLine: { length: 12, lineStyle: { color: 'auto', width: 2 } },
        axisLabel: { color: 'rgba(255,255,255,0.4)', fontSize: 8, distance: -30 },
        title: { offsetCenter: [0, '-20%'], fontSize: 10, color: 'rgba(255,255,255,0.4)' },
        detail: {
          fontSize: 24,
          offsetCenter: [0, '0%'],
          valueAnimation: true,
          formatter: '{value}%',
          color: 'auto'
        },
        data: [{ value: value, name: 'Health' }]
      }
    ]
  };

  return (
    <div className={`w-full h-full relative flex flex-col p-1 ${isError ? 'animate-[pulse_4s_infinite]' : ''}`}>
      <div className="flex justify-between items-center mb-1 px-1">
        <span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
          Snapshot: {new Date(signal.created_at).toLocaleString()}
        </span>
      </div>
      <div className="flex-1 min-h-0">
      {isError && (
        <div className="absolute inset-0 pointer-events-none z-10 opacity-30 mix-blend-overlay bg-[url('https://www.transparenttextures.com/patterns/cracked-glass.png')]" />
      )}
      <ReactECharts option={option} style={{ height: '100%', width: '100%' }} />
      </div>
    </div>
  );
};
