import React from 'react';
import { motion } from 'framer-motion';
import { Layers, Weight, Zap, Database, Target, Search } from 'lucide-react';

interface MaterialStat {
  model: string;
  brand: string;
  composition: {
    aluminum: number;
    steel: number;
    carbon: number;
    magnesium: number;
    others: number;
  };
  weightReduction: string;
  tech: string;
}

export const LightweightView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: MaterialStat[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    const comp = metrics.composition || {};
    return {
      model: metrics.model || s.title_brief || 'Unknown Model',
      brand: metrics.brand || s.involved_entities?.[0] || 'Unknown',
      composition: {
        aluminum: comp.aluminum || 0,
        steel: comp.steel || 0,
        carbon: comp.carbon || 0,
        magnesium: comp.magnesium || 0,
        others: comp.others || 0
      },
      weightReduction: metrics.reduction || 'N/A',
      tech: metrics.tech || 'Integrated Casting'
    };
  });

  const colors = {
    aluminum: 'bg-blue-400',
    steel: 'bg-neutral-500',
    carbon: 'bg-amber-500',
    magnesium: 'bg-purple-400',
    others: 'bg-neutral-700'
  };

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Layers size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Material Genomic Standby</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Target</span>
            <span className="text-white/40">WEIGHT_REDUCTION_INTEL</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Payload</span>
            <span className="text-rose-500/60 font-black">ZERO_MATERIAL_DATA</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Search size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_lightweight_data() <br/> 捕获一体压铸或碳纤维应用的最新比例。
           </span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col p-2 bg-black/40 rounded-lg border border-white/5 space-y-2 overflow-y-auto no-scrollbar">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
          Last Sync: {new Date().toLocaleTimeString()}
        </span>
        <div className="flex items-center gap-1">
           <Weight size={10} className="text-white/20" />
           <span className="text-[7px] text-white/20 uppercase font-black">Material Loop</span>
        </div>
      </div>

      <div className="flex-1 space-y-4 py-1">
        {displayData.map((item, idx) => (
          <motion.div 
            key={`${item.model}-${idx}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="space-y-1.5"
          >
            <div className="flex justify-between items-end px-0.5">
               <div className="flex flex-col">
                  <span className="text-[6px] text-white/40 uppercase font-bold tracking-tighter">{item.brand}</span>
                  <span className="text-[10px] font-black text-white">{item.model}</span>
               </div>
               <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1">
                     <Target size={8} className="text-emerald-400" />
                     <span className="text-[9px] font-mono font-black text-emerald-400">{item.weightReduction}</span>
                  </div>
                  <span className="text-[7px] px-1 rounded bg-white/5 border border-white/10 text-white/40 font-black uppercase whitespace-nowrap">
                    {item.tech}
                  </span>
               </div>
            </div>

            <div className="h-2.5 w-full flex rounded-sm overflow-hidden bg-white/5 border border-white/5 shadow-inner">
               {Object.entries(item.composition).map(([key, val]) => (
                 <motion.div 
                   key={key}
                   initial={{ width: 0 }}
                   animate={{ width: `${val}%` }}
                   className={`${(colors as any)[key]} h-full relative group`}
                 />
               ))}
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-2 border-t border-white/5 flex flex-wrap gap-x-3 gap-y-1">
         {Object.entries(colors).map(([label, color]) => (
           <div key={label} className="flex items-center gap-1">
              <div className={`w-1.5 h-1.5 rounded-full ${color}`} />
              <span className="text-[7px] text-white/30 uppercase font-black">{label}</span>
           </div>
         ))}
      </div>
    </div>
  );
};
