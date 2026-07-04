// AutoPrism - Data Source Management Page
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Plus, Pencil, Trash2 } from 'lucide-react';
import { useSourcesStore } from '@/stores';
import { Button, GlassCard, Input } from '@/components/ui';
import { useNavigate } from 'react-router-dom';
import { sources as sourcesApi } from '@/lib/api';
import { useAuthStore } from '@/stores';
import type { DataSource } from '@/types';

export default function DataSourceManager() {
  const { sources, loadSources, loadSubscriptions, subscriptions } = useSourcesStore();
  const { token } = useAuthStore();
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);
  const [editingSource, setEditingSource] = useState<DataSource | null>(null);
  const [form, setForm] = useState({ name: '', type: 'rss', url: '', botId: '', apiToken: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isCoze = form.type === 'coze';

  useEffect(() => {
    loadSources();
    loadSubscriptions();
  }, []);

  const openAdd = () => {
    setForm({ name: '', type: 'rss', url: '', botId: '', apiToken: '' });
    setEditingSource(null);
    setShowForm(true);
  };

  const openEdit = (source: DataSource) => {
    const cfg = source.config || {};
    setForm({
      name: source.name,
      type: source.type,
      url: source.url || '',
      botId: (cfg as Record<string,string>).bot_id || '',
      apiToken: (cfg as Record<string,string>).api_token || '',
    });
    setEditingSource(source);
    setShowForm(true);
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingSource(null);
    setForm({ name: '', type: 'rss', url: '', botId: '', apiToken: '' });
  };

  const handleSubmit = async () => {
    if (!form.name || !form.url) return;
    if (isCoze && (!form.botId || !form.apiToken)) {
      alert('扣子 Bot 需要填写 Bot ID 和 API Token');
      return;
    }
    setIsSubmitting(true);
    try {
      const payload: Record<string, unknown> = { name: form.name, type: form.type, url: form.url };
      if (isCoze) {
        payload.config = {
          api_token: form.apiToken,
          bot_id: form.botId,
          user_id: 'tech_nebula_user',
        };
      }
      if (editingSource) {
        await sourcesApi.update(editingSource.id, payload as Parameters<typeof sourcesApi.update>[1]);
      } else {
        await sourcesApi.create(payload as Parameters<typeof sourcesApi.create>[0]);
      }
      await loadSources();
      closeForm();
    } catch (e) {
      console.error('Failed to save source:', e);
      alert('保存失败：' + (e instanceof Error ? e.message : String(e)));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除该数据源？')) return;
    try {
      await sourcesApi.delete(id);
      await loadSources();
    } catch (e) {
      console.error('Failed to delete:', e);
    }
  };

  const typeLabels: Record<string, string> = {
    rss: 'RSS',
    api: 'API',
    webpage: '网页',
    coze: '扣子 Bot',
    ota: 'OTA 资讯',
  };

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
            <h1 className="text-lg font-semibold text-gradient">数据源管理</h1>
          </div>
          <Button variant="secondary" size="sm" onClick={openAdd}>
            <Plus size={14} />
            添加数据源
          </Button>
        </GlassCard>
      </div>

      {/* Content */}
      <div className="pt-24 px-4 pb-8 max-w-4xl mx-auto">
        {/* Add/Edit Form */}
        {showForm && (
          <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
            <GlassCard opacity={0.1} className="p-6">
              <h3 className="text-sm font-medium mb-4">
                {editingSource ? '编辑数据源' : '添加新数据源'}
              </h3>
              <div className="flex flex-col gap-3 max-w-lg">
                <Input
                  placeholder="数据源名称"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
                <select
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}
                  className="px-4 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white"
                >
                  <option value="rss">RSS 订阅</option>
                  <option value="api">API 接口</option>
                  <option value="webpage">网页</option>
                  <option value="ota">OTA 资讯</option>
                  <option value="coze">扣子 Bot</option>
                </select>
                <Input
                  placeholder={isCoze ? 'Prompt 提示词' : 'URL 地址'}
                  value={form.url}
                  onChange={(e) => setForm({ ...form, url: e.target.value })}
                />
                {isCoze && (
                  <>
                    <Input
                      placeholder="Bot ID（必填）"
                      value={form.botId}
                      onChange={(e) => setForm({ ...form, botId: e.target.value })}
                    />
                    <Input
                      placeholder="API Token（必填，cztei_ 开头）"
                      value={form.apiToken}
                      onChange={(e) => setForm({ ...form, apiToken: e.target.value })}
                    />
                  </>
                )}
                <div className="flex gap-2 justify-end">
                  <Button variant="ghost" size="sm" onClick={closeForm}>
                    取消
                  </Button>
                  <Button variant="primary" size="sm" onClick={handleSubmit} disabled={isSubmitting}>
                    {isSubmitting ? '保存中...' : '确认'}
                  </Button>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        )}

        {/* Sources Table */}
        <GlassCard opacity={0.08} className="overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-white/10 text-left text-sm text-white/50">
                <th className="px-4 py-3 font-medium">名称</th>
                <th className="px-4 py-3 font-medium">类型</th>
                <th className="px-4 py-3 font-medium">URL</th>
                <th className="px-4 py-3 font-medium text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => {
                const isSubscribed = subscriptions.some((s) => s.data_source_id === source.id);
                return (
                  <tr key={source.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white/90">{source.name}</span>
                        {isSubscribed && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-green-500/20 text-green-400">
                            已订阅
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-white/60">
                      {typeLabels[source.type] || source.type}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-white/40 truncate max-w-[250px] block">
                        {source.url || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        {token && (
                          <>
                            <button
                              onClick={() => openEdit(source)}
                              className="p-1.5 hover:bg-white/10 rounded transition-colors"
                              title="编辑"
                            >
                              <Pencil size={14} className="text-white/50" />
                            </button>
                            <button
                              onClick={() => handleDelete(source.id)}
                              className="p-1.5 hover:bg-white/10 rounded transition-colors"
                              title="删除"
                            >
                              <Trash2 size={14} className="text-white/50 hover:text-red-400" />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {sources.length === 0 && (
            <div className="text-center py-12 text-white/40 text-sm">暂无数据源</div>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
