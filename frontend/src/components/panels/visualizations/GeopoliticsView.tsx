import React from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, Globe, ShieldAlert, ArrowRight, ShieldCheck, Database } from 'lucide-react';

interface RiskItem {
  region: string;
  risk_level: 'CRITICAL' | 'WARNING' | 'MODERATE';
  tariff: string;
  barrier: string;
  impact: string;
  status_text: string;
}

export const GeopoliticsView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];
  
  // 2. 转换逻辑 (不使用 Baseline)
  const displayRisks: RiskItem[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      region: metrics.region || s.geolocation?.name || s.involved_entities?.[0] || '未知区域',
      risk_level: (metrics.risk_level || (s.impact_score > 80 ? 'CRITICAL' : s.impact_score > 50 ? 'WARNING' : 'MODERATE')) as any,
      tariff: metrics.tariff || '待核算',
      barrier: metrics.barrier || s.title_brief || '非关税贸易壁垒',
      impact: metrics.impact || '正在评估对单车利润的影响',
      status_text: s.sentiment < -0.5 ? '严峻' : s.sentiment < 0 ? '受压' : '观察'
    };
  });

  const getLevelStyles = (level: string) => {
    switch (level) {
      case 'CRITICAL': return { bg: 'bg-rose-500/10', border: 'border-rose-500/30', text: 'text-rose-400', icon: 'text-rose-500' };
      case 'WARNING': return { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', icon: 'text-amber-500' };
      default: return { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', icon: 'text-blue-500' };
    }
  };

  // 3. 空状态/调试 UI
  if (displayRisks.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <ShieldCheck size={24} className="text-rose-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-rose-400/60 uppercase tracking-widest text-center">Global Geopolitics Scanner Standby</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Target_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Intelligence_Type</span>
            <span className="text-white/40">COMPLIANCE_RADAR</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Scan_Result</span>
            <span className="text-rose-500/60 font-black">ZERO_SIGNALS_FOUND</span>
          </div>
        </div>
        <div className="mt-6 p-2 bg-white/5 rounded border border-white/5 w-full">
           <div className="flex items-center gap-1 mb-1">
             <Database size={8} className="text-white/40" />
             <span className="text-[6px] text-white/40 uppercase font-bold">Debug Log:</span>
           </div>
           <p className="text-[6px] text-white/20 leading-tight">
             Crawler 尚未捕获涉及 301 条款、反补贴调查或出口管制相关的 L2 结构化信号。
           </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col p-2 bg-black/40 rounded-lg border border-white/5 space-y-2 overflow-y-auto no-scrollbar">
      <div className="flex justify-between items-center mb-1">
        <div className="flex flex-col">
          <span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
            Last Sync: {new Date().toLocaleTimeString()}
          </span>
          <span className="text-[10px] font-bold text-white/40 uppercase tracking-widest flex items-center gap-1">
            出海合规与风险雷达
          </span>
        </div>
        <div className="flex items-center gap-1">
           <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
           <span className="text-[7px] text-white/30 uppercase font-black">Live Monitoring</span>
        </div>
      </div>

      <div className="flex-1 space-y-2">
        {displayRisks.map((risk, idx) => {
          const styles = getLevelStyles(risk.risk_level);
          return (
            <motion.div 
              key={`${risk.region}-${idx}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className={`${styles.bg} ${styles.border} border rounded p-2 relative group overflow-hidden`}
            >
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-1.5">
                  <ShieldAlert size={12} className={styles.icon} />
                  <h4 className="text-[10px] font-black text-white">{risk.region}</h4>
                </div>
                <span className={`text-[7px] font-black uppercase px-1 rounded-sm border ${styles.border} ${styles.text}`}>
                  {risk.status_text}
                </span>
              </div>

              <div className="mt-1.5 flex justify-between items-end">
                <div className="flex flex-col">
                  <span className="text-[7px] text-white/40 uppercase font-bold tracking-tighter">主要壁垒</span>
                  <span className="text-[8px] text-white/80 font-medium">{risk.barrier}</span>
                </div>
                <div className="text-right">
                  <span className="text-[14px] font-black text-white leading-none">{risk.tariff}</span>
                  <div className="text-[6px] text-white/20 font-bold uppercase">基准关税</div>
                </div>
              </div>

              <div className="mt-1 flex items-center gap-1 text-[7px] text-white/30 italic">
                <ArrowRight size={8} />
                {risk.impact}
              </div>

              <div className="absolute -right-2 -bottom-2 opacity-5 pointer-events-none group-hover:opacity-20 transition-opacity">
                <AlertTriangle size={40} className={styles.icon} />
              </div>
            </motion.div>
          );
        })}
      </div>

      <div className="pt-1 flex justify-between items-center opacity-30">
        <span className="text-[6px] uppercase font-bold tracking-tighter text-rose-500 underline underline-offset-2 tracking-widest">Compliance Intel v4.2</span>
      </div>
    </div>
  );
};
