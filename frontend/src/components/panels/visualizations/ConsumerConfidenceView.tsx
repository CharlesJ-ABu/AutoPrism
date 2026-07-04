import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Users, Activity, BarChart3, Database, Search } from 'lucide-react';

interface ConfidenceData {
  region: string;
  score: number;
  change: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  factors: string[];
}

export const ConsumerConfidenceView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: ConfidenceData[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      region: metrics.region || s.geolocation?.name || 'Global',
      score: metrics.score || 50,
      change: metrics.change || '0%',
      sentiment: s.sentiment > 0.2 ? 'positive' : s.sentiment < -0.2 ? 'negative' : 'neutral',
      factors: metrics.factors || [s.title_brief || '消费情绪波动监控中']
    };
  });

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Users size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Sentiment Analysis Stalled</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Type</span>
            <span className="text-white/40">CONSUMER_CONFIDENCE_FEED</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Payload</span>
            <span className="text-rose-500/60 font-black">EMPTY_SENTIMENT_BUF</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Database size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_consumer_confidence() <br/> 捕获全球主要市场的购车意愿指数。
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
           <Activity size={10} className="text-blue-500" />
           <span className="text-[7px] text-white/20 uppercase font-black">Sentiment Pulse</span>
        </div>
      </div>

      <div className="flex-1 space-y-3 py-1">
        {displayData.map((data, idx) => (
          <motion.div 
            key={`${data.region}-${idx}`}
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.1 }}
            className="bg-white/5 border border-white/5 rounded p-2 flex flex-col gap-2 group"
          >
            <div className="flex justify-between items-start">
               <div className="flex flex-col">
                  <span className="text-[10px] font-black text-white group-hover:text-blue-400 transition-colors">{data.region}</span>
                  <div className="flex items-center gap-1 mt-0.5">
                     <div className={`w-1.5 h-1.5 rounded-full ${data.sentiment === 'positive' ? 'bg-emerald-500' : data.sentiment === 'negative' ? 'bg-rose-500' : 'bg-white/20'}`} />
                     <span className="text-[6px] text-white/20 uppercase font-black tracking-tighter">{data.sentiment}</span>
                  </div>
               </div>
               <div className="flex flex-col items-end">
                  <div className="flex items-baseline gap-1">
                     <span className="text-[14px] font-black font-mono text-white leading-none">{data.score}</span>
                     {data.sentiment === 'positive' ? <TrendingUp size={10} className="text-emerald-500" /> : <TrendingDown size={10} className="text-rose-500" />}
                  </div>
                  <span className={`text-[7px] font-black font-mono ${data.sentiment === 'positive' ? 'text-emerald-500/60' : 'text-rose-400/60'}`}>{data.change}</span>
               </div>
            </div>

            <div className="flex flex-wrap gap-1 mt-1 border-t border-white/5 pt-2">
               {data.factors.map((f, fIdx) => (
                 <span key={fIdx} className="text-[7px] px-1.5 py-0.5 rounded-sm bg-white/5 text-white/40 font-medium whitespace-nowrap border border-white/5">
                   {f}
                 </span>
               ))}
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-1 mt-auto border-t border-white/5 opacity-30 flex justify-between items-center">
         <span className="text-[6px] uppercase font-black text-blue-500 italic">Market Mood Sync Active</span>
         <BarChart3 size={8} />
      </div>
    </div>
  );
};
