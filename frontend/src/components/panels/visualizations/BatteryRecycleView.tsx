import React from 'react';
import { motion } from 'framer-motion';
import { RefreshCcw, Recycle, Database, ShieldCheck, Zap, BarChart3, Search } from 'lucide-react';

interface RecycleMetric {
  metal: string;
  rate: string;
  priceTrend: 'up' | 'down';
  marketStatus: string;
}

export const BatteryRecycleView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: RecycleMetric[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      metal: metrics.metal || s.title_brief || 'Unknown Metal',
      rate: metrics.rate || '0%',
      priceTrend: metrics.trend === 'up' || s.sentiment > 0 ? 'up' : 'down',
      marketStatus: metrics.status || 'Monitoring'
    };
  });

  const overallYield = activeSignals.length > 0 ? activeSignals[0].metrics?.yield || '0%' : '0%';
  const processedVolume = activeSignals.length > 0 ? activeSignals[0].metrics?.volume || '0 GWh' : '0 GWh';

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Recycle size={24} className="text-emerald-500/40 mb-2 animate-spin-slow" />
        <span className="text-[10px] font-black text-emerald-400/60 uppercase tracking-widest text-center">Recycle Loop Standby</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Domain</span>
            <span className="text-white/40">CIRCULAR_ECONOMY_LOOP</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Signals</span>
            <span className="text-rose-500/60 font-black">WAITING_FOR_METRICS</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Search size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_battery_recycle() <br/> 捕获黑粉行情或回收渠道建设的最新动向。
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
           <ShieldCheck size={10} className="text-blue-400" />
           <span className="text-[7px] text-white/20 uppercase font-black">Circular Economy Pulse</span>
        </div>
      </div>

      <div className="bg-white/5 rounded p-2 border border-white/5 flex items-center justify-around">
         <div className="flex flex-col items-center">
            <span className="text-[14px] font-black text-emerald-400 font-mono">{overallYield}</span>
            <span className="text-[6px] text-white/40 uppercase font-bold">Yield</span>
         </div>
         <div className="w-[1px] h-6 bg-white/10" />
         <div className="flex flex-col items-center">
            <span className="text-[14px] font-black text-blue-400 font-mono">{processedVolume}</span>
            <span className="text-[6px] text-white/40 uppercase font-bold">Processed</span>
         </div>
      </div>

      <div className="flex-1 space-y-1.5 py-1 overflow-y-auto no-scrollbar">
        {displayData.map((m, idx) => (
          <motion.div 
            key={`${m.metal}-${idx}`}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="bg-white/5 border border-white/5 rounded p-2 flex items-center justify-between group hover:bg-white/10 transition-colors"
          >
            <div className="flex items-center gap-2">
               <div className="p-1.5 rounded bg-emerald-500/10 text-emerald-400">
                  <Recycle size={12} />
               </div>
               <div className="flex flex-col">
                  <span className="text-[9px] font-black text-white/80">{m.metal}</span>
                  <span className="text-[6px] text-white/30 uppercase font-bold">{m.marketStatus}</span>
               </div>
            </div>
            <div className="flex flex-col items-end">
               <span className="text-[11px] font-mono font-black text-emerald-400">{m.rate}</span>
               <span className="text-[6px] text-white/20 uppercase font-black tracking-tighter">Recovery Rate</span>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-1 mt-auto border-t border-white/5 opacity-30 flex justify-between items-center">
         <span className="text-[6px] uppercase font-black text-emerald-500 italic underline tracking-widest">Battery Passport Sync Active</span>
         <Database size={8} />
      </div>
    </div>
  );
};
