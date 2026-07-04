// AutoPrism - 2D Organic Tag Graph with click interaction
import { useRef, useEffect, useMemo, useState, useCallback } from 'react';
import * as echarts from 'echarts';
import type { TechTag, FeedResponse, FeedItem } from '@/types';
import { X, ExternalLink, Clock } from 'lucide-react';

interface NebulaGraphProps {
  tags: TechTag[];
  feeds: FeedResponse[];
  height?: number;
}

const TAG_ICONS: Record<string, string> = {
  'AI': '🤖', '智能驾驶': '🚗', '电池': '🔋', '电驱': '⚡',
  '能源': '🌍', '混动': '🔌', '智能座舱': '🖥️', '电子架构': '📡',
  '材料科学': '🔬', '芯片': '💻', '具身智能': '🦾',
};

const TAG_COLORS: Record<string, string> = {
  AI: '#5EEAD4',
  智能驾驶: '#22D3EE',
  电池: '#4ADE80',
  智能座舱: '#A855F7',
  芯片: '#FB7185',
  材料科学: '#FACC15',
};

function getBaseColor(name: string): string {
  return TAG_COLORS[name] ?? '#94A3B8';
}

function getTagIcon(name: string): string {
  return TAG_ICONS[name] ?? '⭐';
}

function getArticlesForTag(tagName: string, feeds: FeedResponse[]): FeedItem[] {
  const articles: FeedItem[] = [];
  feeds.forEach(src => {
    (src.items ?? []).forEach(item => {
      if ((item.tags ?? []).includes(tagName)) {
        articles.push(item);
      }
    });
  });
  return articles.sort((a, b) => {
    const da = a.published_at ? new Date(a.published_at).getTime() : 0;
    const db = b.published_at ? new Date(b.published_at).getTime() : 0;
    return db - da;
  });
}

export default function NebulaGraph({ tags, feeds, height = 480 }: NebulaGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const selectedIdRef = useRef<string | null>(null);

  const [selectedTag, setSelectedTag] = useState<{ name: string; id: string; color: string } | null>(null);
  const [selectedArticles, setSelectedArticles] = useState<FeedItem[]>([]);

  const withArticles = useMemo(
    () => tags.filter((t) => (t.article_count ?? 0) > 0),
    [tags]
  );

  const graphNodes = useMemo(() => {
    return withArticles.map((tag) => {
      const count = tag.article_count ?? 1;
      const baseColor = getBaseColor(tag.name);
      return {
        id: tag.id,
        name: tag.name,
        value: count,
        baseColor,
        symbolSize: 55,
        itemStyle: {
          color: new echarts.graphic.RadialGradient(0.5, 0.5, 0.8, [
            { offset: 0, color: baseColor },
            { offset: 1, color: baseColor + 'AA' }
          ]),
          shadowBlur: 12,
          shadowColor: baseColor + '40',
          borderWidth: 0
        },
      };
    });
  }, [withArticles]);

  const graphLinks = useMemo(() => {
    const cooccur: Map<string, Map<string, number>> = new Map(withArticles.map((t) => [t.name, new Map()]));
    feeds.forEach(src => {
      (src.items ?? []).forEach(item => {
        const itemTags = (item.tags ?? []).filter(t => withArticles.some(tag => tag.name === t));
        for (let a = 0; a < itemTags.length; a++) {
          for (let b = a + 1; b < itemTags.length; b++) {
            const ma = cooccur.get(itemTags[a]);
            const mb = cooccur.get(itemTags[b]);
            if (ma && mb) {
              ma.set(itemTags[b], (ma.get(itemTags[b]) ?? 0) + 1);
              mb.set(itemTags[a], (mb.get(itemTags[a]) ?? 0) + 1);
            }
          }
        }
      });
    });

    const links: any[] = [];
    cooccur.forEach((targets, srcName) => {
      const src = withArticles.find(t => t.name === srcName);
      if (!src) return;
      targets.forEach((weight, tgtName) => {
        const tgt = withArticles.find(t => t.name === tgtName);
        if (!tgt || src.id >= tgt.id) return;
        links.push({
          source: src.id,
          target: tgt.id,
          lineStyle: {
            width: Math.min(15, weight * 2.5),
            color: getBaseColor(src.name),
            opacity: 0.25,
            curveness: 0.1
          }
        });
      });
    });
    return links;
  }, [withArticles, feeds]);

  const applyHighlight = useCallback((chart: echarts.ECharts, highlightId: string | null) => {
    chart.setOption({
      series: [{
        data: graphNodes.map((n) => {
          const isSelected = highlightId === n.id;
          const isOther = !!highlightId && highlightId !== n.id;
          return {
            ...n,
            itemStyle: {
              ...n.itemStyle,
              shadowBlur: isSelected ? 50 : 12,
              shadowColor: isSelected ? '#ffffff' : (n.baseColor + '40'),
              borderColor: isSelected ? '#ffffff' : 'transparent',
              borderWidth: isSelected ? 2.5 : 0,
              opacity: isOther ? 0.35 : 1,
            },
          };
        }),
      }]
    });
  }, [graphNodes]);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = echarts.init(containerRef.current);
    chartRef.current = chart;

    chart.setOption({
      backgroundColor: 'transparent',
      series: [{
        type: 'graph',
        layout: 'force',
        draggable: true,
        data: graphNodes,
        links: graphLinks,
        label: {
          show: true,
          position: 'right',
          distance: 8,
          formatter: (p: { name: string; value: number }) => {
            const icon = getTagIcon(p.name);
            return `{icon|${icon}}  {name|${p.name}}  {count|${p.value}篇}`;
          },
          rich: {
            icon: { fontSize: 18 },
            name: { color: '#fff', fontSize: 13, fontWeight: 600 },
            count: { color: 'rgba(255,255,255,0.45)', fontSize: 10 },
          }
        },
        force: {
          repulsion: 400,
          gravity: 0.1,
          edgeLength: [100, 150],
          layoutAnimation: true
        },
        emphasis: {
          focus: 'adjacency',
          itemStyle: { shadowBlur: 30, shadowColor: 'rgba(255,255,255,0.2)' },
          lineStyle: { opacity: 0.6 }
        }
      }]
    });

    chart.on('click', (params: any) => {
      // Click on background (not a node) → deselect
      if (params.dataType !== 'node') {
        selectedIdRef.current = null;
        setSelectedTag(null);
        setSelectedArticles([]);
        applyHighlight(chart, null);
        return;
      }

      const tagName = params.data.name as string;
      const tagId = params.data.id as string;

      if (selectedIdRef.current === tagId) {
        // Deselect
        selectedIdRef.current = null;
        setSelectedTag(null);
        setSelectedArticles([]);
        applyHighlight(chart, null);
      } else {
        // Select
        selectedIdRef.current = tagId;
        setSelectedTag({ name: tagName, id: tagId, color: getBaseColor(tagName) });
        setSelectedArticles(getArticlesForTag(tagName, feeds));
        applyHighlight(chart, tagId);
      }
    });

    return () => chart.dispose();
  }, [graphNodes, graphLinks, feeds, applyHighlight]);

  const handleClose = useCallback(() => {
    selectedIdRef.current = null;
    setSelectedTag(null);
    setSelectedArticles([]);
    if (chartRef.current) applyHighlight(chartRef.current, null);
  }, [applyHighlight]);

  if (withArticles.length === 0) {
    return (
      <div className="relative flex items-center justify-center" style={{ height }}>
        <p className="text-white/30 text-sm">暂无标签数据</p>
      </div>
    );
  }

  return (
    <div className="relative" style={{ height }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Article list panel - floating on right when a node is selected */}
      {selectedTag && (
        <div
          className="absolute top-4 right-4 w-72 rounded-xl overflow-hidden border border-white/10 custom-scrollbar shadow-2xl"
          style={{
            background: 'rgba(10,10,26,0.92)',
            backdropFilter: 'blur(16px)',
            maxHeight: height - 32,
            boxShadow: `0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.05) inset`,
          }}
        >
          {/* Panel header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10 flex-shrink-0" style={{ background: 'rgba(10,10,26,0.9)' }}>
            <div
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ background: selectedTag.color, boxShadow: `0 0 8px ${selectedTag.color}` }}
            />
            <span className="text-sm font-semibold text-white">{getTagIcon(selectedTag.name)} {selectedTag.name}</span>
            <button
              onClick={handleClose}
              className="ml-auto p-1 hover:bg-white/10 rounded transition-colors"
            >
              <X size={14} className="text-white/50" />
            </button>
          </div>

          {/* Article list */}
          <div className="p-3 space-y-2 overflow-y-auto custom-scrollbar" style={{ maxHeight: height - 120 }}>
            {selectedArticles.length === 0 ? (
              <p className="text-xs text-white/40 text-center py-4">暂无文章</p>
            ) : (
              selectedArticles.map((item, i) => (
                <a
                  key={i}
                  href={item.url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/15 transition-all group"
                >
                  <div className="flex items-start gap-2">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white/90 font-medium leading-snug line-clamp-2 group-hover:text-white transition-colors">
                        {item.title}
                      </p>
                      {item.content && (
                        <p className="text-xs text-white/40 mt-1 line-clamp-2 leading-relaxed">{item.content}</p>
                      )}
                      <div className="flex items-center gap-2 mt-2 text-xs text-white/30">
                        <Clock size={10} />
                        <span>{item.published_at ? new Date(item.published_at).toLocaleDateString('zh-CN') : ''}</span>
                        {item.source_name && (
                          <>
                            <span>·</span>
                            <span className="truncate">{item.source_name}</span>
                          </>
                        )}
                      </div>
                    </div>
                    <ExternalLink size={12} className="text-white/20 flex-shrink-0 mt-0.5 group-hover:text-white/50 transition-colors" />
                  </div>
                </a>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
