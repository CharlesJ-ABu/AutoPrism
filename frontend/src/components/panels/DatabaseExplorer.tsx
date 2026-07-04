import React from 'react';
import { Database, Layers, ArrowRight, CheckCircle2, Clock } from 'lucide-react';
import { Button } from '@/components/ui';

export const DatabaseExplorer: React.FC = () => {
  const [activeLayer, setActiveLayer] = React.useState<1 | 'info' | 2>(1);
  const [data, setData] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [expandedId, setExpandedId] = React.useState<string | null>(null);

  const fetchData = async (layer: 1 | 'info' | 2) => {
    setLoading(true);
    try {
      const baseUrl = 'http://127.0.0.1:8001';
      let endpoint = '';
      if (layer === 1) endpoint = '/api/v1/admin/debug/raw';
      else if (layer === 'info') endpoint = '/api/v1/admin/debug/info';
      else endpoint = '/api/v1/admin/debug/structured';
      
      const res = await fetch(`${baseUrl}${endpoint}`);
      const json = await res.json();
      setData(json);
    } catch (e) {
      console.error("Failed to fetch debug data", e);
    } finally {
      setLoading(false);
    }
  };

  React.useEffect(() => {
    fetchData(activeLayer);
  }, [activeLayer]);

  return (
    <div className="space-y-4">
      <div className="flex bg-white/5 p-1 rounded-xl border border-white/10 gap-1">
        <button
          onClick={() => setActiveLayer(1)}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg transition-all ${
            activeLayer === 1 ? 'bg-violet-500 text-white shadow-lg' : 'text-white/40 hover:text-white'
          }`}
        >
          <Database size={14} />
          <span className="text-[10px] font-bold">L1: 原始情报</span>
        </button>
        <button
          onClick={() => setActiveLayer('info')}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg transition-all ${
            activeLayer === 'info' ? 'bg-emerald-500 text-white shadow-lg' : 'text-white/40 hover:text-white'
          }`}
        >
          <CheckCircle2 size={14} />
          <span className="text-[10px] font-bold">INFO: 面板解读</span>
        </button>
        <button
          onClick={() => setActiveLayer(2)}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg transition-all ${
            activeLayer === 2 ? 'bg-amber-500 text-white shadow-lg' : 'text-white/40 hover:text-white'
          }`}
        >
          <Layers size={14} />
          <span className="text-[10px] font-bold">L2: 结构信号</span>
        </button>
      </div>

      <div className="min-h-[300px] max-h-[500px] overflow-auto custom-scrollbar border border-white/10 rounded-xl bg-black/20">
        {loading ? (
          <div className="h-full flex items-center justify-center text-white/20 italic text-sm animate-pulse">
            正在扫描数据库底层节点...
          </div>
        ) : (
          <table className="w-full text-left border-collapse min-w-[1000px]">
            <thead className="sticky top-0 bg-[#0a0a0a] border-b border-white/10 z-10">
              <tr>
                <th className="p-3 text-[10px] font-black text-white/40 uppercase tracking-tighter w-[300px]">
                  {activeLayer === 2 ? '战略研判标题' : '标题快报'}
                </th>
                <th className="p-3 text-[10px] font-black text-white/40 uppercase tracking-tighter">
                  {activeLayer === 2 ? '所属角色' : '路由面板'}
                </th>
                <th className="p-3 text-[10px] font-black text-white/40 uppercase tracking-tighter">
                  {activeLayer === 1 ? '来源' : activeLayer === 'info' ? '影响分数' : '渲染类型'}
                </th>
                {activeLayer === 2 && (
                   <>
                     <th className="p-3 text-[10px] font-black text-white/40 uppercase tracking-tighter">地理坐标 (GEO)</th>
                     <th className="p-3 text-[10px] font-black text-white/40 uppercase tracking-tighter">优先级/情绪</th>
                   </>
                )}
                <th className="p-3 text-[10px] font-black text-white/40 uppercase tracking-tighter">同步时间</th>
              </tr>
            </thead>
            <tbody>
              {data.map((item, idx) => (
                <React.Fragment key={item.id}>
                  <tr 
                    className="border-b border-white/5 hover:bg-white/5 transition-colors group cursor-pointer"
                    onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                  >
                    <td className="p-3">
                      <div className="flex flex-col gap-1">
                        <p className="text-xs font-bold text-white line-clamp-1 group-hover:text-violet-300 transition-colors">
                          {item.title}
                        </p>
                        {activeLayer === 2 && (
                          <p className="text-[10px] text-white/40 line-clamp-1 italic">{item.summary}</p>
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      <div className="flex gap-1 flex-wrap">
                        {activeLayer === 2 ? (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-black">
                            {item.role}
                          </span>
                        ) : (
                          item.panels?.map((p: string) => (
                            <span key={p} className={`text-[9px] px-1 rounded border ${
                              activeLayer === 1 ? 'bg-violet-500/10 text-violet-300 border-violet-500/20' : 
                              'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                            }`}>
                              {p}
                            </span>
                          ))
                        )}
                      </div>
                    </td>
                    <td className="p-3">
                      {activeLayer === 1 ? (
                         <span className="text-[10px] text-white/40 px-1.5 py-0.5 bg-white/5 rounded border border-white/5">{item.source}</span>
                      ) : activeLayer === 'info' ? (
                        <div className="flex items-center gap-2">
                           <div className="w-12 h-1 bg-white/10 rounded-full overflow-hidden">
                              <div className="h-full bg-emerald-500" style={{ width: `${item.impact}%` }} />
                           </div>
                           <span className="text-[10px] font-bold text-emerald-400">{item.impact}</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className={`text-[9px] px-1.5 py-0.5 rounded font-black tracking-tighter ${
                            item.display_type === 'FLOW' ? 'bg-blue-500/20 text-blue-300' :
                            item.display_type === 'HOTSPOT' ? 'bg-rose-500/20 text-rose-300' :
                            item.display_type === 'ZONE' ? 'bg-amber-500/20 text-amber-300' :
                            item.display_type === 'RIPPLE' ? 'bg-violet-500/20 text-violet-300' :
                            'bg-white/10 text-white/40'
                          }`}>
                            {item.display_type || 'STRATEGY'}
                          </span>
                        </div>
                      )}
                    </td>
                    {activeLayer === 2 && (
                      <>
                        <td className="p-3">
                          <div className="flex flex-col gap-0.5 min-w-[100px]">
                            <span className="text-[9px] font-mono text-white/60">LAT: {item.geo?.lat?.toFixed(2)}</span>
                            <span className="text-[9px] font-mono text-white/60">LNG: {item.geo?.lng?.toFixed(2)}</span>
                          </div>
                        </td>
                        <td className="p-3">
                           <div className="flex flex-col gap-1">
                              <div className="flex gap-1">
                                {[...Array(4)].map((_, i) => (
                                  <div key={i} className={`w-1.5 h-1.5 rounded-full ${i < (item.priority || 0) ? 'bg-amber-500' : 'bg-white/10'}`} />
                                ))}
                              </div>
                              <span className={`text-[9px] font-bold ${
                                (item.sentiment || 0) > 0 ? 'text-emerald-400' : (item.sentiment || 0) < 0 ? 'text-rose-400' : 'text-white/40'
                              }`}>
                                SNT: {(item.sentiment || 0).toFixed(2)}
                              </span>
                           </div>
                        </td>
                      </>
                    )}
                    <td className="p-3 whitespace-nowrap text-right">
                      <span className="text-[10px] font-mono text-white/20">
                        {new Date(item.created_at).toLocaleTimeString()}
                      </span>
                    </td>
                  </tr>
                  {expandedId === item.id && (
                    <tr className="bg-violet-500/5">
                      <td colSpan={4} className="p-4">
                        <div className="bg-black/40 rounded-lg p-3 border border-violet-500/20">
                          <p className="text-[9px] font-black text-violet-400 uppercase mb-2 flex items-center gap-2">
                            <ArrowRight size={10} /> Raw Intelligence Metrics
                          </p>
                          <pre className="text-[10px] font-mono text-white/60 overflow-x-auto custom-scrollbar">
                            {JSON.stringify(item.metrics || item, null, 2)}
                          </pre>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
      
      <div className="flex justify-between items-center px-1">
        <p className="text-[10px] text-white/20 italic">
          * 数据展示仅限最近 50 条。层级 1 到层级 2 的转换由 AI 引擎自动完成。
        </p>
        <Button 
          variant="secondary" 
          size="sm" 
          className="h-7 text-[10px] font-bold border-white/10 hover:bg-white/10"
          onClick={() => fetchData(activeLayer)}
        >
          刷新实时数据
        </Button>
      </div>
    </div>
  );
};
