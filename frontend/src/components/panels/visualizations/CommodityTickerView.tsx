import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity, AlertCircle, RefreshCw, Database } from 'lucide-react';

interface Commodity {
  name: string;
  price: string;
  unit: string;
  change: string;
  trend: 'up' | 'down' | 'stable';
  color: string;
}

export const CommodityTickerView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: Commodity[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    const trend = s.sentiment > 0 ? 'up' : s.sentiment < 0 ? 'down' : 'stable';
    return {
      name: metrics.name || s.title_brief || '未知材料',
      price: metrics.price || '0.00',
      unit: metrics.unit || '',
      change: metrics.change || (s.sentiment > 0 ? '+??%' : '-??%'),
      trend,
      color: trend === 'up' ? 'text-red-500' : 'text-emerald-500'
    };
  });

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <RefreshCw size={24} className="text-red-500/40 mb-2 animate-spin-slow" />
        <span className="text-[10px] font-black text-red-400/60 uppercase tracking-widest text-center">Metal Exchange Disconnected</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Market_Feed</span>
            <span className="text-white/40">SMM / LME / SHFE</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Ingestion</span>
            <span className="text-rose-500/60 font-black">STALLED</span>
          </div>
        </div>
        <div className="mt-4 flex flex-col items-center gap-1 opacity-20">
           <Database size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待点火 Crawler 获取 LME 铝锭或 <br/> 电池级碳酸锂实时报价。
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
        <span className="text-[7px] text-white/20 uppercase font-black tracking-widest">Real-time Ticker</span>
      </div>

      <div className="flex-1 grid grid-cols-2 gap-2">
        {displayData.map((item, idx) => (
          <motion.div 
            key={`${item.name}-${idx}`}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.1 }}
            className="bg-white/5 border border-white/5 rounded p-2 flex flex-col justify-between group hover:bg-white/10 transition-colors"
          >
            <div className="flex justify-between items-start">
               <span className="text-[8px] font-black text-white/60 truncate mr-1">{item.name}</span>
               {item.trend === 'up' ? <TrendingUp size={10} className="text-red-500" /> : <TrendingDown size={10} className="text-emerald-500" />}
            </div>
            
            <div className="mt-1">
               <div className="flex items-baseline gap-0.5">
                  <span className="text-[12px] font-black text-white font-mono">{item.price}</span>
                  <span className="text-[6px] text-white/30 font-bold">{item.unit}</span>
               </div>
               <div className={`text-[8px] font-black flex items-center gap-1 ${item.color}`}>
                  {item.change}
                  <span className="text-[6px] opacity-40 font-bold uppercase tracking-tighter">Adjusted</span>
               </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-1 flex justify-between items-center opacity-30 border-t border-white/5">
        <span className="text-[6px] uppercase font-black text-blue-500 italic">BOM Price Index Sync Active</span>
      </div>
    </div>
  );
};
