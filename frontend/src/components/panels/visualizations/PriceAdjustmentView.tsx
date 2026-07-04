import React from 'react';
import { motion } from 'framer-motion';
import { TrendingDown, TrendingUp, AlertCircle, Calendar, Tag, Database, Activity } from 'lucide-react';

interface PriceAlert {
	model: string;
	brand: string;
	oldPrice: string;
	newPrice: string;
	change: string;
	type: string;
	date: string;
	trend: string;
}

export const PriceAdjustmentView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
	// 1. 过滤属于 p2 的实时信号
	const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

	// 2. 数据解析
	const displayData: PriceAlert[] = activeSignals.map(s => {
		const metrics = s.metrics || {};
		return {
			model: metrics.model || s.title_brief || '未知车型',
			brand: metrics.brand || '未知品牌',
			oldPrice: metrics.old_price || '0.00',
			newPrice: metrics.new_price || '0.00',
			change: metrics.change || (s.sentiment < 0 ? '-??' : '+??'),
			type: metrics.type || 'Official',
			date: s.created_at ? new Date(s.created_at).toLocaleDateString() : 'Realtime',
			trend: metrics.trend || (s.trend === 'DOWN' ? 'DOWN' : 'UP')
		};
	});

	// 3. 空状态/调试 UI
	if (displayData.length === 0) {
		return (
			<div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
				<Activity size={24} className="text-emerald-500/40 mb-2 animate-pulse" />
				<span className="text-[10px] font-black text-emerald-400/60 uppercase tracking-widest">Price War Engine Idle</span>
				<div className="mt-4 w-full space-y-1">
					<div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
						<span>Module</span>
						<span className="text-white/40">PRICING_RADAR</span>
					</div>
					<div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
						<span>Query_ID</span>
						<span className="text-white/40">{panelId}</span>
					</div>
					<div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
						<span>Records</span>
						<span className="text-rose-500/60 font-black">NULL_SET</span>
					</div>
				</div>
				<p className="mt-4 text-[7px] text-white/30 text-center leading-tight">
					系统正在监控全球 OEM 官网调价动态。<br />
					尚未捕获到 24H 内的结构化调价信号。
				</p>
			</div>
		);
	}

	return (
		<div className="h-full w-full flex flex-col p-2 bg-black/40 rounded-lg border border-white/5 space-y-2 overflow-y-auto no-scrollbar">
			<div className="flex justify-between items-center mb-1">
				<span className="text-[7px] font-mono text-white/20 uppercase tracking-tighter flex items-center gap-1">
					Last Sync: {new Date().toLocaleTimeString()}
				</span>
				<span className="text-[7px] text-white/20 uppercase font-black">24H Active Scan</span>
			</div>

			<div className="flex-1 space-y-2">
				{displayData.map((alert, idx) => {
					const isDrop = alert.change.startsWith('-');
					return (
						<motion.div
							key={`${alert.model}-${idx}`}
							initial={{ opacity: 0, y: 10 }}
							animate={{ opacity: 1, y: 0 }}
							transition={{ delay: idx * 0.1 }}
							className="bg-white/5 border border-white/5 rounded p-2 relative group"
						>
							<div className="flex justify-between items-start">
								<div className="flex flex-col">
									<span className="text-[6px] text-white/30 uppercase font-bold tracking-tighter">{alert.brand}</span>
									<h4 className="text-[9px] font-black text-white">{alert.model}</h4>
								</div>
								<div className={`px-1 rounded-sm text-[7px] font-black border ${alert.type === 'Official' ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/5' : 'border-blue-500/30 text-blue-400 bg-blue-500/5'
									}`}>
									{alert.type.toUpperCase()}
								</div>
							</div>

							<div className="mt-2 flex justify-between items-center">
								<div className="flex items-center gap-2">
									<div className="flex flex-col">
										<span className="text-[6px] text-white/20 uppercase font-bold">MSRP</span>
										<span className="text-[9px] text-white/40 line-through">{alert.oldPrice}</span>
									</div>
									<ArrowRightIcon className="text-white/10" />
									<div className="flex flex-col">
										<span className="text-[6px] text-white/20 uppercase font-bold">Now</span>
										<span className="text-[11px] font-black text-white">{alert.newPrice}</span>
									</div>
								</div>
								<div className={`flex flex-col items-end ${alert.trend === 'DOWN' ? 'text-emerald-400' : 'text-rose-400'}`}>
									<div className="flex items-center gap-0.5">
										{alert.trend === 'DOWN' ? <TrendingDown size={10} /> : <TrendingUp size={10} />}
										<span className="text-[12px] font-black">{alert.change}</span>
									</div>
									<span className="text-[6px] uppercase font-bold opacity-40">Adjusted</span>
								</div>
							</div>

							<div className="mt-2 pt-1 border-t border-white/5 flex justify-between items-center">
								<div className="flex items-center gap-1">
									<Calendar size={8} className="text-white/20" />
									<span className="text-[6px] text-white/20 font-mono">{alert.date}</span>
								</div>
								<Tag size={8} className="text-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
							</div>
						</motion.div>
					);
				})}
			</div>
		</div>
	);
};

const ArrowRightIcon = ({ className }: { className?: string }) => (
	<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className={className}>
		<path d="M5 12h14M12 5l7 7-7 7" />
	</svg>
);
