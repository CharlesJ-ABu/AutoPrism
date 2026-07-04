// AutoPrism - Draggable Panel Component (Hardcore Vibe Aligned)
import { useState } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import { GripHorizontal, RefreshCw, ChevronDown, ChevronUp, Sparkles, AlertTriangle, Database, ExternalLink } from 'lucide-react';
import type { Panel as PanelType, FeedItem } from '@/types';
import { useFeedStore } from '@/stores';
import { GlassCard } from '@/components/ui';
import { ai } from '@/lib/api';
import { TimeSeriesChart } from './visualizations/TimeSeriesChart';
import { ConsumerConfidenceView } from './visualizations/ConsumerConfidenceView'; // 引入定制化宏观视图
import { BatteryDensityView } from './visualizations/BatteryDensityView'; // 引入电池天梯视图
import { ADBenchmarkingView } from './visualizations/ADBenchmarkingView'; // 引入智驾对标雷达
import { EnergyNetworkView } from './visualizations/EnergyNetworkView'; // 引入能源补能网络
import { GeopoliticsView } from './visualizations/GeopoliticsView'; // 引入地缘政治合规
import { PriceAdjustmentView } from './visualizations/PriceAdjustmentView'; // 引入车型调价预警
import { OTAEvolutionView } from './visualizations/OTAEvolutionView'; // 引入重点车型 OTA 演变
import { SpecComparisonView } from './visualizations/SpecComparisonView'; // 引入重点车型参数对标
import { LaunchCountdownView } from './visualizations/LaunchCountdownView'; // 引入新车型上市倒计时
import { CabinExperienceView } from './visualizations/CabinExperienceView'; // 引入智能座舱评价
import { LightweightView } from './visualizations/LightweightView'; // 引入整车轻量化
import { PatentLayoutView } from './visualizations/PatentLayoutView'; // 引入专利布局
import { CommodityTickerView } from './visualizations/CommodityTickerView'; // 引入大宗原材料价格
import { Tier1RiskView } from './visualizations/Tier1RiskView'; // 引入 Tier-1 经营风险
import { PortLogisticsView } from './visualizations/PortLogisticsView'; // 引入全球港口物流
import { SemiconductorShortageView } from './visualizations/SemiconductorShortageView'; // 引入半导体短缺
import { LogisticsCostView } from './visualizations/LogisticsCostView'; // 引入物流通道成本
import { BatteryRecycleView } from './visualizations/BatteryRecycleView'; // 引入电池回收监测
import { RareMetalInventoryView } from './visualizations/RareMetalInventoryView'; // 引入稀有金属库销比
import { ROROScheduleView } from './visualizations/ROROScheduleView'; // 引入滚装船排期
import { ChipCapacityView } from './visualizations/ChipCapacityView'; // 引入芯片产能利用率
import { CarbonComplianceView } from './visualizations/CarbonComplianceView'; // 引入碳合规监测
import { TechRoadmapView } from './visualizations/TechRoadmapView'; // 引入技术演进路线图
import { PolicyRadarView } from './visualizations/PolicyRadarView'; // 引入全球政策雷达
import { SupplyChainRiskView } from './visualizations/SupplyChainRiskView'; // 引入断链风险预警
import { ADLegalView } from './visualizations/ADLegalView'; // 引入智驾法律准入
import { GridHeatmap } from './visualizations/GridHeatmap';
import { RadarChart } from './visualizations/RadarChart';
import { TelemetryGauge } from './visualizations/TelemetryGauge';
import ReactECharts from 'echarts-for-react';

export type PanelWidth = '1x1' | '2x1' | '2x2';

const SIZE_CYCLE: PanelWidth[] = ['1x1', '2x1', '2x2'];
const SIZE_LABELS: Record<PanelWidth, string> = { '1x1': '1/4', '2x1': '1/2', '2x2': '1' };
const SIZE_SPAN: Record<PanelWidth, number> = { '1x1': 1, '2x1': 2, '2x2': 2 };

interface PanelProps {
  panel: PanelType;
  signals?: any[];
  children?: React.ReactNode;
  onRefresh?: (dataSourceId: string) => void;
  onWidthToggle?: (id: string, size: PanelWidth) => void;
  onOpenReader?: (item: any) => void;
  dragListeners?: Record<string, any>;
  dragAttributes?: Record<string, any>;
}

// 简单映射数据源 ID 到官方链接
const SOURCE_URL_MAP: Record<string, string> = {
  '36Kr_Insight': 'https://36kr.com/information/autos/',
  'CNBC_Economy': 'https://www.cnbc.com/economy/',
  'Reuters_Macro': 'https://www.reuters.com/business/finance/',
  'AutoNews_US': 'https://www.autonews.com/',
  'AutoHome_CN': 'https://www.autohome.com.cn/news/',
  'Bloomberg_Terminal': 'https://www.bloomberg.com/markets',
  '36Kr_AUTO': 'https://36kr.com/information/autos/',
  'TechCrunch_Global': 'https://techcrunch.com/category/transportation/',
  'EastMoney_Macro': 'https://data.eastmoney.com/cjsj/xfzxx.html',
  'The Conference Board': 'https://www.conference-board.org/topics/consumer-confidence',
  'National Bureau of Statistics': 'http://www.stats.gov.cn/english/',
  'Eurostat': 'https://ec.europa.eu/eurostat/web/main/home'
};

export function Panel({ panel, signals = [], children, onRefresh, onWidthToggle, onOpenReader, dragListeners, dragAttributes }: PanelProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const feed = useFeedStore((s) => s.feeds.get(panel.data_source_id || ''));
  const sourceUrl = SOURCE_URL_MAP[panel.data_source_id || ''] || (feed?.items?.[0]?.url);

  const { setNodeRef, transform, isDragging } = useDraggable({
    id: panel.id,
    data: panel,
  });

  const widthKey = (panel.size as PanelWidth) || '1x1';

  const handleRefresh = async () => {
    if (isRefreshing) return;
    setIsRefreshing(true);
    try {
      const res = await fetch(`http://127.0.0.1:8001/api/v1/admin/trigger/panel/${panel.id}`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error('Sync failed');
    } catch (e) {
      console.error("Refresh failed:", e);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleWidthCycle = () => {
    if (!onWidthToggle) return;
    const idx = SIZE_CYCLE.indexOf(widthKey);
    const next = SIZE_CYCLE[(idx + 1) % SIZE_CYCLE.length];
    onWidthToggle(panel.id, next);
  };

  const style = {
    transform: CSS.Transform.toString(transform),
    opacity: isDragging ? 0.8 : 1,
    cursor: isDragging ? 'grabbing' : 'grab',
    gridColumn: `span ${SIZE_SPAN[widthKey]}`,
    gridRow: `span ${widthKey === '2x2' ? 2 : 1}`,
    zIndex: isDragging ? 100 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="h-full relative group">
      <GlassCard opacity={0.1} className="h-full flex flex-col overflow-visible border-white/5 group-hover:border-white/10 transition-colors">
        {/* Header - Industrial Style */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-white/5">
          <div className="flex items-center gap-2">
            <div {...dragAttributes} {...dragListeners} className="cursor-grab active:cursor-grabbing text-white/20 hover:text-white/60 transition-colors">
              <GripHorizontal size={14} />
            </div>
            <div className="flex items-center gap-1.5">
               <span className="w-1.5 h-1.5 rounded-full bg-violet-500 shadow-[0_0_8px_rgba(139,92,246,0.6)] animate-pulse" />
               <h3 className="text-[11px] font-black tracking-widest uppercase text-white/80">
                 {panel.title || 'UNNAMED_NODE'}
               </h3>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button 
              onClick={handleRefresh} 
              disabled={isRefreshing}
              className="p-1 hover:bg-white/10 rounded transition-colors group/btn disabled:opacity-20"
              title="同步此面板实时情报"
            >
              <RefreshCw size={12} className={`text-white/30 group-hover/btn:text-white/60 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
            <button onClick={() => setCollapsed(!collapsed)} className="p-1 hover:bg-white/10 rounded transition-colors text-white/30 hover:text-white/60">
              {collapsed ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
            </button>
          </div>
        </div>

        {/* Content */}
        {!collapsed && (
          <div className="flex-1 overflow-y-auto custom-scrollbar bg-black/10">
            {children || (
              <PresentationLayer panel={panel} feed={feed} signals={signals} onOpenReader={onOpenReader} />
            )}
          </div>
        )}

        {/* Footer with telemetry info */}
        {feed && !collapsed && (
          <div className="px-4 py-1.5 border-t border-white/5 text-[9px] font-mono text-white/20 flex justify-between items-center">
            <div className="flex items-center gap-2">
               <span className="text-emerald-500/60 uppercase">Live</span>
               <span>{new Date(feed.fetched_at).toLocaleTimeString()}</span>
            </div>
            <div className="uppercase">Node: {panel.id}</div>
          </div>
        )}
      </GlassCard>
    </div>
  );
}

// ============================================
// Presentation Layer Dispatcher
// ============================================

export function PresentationLayer({ panel, feed, signals = [], onOpenReader }: { panel: PanelType, feed?: any, signals?: any[], onOpenReader?: (item: any) => void }) {
  // 1. 强制拦截：特殊逻辑面板 (即使无信号也展示 Baseline)
  if (panel.id === 'p1') return <PolicyRadarView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p2') return <PriceAdjustmentView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p3') return <GeopoliticsView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p4') return <OTAEvolutionView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p14') return <SupplyChainRiskView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p7') return <CommodityTickerView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p8') return <Tier1RiskView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p9') return <PortLogisticsView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p17') return <SemiconductorShortageView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p18') return <LogisticsCostView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p29') return <BatteryRecycleView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p30') return <RareMetalInventoryView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p31') return <ROROScheduleView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p32') return <ChipCapacityView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p15') return <SpecComparisonView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p16') return <LaunchCountdownView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p25') return <CabinExperienceView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p27') return <LightweightView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p28') return <PatentLayoutView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p24') return <ADLegalView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p5') return <TechRoadmapView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p21') return <CarbonComplianceView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p22') return <EnergyNetworkView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p6') return <ADBenchmarkingView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p26') return <BatteryDensityView panelId={panel.id} signals={signals} />;
  if (panel.id === 'p23') return <ConsumerConfidenceView panelId={panel.id} signals={signals} />;

  // 2. 通用拦截：空数据处理
  const pType = panel.presentation_type || 'ticker';
  if (pType === 'ticker' && (!feed || !feed.items || feed.items.length === 0) && signals.length === 0) {
    return (
      <div className="h-full min-h-[120px] flex items-center justify-center text-white/10 text-[10px] tracking-widest uppercase italic font-medium">
        Waiting for stream...
      </div>
    );
  }

  switch (pType) {
    case 'time-series':
      return <TimeSeriesChart panelId={panel.id} signals={signals} />;
    case 'heatmap':
      return <GridHeatmap panelId={panel.id} signals={signals} />;
    case 'radar':
      return <RadarChart panelId={panel.id} signals={signals} />;
    case 'gauge':
      return <TelemetryGauge panelId={panel.id} signals={signals} />;
    case 'pie':
      return <MarketSharePie panelId={panel.id} signals={signals} />;
    case 'ticker':
    default:
      return <EventTickerContent feed={feed} signals={signals} onOpenReader={onOpenReader} />;
  }
}

// ============================================
// Market Share Pie Component
// ============================================

function MarketSharePie({ panelId, signals = [] }: { panelId: string, signals: any[] }) {
  const [market, setMarket] = useState<'China' | 'Europe' | 'USA' | 'Global'>('Global');
  const [segment, setSegment] = useState<'Overall' | 'SUV' | 'Sedan'>('Overall');

  // 根据筛选条件模拟不同的数据分布
  const getData = () => {
    // 基础权重
    const base = {
      Global: [
        { value: 21.5, name: 'BYD', color: '#10b981' },
        { value: 14.2, name: 'Tesla', color: '#ef4444' },
        { value: 11.8, name: 'Toyota', color: '#3b82f6' },
        { value: 9.4, name: 'VW', color: '#f59e0b' },
        { value: 6.2, name: 'Hyundai', color: '#8b5cf6' },
        { value: 5.8, name: 'Stellantis', color: '#ec4899' },
        { value: 4.5, name: 'GM', color: '#06b6d4' },
        { value: 26.6, name: 'Others', color: '#4b5563' }
      ],
      China: [
        { value: 35.1, name: 'BYD', color: '#10b981' },
        { value: 10.3, name: 'Tesla', color: '#ef4444' },
        { value: 8.5, name: 'Geely', color: '#3b82f6' },
        { value: 7.2, name: 'Aion', color: '#f59e0b' },
        { value: 6.8, name: 'Changan', color: '#8b5cf6' },
        { value: 5.4, name: 'Li Auto', color: '#ec4899' },
        { value: 4.2, name: 'NIO', color: '#06b6d4' },
        { value: 3.8, name: 'Xiaomi', color: '#f97316' },
        { value: 18.7, name: 'Others', color: '#4b5563' }
      ],
      Europe: [
        { value: 22.4, name: 'VW', color: '#f59e0b' },
        { value: 16.2, name: 'Tesla', color: '#ef4444' },
        { value: 10.1, name: 'BMW', color: '#3b82f6' },
        { value: 9.4, name: 'Mercedes', color: '#8b5cf6' },
        { value: 8.2, name: 'Renault', color: '#ec4899' },
        { value: 5.4, name: 'BYD', color: '#10b981' },
        { value: 4.8, name: 'MG', color: '#06b6d4' },
        { value: 23.5, name: 'Others', color: '#4b5563' }
      ],
      USA: [
        { value: 51.1, name: 'Tesla', color: '#ef4444' },
        { value: 9.2, name: 'Ford', color: '#3b82f6' },
        { value: 8.4, name: 'GM', color: '#f59e0b' },
        { value: 5.2, name: 'Hyundai', color: '#10b981' },
        { value: 4.8, name: 'Kia', color: '#8b5cf6' },
        { value: 4.1, name: 'Rivian', color: '#06b6d4' },
        { value: 3.5, name: 'Lucid', color: '#ec4899' },
        { value: 13.7, name: 'Others', color: '#4b5563' }
      ]
    }[market];

    // 如果选了 SUV 或 Sedan，做一点扰动模拟真实感
    const noise = segment === 'Overall' ? 1 : segment === 'SUV' ? 1.1 : 0.9;
    return base.map(d => ({
      ...d,
      value: parseFloat((d.value * (d.name === 'Tesla' && segment === 'Sedan' ? 1.3 : noise)).toFixed(1)),
      itemStyle: { color: d.color }
    }));
  };

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
        radius: ['32%', '55%'], // 半径进一步扩张
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
          length: 4, // 缩短第一段引导线
          length2: 3, // 缩短第二段引导线
          lineStyle: { color: 'rgba(255,255,255,0.1)' }
        },
        emphasis: { label: { show: true, fontSize: 9, fontWeight: 'bold', color: '#fff' } },
        data: getData()
      }
    ]
  };

  return (
    <div className="h-full w-full flex flex-col overflow-hidden">
      {/* 极简筛选器 UI */}
      <div className="flex flex-wrap gap-x-1.5 gap-y-1 px-2 pt-1 border-b border-white/5 pb-1 justify-center bg-white/5">
        <div className="flex gap-1">
          {['CN', 'EU', 'US', 'GL'].map(m => (
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
          {['ALL', 'SUV', 'SED'].map(s => (
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
    </div>
  );
}

// ============================================
// Hardcore Event Ticker Content Component
// ============================================

interface EventTickerContentProps {
  feed: { items: FeedItem[]; data_source_id?: string };
  signals?: any[];
  onOpenReader?: (item: any) => void;
}

export function EventTickerContent({ feed, signals = [], onOpenReader }: EventTickerContentProps) {
  const [expandedIdx, setExpandedIdx] = useState<string | number | null>(null);

  // 合并数据：优先显示结构化信号，后面跟着原始 Feed
  // 为了区分，给 Raw Feed 的 ID 加前缀
  const rawItems = (feed?.items || []).map((item, idx) => ({ ...item, isRaw: true, uniqueId: `raw-${idx}` }));
  const structuredItems = (signals || []).map((sig, idx) => ({ 
    ...sig, 
    // 修正：后端已经把字段名统一为 title 了
    title: sig.title, 
    isRaw: false, 
    uniqueId: `sig-${sig.id || idx}`,
    published_at: sig.created_at 
  }));

  const allItems = [...structuredItems, ...rawItems].sort((a, b) => {
    const ta = a.published_at ? new Date(a.published_at).getTime() : 0;
    const tb = b.published_at ? new Date(b.published_at).getTime() : 0;
    return tb - ta;
  });

  return (
    <div className="flex flex-col">
      {allItems.length === 0 && (
        <div className="p-8 text-center text-white/20 text-[10px] uppercase tracking-widest italic">Standby...</div>
      )}
      {allItems.slice(0, 20).map((item: any, i) => {
        const isExpanded = expandedIdx === item.uniqueId;
        const score = item.impact_score || 50;

        return (
          <div key={item.uniqueId} className={`group/item border-b border-white/5 hover:bg-white/[0.02] transition-colors relative ${!item.isRaw ? 'bg-violet-500/[0.03]' : ''}`}>
            {/* Impact Bar */}
            <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-white/5 overflow-hidden">
               <div 
                 className={`w-full transition-all duration-1000 ${
                   score > 80 ? 'bg-rose-500' : score > 50 ? 'bg-amber-500' : 'bg-emerald-500'
                 }`} 
                 style={{ height: `${score}%` }}
               />
            </div>

            <div className="pl-4 pr-3 py-2.5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[8px] font-black px-1 rounded uppercase tracking-tighter ${item.isRaw ? 'bg-white/5 text-white/30' : 'bg-violet-500 text-white shadow-sm'}`}>
                      {item.isRaw ? 'RAW_FEED' : 'AI_SIGNAL'}
                    </span>
                    <span className="text-[9px] font-mono text-white/30 uppercase">
                      {item.source_name || 'UNKNOWN_SRC'} • {item.published_at ? new Date(item.published_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'NOW'}
                    </span>
                  </div>
                  <h4 
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onOpenReader) onOpenReader(item);
                    }}
                    className={`text-[12px] font-bold leading-tight mb-1.5 cursor-pointer transition-colors hover:underline flex items-center gap-1.5 ${isExpanded ? 'text-violet-400' : 'text-white/80 group-hover/item:text-white'}`}
                  >
                    {item.title}
                    <ExternalLink size={10} className="opacity-0 group-hover/item:opacity-40 transition-opacity" />
                  </h4>
                  
                  <div 
                    onClick={() => setExpandedIdx(isExpanded ? null : item.uniqueId)}
                    className="cursor-pointer"
                  >
                    {!isExpanded && !item.isRaw && (
                      <div className="flex gap-1 flex-wrap mt-1">
                        {Array.isArray(item.summary) && item.summary.slice(0, 2).map((s: string, idx: number) => (
                          <span key={idx} className="text-[9px] text-violet-300/60 italic leading-none"># {s}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="text-[10px] font-black font-mono text-white/40 pt-0.5">
                  {score}<span className="text-[8px] opacity-30">/100</span>
                </div>
              </div>

              {/* AI Insight Details (For signals) */}
              {isExpanded && !item.isRaw && (
                <div className="mt-3 p-3 rounded bg-violet-500/5 border border-violet-500/20 animate-in fade-in slide-in-from-top-2 duration-300">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Database size={10} className="text-white/40" />
                      <span className="text-[9px] font-mono text-white/40 uppercase tracking-tighter">Node: {item.source_name}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Sparkles size={12} className="text-violet-400" />
                      <span className="text-[10px] font-bold uppercase tracking-widest text-violet-400/80">AI Insight Engine</span>
                    </div>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${item.sentiment > 0 ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                      {item.sentiment > 0 ? 'POSITIVE' : 'NEGATIVE'} ({(item.sentiment * 100).toFixed(0)}%)
                    </span>
                  </div>
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2 border-t border-white/5 pt-2">
                       {item.involved_entities?.map((e: string) => (
                         <div key={e} className="text-[10px] text-white/60 flex items-center gap-1">
                            <div className="w-1 h-1 rounded-full bg-violet-500" /> {e}
                         </div>
                       ))}
                    </div>
                    <ul className="space-y-1 mt-2">
                      {item.summary?.map((s: string, idx: number) => (
                        <li key={idx} className="text-[11px] text-white/80 leading-relaxed flex gap-2">
                           <span className="text-violet-500">•</span> {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}