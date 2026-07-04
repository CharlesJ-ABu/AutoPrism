import React from 'react';
import ReactECharts from 'echarts-for-react';
import { MessageSquare, Star, Database, Search, Activity } from 'lucide-react';

export const CabinExperienceView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
	// 1. 过滤实时信号
	const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

	// 2. 转换逻辑
	const brandColors: Record<string, string> = {
		'Xiaomi': '#ff6700',
		'Huawei': '#ef4444',
		'NIO': '#00e5ff',
		'Tesla': '#ffffff',
		'Xpeng': '#5de2ff',
		'Zeekr': '#f0f0f0',
		'Li Auto': '#00ad9b',
		'BYD': '#ff1100'
	};

	const systems = activeSignals.map((s, idx) => {
		const metrics = s.metrics || {};
		const name = metrics.brand || s.involved_entities?.[0] || `OS_${idx}`;
		// 生成不重复颜色的 fallback
		const fallbackColor = `hsl(${(idx * 137) % 360}, 70%, 60%)`;
		return {
			name,
			color: brandColors[name] || fallbackColor,
			data: [
				metrics.ai || 50,         // AI 助手
				metrics.fluidity || 50,   // 流畅度
				metrics.ecosystem || 50,  // 生态融合
				metrics.multimodal || 50, // 多模态感知
				metrics.audio || 50,      // 视听沉浸
				metrics.connectivity || 50 // 互联互通
			],
			quote: metrics.quote || s.title_brief || '评价正在生成中'
		};
	});

	// 3. 轮播逻辑
	const [currentIndex, setCurrentIndex] = React.useState(0);
	React.useEffect(() => {
		if (systems.length <= 1) return;
		const timer = setInterval(() => {
			setCurrentIndex(prev => (prev + 1) % systems.length);
		}, 4000);
		return () => clearInterval(timer);
	}, [systems.length]);

	// 4. 空状态/调试 UI
	if (systems.length === 0) {
		// ... (保持原样)
		return (
			<div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
				<Activity size={24} className="text-purple-500/40 mb-2 animate-pulse" />
				<span className="text-[10px] font-black text-purple-400/60 uppercase tracking-widest text-center">Cabin UX Stream Empty</span>
				<div className="mt-4 w-full space-y-1">
					<div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
						<span>Query_Panel</span>
						<span className="text-white/40">{panelId}</span>
					</div>
					<div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
						<span>Metric_Set</span>
						<span className="text-white/40">UX_SIX_DIMENSION</span>
					</div>
					<div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
						<span>Signals</span>
						<span className="text-rose-500/60 font-black">WAITING_FOR_INGEST</span>
					</div>
				</div>
				<div className="mt-6 flex flex-col items-center gap-1 opacity-20">
					<Search size={10} />
					<span className="text-[6px] font-black text-white uppercase text-center leading-tight">
						等待 SpecializedScraper.fetch_cabin_experience() <br /> 获取最新的智能座舱实测或用户口碑评价。
					</span>
				</div>
			</div>
		);
	}

	const option = {
		backgroundColor: 'transparent',
		color: systems.map(s => s.color),
		radar: {
			radius: '50%',
			center: ['50%', '43%'], // 进一步上移中心点
			indicator: [
				{ name: 'AI 助手', max: 100 },
				{ name: '流畅度', max: 100 },
				{ name: '生态融合', max: 100 },
				{ name: '多模态感知', max: 100 },
				{ name: '视听沉浸', max: 100 },
				{ name: '互联互通', max: 100 }
			],
			axisName: {
				color: 'rgba(255,255,255,0.4)',
				fontSize: 7,
				fontWeight: 'bold',
				padding: [-5, -5] // 负 padding 让标签离图表更近
			},
			shape: 'polygon',
			splitNumber: 4,
			splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } },
			splitArea: { areaStyle: { color: ['rgba(255,255,255,0.01)', 'transparent'] } },
			axisLine: { lineStyle: { color: 'rgba(255,255,255,0.1)' } }
		},
		legend: {
			show: true,
			data: systems.map(s => s.name),
			bottom: -5, // 彻底下沉
			itemWidth: 8,
			itemHeight: 2,
			textStyle: { color: 'rgba(255,255,255,0.3)', fontSize: 7 },
			icon: 'rect'
		},
		series: [
			{
				type: 'radar',
				symbol: 'none',
				lineStyle: { width: 1.5, opacity: 0.8 },
				data: systems.map(s => ({
					value: s.data,
					name: s.name,
					areaStyle: { color: s.color, opacity: 0.05 },
					itemStyle: { color: s.color }
				}))
			}
		]
	};

	return (
		<div className="h-full w-full flex flex-col p-2 bg-black/40 rounded-lg border border-white/5 space-y-2 overflow-hidden">
			<div className="flex justify-between items-center mb-1">
				<span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
					Last Sync: {new Date().toLocaleTimeString()}
				</span>
				<span className="text-[7px] text-emerald-400 font-black uppercase tracking-widest">Active UX Analysis</span>
			</div>

			<div className="flex-1 min-h-0 relative">
				<ReactECharts option={option} style={{ height: '120%', width: '100%', marginTop: '-10%' }} notMerge={true} />
			</div>

			<div className="h-10 relative overflow-hidden bg-white/5 rounded border-l-2" style={{ borderLeftColor: systems[currentIndex]?.color }}>
				<div
					className="absolute inset-0 p-1.5 flex flex-col justify-center transition-all duration-700 ease-in-out"
					key={currentIndex}
					style={{ animation: 'slideUp 0.7s ease-out' }}
				>
					<div className="flex items-center justify-between mb-0.5">
						<span className="text-[7px] font-black text-white/40 uppercase tracking-tighter">{systems[currentIndex]?.name}</span>
						<div className="w-1 h-1 rounded-full animate-pulse" style={{ backgroundColor: systems[currentIndex]?.color }} />
					</div>
					<div className="flex items-center gap-1.5">
						<MessageSquare size={8} className="text-amber-400/60" />
						<span className="text-[9px] text-white/90 font-medium italic truncate">"{systems[currentIndex]?.quote}"</span>
					</div>
				</div>
				<style>{`
           @keyframes slideUp {
             from { transform: translateY(20px); opacity: 0; }
             to { transform: translateY(0); opacity: 1; }
           }
         `}</style>
			</div>
		</div>
	);
};
