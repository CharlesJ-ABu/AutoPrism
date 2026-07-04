import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, Zap, Activity, Info, Clock, Terminal, Database, Server } from 'lucide-react';

interface OTAVersion {
  brand: string;
  model: string;
  version: string;
  date: string;
  features: string[];
  type: 'Major' | 'Minor' | 'Hotfix';
}

export const OTAEvolutionView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: OTAVersion[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      brand: metrics.brand || s.involved_entities?.[0] || 'Unknown',
      model: metrics.model || 'Unknown Model',
      version: metrics.version || s.title_brief || 'v0.0.0',
      date: s.created_at ? new Date(s.created_at).toLocaleDateString() : 'Realtime',
      features: Array.isArray(metrics.features) ? metrics.features : [s.title_brief || '核心功能更新'],
      type: (s.impact_score > 70 ? 'Major' : s.impact_score > 40 ? 'Minor' : 'Hotfix') as any
    };
  });

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'Major': return 'border-emerald-500/50 text-emerald-400 bg-emerald-500/5';
      case 'Minor': return 'border-blue-500/50 text-blue-400 bg-blue-500/5';
      default: return 'border-white/20 text-white/40 bg-white/5';
    }
  };

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10 overflow-hidden">
        <Server size={24} className="text-purple-500/40 mb-2 animate-bounce" />
        <span className="text-[10px] font-black text-purple-400/60 uppercase tracking-widest text-center">OTA Stream Syncing...</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Module</span>
            <span className="text-white/40">SOFTWARE_EVOLUTION</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_Panel</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Result</span>
            <span className="text-rose-500/60 font-black">NO_DATA_INGESTED</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Terminal size={12} />
           <span className="text-[6px] font-mono tracking-tighter uppercase whitespace-nowrap">Await specialized.fetch_ota_evolution() callback</span>
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
           <Activity size={10} className="text-emerald-500 animate-pulse" />
           <span className="text-[7px] text-white/20 uppercase font-black tracking-widest">Active OS Tracking</span>
        </div>
      </div>

      <div className="flex-1 space-y-3 relative before:absolute before:left-[5px] before:top-2 before:bottom-2 before:w-[1px] before:bg-white/5">
        {displayData.map((ota, idx) => (
          <motion.div 
            key={`${ota.brand}-${ota.version}-${idx}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="pl-5 relative group"
          >
            <div className="absolute left-[2px] top-1.5 w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] group-hover:scale-150 transition-transform" />
            
            <div className="flex justify-between items-start mb-1">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[8px] font-black text-white/40 uppercase tracking-tighter">{ota.brand} {ota.model}</span>
                  <span className={`text-[6px] font-black px-1 rounded-sm border ${getTypeColor(ota.type)}`}>
                    {ota.type}
                  </span>
                </div>
                <h4 className="text-[10px] font-black text-white mt-0.5">{ota.version}</h4>
              </div>
              <div className="flex items-center gap-1 opacity-30">
                <Clock size={8} />
                <span className="text-[7px] font-mono">{ota.date}</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-1 mt-1.5">
              {ota.features.map(feat => (
                <span key={feat} className="text-[7px] px-1.5 py-0.5 rounded-full bg-white/5 border border-white/10 text-white/60 font-medium whitespace-nowrap">
                  {feat}
                </span>
              ))}
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-1 flex justify-between items-center opacity-30 border-t border-white/5 mt-1">
        <span className="text-[6px] uppercase font-black tracking-tighter text-emerald-500 italic">Software Moat Detected</span>
      </div>
    </div>
  );
};
