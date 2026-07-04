// AutoPrism - Add Panel Modal
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { X, Rss, Globe, Plus, Check, Tag } from 'lucide-react';
import { useSourcesStore, useFeedStore, usePanelsStore } from '@/stores';
import { panels as panelsApi } from '@/lib/api';
import { Button, GlassCard } from '@/components/ui';

interface SourceSelectorProps {
  onClose: () => void;
}

// Available tag panels (from Coze data source)
const TAG_PANELS = [
  'AI', '智能驾驶', '电子架构', '材料科学', '智能座舱',
  '电池', '能源', '电驱', '芯片', '混动', '具身智能',
];

export default function SourceSelector({ onClose }: SourceSelectorProps) {
  const { sources: allSources, loadSources, subscribe, unsubscribe, subscriptions, loadSubscriptions } = useSourcesStore();
  const { refreshSource } = useFeedStore();
  const { panels, loadPanels, removePanel } = usePanelsStore();
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadSources();
  }, []);

  const handleToggleSubscribe = async (sourceId: string, currentlySubscribed: boolean) => {
    setIsLoading(true);
    try {
      if (currentlySubscribed) {
        // Find and delete the panel for this data source before unsubscribing
        const targetPanel = panels.find((p) => p.data_source_id === sourceId && !p.tag);
        if (targetPanel) {
          await removePanel(targetPanel.id);
        }
        await unsubscribe(sourceId);
      } else {
        const existing = panels.find((p) => p.data_source_id === sourceId && !p.tag);
        if (!existing) {
          try {
            await subscribe(sourceId);
            await refreshSource(sourceId);
          } catch (e) {
            if (e instanceof Error && e.message.includes('Already subscribed')) {
              // Subscription already exists — just reload subscriptions to sync state
              await loadSubscriptions();
            } else {
              throw e;
            }
          }
        }
      }
      await loadPanels();
    } catch (e) {
      console.error('Toggle failed:', e);
    } finally {
      setIsLoading(false);
    }
  };

  // Create a tag-based panel directly (no auth needed for /panels/public)
  const handleAddTagPanel = async (tag: string) => {
    try {
      await panelsApi.create({
        data_source_id: '3d438b03-ff5e-4ad4-8011-90f537ef1b12',
        tag,
        title: `${tag}资讯`,
        type: 'list',
        size: '1x1',
        position: { x: 0, y: 0, w: 1, h: 1 },
      } as Parameters<typeof panelsApi.create>[0]);
      await loadPanels();
    } catch (e) {
      console.error('Failed to add tag panel:', e);
    }
  };

  // Remove a tag panel
  const handleRemoveTagPanel = async (tag: string) => {
    const targetPanel = panels.find((p) => p.tag === tag);
    if (targetPanel) {
      await removePanel(targetPanel.id);
    }
  };

  // Unified toggle for tag panel: add if missing, remove if exists
  const handleToggleTagPanel = async (tag: string) => {
    const existing = panels.find((p) => p.tag === tag);
    if (existing) {
      await handleRemoveTagPanel(tag);
    } else {
      await handleAddTagPanel(tag);
    }
  };

  const isSubscribed = (sourceId: string) =>
    subscriptions.some((s) => s.data_source_id === sourceId);

  const typeIcons: Record<string, React.ReactNode> = {
    rss: <Rss size={16} className="text-orange-400" />,
    api: <Globe size={16} className="text-blue-400" />,
    webpage: <Globe size={16} className="text-green-400" />,
    coze: <Globe size={16} className="text-purple-400" />,
  };

  return (
    <motion.div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <GlassCard opacity={0.15} className="w-full max-w-2xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <h2 className="text-lg font-semibold">添加面板</h2>
          <button onClick={onClose} className="p-1 hover:bg-white/10 rounded">
            <X size={20} className="text-white/50" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4 space-y-6">

          {/* ===== Part 1: Tag Panels ===== */}
          <section>
            <h3 className="text-sm font-medium text-white/60 mb-3 flex items-center gap-2">
              <Tag size={14} />
              标签面板
            </h3>
            <div className="grid grid-cols-3 gap-2">
              {TAG_PANELS.map((tag) => {
                const hasPanel = panels.some((p) => p.tag === tag);
                return (
                  <button
                    key={tag}
                    onClick={() => handleToggleTagPanel(tag)}
                    className={`flex items-center gap-2 p-2.5 rounded-lg text-left text-sm transition-colors ${
                      hasPanel
                        ? 'bg-purple-400/10 text-white/90 hover:bg-purple-400/20'
                        : 'bg-white/5 hover:bg-white/10 text-white/90'
                    }`}
                  >
                    <div className={`w-2 h-2 rounded-full ${hasPanel ? 'bg-purple-400' : 'bg-purple-400/40'}`} />
                    {hasPanel && <Check size={12} className="text-purple-400" />}
                    {tag}
                  </button>
                );
              })}
            </div>
          </section>

          {/* ===== Part 2: Data Source Panels ===== */}
          <section>
            <h3 className="text-sm font-medium text-white/60 mb-3 flex items-center gap-2">
              <Rss size={14} />
              数据源面板
            </h3>

            {/* Sources list */}
            <div className="flex flex-col gap-2">
              {allSources.length === 0 && (
                <p className="text-white/40 text-sm text-center py-6">暂无可用数据源</p>
              )}
              {allSources.map((source) => {
                const subscribed = isSubscribed(source.id);
                return (
                  <div
                    key={source.id}
                    className="flex items-center justify-between p-3 bg-white/5 hover:bg-white/8 rounded-lg transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      {typeIcons[source.type as keyof typeof typeIcons]}
                      <div>
                        <p className="text-sm font-medium">{source.name}</p>
                        <p className="text-xs text-white/40 truncate max-w-[200px]">
                          {source.url || '—'}
                        </p>
                      </div>
                    </div>
                    <Button
                      variant={subscribed ? 'secondary' : 'ghost'}
                      size="sm"
                      onClick={() => handleToggleSubscribe(source.id, subscribed)}
                      disabled={isLoading}
                    >
                      {subscribed ? (
                        <>
                          <Check size={14} />
                          已订阅
                        </>
                      ) : (
                        <>
                          <Plus size={14} />
                          订阅
                        </>
                      )}
                    </Button>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      </GlassCard>
    </motion.div>
  );
}
