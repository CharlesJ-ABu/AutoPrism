import React from 'react';
import { motion } from 'framer-motion';
import { Scale, CheckCircle, HelpCircle, AlertCircle, MapPin, Gauge, Database, Search } from 'lucide-react';

interface LegalStatus {
  region: string;
  level: string;
  status: string;
  liability: string;
  speedLimit: string;
  keyNote: string;
}

export const ADLegalView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: LegalStatus[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      region: metrics.region || s.geolocation?.name || 'Unknown Region',
      level: metrics.level || 'N/A',
      status: metrics.status || 'Testing',
      liability: metrics.liability || 'Shared',
      speedLimit: metrics.speed || 'N/A',
      keyNote: metrics.note || s.title_brief || '法规细则正在解析中'
    };
  });

  const getStatusIcon = (status: string) => {
    const s = status.toLowerCase();
    if (s.includes('licensed') || s.includes('approved')) return <CheckCircle size={10} className="text-emerald-400" />;
    if (s.includes('pilot') || s.includes('permit')) return <HelpCircle size={10} className="text-amber-400" />;
    return <AlertCircle size={10} className="text-blue-400" />;
  };

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Scale size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Legal Compliance Engine Waiting</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Standard</span>
            <span className="text-white/40">UN R157 / WP.29</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Signals</span>
            <span className="text-rose-500/60 font-black">NO_LEGAL_FEED</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Search size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_ad_legal_framework() <br/> 捕获工信部 L3/L4 试点或加州新规动态。
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
           <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
           <span className="text-[7px] text-white/30 uppercase font-black tracking-widest">Legal Loop</span>
        </div>
      </div>

      <div className="flex-1 space-y-2">
        {displayData.map((item, idx) => (
          <motion.div 
            key={`${item.region}-${idx}`}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="bg-white/5 border border-white/5 rounded p-2 relative group"
          >
            <div className="flex justify-between items-start mb-1.5">
              <div className="flex items-center gap-1.5">
                <MapPin size={10} className="text-blue-400 opacity-60" />
                <h4 className="text-[10px] font-black text-white uppercase tracking-tight">{item.region}</h4>
              </div>
              <div className="flex gap-1">
                <span className="text-[7px] font-black uppercase bg-blue-500/20 text-blue-400 px-1 rounded-sm">
                  {item.level}
                </span>
                <span className={`text-[7px] font-black uppercase px-1 rounded-sm border border-white/10 text-white/40 flex items-center gap-1`}>
                  {getStatusIcon(item.status)} {item.status.toUpperCase()}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 mt-2">
              <div className="flex flex-col">
                <span className="text-[6px] text-white/20 uppercase font-bold">Liability</span>
                <span className="text-[8px] text-white/80 font-medium">{item.liability}</span>
              </div>
              <div className="flex flex-col items-end text-right">
                <span className="text-[6px] text-white/20 uppercase font-bold">Max Speed</span>
                <div className="flex items-center gap-1">
                   <Gauge size={8} className="text-white/20" />
                   <span className="text-[8px] text-white font-mono">{item.speedLimit}</span>
                </div>
              </div>
            </div>

            <div className="mt-2 pt-1.5 border-t border-white/5">
               <p className="text-[8px] text-white/40 leading-snug italic">
                 {item.keyNote}
               </p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
