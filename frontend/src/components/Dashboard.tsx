import React, { useState, useEffect } from 'react';
import { Plus, Layers, Settings, Database, Cpu, Play, Zap, X, Clock, Calendar, MousePointer2, Loader2, Info, AlertCircle, CheckCircle2 } from 'lucide-react';
import { GlassCard, Button } from '@/components/ui';
import { GlobeMap } from '@/components/maps/GlobeMap';
import { DeckGLMap } from '@/components/maps/DeckGLMap';
import { usePanelsStore, useFeedStore, useSignalStore } from '@/stores';
import { Panel } from '@/components/panels/Panel';
import { SettingsModal } from '@/components/panels/SettingsModal';
import { IntelligenceReader } from '@/components/panels/IntelligenceReader';
import { InsightsStream } from '@/components/panels/InsightsStream';

const Dashboard: React.FC = () => {
	const [mapMode, setMapMode] = useState<'globe' | 'deckgl'>('globe');
	const [mapStyle, setMapStyle] = useState<'industrial' | 'cyber' | 'ghost'>('cyber');
	const [activeRole, setActiveRole] = useState('全量情报');
	const [selectedIntel, setSelectedIntel] = useState<any | null>(null);
	const [isSettingsOpen, setIsSettingsOpen] = useState(false);
	const [logs, setLogs] = useState<{ msg: string, time: string, level: string }[]>([]);
	const [isConsoleOpen, setIsConsoleOpen] = useState(true);
	const [notifications, setNotifications] = useState<{ id: number, msg: string, type: 'info' | 'error' | 'success' }[]>([]);
	const [taskProgress, setTaskProgress] = useState<Record<string, { progress: number, message: string }>>({});

	const [schedConfig, setSchedConfig] = useState({
		crawlerMode: 'manual' as const,
		crawlerValue: '08:00',
		aiMode: 'manual' as const,
		aiValue: '30',
		aiBatchSize: 50
	});

	const logRef = React.useRef<HTMLDivElement>(null);

	useEffect(() => {
		if (logRef.current) {
			logRef.current.scrollTop = logRef.current.scrollHeight;
		}
	}, [logs, taskProgress, isConsoleOpen]);

	const { panels, loadPanels, refreshSource, isLoading: isPanelsLoading } = usePanelsStore();
	const { feeds, loadFeed, isLoading: isFeedsLoading } = useFeedStore();
	const { signals, loadSignals } = useSignalStore();
	const [insights, setInsights] = useState<any[]>([]);
	const [isInsightLoading, setIsInsightLoading] = useState(false);

	const loadL2Insights = async (role: string) => {
		setIsInsightLoading(true);
		try {
			const res = await fetch(`http://127.0.0.1:8001/api/v1/ai/insights?role=${encodeURIComponent(role)}`);
			if (res.ok) {
				const data = await res.json();
				setInsights(data);
			}
		} catch (e) {
			console.error("L2 Insights load failed", e);
		} finally {
			setIsInsightLoading(false);
		}
	};

	useEffect(() => {
		loadL2Insights(activeRole);
	}, [activeRole]);

	const addNotify = (msg: string, type: 'info' | 'error' | 'success' = 'info') => {
		const id = Date.now();
		setNotifications(prev => [...prev, { id, msg, type }]);
		setLogs(prev => [...prev.slice(-49), {
			msg, time: new Date().toLocaleTimeString(), level: type === 'error' ? 'error' : 'success'
		}]);
		setTimeout(() => {
			setNotifications(prev => prev.filter(n => n.id !== id));
		}, 5000);
	};

	useEffect(() => {
		const init = async () => {
			await loadPanels();
			await loadFeed();
			await loadSignals();
		};
		init();

		const userId = "admin";
		const ws = new WebSocket(`ws://127.0.0.1:8001/ws/${userId}`);
		ws.onmessage = (event) => {
			const data = JSON.parse(event.data);
			if (data.type === 'log') {
				setLogs(prev => [...prev.slice(-49), {
					msg: data.message, time: new Date().toLocaleTimeString(), level: data.level
				}]);
			} else if (data.type === 'progress') {
				setTaskProgress(prev => ({
					...prev,
					[data.task]: { progress: data.progress, message: data.message }
				}));
				if (data.progress === 100) {
					setTimeout(() => {
						setTaskProgress(prev => {
							const next = { ...prev };
							delete next[data.task];
							return next;
						});
					}, 5000);
				}
			}
		};
		const interval = setInterval(loadSignals, 10000);
		return () => { clearInterval(interval); ws.close(); };
	}, []);

	const handleManualTrigger = async (engine: 'crawler' | 'ai') => {
		console.log(`[Dashboard] Triggering ${engine}...`);
		try {
			let endpoint = engine === 'crawler' ? '/admin/trigger/fetch' : '/admin/trigger/ai';
			let method = 'POST';
			let body: string | null = null;

			if (engine === 'ai') {
				endpoint = '/ai/denoise';
				body = JSON.stringify({ role: activeRole });
				console.log(`[Dashboard] Role: ${activeRole}, Payload: ${body}`);
			}

			const baseUrl = 'http://127.0.0.1:8001/api/v1';
			console.log(`[Dashboard] Fetching: ${baseUrl}${endpoint}`);

			const response = await fetch(`${baseUrl}${endpoint}`, {
				method,
				headers: body ? { 'Content-Type': 'application/json' } : {},
				body
			});

			if (response.ok) {
				console.log(`[Dashboard] ${engine} trigger success`);
				addNotify(`${engine === 'crawler' ? '情报抓取' : 'AI 战略洞察合成'}流程已启动，系统正在响应...`, 'success');
				if (engine === 'ai') {
					setTimeout(() => {
						console.log("[Dashboard] Refreshing L2 insights...");
						loadL2Insights(activeRole);
					}, 5000);
				} else {
					setTimeout(loadFeed, 3000);
				}
			} else {
				console.error(`[Dashboard] ${engine} trigger failed:`, response.status);
				addNotify('触发指令失败：服务器响应异常', 'error');
			}
		} catch (error) {
			console.error(`[Dashboard] ${engine} connection error:`, error);
			addNotify('指令下达失败：无法连接至后端节点', 'error');
		}
	};

	const getFreqLabel = (mode: string, value: string) => {
		if (mode === 'manual') return '纯手动模式';
		if (mode === 'daily') return `每日 ${value}`;
		return `每 ${value} 分钟`;
	};

	const roles = ['全量情报', '宏观决策', '战略与产品', '供应链与采购'];
	const visiblePanels = (panels || []).filter(p => activeRole === '全量情报' || p.role === activeRole);

	const getFeedForPanel = (panelId: string, sourceId?: string) => {
		if (sourceId && feeds.has(sourceId)) return feeds.get(sourceId);
		const allFeeds = Array.from(feeds.values());
		if (allFeeds.length > 0) return allFeeds[0];
		return { items: [], data_source_id: '', fetched_at: '' };
	};

	const containerClass = "w-full max-w-[1700px] mx-auto px-6";

	return (
		<div className="relative min-h-screen bg-[#0F0F23] text-white flex flex-col items-center">

			{/* Toast Notification Container */}
			<div className="fixed top-24 left-6 z-[100] flex flex-col gap-3 pointer-events-none">
				{notifications.map(n => (
					<div key={n.id} className="pointer-events-auto animate-in slide-in-from-left duration-300">
						<GlassCard opacity={0.2} className={`px-4 py-3 border-l-4 min-w-[300px] shadow-2xl ${n.type === 'error' ? 'border-rose-500' : n.type === 'success' ? 'border-emerald-500' : 'border-violet-500'
							}`}>
							<div className="flex items-center gap-3">
								{n.type === 'error' ? <AlertCircle size={18} className="text-rose-500" /> :
									n.type === 'success' ? <CheckCircle2 size={18} className="text-emerald-500" /> :
										<Info size={18} className="text-violet-500" />}
								<div className="flex flex-col">
									<span className="text-[10px] font-black uppercase tracking-widest opacity-40">System Notification</span>
									<span className="text-xs font-bold text-white/90">{n.msg}</span>
								</div>
							</div>
						</GlassCard>
					</div>
				))}
			</div>

			{/* Navbar Container */}
			<div className="fixed top-0 left-0 right-0 z-50 pt-6">
				<div className={containerClass}>
					<GlassCard opacity={0.15} className="px-6 py-2 flex items-center justify-between border-white/10 shadow-xl">
						<div className="flex items-center gap-3">
							<div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-fuchsia-500 rounded-lg flex items-center justify-center">
								<Layers size={18} className="text-white" />
							</div>
							<h1 className="text-xl font-bold tracking-tight">AutoPrism</h1>
						</div>

						<div className="flex items-center gap-6 bg-white/5 px-6 py-1.5 rounded-full border border-white/10">
							<div className="flex items-center gap-1">
								{roles.map(role => (
									<button
										key={role}
										onClick={() => setActiveRole(role)}
										className={`px-4 py-1 rounded-full text-[10px] font-bold uppercase transition-all ${activeRole === role ? 'bg-violet-500 text-white shadow-lg shadow-violet-500/20' : 'text-white/30 hover:text-white'
											}`}
									>
										{role}
									</button>
								))}
							</div>
							<div className="h-4 w-[1px] bg-white/10 mx-2" />
							<div className="flex items-center gap-6">
								<div className="flex items-center gap-4">
									<div className="flex flex-col text-right">
										<span className="text-[8px] text-white/30 tracking-widest uppercase font-bold">Crawler</span>
										<span className="text-[9px] font-medium text-emerald-400">{getFreqLabel(schedConfig.crawlerMode, schedConfig.crawlerValue)}</span>
									</div>
									<button onClick={() => handleManualTrigger('crawler')} className="p-1.5 bg-emerald-500/10 text-emerald-400 rounded-md border border-emerald-500/20 hover:bg-emerald-500/20 transition-all"><Play size={10} fill="currentColor" /></button>
								</div>
								<div className="flex items-center gap-4">
									<div className="flex flex-col text-right">
										<span className="text-[8px] text-white/30 tracking-widest uppercase font-bold">AI Denoise</span>
										<span className="text-[9px] font-medium text-violet-400">{getFreqLabel(schedConfig.aiMode, schedConfig.aiValue)}</span>
									</div>
									<button
										onClick={() => {
											console.log("AI Denoise button clicked!");
											handleManualTrigger('ai');
										}}
										className="p-1.5 bg-violet-500/20 text-violet-400 rounded-md border border-violet-500/40 hover:bg-violet-500/40 transition-all relative z-[100] cursor-pointer pointer-events-auto"
									>
										<Zap size={10} fill="currentColor" />
									</button>
								</div>
							</div>
						</div>

						<div className="flex items-center gap-4">
							<button onClick={() => setIsSettingsOpen(true)} className="p-2 rounded-lg bg-white/5 text-white/40 hover:text-white transition-all"><Settings size={18} /></button>
							<div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-600 to-indigo-700 flex items-center justify-center text-xs font-bold shadow-lg border border-white/10">AD</div>
						</div>
					</GlassCard>
				</div>
			</div>

			{/* Main Content Area */}
			<div className="pt-28 pb-12 w-full flex flex-col items-center gap-8">
				<div className={containerClass}>
					{/* Row 1: Globe Panel */}
					<div className="h-[550px] w-full mb-8">
						<GlassCard className="w-full h-full p-0 overflow-hidden relative border-white/10 shadow-[0_0_50px_rgba(139,92,246,0.1)]">
							<div className="absolute top-4 right-4 z-20 flex gap-2">
								<div className="flex bg-white/5 rounded-lg p-1 border border-white/10 mr-4">
									{['industrial', 'cyber', 'ghost'].map(s => (
										<button
											key={s}
											onClick={() => setMapStyle(s as any)}
											className={`px-3 py-1 rounded-md text-[9px] font-black uppercase transition-all ${mapStyle === s ? 'bg-white/10 text-white' : 'text-white/20 hover:text-white/40'}`}
										>
											{s}
										</button>
									))}
								</div>
								<Button variant={mapMode === 'globe' ? 'primary' : 'ghost'} size="sm" onClick={() => setMapMode('globe')}>3D GLOBE</Button>
								<Button variant={mapMode === 'deckgl' ? 'primary' : 'ghost'} size="sm" onClick={() => setMapMode('deckgl')}>2D TACTICAL</Button>
							</div>
							<div className="w-full flex-1 min-h-0">
								{mapMode === 'globe' ? (
									<GlobeMap
										data={insights.map((s, idx) => {
											// 基于 L2 结构的映射
											return {
												lat: s.geo_coordinates?.lat || 0,
												lng: s.geo_coordinates?.lng || 0,
												size: (s.priority || 2) * 0.2, // 根据优先级决定高度
												color: s.sentiment > 0 ? '#10b981' : s.sentiment < 0 ? '#ef4444' : '#f59e0b',
												name: s.title,
												display_type: s.display_type,
												geo_coordinates: s.geo_coordinates
											};
										})}
										styleMode={mapStyle}
										onSelect={(name) => {
											const insight = insights.find(s => s.title === name);
											if (insight) setSelectedIntel({
												...insight,
												title_brief: insight.title,
												content: insight.summary,
												// 适配 IntelligenceReader 的展示逻辑
												metrics: insight.analysis,
												reasoning: insight.strategic_advice
											});
										}}
									/>
								) : (
									<DeckGLMap
										data={insights.map((s, idx) => {
											return {
												position: [s.geo_coordinates?.lng || 0, s.geo_coordinates?.lat || 0],
												size: (s.priority || 2) * 20,
												color: s.sentiment > 0 ? [16, 185, 129] : s.sentiment < 0 ? [239, 68, 68] : [245, 158, 11],
												name: s.title,
                        display_type: s.display_type,
                        geo_coordinates: s.geo_coordinates
											};
										})}
										styleMode={mapStyle}
										onSelect={(name) => {
											const insight = insights.find(s => s.title === name);
											if (insight) setSelectedIntel({
												...insight,
												title_brief: insight.title,
												content: insight.summary,
												metrics: insight.analysis,
												reasoning: insight.strategic_advice
											});
										}}
									/>
								)}
							</div>
						</GlassCard>
					</div>

					{/* Row 2: AI 实时情报洞察流 - 独立全宽层级 */}
					<div className="w-full mb-8">
						<div className="flex items-center gap-3 mb-4 px-1">
							<div className="w-1 h-4 bg-violet-500 rounded-full" />
							<h3 className="text-xs font-black text-white/40 uppercase tracking-[0.2em]">实时战略洞察系统</h3>
							<div className="flex-1 h-px bg-gradient-to-r from-white/10 to-transparent" />
						</div>
						<InsightsStream 
							insights={insights} 
							onSelect={(name) => {
								const insight = insights.find(s => s.title === name);
								if (insight) setSelectedIntel({
									...insight,
									title_brief: insight.title,
									content: insight.summary,
									metrics: insight.analysis,
									reasoning: insight.strategic_advice
								});
							}} 
						/>
					</div>

					{/* Row 3: Intelligence Panels Grid */}
					<div className="w-full">
						{(isPanelsLoading || isFeedsLoading) ? (
							<div className="w-full h-40 flex items-center justify-center">
								<Loader2 size={32} className="text-violet-500 animate-spin" />
							</div>
						) : visiblePanels.length > 0 ? (
							<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 auto-rows-[250px]">
								{visiblePanels.map(panel => {
									// 增加安全过滤，防止 target_panel_ids 为空导致崩溃
									const panelSignals = (signals || []).filter(s =>
										s.target_panel_ids && Array.isArray(s.target_panel_ids) && s.target_panel_ids.includes(panel.id)
									);
									return (
										<div key={panel.id} className={`${panel.size === '2x1' ? 'lg:col-span-2' : panel.size === '2x2' ? 'lg:col-span-2 lg:row-span-2' : ''} h-full`}>
											<Panel
												panel={panel}
												signals={panelSignals}
												onRefresh={refreshSource}
												onOpenReader={(item) => setSelectedIntel(item)}
											/>
										</div>
									);
								})}
							</div>
						) : (
							<GlassCard className="p-24 flex flex-col items-center justify-center text-white/10 border-dashed border-white/5 rounded-3xl">
								<Database size={48} className="mb-4 opacity-20" />
								<div className="text-sm font-bold tracking-widest uppercase">视角: {activeRole}</div>
								<div className="text-[10px] mt-2 opacity-40 italic">等待情报看板数据接入...</div>
							</GlassCard>
						)}
					</div>
				</div>
			</div>

			{/* Console Overlay - Hardcore Progress Support */}
			<div className={`fixed bottom-6 right-[74px] z-[60] transition-all duration-300 ${isConsoleOpen ? 'w-[400px] h-[320px]' : 'w-64 h-10'}`}>
				<GlassCard className="w-full h-full flex flex-col overflow-hidden border-white/10 shadow-2xl">
					<div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/5 cursor-pointer shrink-0" onClick={() => setIsConsoleOpen(!isConsoleOpen)}>
						<div className="flex items-center gap-2">
							<div className={`w-1.5 h-1.5 rounded-full ${isConsoleOpen ? 'bg-emerald-500 animate-pulse' : 'bg-white/20'}`} />
							<span className="text-[10px] font-bold tracking-widest uppercase opacity-60">System Console</span>
						</div>
						<span className="text-[10px] opacity-40">{isConsoleOpen ? 'COLLAPSE' : 'EXPAND'}</span>
					</div>

					{isConsoleOpen && (
						<div className="flex-1 flex flex-col bg-black/40 min-h-0">
							{/* Pinned Tasks Progress Area */}
							{Object.entries(taskProgress).length > 0 && (
								<div className="p-4 border-b border-white/10 bg-violet-500/5 shrink-0">
									{Object.entries(taskProgress).map(([task, info]) => (
										<div key={task} className="mb-2 last:mb-0">
											<div className="flex justify-between text-[8px] mb-1 font-mono">
												<span className="text-violet-400 font-bold tracking-widest uppercase">{task}</span>
												<span className="text-white/50">{info.message}</span>
											</div>
											<div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
												<div
													className="h-full bg-gradient-to-r from-violet-500 via-fuchsia-500 to-indigo-500 transition-all duration-500 ease-out"
													style={{ width: `${info.progress}%` }}
												/>
											</div>
											<div className="text-right text-[8px] mt-1 text-white/30 font-mono tracking-tighter">{info.progress}% COMPLETE</div>
										</div>
									))}
								</div>
							)}

							{/* Scrollable Logs Area */}
							<div ref={logRef} className="flex-1 p-4 font-mono text-[10px] overflow-y-auto custom-scrollbar min-h-0">
								{logs.map((log, i) => (
									<div key={i} className="mb-1.5 flex gap-2 animate-in fade-in slide-in-from-left-1 duration-300">
										<span className="text-white/10">[{log.time}]</span>
										<span className={log.level === 'success' ? 'text-emerald-400' : log.level === 'error' ? 'text-rose-400' : 'text-violet-300'}>{log.msg}</span>
									</div>
								))}
							</div>
						</div>
					)}
				</GlassCard>
			</div>

			<SettingsModal
				isOpen={isSettingsOpen}
				onClose={() => setIsSettingsOpen(false)}
				config={schedConfig}
				onSave={async (newConfig) => {
					try {
						const res = await fetch('http://127.0.0.1:8001/api/v1/admin/scheduler/config', {
							method: 'POST',
							headers: { 'Content-Type': 'application/json' },
							body: JSON.stringify(newConfig)
						});
						if (res.ok) {
							setSchedConfig(newConfig);
							setIsSettingsOpen(false);
							addNotify("调度配置已同步至云端", "success");
						}
					} catch (e) {
						addNotify("配置同步失败，请检查网络", "error");
					}
				}}
			/>
			<IntelligenceReader
				item={selectedIntel}
				onClose={() => setSelectedIntel(null)}
			/>
		</div>
	);
};

export default Dashboard;