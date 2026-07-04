import React, { useState, useEffect } from 'react';
import { GlassCard, Button } from '@/components/ui';
import { Settings, Play, Database, Cpu } from 'lucide-react';
import { system } from '@/lib/api';

export const SystemControlPanel: React.FC = () => {
  const [config, setConfig] = useState({
    mode: 'auto',
    fetch_interval: 60,
    process_interval: 15
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    system.getSchedulerConfig()
      .then(data => setConfig(data))
      .catch(err => console.error("Failed to load config:", err));
  }, []);

  const updateConfig = async (updates: any) => {
    const newConfig = { ...config, ...updates };
    setConfig(newConfig);
    try {
      await system.updateSchedulerConfig(newConfig);
    } catch (err) {
      console.error("Failed to update config:", err);
    }
  };

  const triggerAction = async (type: 'fetch' | 'process') => {
    setLoading(true);
    try {
      if (type === 'fetch') {
        await system.forceFetch();
      } else {
        await system.forceProcess();
      }
      setTimeout(() => setLoading(false), 1000);
    } catch (err) {
      console.error("Failed to trigger:", err);
      setLoading(false);
    }
  };

  return (
    <GlassCard opacity={0.15} className="p-4 w-full h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4 border-b border-white/10 pb-2">
        <Settings size={16} className="text-white/60" />
        <h3 className="text-sm font-semibold text-white/80">SYSTEM CONTROL CENTER</h3>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto pr-2">
        {/* Crawler Engine */}
        <div className="bg-black/20 rounded-lg p-3 border border-white/5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Database size={14} className="text-blue-400" />
              <span className="text-sm font-medium text-white/90">Crawler Engine</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className={config.mode === 'manual' ? 'text-white' : 'text-white/40'}>Manual</span>
              <button 
                onClick={() => updateConfig({ mode: config.mode === 'auto' ? 'manual' : 'auto' })}
                className={`w-8 h-4 rounded-full relative transition-colors ${config.mode === 'auto' ? 'bg-blue-500' : 'bg-gray-600'}`}
              >
                <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full transition-transform ${config.mode === 'auto' ? 'right-0.5' : 'left-0.5'}`} />
              </button>
              <span className={config.mode === 'auto' ? 'text-blue-400' : 'text-white/40'}>Auto</span>
            </div>
          </div>
          
          {config.mode === 'auto' && (
            <div className="mb-3">
              <div className="flex justify-between text-xs text-white/50 mb-1">
                <span>Fetch Interval</span>
                <span>{config.fetch_interval} min</span>
              </div>
              <input 
                type="range" 
                min="5" max="1440" step="5"
                value={config.fetch_interval}
                onChange={(e) => updateConfig({ fetch_interval: parseInt(e.target.value) })}
                className="w-full accent-blue-500"
              />
            </div>
          )}
          
          <Button 
            variant="secondary" 
            size="sm" 
            className="w-full bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/30 flex justify-center items-center gap-1"
            onClick={() => triggerAction('fetch')}
            disabled={loading}
          >
            <Play size={12} /> FORCE FETCH NOW
          </Button>
        </div>

        {/* AI Denoising Engine */}
        <div className="bg-black/20 rounded-lg p-3 border border-white/5">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Cpu size={14} className="text-purple-400" />
              <span className="text-sm font-medium text-white/90">AI Denoising</span>
            </div>
            {/* AI doesn't have a separate mode in this simple flat config, it shares 'mode' or we just show interval */}
          </div>
          
          {config.mode === 'auto' && (
            <div className="mb-3">
              <div className="flex justify-between text-xs text-white/50 mb-1">
                <span>Process Interval</span>
                <span>{config.process_interval} min</span>
              </div>
              <input 
                type="range" 
                min="1" max="120" step="1"
                value={config.process_interval}
                onChange={(e) => updateConfig({ process_interval: parseInt(e.target.value) })}
                className="w-full accent-purple-500"
              />
            </div>
          )}
          
          <Button 
            variant="secondary" 
            size="sm" 
            className="w-full bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/30 flex justify-center items-center gap-1"
            onClick={() => triggerAction('process')}
            disabled={loading}
          >
            <Play size={12} /> FORCE PROCESS NOW
          </Button>
        </div>
      </div>
    </GlassCard>
  );
};
