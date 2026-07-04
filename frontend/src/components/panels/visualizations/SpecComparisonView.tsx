import React from 'react';
import { motion } from 'framer-motion';
import { Zap, Battery, Cpu, Box, Trophy, ArrowRight, Database, Search } from 'lucide-react';

interface ModelSpec {
  name: string;
  brand: string;
  acceleration: string;
  range: string;
  power: string;
  tech: string;
}

export const SpecComparisonView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayModels: ModelSpec[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      name: metrics.model || s.title_brief || 'Unknown',
      brand: metrics.brand || s.involved_entities?.[0] || 'Unknown',
      acceleration: metrics.acceleration || 'N/A',
      range: metrics.range || 'N/A',
      power: metrics.power || 'N/A',
      tech: metrics.tech || 'Standard'
    };
  });

  const specs = [
    { label: '0-100 km/h', key: 'acceleration', unit: 's', icon: <Zap size={10} /> },
    { label: 'CLTC 续航', key: 'range', unit: 'km', icon: <Battery size={10} /> },
    { label: '峰值功率', key: 'power', unit: '', icon: <Cpu size={10} /> },
    { label: '核心智驾', key: 'tech', unit: '', icon: <Box size={10} /> }
  ];

  // 3. 空状态/调试 UI
  if (displayModels.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10 overflow-hidden">
        <Cpu size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Spec Benchmark Pending</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Target</span>
            <span className="text-white/40">COMPETITIVE_SPEC_MATRIX</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Cache</span>
            <span className="text-rose-500/60 font-black">MISSING_METRICS</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Database size={10} />
           <span className="text-[6px] font-bold text-white uppercase text-center leading-tight">
             等待点火 Crawler 深度爬取小米 SU7、<br/>Model 3 或 001 等重点车型的技术参数。
           </span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col p-2 bg-black/40 rounded-lg border border-white/5 space-y-2 overflow-x-auto no-scrollbar">
      <div className="flex justify-between items-center mb-1 sticky left-0">
        <span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
          Last Sync: {new Date().toLocaleTimeString()}
        </span>
        <span className="text-[7px] text-white/20 uppercase font-black">Live Market Benchmark</span>
      </div>

      <table className="w-full text-left border-collapse min-w-[300px]">
        <thead>
          <tr>
            <th className="p-1.5 text-[8px] font-black text-white/20 uppercase border-b border-white/5 sticky left-0 bg-neutral-950 z-10">Spec Category</th>
            {displayModels.map((model, idx) => (
              <th key={`${model.name}-${idx}`} className="p-1.5 border-b border-white/5 text-center">
                <div className="flex flex-col items-center">
                  <span className="text-[6px] text-white/40 uppercase font-bold tracking-tighter">{model.brand}</span>
                  <span className="text-[9px] font-black text-white whitespace-nowrap">{model.name}</span>
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {specs.map((spec) => (
            <tr key={spec.label} className="group hover:bg-white/5 transition-colors">
              <td className="p-2 border-b border-white/5 sticky left-0 bg-neutral-950 z-10 group-hover:bg-neutral-900 transition-colors">
                <div className="flex items-center gap-1.5">
                  <div className="text-white/20">{spec.icon}</div>
                  <span className="text-[8px] font-bold text-white/40 uppercase whitespace-nowrap">{spec.label}</span>
                </div>
              </td>
              {displayModels.map((model, mIdx) => {
                const val = (model as any)[spec.key];
                return (
                  <td key={`${model.name}-${spec.key}-${mIdx}`} className="p-2 border-b border-white/5 text-center">
                    <span className="text-[10px] font-mono font-black text-white/80">
                      {val}{spec.unit}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pt-2 flex justify-between items-center opacity-30 sticky left-0">
        <div className="flex items-center gap-1">
          <ArrowRight size={8} />
          <span className="text-[6px] uppercase font-bold tracking-tighter">Swipe to view more comparisons</span>
        </div>
        <span className="text-[6px] uppercase font-bold tracking-tighter text-blue-500 font-black italic underline">Spec Intel v4.5</span>
      </div>
    </div>
  );
};
