import React from 'react';
import { X, Clock, Calendar, MousePointer2, Save, Settings, Database, Cpu, AlertCircle } from 'lucide-react';
import { GlassCard, Button, Input } from '@/components/ui';
import { DatabaseExplorer } from './DatabaseExplorer';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: {
    crawlerMode: 'manual' | 'daily' | 'interval';
    crawlerValue: string;
    aiMode: 'manual' | 'daily' | 'interval';
    aiValue: string;
    aiBatchSize: number;
  };
  onSave: (newConfig: any) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose, config, onSave }) => {
  const [localConfig, setLocalConfig] = React.useState(config);
  const [error, setError] = React.useState<string | null>(null);

  const handleResetLayer = async (layer: 'l1' | 'info' | 'l2') => {
    setError(null);
    try {
      const res = await fetch(`http://127.0.0.1:8001/api/v1/admin/trigger/reset/${layer}`, { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}: 指令执行失败`);
    } catch (e: any) {
      setError(e.message || `清空 ${layer.toUpperCase()} 失败`);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <GlassCard opacity={0.2} className="w-full max-w-2xl overflow-hidden shadow-2xl border-white/20">
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <Settings className="text-violet-400" size={24} />
            <h2 className="text-xl font-bold text-white">系统调度配置</h2>
          </div>
          <button onClick={onClose} className="text-white/40 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>

        <div className="p-8 space-y-8 max-h-[70vh] overflow-y-auto custom-scrollbar">
          {/* Crawler Section */}
          <section className="space-y-4">
            <h3 className="text-sm font-bold text-white/40 uppercase tracking-widest flex items-center gap-2">
              <Database size={14} /> 数据抓取引擎 (Crawler)
            </h3>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: 'manual', label: '纯手动', icon: MousePointer2 },
                { id: 'daily', label: '每日定时', icon: Clock },
                { id: 'interval', label: '周期重复', icon: Calendar },
              ].map((mode) => (
                <button
                  key={mode.id}
                  onClick={() => setLocalConfig({ ...localConfig, crawlerMode: mode.id as any })}
                  className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${
                    localConfig.crawlerMode === mode.id
                      ? 'bg-violet-500/20 border-violet-500/50 text-white'
                      : 'bg-white/5 border-white/5 text-white/40 hover:bg-white/8'
                  }`}
                >
                  <mode.icon size={20} />
                  <span className="text-xs font-medium">{mode.label}</span>
                </button>
              ))}
            </div>
            {localConfig.crawlerMode === 'daily' && (
              <Input 
                type="time" 
                label="执行时间" 
                value={localConfig.crawlerValue}
                onChange={(e) => setLocalConfig({...localConfig, crawlerValue: e.target.value})}
              />
            )}
            {localConfig.crawlerMode === 'interval' && (
              <Input 
                type="number" 
                label="执行间隔 (分钟)" 
                placeholder="例如: 60"
                value={localConfig.crawlerValue}
                onChange={(e) => setLocalConfig({...localConfig, crawlerValue: e.target.value})}
              />
            )}
          </section>

          <div className="h-[1px] bg-white/5" />

          {/* AI Denoise Section */}
          <section className="space-y-4">
            <h3 className="text-sm font-bold text-white/40 uppercase tracking-widest flex items-center gap-2">
              <Cpu size={14} /> AI 降噪引擎 (Denoise)
            </h3>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: 'manual', label: '纯手动', icon: MousePointer2 },
                { id: 'daily', label: '每日定时', icon: Clock },
                { id: 'interval', label: '周期重复', icon: Calendar },
              ].map((mode) => (
                <button
                  key={mode.id}
                  onClick={() => setLocalConfig({ ...localConfig, aiMode: mode.id as any })}
                  className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${
                    localConfig.aiMode === mode.id
                      ? 'bg-emerald-500/20 border-emerald-500/50 text-white'
                      : 'bg-white/5 border-white/5 text-white/40 hover:bg-white/8'
                  }`}
                >
                  <mode.icon size={20} />
                  <span className="text-xs font-medium">{mode.label}</span>
                </button>
              ))}
            </div>
            {localConfig.aiMode === 'daily' && (
              <Input 
                type="time" 
                label="执行时间" 
                value={localConfig.aiValue}
                onChange={(e) => setLocalConfig({...localConfig, aiValue: e.target.value})}
              />
            )}
            {localConfig.aiMode === 'interval' && (
              <Input 
                type="number" 
                label="执行间隔 (分钟)" 
                placeholder="例如: 30"
                value={localConfig.aiValue}
                onChange={(e) => setLocalConfig({...localConfig, aiValue: e.target.value})}
              />
            )}
            
            <div className="pt-4 border-t border-white/5">
              <Input 
                type="number" 
                label="单次降噪数量 (0 = 全量)" 
                placeholder="建议值: 10-50"
                value={localConfig.aiBatchSize}
                onChange={(e) => setLocalConfig({...localConfig, aiBatchSize: parseInt(e.target.value) || 0})}
              />
              <p className="text-[10px] text-white/30 mt-2 italic">
                * 限制单次任务的处理量可以节省 Token 并提高响应速度。设置 0 则处理所有待办。
              </p>
            </div>
          </section>

          <div className="h-[1px] bg-white/5 my-6" />

          {/* Database Explorer Section */}
          <section className="space-y-4">
            <h3 className="text-sm font-black text-white uppercase tracking-tighter flex items-center gap-2">
              DATABASE EXPLORER / 数据库浏览器
            </h3>
            <DatabaseExplorer />
          </section>

          <div className="h-[1px] bg-white/5 my-6" />

          {/* Manual Triggers */}
          <section className="space-y-4">
            <h3 className="text-sm font-black text-white uppercase tracking-tighter flex items-center gap-2">
              MANUAL TRIGGERS / 手动触发
            </h3>
            <div className="flex gap-4">
              <Button 
                variant="secondary" 
                className="flex-1 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/30 font-bold"
                onClick={() => fetch('/api/v1/admin/trigger/fetch', { method: 'POST' })}
              >
                强制爬取新闻 (FORCE FETCH)
              </Button>
              <Button 
                variant="secondary" 
                className="flex-1 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/30 font-bold"
                onClick={() => fetch('/api/v1/admin/trigger/ai', { method: 'POST' })}
              >
                强制 AI 降噪 (FORCE PROCESS)
              </Button>
            </div>
          </section>

          <div className="h-[1px] bg-white/5 my-6" />
          <section className="space-y-4 bg-rose-500/5 p-6 rounded-2xl border border-rose-500/10">
            <h3 className="text-sm font-black text-rose-500 uppercase tracking-tighter flex items-center gap-2">
              DANGER ZONE / 调试区域
            </h3>
            <p className="text-[10px] text-rose-500/60 leading-relaxed">
              分层清空数据库。注意：L2 洞察生成依赖 INFO 和 L1 数据。
            </p>
            
            {error && (
              <div className="p-3 bg-rose-500/20 border border-rose-500/30 rounded-xl flex items-center gap-2">
                <AlertCircle size={14} className="text-rose-500 shrink-0" />
                <span className="text-[10px] font-bold text-rose-400">{error}</span>
              </div>
            )}
            
            <div className="grid grid-cols-3 gap-3">
              <Button 
                variant="secondary" 
                className="border-rose-500/20 text-rose-500 hover:bg-rose-500 hover:text-white transition-all font-bold text-[10px]"
                onClick={() => handleResetLayer('l1')}
              >
                清空 L1 原始库
              </Button>
              <Button 
                variant="secondary" 
                className="border-rose-500/20 text-rose-500 hover:bg-rose-500 hover:text-white transition-all font-bold text-[10px]"
                onClick={() => handleResetLayer('info')}
              >
                清空 INFO 指标
              </Button>
              <Button 
                variant="secondary" 
                className="border-rose-500/20 text-rose-500 hover:bg-rose-500 hover:text-white transition-all font-bold text-[10px]"
                onClick={() => handleResetLayer('l2')}
              >
                清空 L2 战略洞察
              </Button>
            </div>
          </section>
        </div>

        <div className="p-6 bg-white/5 flex items-center justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>取消</Button>
          <Button variant="primary" onClick={() => onSave(localConfig)} className="gap-2">
            <Save size={18} /> 保存配置
          </Button>
        </div>
      </GlassCard>
    </div>
  );
};
