import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, Zap, Activity, Clock, Server, AlertCircle, Database, Search } from 'lucide-react';

interface ChipCategory {
  type: string;
  leadTime: string;
  stressLevel: number;
  keyParts: string;
}

export const SemiconductorShortageView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: ChipCategory[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      type: metrics.type || s.title_brief || 'Unknown Chip',
      leadTime: metrics.lead_time || 'N/A',
      stressLevel: metrics.stress || s.impact_score || 50,
      keyParts: metrics.parts || 'Critical Component'
    };
  });

  const overallScore = displayData.length > 0 
    ? (displayData.reduce((acc, curr) => acc + curr.stressLevel, 0) / displayData.length).toFixed(1)
    : '0.0';

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Cpu size={24} className="text-emerald-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-emerald-400/60 uppercase tracking-widest text-center">Chip Supply Monitor Waiting</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Foundry</span>
            <span className="text-white/40">TSMC / SAMSUNG / SMIC</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Signals</span>
            <span className="text-rose-500/60 font-black">NO_INTEL_FLOW</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Search size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_semiconductor_intel() <br/> 捕获 SiC、MCU 或 AI SoC 的交期异常。
           </span>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col p-2 bg-black/40 rounded-lg border border-white/5 space-y-2 overflow-hidden">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
          Last Sync: {new Date().toLocaleTimeString()}
        </span>
        <div className="flex items-center gap-2">
           <Activity size={10} className="text-emerald-400" />
           <span className="text-[7px] text-white/20 uppercase font-black">Real-time Monitor</span>
        </div>
      </div>

      <div className="flex flex-col items-center justify-center py-2 bg-white/5 rounded relative border border-white/5">
         <span className="text-[24px] font-black text-white font-mono leading-none">{overallScore}</span>
         <span className="text-[7px] text-white/40 uppercase font-bold tracking-widest mt-1">Overall Shortage Index</span>
         {parseFloat(overallScore) > 70 && (
           <div className="absolute right-2 top-2">
              <AlertCircle size={12} className="text-amber-500 animate-pulse" />
           </div>
         )}
      </div>

      <div className="flex-1 space-y-2 py-1 overflow-y-auto no-scrollbar">
        {displayData.map((chip, idx) => (
          <motion.div 
            key={`${chip.type}-${idx}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="space-y-1"
          >
            <div className="flex justify-between items-end px-0.5">
               <div className="flex flex-col">
                  <span className="text-[9px] font-black text-white/80">{chip.type}</span>
                  <span className="text-[6px] text-white/30 uppercase font-bold">{chip.keyParts}</span>
               </div>
               <div className="flex items-center gap-1">
                  <Clock size={8} className="text-white/20" />
                  <span className={`text-[10px] font-mono font-black ${chip.stressLevel > 80 ? 'text-red-500' : 'text-amber-400'}`}>{chip.leadTime}</span>
               </div>
            </div>
            
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
               <motion.div 
                 initial={{ width: 0 }}
                 animate={{ width: `${chip.stressLevel}%` }}
                 className={`h-full ${chip.stressLevel > 80 ? 'bg-red-500' : 'bg-purple-500'}`}
               />
            </div>
          </motion.div>
        ))}
      </div>

      <div className="mt-1 pt-1 border-t border-white/5 opacity-30">
        <span className="text-[6px] uppercase font-black text-purple-400 italic">Wafer Utilization Sync Active</span>
      </div>
    </div>
  );
};
