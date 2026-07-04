import React from 'react';
import { motion } from 'framer-motion';
import { Anchor, Clock, AlertTriangle, CheckCircle2, Navigation, Ship, Database } from 'lucide-react';

interface PortStatus {
  name: string;
  location: string;
  waitTime: string;
  efficiency: number;
  status: 'critical' | 'warning' | 'normal';
  reason: string;
}

export const PortLogisticsView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: PortStatus[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    const impact = s.impact_score || 50;
    return {
      name: metrics.port || s.involved_entities?.[0] || 'Unknown Port',
      location: metrics.location || 'Global',
      waitTime: metrics.wait || 'N/A',
      efficiency: 100 - impact,
      status: impact > 80 ? 'critical' : impact > 40 ? 'warning' : 'normal',
      reason: metrics.status || s.title_brief || '港口运行状态监控中'
    };
  });

  const getStatusColor = (status: string) => {
    if (status === 'critical') return 'text-red-500 bg-red-500/10 border-red-500/20';
    if (status === 'warning') return 'text-amber-400 bg-amber-400/10 border-amber-400/20';
    return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
  };

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Anchor size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Port Beacon Offline</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_Panel</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Data_Feed</span>
            <span className="text-white/40">MARINETRAFFIC_AIS</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Alerts</span>
            <span className="text-rose-500/60 font-black">NO_CONGESTION_LOGS</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Database size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             尚未捕获到广州、上海或汉堡等 <br/> 核心汽车滚装枢纽的拥堵异常信号。
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
           <Ship size={10} className="text-white/20" />
           <span className="text-[7px] text-white/20 uppercase font-black tracking-widest">Port Efficiency Loop</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto no-scrollbar space-y-1">
        {displayData.map((p, idx) => (
          <motion.div 
            key={`${p.name}-${idx}`}
            initial={{ opacity: 0, x: -5 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            className="flex items-center justify-between p-1.5 bg-white/5 rounded border border-white/5 hover:bg-white/10 transition-colors group"
          >
            <div className="flex items-center gap-2 flex-1 min-w-0">
               {p.status === 'normal' ? (
                 <CheckCircle2 size={12} className="text-emerald-500/40" />
               ) : (
                 <AlertTriangle size={12} className={p.status === 'critical' ? 'text-red-500' : 'text-amber-400'} />
               )}
               <div className="flex flex-col min-w-0">
                  <span className="text-[9px] font-black text-white truncate">{p.name}</span>
                  <span className="text-[6px] text-white/30 uppercase font-bold truncate">{p.reason}</span>
               </div>
            </div>

            <div className="flex items-center gap-3">
               <div className="w-12 h-1 bg-white/5 rounded-full overflow-hidden hidden sm:block">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${p.efficiency}%` }}
                    className={`h-full ${p.status === 'critical' ? 'bg-red-500' : p.status === 'warning' ? 'bg-amber-400' : 'bg-emerald-500'}`}
                  />
               </div>
               
               <div className="flex flex-col items-end min-w-[40px]">
                  <div className="flex items-center gap-1">
                     <Clock size={8} className="text-white/20" />
                     <span className={`text-[9px] font-mono font-black ${p.status === 'critical' ? 'text-red-500' : 'text-white/60'}`}>{p.waitTime}</span>
                  </div>
                  <span className="text-[6px] text-white/20 uppercase font-bold tracking-tighter">Waiting</span>
               </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-1.5 border-t border-white/5">
         <div className="flex justify-between items-center bg-blue-500/5 p-1 rounded">
            <div className="flex items-center gap-2">
               <Navigation size={10} className="text-blue-400 animate-pulse" />
               <span className="text-[7px] text-blue-400/80 font-black uppercase tracking-tighter">Global Maritime Hubs In-Sync</span>
            </div>
         </div>
      </div>
    </div>
  );
};
