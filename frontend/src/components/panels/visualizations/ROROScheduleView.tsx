import React from 'react';
import { motion } from 'framer-motion';
import { Ship, Navigation, Calendar, Anchor, ShieldAlert, MapPin, Database, Search } from 'lucide-react';

interface VesselVoyage {
  name: string;
  fleet: string;
  route: string;
  status: string;
  eta: string;
  utilization: string;
}

export const ROROScheduleView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: VesselVoyage[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      name: metrics.vessel || s.title_brief || 'Unknown Vessel',
      fleet: metrics.fleet || s.involved_entities?.[0] || 'Unknown Fleet',
      route: metrics.route || 'Global Route',
      status: metrics.status || (s.impact_score > 70 ? 'Detouring' : 'In Transit'),
      eta: metrics.eta || 'TBD',
      utilization: metrics.utilization || 'N/A'
    };
  });

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Ship size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Maritime Tracker Offline</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Type</span>
            <span className="text-white/40">RORO_FLEET_AIS</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Payload</span>
            <span className="text-rose-500/60 font-black">MISSING_VOYAGE_DATA</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Search size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_roro_schedule() <br/> 捕获比亚迪、安吉物流或华轮威尔森的最新航期。
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
           <Navigation size={10} className="text-blue-400" />
           <span className="text-[7px] text-white/20 uppercase font-black">Global Fleet Matrix</span>
        </div>
      </div>

      <div className="flex-1 space-y-1.5 py-1 overflow-y-auto no-scrollbar">
        {displayData.map((v, idx) => (
          <motion.div 
            key={`${v.name}-${idx}`}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="bg-white/5 border border-white/5 rounded p-2 flex flex-col gap-1.5 group hover:bg-white/10 transition-colors"
          >
            <div className="flex justify-between items-start">
               <div className="flex flex-col">
                  <span className="text-[10px] font-black text-white">{v.name}</span>
                  <span className="text-[6px] text-white/30 uppercase font-bold">{v.fleet}</span>
               </div>
               <div className={`px-1 rounded-sm text-[7px] font-black uppercase ${v.status === 'Detouring' ? 'bg-amber-500/20 text-amber-500' : 'bg-blue-500/20 text-blue-400'}`}>
                  {v.status}
               </div>
            </div>

            <div className="flex items-center justify-between border-t border-white/5 pt-1.5">
               <div className="flex items-center gap-2 min-w-0 flex-1">
                  <MapPin size={8} className="text-white/20 shrink-0" />
                  <span className="text-[8px] text-white/60 truncate font-medium">{v.route}</span>
               </div>
               <div className="flex items-center gap-3 shrink-0 pl-2">
                  <div className="flex flex-col items-end">
                     <span className="text-[9px] font-mono font-black text-white">{v.eta}</span>
                     <span className="text-[5px] text-white/20 uppercase font-black tracking-tighter">ETA</span>
                  </div>
                  <div className="flex flex-col items-end">
                     <span className="text-[9px] font-mono font-black text-emerald-400">{v.utilization}</span>
                     <span className="text-[5px] text-white/20 uppercase font-black tracking-tighter">LOAD</span>
                  </div>
               </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-1 flex justify-between items-center opacity-30 border-t border-white/5">
        <span className="text-[6px] uppercase font-black text-emerald-500 italic underline tracking-widest">Maritime Logistics Sync Active</span>
        <Database size={8} />
      </div>
    </div>
  );
};
