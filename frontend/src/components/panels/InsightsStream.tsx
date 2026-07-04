import React from 'react';
import { motion } from 'framer-motion';
import { Shield, Zap, Target, ArrowUpRight, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { GlassCard } from '../ui';

interface Insight {
  id: string;
  title: string;
  summary: string;
  priority: number;
  sentiment: number;
  display_type: string;
}

interface InsightsStreamProps {
  insights: Insight[];
  onSelect: (name: string) => void;
}

export const InsightsStream: React.FC<InsightsStreamProps> = ({ insights, onSelect }) => {
  if (insights.length === 0) {
    return (
      <div className="w-full h-[120px] mt-4 flex gap-4 overflow-hidden px-1">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex-shrink-0 w-[300px] h-full">
            <GlassCard opacity={0.02} className="h-full border-dashed border-white/5 flex flex-col items-center justify-center gap-2 text-center">
              <Zap size={20} className="text-white/5 animate-pulse mx-auto" />
              <div className="px-4">
                <p className="text-[10px] font-bold text-white/20 uppercase tracking-widest">
                  等待战略合成...
                </p>
                <p className="text-[9px] text-white/10 italic">
                  点击顶部 [AI 降噪] 激活该节点情报
                </p>
              </div>
            </GlassCard>
          </div>
        ))}
      </div>
    );
  }

  // 为无缝循环准备双倍数据
  const doubledInsights = [...insights, ...insights];
  const cardWidth = 316; // 300px width + 16px (gap-4)

  return (
    <div className="w-full h-[120px] mt-4 overflow-hidden relative group">
      {/* 边缘淡出遮罩 */}
      <div className="absolute left-0 top-0 bottom-0 w-20 bg-gradient-to-r from-black/80 to-transparent z-10 pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-20 bg-gradient-to-l from-black/80 to-transparent z-10 pointer-events-none" />

      <motion.div
        className="flex gap-4 w-max px-4"
        animate={{
          x: [0, -(insights.length * cardWidth)]
        }}
        transition={{
          duration: insights.length * 10, // 速度：每张卡片约 10 秒
          ease: "linear",
          repeat: Infinity,
        }}
        // 关键：Hover 时暂停动画
        style={{ cursor: 'pointer' }}
        whileHover={{ animationPlayState: 'paused' }}
      >
        {doubledInsights.map((insight, idx) => {
          const isPositive = insight.sentiment > 0;
          const isNegative = insight.sentiment < 0;
          
          return (
            <div
              key={`${insight.id}-${idx}`}
              onClick={() => onSelect(insight.title)}
              className="flex-shrink-0 w-[300px] h-full group"
            >
              <GlassCard 
                opacity={0.1} 
                className="h-full border-white/5 group-hover:border-white/20 transition-all duration-300 relative overflow-hidden"
              >
                {/* 背景装饰线 */}
                <div 
                  className="absolute top-0 left-0 w-1 h-full" 
                  style={{ background: isPositive ? '#10b981' : isNegative ? '#ef4444' : '#f59e0b' }}
                />
                
                <div className="p-3">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      {isPositive ? (
                        <TrendingUp size={12} className="text-emerald-400" />
                      ) : isNegative ? (
                        <TrendingDown size={12} className="text-rose-400" />
                      ) : (
                        <Minus size={12} className="text-amber-400" />
                      )}
                      <span className="text-[10px] font-black text-white/40 uppercase tracking-widest">
                        {insight.display_type}
                      </span>
                    </div>
                    <span className="text-[8px] text-white/20 font-mono">#{idx % insights.length + 1}</span>
                  </div>

                  <h4 className="text-[11px] font-bold text-white leading-tight mb-1 truncate group-hover:text-violet-400 transition-colors">
                    {insight.title}
                  </h4>
                  
                  <p className="text-[10px] text-white/50 leading-relaxed line-clamp-2 italic">
                    {insight.summary}
                  </p>

                  <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ArrowUpRight size={14} className="text-white/20" />
                  </div>
                </div>
              </GlassCard>
            </div>
          );
        })}
      </motion.div>
    </div>
  );
};
