import React from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, TrendingDown, TrendingUp, Users, Activity, ExternalLink, Database } from 'lucide-react';

interface SupplierRisk {
  name: string;
  score: number;
  margin: string;
  rating: string;
  status: string;
  risks: string[];
}

export const Tier1RiskView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: SupplierRisk[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      name: metrics.name || s.involved_entities?.[0] || 'Unknown OEM',
      score: metrics.risk_score || s.impact_score || 50,
      margin: metrics.margin || 'N/A',
      rating: metrics.rating || 'N/A',
      status: metrics.status || (s.sentiment < -0.3 ? 'Warning' : 'Stable'),
      risks: metrics.risks || [s.title_brief || '经营波动监控中']
    };
  });

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Users size={24} className="text-amber-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-amber-400/60 uppercase tracking-widest text-center">Supplier Audit Timeout</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Module_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_Target</span>
            <span className="text-white/40">TIER1_GLOBAL_HEALTH</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Result</span>
            <span className="text-rose-500/60 font-black">NO_RECORDS_YET</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Database size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             正在等待 SpecializedScraper.fetch_tier1_risks() <br/> 的供应商信用评级更新。
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
        <span className="text-[7px] text-white/20 uppercase font-black">Risk Matrix v3.0</span>
      </div>

      <div className="flex-1 space-y-3 py-1">
        {displayData.map((s, idx) => (
          <motion.div 
            key={`${s.name}-${idx}`}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="bg-white/5 rounded p-2 border border-white/5 relative group hover:border-white/20 transition-colors"
          >
            <div className="absolute left-0 top-0 bottom-0 w-1 bg-red-500/50 rounded-l" style={{ height: `${s.score}%`, opacity: s.score / 100 }} />

            <div className="flex justify-between items-start pl-1">
               <div className="flex flex-col">
                  <span className="text-[11px] font-black text-white">{s.name}</span>
                  <div className="flex items-center gap-2 mt-0.5">
                     <span className="text-[7px] px-1 rounded bg-red-500/20 text-red-400 font-bold uppercase">{s.status}</span>
                     <span className="text-[7px] text-white/40 font-mono">Rating: {s.rating}</span>
                  </div>
               </div>
               <div className="flex flex-col items-end">
                  <span className={`text-[12px] font-black font-mono ${s.score > 75 ? 'text-red-500' : 'text-amber-500'}`}>{s.score}</span>
                  <span className="text-[6px] text-white/20 uppercase font-bold">Risk Index</span>
               </div>
            </div>

            <div className="mt-2 flex items-center justify-between border-t border-white/5 pt-1.5">
               <div className="flex gap-1.5 overflow-hidden">
                  {s.risks.map((r, rIdx) => (
                    <span key={`${r}-${rIdx}`} className="text-[8px] text-white/60 flex items-center gap-1 whitespace-nowrap">
                       <Activity size={8} className="text-red-500/60" /> {r}
                    </span>
                  ))}
               </div>
               <div className="flex items-center gap-1 ml-2">
                  <TrendingDown size={10} className="text-red-500/40" />
                  <span className="text-[9px] font-mono font-bold text-white/80">{s.margin}</span>
               </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-1 flex justify-between items-center opacity-30 border-t border-white/5">
        <div className="flex items-center gap-1">
           <ExternalLink size={8} />
           <span className="text-[6px] uppercase font-black">Tier-1 Strategy Audit Active</span>
        </div>
      </div>
    </div>
  );
};
