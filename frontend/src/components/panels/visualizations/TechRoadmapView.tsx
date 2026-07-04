import React from 'react';
import { motion } from 'framer-motion';
import { Cpu, Battery, Navigation, FlaskConical, Target, Rocket, Database, AlertCircle } from 'lucide-react';

interface RoadmapNode {
  year: string;
  milestones: { track: 'Energy' | 'AD' | 'EE'; title: string; status: 'R&D' | 'Pilot' | 'Mass' }[];
}

export const TechRoadmapView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  // 1. 过滤实时信号
  const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

  // 2. 转换逻辑 (根据抓取到的信号动态生成)
  // 我们按照年份进行分组显示
  const displayRoadmap: RoadmapNode[] = [];
  const yearGroups: Record<string, RoadmapNode['milestones']> = {};

  activeSignals.forEach(s => {
    const metrics = s.metrics || {};
    const year = metrics.year || 'Next Gen';
    if (!yearGroups[year]) yearGroups[year] = [];
    
    yearGroups[year].push({
      track: (metrics.track || 'AD') as any,
      title: metrics.milestone || s.title_brief || '关键技术节点',
      status: (s.impact_score > 80 ? 'Mass' : s.impact_score > 50 ? 'Pilot' : 'R&D') as any
    });
  });

  Object.entries(yearGroups).forEach(([year, milestones]) => {
    displayRoadmap.push({ year, milestones });
  });

  // 按年份排序
  displayRoadmap.sort((a, b) => a.year.localeCompare(b.year));

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'R&D': return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
      case 'Pilot': return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      default: return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    }
  };

  const getTrackIcon = (track: string) => {
    switch (track) {
      case 'Energy': return <Battery size={10} className="text-emerald-400" />;
      case 'AD': return <Navigation size={10} className="text-blue-400" />;
      default: return <Cpu size={10} className="text-purple-400" />;
    }
  };

  // 3. 空状态/调试 UI
  if (displayRoadmap.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <Rocket size={24} className="text-orange-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-orange-400/60 uppercase tracking-widest text-center">Tech Roadmap Standby</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Layer</span>
            <span className="text-white/40">STRATEGIC_PLANNING</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Scan_Result</span>
            <span className="text-rose-500/60 font-black">EMPTY_ROADMAP_BUF</span>
          </div>
        </div>
        <div className="mt-6 flex items-center gap-1 opacity-40">
           <AlertCircle size={10} className="text-white/40" />
           <span className="text-[6px] text-white/30 uppercase font-bold text-center leading-tight">
             正在等待 SpecializedScraper.fetch_tech_roadmap() <br/> 的最新架构推演结果...
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
           <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-blue-500" /> <span className="text-[7px] text-white/30 uppercase">R&D</span></div>
           <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> <span className="text-[7px] text-white/30 uppercase">Pilot</span></div>
           <div className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> <span className="text-[7px] text-white/30 uppercase">Mass</span></div>
        </div>
      </div>

      <div className="flex-1 flex flex-col space-y-3 relative">
        <div className="absolute left-[3px] top-4 bottom-4 w-[1px] bg-white/5" />

        {displayRoadmap.map((node, nIdx) => (
          <div key={node.year} className="relative pl-4">
            <div className="absolute left-0 top-1 w-2 h-2 rounded-full bg-white/20 border border-white/10 z-10" />
            
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[12px] font-black text-white font-mono leading-none">{node.year}</span>
              <div className="h-[1px] flex-1 bg-white/5" />
            </div>

            <div className="grid grid-cols-1 gap-1.5">
              {node.milestones.map((m, mIdx) => (
                <motion.div 
                  key={`${m.title}-${mIdx}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: nIdx * 0.2 + mIdx * 0.1 }}
                  className="bg-white/5 border border-white/5 rounded p-1.5 flex items-center justify-between group hover:bg-white/10 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    {getTrackIcon(m.track)}
                    <span className="text-[8px] text-white/80 font-medium">{m.title}</span>
                  </div>
                  <span className={`text-[6px] font-black px-1 rounded-sm border ${getStatusColor(m.status)}`}>
                    {m.status}
                  </span>
                </motion.div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="pt-1 mt-auto flex justify-between items-center opacity-30 border-t border-white/5 pt-2">
        <span className="text-[6px] uppercase font-bold tracking-tighter text-purple-400 font-black italic underline">Strategic Roadmap Sync Active</span>
      </div>
    </div>
  );
};
