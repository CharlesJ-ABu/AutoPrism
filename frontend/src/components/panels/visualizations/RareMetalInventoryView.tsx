import React from 'react';
import { motion } from 'framer-motion';
import { Gauge, TrendingUp, TrendingDown, Database, AlertCircle, Search } from 'lucide-react';

interface MetalBalance {
  name: string;
  isRatio: string;
  status: string;
  inventoryLevel: number;
  trend: 'up' | 'down';
  notes: string;
}

export const RareMetalInventoryView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: MetalBalance[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      name: metrics.name || s.title_brief || 'Unknown Metal',
      isRatio: metrics.ratio || 'N/A',
      status: metrics.status || (s.sentiment < -0.2 ? 'Deficit' : 'Balanced'),
      inventoryLevel: metrics.level || s.impact_score || 50,
      trend: metrics.trend === 'down' || s.sentiment < 0 ? 'down' : 'up',
      notes: metrics.notes || s.title_brief || '供需趋势扫描中'
    };
  });

  const getStatusColor = (status: string) => {
    const s = status.toLowerCase();
    if (s.includes('deficit') || s.includes('short')) return 'text-red-500 bg-red-500/10 border-red-500/20';
    if (s.includes('surplus') || s.includes('excess')) return 'text-blue-400 bg-blue-400/10 border-blue-500/20';
    return 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20';
  };

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Database size={24} className="text-amber-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-amber-400/60 uppercase tracking-widest text-center">Inventory Tracker Sleeping</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Market</span>
            <span className="text-white/40">SMM / LME / USGS</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Payload</span>
            <span className="text-rose-500/60 font-black">STALLED_BY_NULL</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Search size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_rare_metal_inventory() <br/> 获取最新的库销比或黑粉库存数据。
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
           <Gauge size={10} className="text-white/20" />
           <span className="text-[7px] text-white/20 uppercase font-black">Supply Balance Matrix</span>
        </div>
      </div>

      <div className="flex-1 space-y-2 py-1 overflow-y-auto no-scrollbar">
        {displayData.map((m, idx) => (
          <motion.div 
            key={`${m.name}-${idx}`}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.1 }}
            className="bg-white/5 border border-white/5 rounded p-2 flex flex-col gap-2 group hover:bg-white/10 transition-colors"
          >
            <div className="flex justify-between items-start">
               <div className="flex flex-col">
                  <span className="text-[10px] font-black text-white/80">{m.name}</span>
                  <div className={`mt-0.5 px-1 rounded-sm border inline-flex text-[6px] font-black uppercase ${getStatusColor(m.status)}`}>
                     {m.status}
                  </div>
               </div>
               <div className="flex flex-col items-end">
                  <span className={`text-[12px] font-mono font-black ${m.status.toLowerCase().includes('deficit') ? 'text-red-500' : 'text-blue-400'}`}>{m.isRatio}</span>
                  <span className="text-[6px] text-white/20 uppercase font-black tracking-tighter">I/S Ratio</span>
               </div>
            </div>

            <div className="space-y-1">
               <div className="flex justify-between items-center">
                  <span className="text-[6px] text-white/20 uppercase font-bold">Inventory Level</span>
                  {m.trend === 'down' ? <TrendingDown size={8} className="text-red-500" /> : <TrendingUp size={8} className="text-blue-400" />}
               </div>
               <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: `${m.inventoryLevel}%` }}
                    className={`h-full ${m.status.toLowerCase().includes('deficit') ? 'bg-red-500' : 'bg-blue-500'}`}
                  />
               </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-1 mt-auto border-t border-white/5 opacity-30 flex justify-between items-center">
         <span className="text-[6px] uppercase font-black text-blue-500 italic underline">Supply Chain Balance Sync</span>
         <AlertCircle size={8} />
      </div>
    </div>
  );
};
