import React from 'react';
import { motion } from 'framer-motion';
import { Globe, Zap, Repeat, Info, Database, Search } from 'lucide-react';

interface NetworkStats {
  region: string;
  total_chargers: string;
  ev_to_charger_ratio: string;
  fast_charge_percent: number;
  stations: { brand: string; count: string; type: 'Supercharger' | 'Swap' | 'Public' }[];
}

export const EnergyNetworkView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑
  const displayData: NetworkStats[] = activeSignals.map(s => {
    const metrics = s.metrics || {};
    return {
      region: metrics.region || s.geolocation?.name || 'Global',
      total_chargers: metrics.total || 'N/A',
      ev_to_charger_ratio: metrics.ratio || 'N/A',
      fast_charge_percent: metrics.fast_percent || 0,
      stations: metrics.stations || []
    };
  });

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Zap size={24} className="text-blue-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-blue-400/60 uppercase tracking-widest text-center">Charging Network Grid Off</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Domain</span>
            <span className="text-white/40">EV_INFRASTRUCTURE</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Signals</span>
            <span className="text-rose-500/60 font-black">NULL_INFRA_STREAM</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20">
           <Database size={10} />
           <span className="text-[6px] font-black text-white uppercase text-center leading-tight">
             等待 SpecializedScraper.fetch_energy_network() <br/> 获取最新的公用桩数或换电站分布数据。
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
        <div className="flex gap-2">
           <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> <span className="text-[7px] text-white/30 font-black uppercase">Charge</span></div>
           <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-purple-500" /> <span className="text-[7px] text-white/30 font-black uppercase">Swap</span></div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2">
        {displayData.map((item, idx) => (
          <div key={`${item.region}-${idx}`} className="bg-white/5 border border-white/5 rounded p-2 relative overflow-hidden group">
            <div className="flex justify-between items-start mb-2">
              <div>
                <h4 className="text-[10px] font-black text-white">{item.region}</h4>
                <div className="flex gap-2 mt-0.5">
                  <span className="text-[7px] text-white/40 font-bold uppercase">Total: {item.total_chargers}</span>
                  <span className="text-[7px] text-emerald-400 font-bold uppercase tracking-tighter">Ratio: {item.ev_to_charger_ratio}</span>
                </div>
              </div>
              <div className="flex flex-col items-end">
                 <span className="text-[12px] font-mono font-bold text-blue-400">{item.fast_charge_percent}%</span>
                 <span className="text-[6px] text-white/20 uppercase font-black tracking-tighter">Fast</span>
              </div>
            </div>

            <div className="flex flex-wrap gap-1 mt-1">
              {item.stations.map((st, sIdx) => (
                <div key={sIdx} className="bg-black/40 border border-white/5 rounded p-1 flex items-center justify-between min-w-[80px]">
                  <div className="flex items-center gap-1">
                    {st.type === 'Swap' ? <Repeat size={8} className="text-purple-500" /> : <Zap size={8} className="text-blue-500" />}
                    <span className="text-[7px] text-white/60 truncate max-w-[40px] font-bold">{st.brand}</span>
                  </div>
                  <span className="text-[8px] font-mono font-black text-white/90">{st.count}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="pt-1 mt-auto flex justify-between items-center opacity-30 border-t border-white/5">
        <span className="text-[6px] uppercase font-black text-emerald-500 italic">Energy Map Real-time Sync Active</span>
      </div>
    </div>
  );
};
