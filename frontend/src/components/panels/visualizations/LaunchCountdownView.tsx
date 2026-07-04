import React from 'react';
import { motion } from 'framer-motion';
import { Calendar, Rocket, Timer, ChevronRight, Activity, Flame, Database, Search } from 'lucide-react';

interface LaunchEvent {
  model: string;
  brand: string;
  status: string;
  date: string;
  daysRemaining: string;
  expectedPrice: string;
  hotScore: number;
}

export const LaunchCountdownView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: LaunchEvent[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      model: metrics.model || s.title_brief || 'Unknown Model',
      brand: metrics.brand || s.involved_entities?.[0] || 'Unknown',
      status: metrics.status || 'Announcement',
      date: metrics.date || 'TBD',
      daysRemaining: metrics.days || 'N/A',
      expectedPrice: metrics.price || '待定',
      hotScore: s.impact_score || 50
    };
  });

  const getStatusColor = (status: string) => {
    const s = status.toLowerCase();
    if (s.includes('delivery')) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    if (s.includes('pre-sale') || s.includes('presale')) return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
    if (s.includes('spy') || s.includes('shots')) return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
    return 'text-white/40 bg-white/5 border-white/10';
  };

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Rocket size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Launch Radar Scanning</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Type</span>
            <span className="text-white/40">VEHICLE_RELEASE_MONITOR</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Signals</span>
            <span className="text-rose-500/60 font-black">ZERO_MATCHES</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Search size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_launch_countdown() <br/> 捕获新车型工信部申报或官宣节点。
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
           <Activity size={10} className="text-blue-500 animate-pulse" />
           <span className="text-[7px] text-white/20 uppercase font-black tracking-widest">Upcoming Nodes</span>
        </div>
      </div>

      <div className="flex-1 space-y-2">
        {displayData.map((car, idx) => (
          <motion.div 
            key={`${car.model}-${idx}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="bg-white/5 border border-white/5 rounded p-2 relative group hover:border-blue-500/30 transition-colors"
          >
            <div className="flex justify-between items-start mb-1.5">
              <div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[7px] font-black text-blue-400 uppercase tracking-tighter">{car.brand}</span>
                  <span className={`text-[6px] font-black px-1 rounded-sm border ${getStatusColor(car.status)}`}>
                    {car.status.toUpperCase()}
                  </span>
                </div>
                <h4 className="text-[11px] font-black text-white mt-0.5">{car.model}</h4>
              </div>
              <div className="flex flex-col items-end">
                <div className="flex items-center gap-1 text-emerald-400">
                  <Timer size={10} />
                  <span className="text-[10px] font-mono font-black">{car.daysRemaining}</span>
                </div>
                <span className="text-[6px] text-white/20 font-bold uppercase tracking-widest mt-0.5">{car.date}</span>
              </div>
            </div>

            <div className="h-[2px] w-full bg-white/5 rounded-full mt-2 relative overflow-hidden">
               <motion.div 
                 initial={{ width: 0 }}
                 animate={{ width: `${car.hotScore}%` }}
                 className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full"
               />
            </div>

            <div className="flex justify-between items-center mt-2 pt-1 border-t border-white/5">
               <div className="flex items-center gap-1">
                 <Flame size={8} className="text-amber-500" />
                 <span className="text-[7px] text-white/40 font-bold uppercase tracking-tight">Market Interest: {car.hotScore}%</span>
               </div>
               <div className="flex items-center gap-1">
                  <span className="text-[7px] text-white/60 font-black uppercase tracking-tighter">{car.expectedPrice}</span>
                  <ChevronRight size={8} className="text-white/20" />
               </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
