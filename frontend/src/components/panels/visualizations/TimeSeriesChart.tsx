import React from 'react';
import ReactECharts from 'echarts-for-react';

interface TimeSeriesChartProps {
  panelId: string;
  signals?: any[];
}

export const TimeSeriesChart: React.FC<TimeSeriesChartProps> = ({ panelId, signals = [] }) => {
  // 1. 数据分组逻辑：按地区（Region）对信号进行归类
  const filteredSignals = signals.filter(s => s.target_panel_ids?.includes(panelId));
  
  const regions = ['USA', 'China', 'EU', 'Global'];
  const colors: Record<string, string> = {
    'USA': '#3b82f6',    // 蓝色
    'China': '#10b981',  // 绿色
    'EU': '#f59e0b',     // 橙色
    'Global': '#8b5cf6'  // 紫色
  };

  const hasRealData = filteredSignals.length >= 2;
  let series: any[] = [];
  let xAxisData: string[] = [];

  if (hasRealData) {
    const grouped = filteredSignals.reduce((acc: any, s) => {
      const reg = s.metrics?.region || 'Global';
      if (!acc[reg]) acc[reg] = [];
      acc[reg].push(s);
      return acc;
    }, {});

    series = Object.keys(grouped).map(reg => ({
      name: reg,
      type: 'line',
      smooth: true,
      data: grouped[reg].map((s: any) => s.metrics?.confidence_index || s.impact_score),
      itemStyle: { color: colors[reg] || '#fff' },
      symbolSize: 4,
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: `${colors[reg] || '#fff'}22` },
            { offset: 1, color: 'transparent' }
          ]
        }
      }
    }));
    xAxisData = Array.from(new Set(filteredSignals.map(s => new Date(s.created_at).toLocaleDateString()))).sort();
  } else {
    return (
      <div className="h-full min-h-[120px] flex items-center justify-center px-4 text-center text-white/20 text-[10px] tracking-widest uppercase">
        暂无可验证的时序数据
      </div>
    );
  }

  const option = {
    grid: { top: 35, right: 10, bottom: 20, left: 30 },
    legend: {
      show: true,
      top: 0,
      left: 'center',
      itemWidth: 10,
      itemHeight: 2,
      textStyle: { color: 'rgba(255,255,255,0.5)', fontSize: 8 },
      icon: 'rect'
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(0, 0, 0, 0.9)',
      textStyle: { color: '#fff', fontSize: 10 },
      borderWidth: 0
    },
    xAxis: {
      type: 'category',
      data: xAxisData,
      axisLabel: { color: 'rgba(255,255,255,0.3)', fontSize: 8 },
      axisLine: { show: false },
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: 'rgba(255,255,255,0.3)', fontSize: 8 },
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } }
    },
    series: series
  };

  return (
    <div className="w-full h-full p-1 flex flex-col">
      <div className="flex justify-between items-center mb-1 px-1">
        <span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
          Snapshot: {new Date(filteredSignals[0]?.created_at).toLocaleString()}
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <ReactECharts option={option} style={{ height: '100%', width: '100%' }} notMerge={true} />
      </div>
    </div>
  );
};
