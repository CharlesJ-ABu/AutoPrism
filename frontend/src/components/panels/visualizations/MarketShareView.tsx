import React from 'react';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp, TrendingDown, PieChart, Activity, Database, Info } from 'lucide-react';

interface MarketData {
  brand: string;
  share: number;
  change: string;
  trend: 'up' | 'down';
}

export const MarketShareView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: MarketData[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      brand: metrics.brand || s.involved_entities?.[0] || 'Unknown',
      share: parseFloat(metrics.share) || 0,
      change: metrics.change || '0%',
      trend: metrics.change?.startsWith('+') || s.sentiment > 0 ? 'up' : 'down'
    };
  });

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <PieChart size={24} className="text-emerald-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-emerald-400/60 uppercase tracking-widest text-center">Market Data Reconstructing</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Source</span>
            <span className="text-white/40">CPCA / VDA / ACEA</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Payload</span>
            <span className="text-rose-500/60 font-black">NO_VALID_METRICS</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20 text-center">
           <Database size={10} />
           <span className="text-[6px] font-black text-white uppercase leading-tight">
             等待 SpecializedScraper.fetch_market_share() <br/> 捕获乘联会或厂商最新交付快报。
           </span>
        </div>
      </div>
    );
  }

  const maxShare = Math.max(...displayData.map(d => d.share), 1);

  return (
    <div className="h-full w-full flex flex-col p-2 bg-black/40 rounded-lg border border-white/5 space-y-2 overflow-hidden">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
          Last Sync: {new Date().toLocaleTimeString()}
        </span>
        <div className="flex items-center gap-1">
           <BarChart3 size={10} className="text-white/20" />
           <span className="text-[7px] text-white/20 uppercase font-black">Global Delivery Matrix</span>
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto no-scrollbar py-1">
        {displayData.map((item, idx) => (
          <div key={`${item.brand}-${idx}`} className="group relative">
            <div className="flex justify-between items-end mb-1 px-0.5">
               <div className="flex flex-col">
                  <span className="text-[10px] font-black text-white group-hover:text-emerald-400 transition-colors">{item.brand}</span>
                  <div className="flex items-center gap-1 mt-0.5">
                     <span className="text-[6px] text-white/20 uppercase font-black tracking-widest">Market Share</span>
                     <span className="text-[8px] font-mono font-bold text-white/80">{item.share}%</span>
                  </div>
               </div>
               <div className={`flex items-center gap-1 ${item.trend === 'up' ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {item.trend === 'up' ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                  <span className="text-[9px] font-black font-mono">{item.change}</span>
               </div>
            </div>

            <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
               <motion.div 
                 initial={{ width: 0 }}
                 animate={{ width: `${(item.share / maxShare) * 100}%` }}
                 transition={{ duration: 1, delay: idx * 0.1 }}
                 className="h-full bg-gradient-to-r from-emerald-600/40 to-emerald-400 rounded-full"
               />
            </div>
          </div>
        ))}
      </div>

      <div className="pt-1 mt-auto border-t border-white/5 opacity-30 flex justify-between items-center">
         <span className="text-[6px] uppercase font-bold tracking-tighter">Deliveries Analyzed: 24H Window</span>
         <Info size={8} />
      </div>
    </div>
  );
};
