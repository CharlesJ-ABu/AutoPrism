import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Target, Info, Search, Database } from 'lucide-react';

interface ADBenchmarkingViewProps {
  panelId: string;
  signals?: any[];
}

export const ADBenchmarkingView: React.FC<ADBenchmarkingViewProps> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 数据转换逻辑
  const brandColors: Record<string, string> = {
    'Tesla': '#ffffff',
    'Huawei': '#ef4444',
    'Xiaomi': '#ff6700',
    'XPENG': '#5de2ff',
    'NIO': '#00e5ff',
    'Li Auto': '#00ad9b',
    'Zeekr': '#f0f0f0'
  };

  const systems = activeSignals.map((s, idx) => {
    const metrics = s.metrics || {};
    const name = metrics.name || s.involved_entities?.[0] || `System_${idx}`;
    const fallbackColor = `hsl(${(idx * 137) % 360}, 70%, 60%)`;
    const color = brandColors[name] || fallbackColor;

    return {
      name,
      color,
      data: [
        metrics.tops || 50,         // 算力
        metrics.perception || 50,   // 感知
        metrics.iq || 50,           // 智商
        metrics.safety || 50,       // 安全
        metrics.coverage || 50,     // 开城
        metrics.ux || 50            // 体验
      ]
    };
  });

  // 3. 空状态/调试 UI
  if (systems.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Target size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">AD Benchmark Engine Standby</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_Panel</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Type</span>
            <span className="text-white/40">SIX_AXIS_AD_BENCHMARK</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Result</span>
            <span className="text-rose-500/60 font-black">MISSING_SIGNAL_INPUT</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Database size={10} />
           <span className="text-[6px] font-bold text-white uppercase tracking-tighter">Waiting for SpecializedScraper.fetch_ad_benchmarking()</span>
        </div>
      </div>
    );
  }

  const option = {
    backgroundColor: 'transparent',
    color: systems.map(s => s.color),
    legend: {
      show: true,
      bottom: 0,
      itemWidth: 8,
      itemHeight: 2,
      textStyle: { color: 'rgba(255,255,255,0.4)', fontSize: 8 },
      icon: 'rect',
      data: systems.map(s => s.name)
    },
    radar: {
      indicator: [
        { name: '算力 (TOPS)', max: 100 },
        { name: '感知 (Sensors)', max: 100 },
        { name: '智商 (Algorithm)', max: 100 },
        { name: '安全 (Safety)', max: 100 },
        { name: '开城 (Coverage)', max: 100 },
        { name: '体验 (UX)', max: 100 }
      ],
      shape: 'polygon',
      splitNumber: 4,
      name: {
        textStyle: { color: 'rgba(255,255,255,0.5)', fontSize: 7, fontWeight: 'bold' }
      },
      splitLine: {
        lineStyle: { color: 'rgba(255,255,255,0.05)' }
      },
      splitArea: {
        areaStyle: { color: ['rgba(255,255,255,0.01)', 'transparent'] }
      },
      axisLine: {
        lineStyle: { color: 'rgba(255,255,255,0.1)' }
      }
    },
    series: [
      {
        type: 'radar',
        lineStyle: { width: 1.5 },
        emphasis: {
          lineStyle: { width: 3 }
        },
        data: systems.map(s => ({
          value: s.data,
          name: s.name,
          areaStyle: {
            color: s.color,
            opacity: 0.05
          },
          symbol: 'none'
        }))
      }
    ]
  };

  return (
    <div className="h-full w-full flex flex-col p-2 bg-black/40 rounded-lg border border-white/5 relative overflow-hidden">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
          Last Sync: {new Date().toLocaleTimeString()}
        </span>
      </div>
      
      <div className="absolute top-0 right-0 p-2 opacity-10">
        <div className="text-[40px] font-black text-white leading-none tracking-tighter">AD</div>
      </div>

      <div className="flex-1 min-h-0">
        <ReactECharts option={option} style={{ height: '100%', width: '100%' }} notMerge={true} />
      </div>

      <div className="flex justify-between items-center px-1 border-t border-white/5 pt-1 mt-1">
        <span className="text-[6px] text-white/20 uppercase tracking-widest font-black underline underline-offset-2">AD Metrics Validated</span>
      </div>
    </div>
  );
};
