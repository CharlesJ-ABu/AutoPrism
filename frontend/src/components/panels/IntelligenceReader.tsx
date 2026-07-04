import React from 'react';
import { X, Shield, Zap, Globe, Clock, Target, AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { GlassCard, Button } from '@/components/ui';

interface IntelligenceReaderProps {
  item: any | null;
  onClose: () => void;
}

export const IntelligenceReader: React.FC<IntelligenceReaderProps> = ({ item, onClose }) => {
  if (!item) return null;

  // 判断是否为 L2 战略洞察 (具有 analysis 字段)
  const isStrategic = !!item.analysis || !!item.strategic_advice;

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center bg-black/80 backdrop-blur-md p-6 animate-in fade-in duration-300">
      <GlassCard opacity={0.1} className="w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden border-white/20 shadow-[0_0_80px_rgba(139,92,246,0.3)]">
        {/* Header */}
        <div className="p-6 border-b border-white/10 flex items-center justify-between bg-white/5 relative">
          {/* 背景装饰图 */}
          <div className="absolute top-0 right-20 opacity-10 pointer-events-none">
            {isStrategic ? <Shield size={120} /> : <Globe size={120} />}
          </div>

          <div className="flex flex-col gap-1 relative z-10">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-[10px] font-black px-2 py-0.5 rounded tracking-tighter ${isStrategic ? 'bg-amber-500 text-black' : 'bg-violet-500 text-white'}`}>
                {isStrategic ? 'STRATEGIC_INSIGHT_L2' : 'RAW_INTEL_L1'}
              </span>
              <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest">
                {isStrategic ? item.role : item.source_name}
              </span>
            </div>
            <h2 className="text-2xl font-black text-white tracking-tight leading-tight max-w-2xl">
              {item.title}
            </h2>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full text-white/40 hover:text-white transition-all">
            <X size={28} />
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-8 custom-scrollbar bg-black/20">
          <div className="max-w-3xl mx-auto space-y-8">
            
            {/* 核心摘要 */}
            <div className="p-6 bg-white/5 rounded-xl border border-white/5 italic text-lg text-white/90 leading-relaxed font-serif relative">
              <div className="absolute -top-3 -left-3 p-2 bg-violet-600 rounded-lg">
                <Zap size={16} className="text-white" />
              </div>
              "{item.summary || item.content?.substring(0, 200)}"
            </div>

            {isStrategic ? (
              <div className="space-y-8">
                {/* 维度矩阵 */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    { label: 'SENTIMENT', val: item.sentiment, icon: item.sentiment > 0 ? TrendingUp : item.sentiment < 0 ? TrendingDown : Minus, color: item.sentiment > 0 ? 'text-emerald-400' : 'text-rose-400' },
                    { label: 'HORIZON', val: item.analysis?.horizon || 'MEDIUM', icon: Clock, color: 'text-sky-400' },
                    { label: 'SCALE', val: item.analysis?.impact_scale || 'REGIONAL', icon: Globe, color: 'text-indigo-400' },
                    { label: 'PRIORITY', val: `LEVEL ${item.priority}`, icon: Target, color: 'text-amber-400' },
                  ].map((meta, i) => (
                    <div key={i} className="p-4 bg-white/5 border border-white/5 rounded-lg flex flex-col gap-2">
                      <div className="flex items-center gap-2 text-[10px] font-black text-white/30 uppercase tracking-widest">
                        <meta.icon size={12} className={meta.color} />
                        {meta.label}
                      </div>
                      <div className="text-sm font-bold text-white uppercase tracking-tight">{meta.val}</div>
                    </div>
                  ))}
                </div>

                {/* 深度分析网格 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <h5 className="text-[11px] font-black text-violet-400 uppercase tracking-[0.2em] flex items-center gap-2">
                      <div className="w-1 h-3 bg-violet-500 rounded-full" /> 现状深度拆解
                    </h5>
                    <div className="text-sm text-white/70 leading-relaxed bg-white/5 p-4 rounded-lg border border-white/5 min-h-[120px]">
                      {item.analysis?.situation || "AI 正在重新解析现状特征..."}
                    </div>
                  </div>
                  <div className="space-y-3">
                    <h5 className="text-[11px] font-black text-rose-400 uppercase tracking-[0.2em] flex items-center gap-2">
                      <div className="w-1 h-3 bg-rose-500 rounded-full" /> 潜在战略影响
                    </h5>
                    <div className="text-sm text-white/70 leading-relaxed bg-white/5 p-4 rounded-lg border border-white/5 min-h-[120px]">
                      {item.analysis?.implication || "AI 正在推演二级传导链条..."}
                    </div>
                  </div>
                </div>

                {/* 行动建议 - 核心高亮 */}
                <div className="p-6 bg-gradient-to-br from-violet-600/20 to-indigo-600/20 rounded-xl border border-violet-500/30 relative group">
                  <div className="flex items-center gap-3 mb-4">
                    <Shield className="text-violet-400" size={20} />
                    <h5 className="text-sm font-black text-white uppercase tracking-widest">战略行动路线 (Strategic Advice)</h5>
                  </div>
                  <div className="text-base text-white/90 leading-relaxed font-bold">
                    {item.strategic_advice || "该情报暂未生成明确的行动建议。"}
                  </div>
                  {/* 装饰发光 */}
                  <div className="absolute -inset-px bg-gradient-to-r from-violet-500/10 to-transparent rounded-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                </div>
              </div>
            ) : (
              /* 普通情报正文 */
              <div className="text-white/80 leading-relaxed text-base space-y-4 whitespace-pre-wrap font-sans">
                {item.content || "正文提取中或该条目暂无详细正文内容。"}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-white/10 bg-white/5 flex items-center justify-between">
          <div className="flex flex-col">
            <span className="text-[10px] text-white/40 font-mono tracking-tighter uppercase">Intelligent Strategic Synthesis Engine v2.0</span>
            <p className="text-[9px] text-white/20 italic">
              * 此报告由 AutoPrism 战略引擎基于多维实时数据聚合生成，用于决策辅助参考。
            </p>
          </div>
          {item.source_url && !isStrategic && (
            <Button 
              onClick={() => window.open(item.source_url, '_blank')}
              className="bg-violet-600 hover:bg-violet-500 text-white font-bold gap-2 px-6"
            >
              访问网页原文
            </Button>
          )}
        </div>
      </GlassCard>
    </div>
  );
};
