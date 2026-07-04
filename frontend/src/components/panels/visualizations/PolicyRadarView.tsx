import React from 'react';
import { motion } from 'framer-motion';
import { Gavel, Globe2, AlertTriangle, CheckCircle2, Zap, Database, Search } from 'lucide-react';

interface PolicyItem {
  region: string;
  title: string;
  impact: 'CRITICAL' | 'MEDIUM' | 'LOW';
  summary: string;
  status: string;
}

export const PolicyRadarView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤属于 p1 的实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 数据转换逻辑
  const displayData: PolicyItem[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    const impactVal = metrics.impact_score || s.impact_score || 50;
    const sentimentVal = metrics.sentiment !== undefined ? metrics.sentiment : s.sentiment;
    
    return {
      region: metrics.region || s.geolocation?.name || 'Global',
      title: metrics.title_brief || s.title_brief || s.title,
      impact: (impactVal > 80 ? 'CRITICAL' : impactVal > 50 ? 'MEDIUM' : 'LOW'),
      summary: metrics.reasoning || s.reasoning || '内容正在由 AI 引擎降噪中...',
      status: sentimentVal < -0.3 ? '政策收紧' : sentimentVal > 0.3 ? '政策利好' : '观察中'
    };
  });

  const getImpactStyles = (impact: string) => {
    switch (impact) {
      case 'CRITICAL': return { bg: 'bg-rose-500/10', border: 'border-rose-500/30', text: 'text-rose-400', icon: <AlertTriangle size={12} className="text-rose-500" /> };
      case 'MEDIUM': return { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', icon: <Zap size={12} className="text-amber-500" /> };
      default: return { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', icon: <CheckCircle2 size={12} className="text-blue-400" /> };
    }
  };

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Database size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest">Waiting for Data Stream</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Panel_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Backend_Status</span>
            <span className="text-emerald-500/60 font-black">Connected</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Query_Result</span>
            <span className="text-rose-500/60 font-black">Empty_Result_Set</span>
          </div>
        </div>
        <div className="mt-6 flex items-center gap-2 text-[8px] text-white/30 italic">
          <Search size={10} />
          <span>请点击上方 Crawler 按钮启动全球政策扫描...</span>
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
           <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
           <span className="text-[7px] text-white/30 uppercase font-black">Live Regulatory Feed</span>
        </div>
      </div>

      <div className="flex-1 space-y-2">
        {displayData.map((policy, idx) => {
          const styles = getImpactStyles(policy.impact);
          return (
            <motion.div 
              key={`${policy.title}-${idx}`}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className={`${styles.bg} ${styles.border} border rounded p-2 relative group`}
            >
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-1.5">
                  <Gavel size={10} className="text-white/40" />
                  <span className="text-[7px] text-white/40 uppercase font-black tracking-tighter">{policy.region}</span>
                </div>
                <span className={`text-[6px] font-black uppercase px-1 rounded-sm border ${styles.border} ${styles.text}`}>
                  {policy.status}
                </span>
              </div>

              <h4 className="mt-1 text-[9px] font-black text-white leading-tight uppercase">{policy.title}</h4>
              <p className="mt-1 text-[8px] text-white/60 font-medium leading-normal">{policy.summary}</p>

              <div className="mt-2 flex items-center gap-1">
                 {styles.icon}
                 <span className={`text-[7px] font-black uppercase ${styles.text}`}>Impact: {policy.impact}</span>
              </div>
            </motion.div>
          );
        })}
      </div>

      <div className="pt-1 flex justify-between items-center opacity-30">
        <span className="text-[6px] uppercase font-bold tracking-tighter">Regulatory Intel v5.0</span>
        <span className="text-[6px] uppercase font-bold tracking-tighter text-blue-500">已对齐 27 面板标准</span>
      </div>
    </div>
  );
};
