import React from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, Ship, Factory, Truck, Clock, AlertCircle, Database, Search } from 'lucide-react';

interface Disruption {
	id: string;
	title: string;
	category: 'Logistics' | 'Material' | 'Production';
	status: 'CRITICAL' | 'WARNING' | 'STABLE';
	impact: string;
	delay: string;
	location: string;
}

export const SupplyChainRiskView: React.FC<{ panelId: string; signals?: any[] }> = ({ panelId, signals = [] }) => {
	// 1. 过滤实时信号
	const activeSignals = signals?.filter(s => s.target_panel_ids?.includes(panelId)) || [];

	// 2. 转换逻辑
	const displayRisks: Disruption[] = activeSignals.map((s, idx) => {
		const metrics = s.metrics || {};
		const impact = s.impact_score || 50;
		return {
			id: s.id || `risk-${idx}`,
			title: metrics.title_brief || metrics.title,
			category: (metrics.category || 'Logistics') as any,
			status: impact > 80 ? 'CRITICAL' : impact > 40 ? 'WARNING' : 'STABLE',
			impact: metrics.impact || '正在评估断链对产能的影响',
			delay: metrics.delay || '估算中',
			location: s.geolocation?.name || metrics.location || 'Global'
		};
	});

	const getStatusStyles = (status: string) => {
		switch (status) {
			case 'CRITICAL': return 'bg-rose-500/10 border-rose-500/40 text-rose-400';
			case 'WARNING': return 'bg-amber-500/10 border-amber-500/40 text-amber-400';
			default: return 'bg-blue-500/10 border-blue-500/40 text-blue-400';
		}
	};

	const getCategoryIcon = (category: string) => {
		switch (category) {
			case 'Logistics': return <Ship size={12} className="text-blue-400" />;
			case 'Material': return <Factory size={12} className="text-purple-400" />;
			default: return <Truck size={12} className="text-amber-400" />;
		}
	};

	// 3. 空状态/调试 UI
	if (displayRisks.length === 0) {
		return (
			<div className="h-full w-full flex flex-col items-center justify-center p-4 bg-black/60 rounded-lg border border-dashed border-white/10">
				<ShieldAlert size={24} className="text-emerald-500/40 mb-2 animate-pulse" />
				<span className="text-[10px] font-black text-emerald-400/60 uppercase tracking-widest text-center">Supply Chain Quiet</span>
				<div className="mt-4 w-full space-y-1">
					<div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
						<span>Module</span>
						<span className="text-white/40">DISRUPTION_MONITOR</span>
					</div>
					<div className="flex justify-between text-[7px] text-white/20 uppercase font-mono border-b border-white/5 pb-1">
						<span>Panel_ID</span>
						<span className="text-white/40">{panelId}</span>
					</div>
					<div className="flex justify-between text-[7px] text-white/20 uppercase font-mono">
						<span>Intelligence</span>
						<span className="text-rose-500/60 font-black">STABLE_FLOW</span>
					</div>
				</div>
				<div className="mt-6 flex flex-col items-center gap-1 opacity-20">
					<Database size={10} />
					<span className="text-[6px] font-black text-white uppercase text-center leading-tight">
						目前尚未检测到重大海运阻塞、<br />罢工或原材料断供预警。
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
					<span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
					<span className="text-[7px] text-white/30 uppercase font-black tracking-widest text-center">24H Risk Monitor</span>
				</div>
			</div>

			<div className="flex-1 space-y-2">
				{displayRisks.map((risk, idx) => (
					<motion.div
						key={`${risk.id}-${idx}`}
						initial={{ opacity: 0, scale: 0.95 }}
						animate={{ opacity: 1, scale: 1 }}
						transition={{ delay: idx * 0.1 }}
						className={`border rounded p-2 relative overflow-hidden transition-all hover:scale-[1.02] ${getStatusStyles(risk.status)}`}
					>
						<div className="flex justify-between items-start mb-1.5">
							<div className="flex items-center gap-1.5">
								{getCategoryIcon(risk.category)}
								<h4 className="text-[10px] font-black uppercase tracking-tight">{risk.title}</h4>
							</div>
							<span className="text-[7px] font-black uppercase bg-white/10 px-1 rounded-sm">
								{risk.location}
							</span>
						</div>

						<p className="text-[9px] font-medium opacity-80 leading-snug mb-2">
							{risk.impact}
						</p>

						<div className="flex justify-between items-end border-t border-white/5 pt-1.5">
							<div className="flex items-center gap-1">
								<Clock size={10} className="opacity-40" />
								<span className="text-[10px] font-black font-mono">{risk.delay}</span>
							</div>
							<div className="flex items-center gap-1">
								<AlertCircle size={8} className="opacity-40" />
								<span className="text-[6px] uppercase font-bold tracking-tighter opacity-60">Impact: {risk.status}</span>
							</div>
						</div>

						<div className="absolute -right-2 -bottom-2 opacity-[0.03] pointer-events-none">
							{getCategoryIcon(risk.category)}
						</div>
					</motion.div>
				))}
			</div>

			<div className="pt-1 mt-auto flex justify-between items-center opacity-30 border-t border-white/5">
				<span className="text-[6px] uppercase font-bold tracking-tighter text-rose-500 font-black italic underline">Disruption Pulse Scan Active</span>
			</div>
		</div>
	);
};
