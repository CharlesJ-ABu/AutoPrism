import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, Server, Activity, Thermometer, Database, Search } from 'lucide-react';

interface FoundryNode {
  node: string;
  utilization: number;
  status: string;
  majorClient: string;
}

export const ChipCapacityView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: FoundryNode[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      node: metrics.node || s.title_brief || 'Unknown Node',
      utilization: metrics.utilization || s.impact_score || 50,
      status: metrics.status || (s.impact_score > 80 ? 'Critical' : 'Healthy'),
      majorClient: metrics.client || 'Automotive IVI'
    };
  });

  const getStatusColor = (status: string) => {
    const s = status.toLowerCase();
    if (s.includes('critical') || s.includes('tight')) return 'text-red-500';
    return 'text-emerald-400';
  };

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Server size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Node Utilization Buffer Empty</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Foundry</span>
            <span className="text-white/40">TSMC / SAMSUNG / UMC</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Payload</span>
            <span className="text-rose-500/60 font-black">NULL_CAPACITY_INTEL</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Search size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_chip_capacity() <br/> 捕获 3nm/5nm 制程或车规 MCU 的产能负载波动。
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
        <div className="flex items-center gap-1">
           <Activity size={10} className="text-emerald-400" />
           <span className="text-[7px] text-white/20 uppercase font-black">Wafer Node Tracker</span>
        </div>
      </div>

      <div className="flex-1 space-y-2 py-1 overflow-y-auto no-scrollbar">
        {displayData.map((n, idx) => (
          <motion.div 
            key={`${n.node}-${idx}`}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.1 }}
            className="space-y-1"
          >
            <div className="flex justify-between items-end px-0.5">
               <div className="flex flex-col">
                  <span className="text-[9px] font-black text-white/80">{n.node}</span>
                  <span className="text-[6px] text-white/30 uppercase font-bold">Client: {n.majorClient}</span>
               </div>
               <div className="flex items-center gap-1">
                  <Thermometer size={8} className={getStatusColor(n.status)} />
                  <span className={`text-[11px] font-mono font-black ${getStatusColor(n.status)}`}>{n.utilization}%</span>
               </div>
            </div>
            
            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
               <motion.div 
                 initial={{ width: 0 }}
                 animate={{ width: `${n.utilization}%` }}
                 className={`h-full ${n.utilization > 90 ? 'bg-red-500' : 'bg-blue-500'}`}
               />
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-1 mt-auto border-t border-white/5 opacity-30 flex justify-between items-center">
         <span className="text-[6px] uppercase font-black text-blue-500 italic underline tracking-widest">Wafer Supply Loop Active</span>
         <Database size={8} />
      </div>
    </div>
  );
};
