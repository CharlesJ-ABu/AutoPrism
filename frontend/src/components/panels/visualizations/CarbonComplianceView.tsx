import React from 'react';
import { motion } from 'framer-motion';
import { Leaf, Timer, TrendingUp, Info, Activity, Database, Search } from 'lucide-react';

interface CarbonMarket {
  name: string;
  price: string;
  currency: string;
  trend: 'up' | 'down';
  change: string;
}

interface Deadline {
  title: string;
  date: string;
  status: 'Critical' | 'Upcoming' | 'In-Progress';
}

export const CarbonComplianceView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const markets: CarbonMarket[] = [];
  const deadlines: Deadline[] = [];

  activeSignals.forEach(s => {
    const metrics = s.metrics || {};
    if (metrics.price) {
      markets.push({
        name: metrics.market || s.title_brief || 'Unknown Market',
        price: metrics.price,
        currency: metrics.currency || '?',
        trend: metrics.change?.startsWith('+') || s.sentiment > 0 ? 'up' : 'down',
        change: metrics.change || '0%'
      });
    } else {
      deadlines.push({
        title: s.title_brief || s.title,
        date: metrics.date || 'TBD',
        status: (s.impact_score > 80 ? 'Critical' : s.impact_score > 40 ? 'In-Progress' : 'Upcoming') as any
      });
    }
  });

  // 3. 空状态/调试 UI
  if (markets.length === 0 && deadlines.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Leaf size={24} className="text-emerald-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-emerald-400/60 uppercase tracking-widest text-center">Carbon Tracker Offline</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Data_Point</span>
            <span className="text-white/40">EU_ETS / CHINA_ETS</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Scan</span>
            <span className="text-rose-500/60 font-black">NO_ENVIRONMENTAL_INTEL</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Search size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_carbon_compliance() <br/> 捕获欧标 Euro 7 或电池护照相关的法规动向。
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
        <Activity size={10} className="text-emerald-500/40 animate-pulse" />
      </div>

      {markets.length > 0 && (
        <div className="grid grid-cols-2 gap-2">
          {markets.map((m, idx) => (
            <div key={`${m.name}-${idx}`} className="bg-emerald-500/5 border border-emerald-500/10 rounded p-2">
              <div className="text-[7px] text-white/40 uppercase font-black truncate">{m.name}</div>
              <div className="flex items-baseline gap-1 mt-1">
                <span className="text-[14px] font-black text-white">{m.price}</span>
                <span className="text-[6px] text-white/30 uppercase font-bold">{m.currency}</span>
              </div>
              <div className="flex items-center gap-1 mt-0.5">
                 <TrendingUp size={8} className={m.trend === 'up' ? 'text-emerald-400' : 'text-rose-400'} />
                 <span className={`text-[7px] font-mono font-bold ${m.trend === 'up' ? 'text-emerald-400' : 'text-rose-400'}`}>{m.change}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex-1 space-y-1.5">
        <div className="text-[8px] text-white/20 uppercase font-black tracking-widest mb-1 flex items-center gap-1">
          <Timer size={8} /> Regulatory Deadlines
        </div>
        {deadlines.map((d, idx) => (
          <motion.div 
            key={`${d.title}-${idx}`}
            initial={{ opacity: 0, x: -5 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="flex items-center justify-between p-1.5 bg-white/5 rounded border border-white/5 hover:bg-white/10 transition-colors"
          >
            <div className="flex flex-col">
              <span className="text-[8px] text-white/80 font-medium">{d.title}</span>
              <span className="text-[6px] text-white/30 font-mono">{d.date}</span>
            </div>
            <span className={`text-[6px] font-black px-1 rounded-sm border ${
              d.status === 'Critical' ? 'text-rose-400 border-rose-500/30 bg-rose-500/5' : 'text-blue-400 border-blue-500/30 bg-blue-500/5'
            }`}>
              {d.status.toUpperCase()}
            </span>
          </motion.div>
        ))}
      </div>

      <div className="pt-1 mt-auto border-t border-white/5 opacity-30 flex justify-between items-center">
         <span className="text-[6px] uppercase font-bold tracking-tighter text-emerald-500 font-black italic underline tracking-widest">Net-Zero Compliance Sync</span>
         <Database size={8} />
      </div>
    </div>
  );
};
