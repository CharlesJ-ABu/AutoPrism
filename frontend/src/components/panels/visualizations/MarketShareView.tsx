import React, { useState } from 'react';
import { PieChart, Database, Info, Activity } from 'lucide-react';
import ReactECharts from 'echarts-for-react';

interface MarketData {
  brand: string;
  share: number;
  change: string;
  trend: 'up' | 'down';
}

export const MarketShareView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
  const [market, setMarket] = useState<'China' | 'Europe' | 'USA' | 'Global'>('Global');
  const [segment, setSegment] = useState<'Overall' | 'SUV' | 'Sedan'>('Overall');

  // 1. 过滤实时信号 (结合大盘路由与本地 UI 筛选)
  const activeSignals = signals?.filter(s => {
    if (!s.target_panel_ids?.includes(panelId)) return false;
    const metrics = s.metrics || {};
    const sMarket = metrics.market || 'Unknown';
    const sSegment = metrics.segment || 'Unknown';
    
    // 如果 UI 选择了 Global/Overall，则包含该维度下的所有地区/车型数据；否则要求精准匹配
    const matchMarket = market === 'Global' ? true : sMarket === market;
    const matchSegment = segment === 'Overall' ? true : sSegment === segment;
    
    return matchMarket && matchSegment;
  }) || [];

  // 2. 转换并聚合数据
  // 因为 Global/Overall 会圈中同一个品牌在不同地区的数据，我们需要对同品牌进行动态聚合计算
  const brandMap = new Map<string, { shareSum: number, count: number, change: string, trend: 'up' | 'down' }>();

  activeSignals.forEach(s => {
    const metrics = s.metrics || {};
    const brand = metrics.brand || s.involved_entities?.[0] || 'Unknown';
    const share = parseFloat(metrics.share) || 0;
    const change = metrics.change || '0%';
    const trend = metrics.change?.startsWith('+') || s.sentiment > 0 ? 'up' : 'down';

    if (!brandMap.has(brand)) {
      brandMap.set(brand, { shareSum: 0, count: 0, change, trend });
    }
    const state = brandMap.get(brand)!;
    state.shareSum += share;
    state.count += 1;
  });

  const displayData: MarketData[] = Array.from(brandMap.entries()).map(([brand, data]) => {
    return {
      brand,
      // 简单平均 (注：严格的全球市占率需引入绝对销量 Volume 作为权重，这里先做无权平均并由饼图自适应)
      share: data.shareSum / data.count, 
      change: data.change, // 默认取遇到的一条变动数据展示
      trend: data.trend
    };
  });

  // 可选：对聚合出来的 share 进行 100% 归一化，保证展示的严谨性
  const totalShare = displayData.reduce((sum, d) => sum + d.share, 0);
  if (totalShare > 0) {
    displayData.forEach(d => {
      d.share = parseFloat(((d.share / totalShare) * 100).toFixed(1));
    });
  }

  // 3. 空状态/调试 UI
  if (displayData.length === 0) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
        <PieChart size={24} className="text-emerald-500/40 mb-2 animate-pulse" />
        <span className="text-[10px] font-black text-emerald-400/60 uppercase tracking-widest text-center">Market Data Reconstructing</span>
        <div className="mt-4 w-full space-y-1">
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Query_ID</span>
            <span className="text-white/40">{panelId}</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
            <span>Source</span>
            <span className="text-white/40">CPCA / VDA / ACEA</span>
          </div>
          <div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
            <span>Payload</span>
            <span className="text-rose-500/60 font-black">NO_VALID_METRICS</span>
          </div>
        </div>
        <div className="mt-6 flex flex-col items-center gap-1 opacity-20 text-center">
           <Database size={10} />
           <span className="text-[6px] font-black text-white uppercase leading-tight">
             等待 SpecializedScraper.fetch_market_share() <br/> 捕获乘联会或厂商最新交付快报。
           </span>
        </div>
      </div>
    );
  }

  // 4. 构建 ECharts 饼图所需的数据格式
  // 为了美观，我们根据品牌名称自动分配一些默认的主题色
  const brandColors: Record<string, string> = {
    'BYD': '#10b981',
    'Tesla': '#ef4444',
    'Toyota': '#3b82f6',
    'VW': '#f59e0b',
    'Hyundai': '#8b5cf6',
    'Stellantis': '#ec4899',
    'GM': '#06b6d4',
    'Geely': '#3b82f6',
    'NIO': '#06b6d4',
    'Li Auto': '#ec4899',
    'Xiaomi': '#f97316',
    'Ford': '#2563eb',
    'BMW': '#1d4ed8',
    'Mercedes': '#9ca3af',
    'Renault': '#fcd34d',
    'MG': '#dc2626',
    'Kia': '#ef4444',
    'Rivian': '#fbbf24',
    'Lucid': '#0f766e',
    'Aion': '#34d399',
    'Changan': '#2563eb',
    'Honda': '#dc2626',
    'Nissan': '#9ca3af',
    'Mazda': '#991b1b',
    'Subaru': '#1e3a8a',
    'Suzuki': '#0284c7',
    'Porsche': '#b91c1c',
    'Audi': '#1f2937',
    'Volvo': '#1e40af',
    'XPeng': '#10b981',
    'Leapmotor': '#059669',
    'Zeekr': '#f97316',
    'Avatr': '#6366f1',
    'Deepal': '#14b8a6',
    'AITO': '#be123c',
    'Chery': '#991b1b',
    'GWM': '#b45309',
    'SAIC': '#1d4ed8',
    'FAW': '#1e3a8a',
    'Dongfeng': '#dc2626',
    'BAIC': '#3b82f6',
    'Polestar': '#fbbf24',
    'Land Rover': '#065f46',
    'Jaguar': '#1f2937',
    'Lexus': '#4b5563',
    'Cadillac': '#d97706',
    'Chevrolet': '#d97706'
  };

  const chartData = displayData.map(d => ({
    name: d.brand,
    value: d.share,
    itemStyle: { 
      // 匹配预设颜色，如果没有则使用淡蓝色
      color: brandColors[d.brand] || '#60a5fa' 
    }
  }));

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(0,0,0,0.8)',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#fff', fontSize: 10 },
      formatter: '{b}: {c}%'
    },
    series: [
      {
        name: 'Market Share',
        type: 'pie',
        radius: ['32%', '55%'], // 环形饼图半径
        center: ['50%', '52%'], 
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 3, borderColor: 'transparent', borderWidth: 1.5 },
        label: { 
          show: true, 
          position: 'outside', 
          color: 'rgba(255,255,255,0.7)', 
          fontSize: 7, 
          distanceToLabelLine: 2,
          formatter: '{b}' 
        },
        labelLine: {
          show: true,
          length: 4, 
          length2: 3, 
          lineStyle: { color: 'rgba(255,255,255,0.1)' }
        },
        emphasis: { label: { show: true, fontSize: 9, fontWeight: 'bold', color: '#fff' } },
        data: chartData
      }
    ]
  };

  return (
    <div className="h-full w-full flex flex-col overflow-hidden bg-black/40 rounded-lg border border-white/5">
      {/* 极简筛选器 UI (完全还原之前的视觉效果) */}
      <div className="flex flex-wrap gap-x-1.5 gap-y-1 px-2 pt-1 border-b border-white/5 pb-1 justify-center bg-white/5">
        <div className="flex gap-1">
          {(['CN', 'EU', 'US', 'GL'] as const).map(m => (
            <button 
              key={m} 
              onClick={() => setMarket({CN: 'China', EU: 'Europe', US: 'USA', GL: 'Global'}[m] as any)}
              className={`text-[7px] px-1 py-0.5 rounded-sm transition-all font-bold ${market.startsWith({CN: 'Chi', EU: 'Eur', US: 'USA', GL: 'Glo'}[m]) ? 'bg-violet-500 text-white' : 'text-white/20 hover:text-white/40'}`}
            >
              {m}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {(['ALL', 'SUV', 'SED'] as const).map(s => (
            <button 
              key={s} 
              onClick={() => setSegment({ALL: 'Overall', SUV: 'SUV', SED: 'Sedan'}[s] as any)}
              className={`text-[7px] px-1 py-0.5 rounded-sm transition-all font-bold ${segment.startsWith({ALL: 'Ove', SUV: 'SUV', SED: 'Sed'}[s]) ? 'bg-emerald-500 text-white' : 'text-white/20 hover:text-white/40'}`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0 relative">
        <ReactECharts 
          option={option} 
          style={{ height: '100%', width: '100%' }}
          opts={{ renderer: 'svg' }}
          notMerge={true}
        />
      </div>

      {/* 底部信息栏 */}
      <div className="px-2 pb-1.5 pt-1 border-t border-white/5 opacity-30 flex justify-between items-center">
         <span className="text-[6px] uppercase font-bold tracking-tighter">Real-time AI Parsed Stream</span>
         <Info size={8} />
      </div>
    </div>
  );
};
