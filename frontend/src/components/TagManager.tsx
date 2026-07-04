// AutoPrism - Tag Management Page
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Plus, Tag } from 'lucide-react';
import { Button, GlassCard, Input } from '@/components/ui';
import { useNavigate } from 'react-router-dom';
import { tags as tagsApi } from '@/lib/api';

interface TagItem {
  id: string;
  name: string;
  category: string | null;
  color: string | null;
  hotness: number;
}

const PRESET_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
  '#BB8FCE', '#85C1E9', '#F8B500', '#00D9FF',
];

export default function TagManager() {
  const navigate = useNavigate();
  const [tags, setTags] = useState<TagItem[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', category: '', color: '#4ECDC4' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);

  const loadTags = async () => {
    const data = await tagsApi.list(undefined, 100) as TagItem[];
    setTags(data);
  };

  const loadCategories = async () => {
    const data = await tagsApi.categories() as string[];
    setCategories(data);
  };

  useEffect(() => {
    loadTags();
    loadCategories();
  }, []);

  const openAdd = () => {
    setForm({ name: '', category: '', color: '#4ECDC4' });
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setForm({ name: '', category: '', color: '#4ECDC4' });
  };

  const handleSubmit = async () => {
    if (!form.name.trim()) return;
    setIsSubmitting(true);
    try {
      const payload = {
        name: form.name.trim(),
        category: form.category.trim() || undefined,
        color: form.color,
      };
      if (form.name.trim()) {
        await tagsApi.create(payload);
      }
      await loadTags();
      await loadCategories();
      closeForm();
    } catch (e) {
      console.error('Failed to save tag:', e);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Group tags by category
  const grouped: Record<string, TagItem[]> = {};
  for (const tag of tags) {
    const cat = tag.category || '未分类';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(tag);
  }

  return (
    <div className="min-h-screen bg-[#0F0F23]">
      {/* Header */}
      <div className="fixed top-0 left-0 right-0 z-50 p-4">
        <GlassCard opacity={0.15} className="px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => navigate('/')}>
              <ArrowLeft size={16} />
              返回
            </Button>
            <h1 className="text-lg font-semibold text-gradient">标签管理</h1>
          </div>
          <Button variant="secondary" size="sm" onClick={openAdd}>
            <Plus size={14} />
            添加标签
          </Button>
        </GlassCard>
      </div>

      {/* Content */}
      <div className="pt-24 px-4 pb-8 max-w-4xl mx-auto">
        {/* Add/Edit Form */}
        {showForm && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
            <GlassCard opacity={0.1} className="p-6">
              <h3 className="text-sm font-medium mb-4">
                {'添加新标签'}
              </h3>
              <div className="flex flex-col gap-3 max-w-lg">
                <Input
                  placeholder="标签名称，如：LLM、Rust、AI Agent"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="分类（可选），如：AI、Infra、Web3"
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                    className="flex-1 px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm"
                    list="category-list"
                  />
                  <datalist id="category-list">
                    {categories.map((c) => (
                      <option key={c} value={c} />
                    ))}
                  </datalist>
                </div>
                {/* Color picker */}
                <div className="flex items-center gap-3">
                  <span className="text-sm text-white/50">颜色：</span>
                  <div className="flex gap-1.5 flex-wrap">
                    {PRESET_COLORS.map((color) => (
                      <button
                        key={color}
                        onClick={() => setForm({ ...form, color })}
                        className="w-7 h-7 rounded-full transition-transform hover:scale-110 ring-offset-0"
                        style={{
                          backgroundColor: color,
                          outline: form.color === color ? '2px solid white' : 'none',
                          outlineOffset: '2px',
                        }}
                      />
                    ))}
                    <input
                      type="color"
                      value={form.color}
                      onChange={(e) => setForm({ ...form, color: e.target.value })}
                      className="w-7 h-7 rounded-full cursor-pointer"
                    />
                  </div>
                  <span
                    className="w-8 h-8 rounded-full border border-white/20 flex items-center justify-center text-xs font-bold"
                    style={{ backgroundColor: form.color }}
                  >
                    T
                  </span>
                </div>
                <div className="flex gap-2 justify-end">
                  <Button variant="ghost" size="sm" onClick={closeForm}>取消</Button>
                  <Button variant="primary" size="sm" onClick={handleSubmit} disabled={isSubmitting}>
                    {isSubmitting ? '保存中...' : '确认'}
                  </Button>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* Tags grouped by category */}
        {Object.entries(grouped).map(([category, categoryTags]) => (
          <div key={category} className="mb-8">
            <div className="flex items-center gap-2 mb-3">
              <Tag size={12} className="text-white/40" />
              <span className="text-sm text-white/40 font-medium">{category}</span>
              <span className="text-xs text-white/20">({categoryTags.length})</span>
            </div>
            <GlassCard opacity={0.06} className="p-4">
              <div className="flex flex-wrap gap-2">
                {categoryTags.map((tag) => (
                  <div
                    key={tag.id}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm border"
                    style={{
                      borderColor: `${tag.color ?? "#888"}50`,
                      backgroundColor: `${tag.color ?? "#888"}15`,
                    }}
                  >
                    <span style={{ color: tag.color ?? "#888" }}>{tag.name}</span>
                    <span className="text-white/30 text-xs">({tag.hotness})</span>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>
        ))}

        {tags.length === 0 && !showForm && (
          <div className="text-center py-20 text-white/40 text-sm">
            暂无标签
          </div>
        )}
      </div>
    </div>
  );
}
