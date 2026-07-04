import React from 'react';
import { motion } from 'framer-motion';
import { Zap, Layers, ShieldCheck, Database, Search } from 'lucide-react';

interface BatteryData {
  model: string;
  manufacturer: string;
  density: number;
  type: string;
  status: string;
}

export const BatteryDensityView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: BatteryData[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      model: metrics.model || s.title_brief || 'Unknown Cell',
      manufacturer: metrics.brand || s.involved_entities?.[0] || 'Unknown',
      density: parseFloat(metrics.density) || 0,
      type: metrics.type || 'NCM',
      status: metrics.status || (s.impact_score > 80 ? '量产中' : '研发中')
    };
  }).sort((a, b) => b.density - a.density);

  const getTypeColor = (type: string) => {
    const t = type.toUpperCase();
    if (t.includes('SOLID')) return '#8b5cf6'; // 紫色
    if (t.includes('NCM')) return '#3b82f6';   // 蓝色
    if (t.includes('LFP')) return '#10b981';   // 绿色
    return '#f43f5e'; // 默认红色
  };

  const MAX_DENSITY = Math.max(...displayData.map(d => d.density), 500);

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Zap size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Battery Tech Intel Empty</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Domain</span>
            <span className="text-white/40">ENERGY_STORAGE_GENOMICS</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Signals</span>
            <span className="text-rose-500/60 font-black">NULL_CELL_DATA</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Search size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_battery_tech() <br/> 捕获宁德时代、比亚迪或卫蓝的最新电芯规格。
           </span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col p-2 space-y-2 overflow-y-auto no-scrollbar bg-black/40 rounded-lg border border-white/5">
      <div className="flex justify-between items-center mb-1">
        <div className="flex flex-col">
          <span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
            Last Sync: {new Date().toLocaleTimeString()}
          </span>
          <span className="text-[10px] font-bold text-white/40 uppercase tracking-widest">动力电池技术天梯 (Wh/kg)</span>
        </div>
        <div className="flex gap-2 text-[7px] text-white/30 font-black">
           <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> LFP</div>
           <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> NCM</div>
           <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-purple-500" /> SOLID</div>
        </div>
      </div>

      <div className="flex-1 space-y-2.5">
        {displayData.map((item, idx) => (
          <div key={`${item.model}-${idx}`} className="group relative">
            <div className="flex justify-between items-end mb-1 px-1">
              <div className="flex flex-col">
                <span className="text-[10px] font-black text-white group-hover:text-blue-400 transition-colors">{item.model}</span>
                <span className="text-[7px] text-white/30 font-bold uppercase">{item.manufacturer}</span>
              </div>
              <div className="flex items-baseline gap-0.5">
                <span className="text-[12px] font-mono font-bold text-white">{item.density}</span>
                <span className="text-[6px] text-white/20 font-bold uppercase">Wh/kg</span>
              </div>
            </div>
            
            <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden border border-white/5 relative">
              <motion.div 
                initial={{ width: 0 }}
                animate={{ width: `${(item.density / MAX_DENSITY) * 100}%` }}
                transition={{ duration: 1, delay: idx * 0.1 }}
                className="h-full rounded-full relative shadow-[0_0_8px_rgba(255,255,255,0.1)]"
                style={{ backgroundColor: getTypeColor(item.type) }}
              />
            </div>

            <div className="absolute -top-1 -right-1">
               <span className="text-[6px] px-1 rounded-sm font-black border border-white/5 bg-white/5 text-white/40 uppercase tracking-tighter">
                 {item.status}
               </span>
            </div>
          </div>
        ))}
      </div>

      <div className="pt-2 border-t border-white/5 flex justify-between items-center opacity-30">
        <span className="text-[6px] uppercase font-black text-emerald-500 italic underline">Energy Density Sync Active</span>
        <Database size={8} />
      </div>
    </div>
  );
};
