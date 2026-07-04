import React from 'react';
import { motion } from 'framer-motion';
import { Shield, Zap, TrendingUp, Search, Info, Database } from 'lucide-react';

interface PatentMetric {
  domain: string;
  [key: string]: any;
}

export const PatentLayoutView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑 (动态构建矩阵)
  const companiesSet = new Set<string>();
  const domainsMap: Record<string, Record<string, number>> = {};

  activeSignals.forEach(s => {
    const metrics = s.metrics || {};
    const domain = metrics.domain || '其他';
    const comp = metrics.brand || s.involved_entities?.[0] || 'Unknown';
    const score = metrics.intensity || s.impact_score || 50;

    companiesSet.add(comp);
    if (!domainsMap[domain]) domainsMap[domain] = {};
    domainsMap[domain][comp] = score;
  });

  const companies = Array.from(companiesSet);
  const displayData: PatentMetric[] = Object.entries(domainsMap).map(([domain, values]) => ({
    domain,
    ...values
  }));

  const getHeatColor = (score: number) => {
    if (score > 90) return 'bg-amber-400 text-black';
    if (score > 70) return 'bg-blue-500 text-white';
    if (score > 40) return 'bg-blue-600/60 text-white/80';
    return 'bg-white/5 text-white/30';
  };

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Shield size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Patent Matrix Offline</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Registry</span>
            <span className="text-white/40">WIPO / CNIPA / USPTO</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Payload</span>
            <span className="text-rose-500/60 font-black">NULL_IP_RECORDS</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Database size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_patent_layout() <br/> 捕获竞争对手在固态电池或智驾领域的专利布局。
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
           <TrendingUp size={10} className="text-emerald-400" />
           <span className="text-[7px] text-white/20 uppercase font-black tracking-widest">IP Intensity Matrix</span>
        </div>
      </div>

      <div className="flex-1 overflow-auto no-scrollbar pb-2">
        {/* 为内部 Grid 设置一个足以容纳所有列的最小宽度 */}
        <div style={{ minWidth: `${80 + companies.length * 36}px` }}>
          {/* Header Row */}
          <div 
            className="grid gap-1 mb-1" 
            style={{ gridTemplateColumns: `80px repeat(${companies.length}, 36px)` }}
          >
            <div className="text-[7px] text-white/20 uppercase font-black">Domain</div>
            {companies.map(c => (
              <div key={c} className="text-[7px] text-white/40 uppercase font-black text-center truncate px-0.5" title={c}>
                {c.substring(0, 4)}
              </div>
            ))}
          </div>

          {/* Data Rows */}
          <div className="space-y-1">
            {displayData.map((row, idx) => (
              <div 
                key={`${row.domain}-${idx}`}
                className="grid gap-1 items-center"
                style={{ gridTemplateColumns: `80px repeat(${companies.length}, 36px)` }}
              >
                <div className="text-[8px] font-bold text-white/60 truncate pr-1" title={row.domain}>
                  {row.domain}
                </div>
                {companies.map(comp => {
                  const score = row[comp] || 0;
                  const isMoat = score > 98;
                  return (
                    <motion.div 
                      key={comp}
                      initial={{ scale: 0.8, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: idx * 0.05 }}
                      className={`h-9 w-9 flex items-center justify-center rounded-sm text-[8px] font-black transition-all hover:scale-110 cursor-pointer ${getHeatColor(score)}`}
                    >
                      {isMoat ? <Zap size={8} className="text-black" /> : score || '-'}
                    </motion.div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="pt-2 flex justify-between items-center border-t border-white/5 opacity-30">
        <span className="text-[6px] uppercase font-black text-blue-500 italic underline">Patent Moat Analysis Active</span>
      </div>
    </div>
  );
};
