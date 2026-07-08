// @ts-nocheck
// AutoPrism - Centralized API Client (Strategic Node Binding)
export const API_BASE_URL = '/api/v1';

// ============================================
// Ultra Deep Mock Data (36 Panels with Source Binding)
// ============================================

const MOCK_PANELS = [
  // 1. 宏观决策视角
  { id: 'p1', title: '全球汽车政策雷达', type: 'list', presentation_type: 'ticker', is_visible: true, role: '宏观决策', size: '1x1', data_source_id: '36Kr_AUTO' },
  { id: 'p2', title: '车型调价预警', type: 'list', presentation_type: 'ticker', is_visible: true, role: '宏观决策', size: '1x1', data_source_id: 'Jiemian_News' },
  { id: 'p3', title: '地缘政治与出海合规', type: 'list', presentation_type: 'ticker', is_visible: true, role: '宏观决策', size: '1x1', data_source_id: 'Reuters_Finance' },
  { id: 'p13', title: '全球销量市占率大盘', type: 'list', presentation_type: 'pie', is_visible: true, role: '宏观决策', size: '1x1', data_source_id: '36Kr_Insight' },
  { id: 'p14', title: '重大断链风险预警', type: 'list', presentation_type: 'ticker', is_visible: true, role: '宏观决策', size: '1x1', data_source_id: 'AutoNews_US' },
  { id: 'p21', title: '碳配额与排放法规监测', type: 'list', presentation_type: 'ticker', is_visible: true, role: '宏观决策', size: '1x1', data_source_id: 'Handelsblatt_DE' },
  { id: 'p22', title: '全球能源补能网络版图', type: 'list', presentation_type: 'heatmap', is_visible: true, role: '宏观决策', size: '1x1', data_source_id: 'Bloomberg_Terminal' },
  { id: 'p23', title: '中国市场消费信心指数', type: 'list', presentation_type: 'time-series', is_visible: true, role: '宏观决策', size: '1x1', data_source_id: 'EastMoney_Macro' },
  { id: 'p24', title: '自动驾驶法律框架准入', type: 'list', presentation_type: 'ticker', is_visible: true, role: '宏观决策', size: '1x1', data_source_id: 'TechCrunch_Main' },
  
  // 2. 战略与产品视角
  { id: 'p4', title: '重点车型OTA 演变追踪', type: 'list', presentation_type: 'ticker', is_visible: true, role: '战略与产品', size: '1x1', data_source_id: 'Teslarati_Pulse' },
  { id: 'p5', title: '技术路径演进图谱', type: 'list', presentation_type: 'time-series', is_visible: true, role: '战略与产品', size: '1x1', data_source_id: 'TheVerge_Tech' },
  { id: 'p6', title: '全球智驾对标', type: 'list', presentation_type: 'radar', is_visible: true, role: '战略与产品', size: '1x1', data_source_id: 'Wired_Transport' },
  { id: 'p15', title: '重点车型参数对标矩阵', type: 'list', presentation_type: 'radar', is_visible: true, role: '战略与产品', size: '1x1', data_source_id: '36Kr_AUTO' },
  { id: 'p16', title: '新车型上市倒计时', type: 'list', presentation_type: 'ticker', is_visible: true, role: '战略与产品', size: '1x1', data_source_id: 'AutoHome_CN' },
  { id: 'p25', title: '智能座舱交互体验评价', type: 'list', presentation_type: 'radar', is_visible: true, role: '战略与产品', size: '1x1', data_source_id: 'InsideEVs_Insight' },
  { id: 'p26', title: '动力电池能量密度排行', type: 'list', presentation_type: 'time-series', is_visible: true, role: '战略与产品', size: '1x1', data_source_id: 'Electrek_EV' },
  { id: 'p27', title: '整车轻量化材料比例', type: 'list', presentation_type: 'radar', is_visible: true, role: '战略与产品', size: '1x1', data_source_id: 'Handelsblatt_DE' },
  { id: 'p28', title: '竞品专利布局强度监控', type: 'list', presentation_type: 'time-series', is_visible: true, role: '战略与产品', size: '1x1', data_source_id: 'Nikkei_Asia' },
  
  // 3. 供应链与采购视角
  { id: 'p7', title: '大宗原材料价格脉搏', type: 'list', presentation_type: 'time-series', is_visible: true, role: '供应链与采购', size: '1x1', data_source_id: 'SMM_METAL_INDEX' },
  { id: 'p8', title: '核心 Tier-1 经营性风险', type: 'list', presentation_type: 'ticker', is_visible: true, role: '供应链与采购', size: '1x1', data_source_id: 'Yonhap_KR' },
  { id: 'p9', title: '全球港口物流异常', type: 'list', presentation_type: 'heatmap', is_visible: true, role: '供应链与采购', size: '1x1', data_source_id: 'MARINE_TRAFFIC_OSINT' },
  { id: 'p17', title: '半导体供应短缺指数', type: 'list', presentation_type: 'time-series', is_visible: true, role: '供应链与采购', size: '1x1', data_source_id: 'Jiemian_News' },
  { id: 'p18', title: '物流通道成本趋势', type: 'list', presentation_type: 'time-series', is_visible: true, role: '供应链与采购', size: '1x1', data_source_id: 'Reuters_Finance' },
  { id: 'p29', title: '动力电池回收链条监测', type: 'list', presentation_type: 'heatmap', is_visible: true, role: '供应链与采购', size: '1x1', data_source_id: '36Kr_AUTO' },
  { id: 'p30', title: '稀有金属库销比动态', type: 'list', presentation_type: 'time-series', is_visible: true, role: '供应链与采购', size: '1x1', data_source_id: 'SMM_METAL_INDEX' },
  { id: 'p31', title: '全球滚装船运力排期', type: 'list', presentation_type: 'time-series', is_visible: true, role: '供应链与采购', size: '1x1', data_source_id: 'MARINE_TRAFFIC_OSINT' },
  { id: 'p32', title: '车规级芯片产能利用率', type: 'list', presentation_type: 'heatmap', is_visible: true, role: '供应链与采购', size: '1x1', data_source_id: 'Yonhap_KR' },
];

export const panels = { 
  list: async (...args: any[]) => MOCK_PANELS,
  public: async (...args: any[]) => MOCK_PANELS, 
  create: async (d: any, ...args: any[]) => ({ ...d, id: Math.random().toString() }), 
  update: async (...args: any[]) => ({}), 
  delete: async (...args: any[]) => ({}) 
};

export const feed = { 
  list: async (...args: any[]) => [],
  public: async (...args: any[]) => [], 
  source: async (...args: any[]) => ({ items: [], data_source_id: args[0] || 's1', fetched_at: new Date().toISOString() }), 
  refresh: async (...args: any[]) => ({}) 
};

export const ai = { 
  interpret: async (...args: any[]) => ({}), summarize: async (...args: any[]) => ({}), extractEntities: async (...args: any[]) => ({}),
  interpretOta: async (...args: any[]) => ({ vehicle_model: 'Tesla Model 3/Y', update_type: '智驾与视觉泊车', description: '本次更新引入了全新的端到端视觉泊车方案，显著提升了在弱光和非标准车位的识别能力。' })
};
export const auth = { login: async (...args: any[]) => ({}), register: async (...args: any[]) => ({}), me: async (...args: any[]) => ({}) };
export const sources = { list: async (...args: any[]) => [], subscriptions: async (...args: any[]) => [], subscribe: async (...args: any[]) => ({}), unsubscribe: async (...args: any[]) => ({}) };
export const layouts = { list: async (...args: any[]) => [], save: async (...args: any[]) => ({}), apply: async (...args: any[]) => ({}), delete: async (...args: any[]) => ({}) };
export const tags = { list: async (...args: any[]) => [], withCounts: async (...args: any[]) => [], categories: async (...args: any[]) => [], create: async (...args: any[]) => ({}), update: async (...args: any[]) => ({}), delete: async (...args: any[]) => ({}) };
export const system = { getSchedulerConfig: async (...args: any[]) => ({ mode: 'auto', fetch_interval: 60, process_interval: 15 }), updateSchedulerConfig: async (...args: any[]) => ({}), forceFetch: async (...args: any[]) => ({}), forceProcess: async (...args: any[]) => ({}), resetDatabase: async (...args: any[]) => ({}) };