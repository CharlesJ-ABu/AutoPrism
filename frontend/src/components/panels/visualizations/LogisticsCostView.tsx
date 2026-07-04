import React from 'react';
import { motion } from 'framer-motion';
import { Ship, Train, Plane, TrendingUp, TrendingDown, Clock, Fuel, Database, Search } from 'lucide-react';

interface RouteCost {
  mode: 'Sea' | 'Rail' | 'Air';
  route: string;
  price: string;
  change: string;
  trend: 'up' | 'down';
  transitTime: string;
}

export const LogisticsCostView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: RouteCost[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      mode: (metrics.mode || 'Sea') as any,
      route: metrics.route || s.title_brief || 'Global Route',
      price: metrics.price || 'N/A',
      change: metrics.change || '0%',
      trend: metrics.change?.startsWith('+') || s.sentiment > 0 ? 'up' : 'down',
      transitTime: metrics.transit || 'N/A'
    };
  });

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Ship size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Logistics Rate Scan Idle</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Market</span>
            <span className="text-white/40">SCFI / WCI / Drewry</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Intelligence</span>
            <span className="text-rose-500/60 font-black">NO_COST_SIGNALS</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Search size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_logistics_costs() <br/> 捕获中欧班列或全球滚装船的即时运价。
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
           <TrendingUp size={10} className="text-red-500/60" />
           <span className="text-[7px] text-white/20 uppercase font-black">Rate Matrix</span>
        </div>
      </div>

      <div className="flex-1 space-y-1.5 overflow-y-auto no-scrollbar py-1">
        {displayData.map((route, idx) => (
          <motion.div 
            key={`${route.route}-${idx}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="bg-white/5 border border-white/5 rounded p-2 flex items-center justify-between group hover:bg-white/10 transition-colors"
          >
            <div className="flex items-center gap-3">
               <div className="p-1.5 rounded-full bg-white/5 text-white/40">
                  {route.mode === 'Sea' && <Ship size={12} />}
                  {route.mode === 'Rail' && <Train size={12} />}
                  {route.mode === 'Air' && <Plane size={12} />}
               </div>
               <div className="flex flex-col">
                  <span className="text-[9px] font-black text-white/80">{route.route}</span>
                  <div className="flex items-center gap-2">
                     <Clock size={8} className="text-white/20" />
                     <span className="text-[7px] text-white/30 font-bold uppercase">{route.transitTime} Lead</span>
                  </div>
               </div>
            </div>

            <div className="flex flex-col items-end">
               <div className="flex items-center gap-1">
                  <span className="text-[10px] font-mono font-black text-white">{route.price}</span>
                  {route.trend === 'up' ? <TrendingUp size={8} className="text-red-500" /> : <TrendingDown size={8} className="text-emerald-500" />}
               </div>
               <span className={`text-[7px] font-bold ${route.trend === 'up' ? 'text-red-500/60' : 'text-emerald-500/60'}`}>{route.change}</span>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-1 flex justify-between items-center opacity-30 border-t border-white/5 mt-auto">
        <span className="text-[6px] uppercase font-black text-blue-500 italic">Freight Cost Loop Active</span>
      </div>
    </div>
  );
};
