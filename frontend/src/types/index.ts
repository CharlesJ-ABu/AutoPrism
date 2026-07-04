// AutoPrism - TypeScript Types

export type DataSourceType = 'rss' | 'api' | 'webpage';
export type PanelType = 'list' | 'number' | 'ai_summary';
export type PanelSize = '1x1' | '2x1' | '2x2';

export interface User {
  id: string;
  email: string;
  ai_quota_used: number;
  created_at: string;
}

export interface DataSource {
  id: string;
  name: string;
  type: DataSourceType;
  url: string;
  config: Record<string, unknown>;
  schema_template?: Record<string, string>;
  global_cache_timeout: number;
  tags: TechTag[];
  created_at: string;
}

export interface TechTag {
  id: string;
  name: string;
  category: string;
  color: string;
  hotness: number;
  article_count?: number;
}

export interface Panel {
  id: string;
  user_id: string;
  data_source_id?: string;
  tag?: string;
  title?: string;
  type: PanelType;
  presentation_type?: 'ticker' | 'time-series' | 'heatmap' | 'radar' | 'gauge';
  size: PanelSize;
  position: { x: number; y: number; w: number; h: number };
  is_visible: boolean;
  role?: string;
  created_at: string;
}

export interface Subscription {
  id: string;
  user_id: string;
  data_source_id: string;
  poll_interval: number;
  is_active: boolean;
  data_source: DataSource;
  panel?: Panel;
}

export interface FeedItem {
  id: string;
  title: string;
  content?: string;
  url?: string;
  published_at?: string;
  tags: string[];
  source_name: string;
  impact_score?: number;
  sentiment?: number;
  geo_tags?: string[];
}

export interface FeedResponse {
  items: FeedItem[];
  data_source_id: string;
  fetched_at: string;
}

export interface LayoutSnapshot {
  id: string;
  user_id: string;
  name?: string;
  layout_config: { panels: Panel[] };
  is_default: boolean;
  created_at: string;
}

export interface AIInterpretation {
  cache_key: string;
  interpretation: {
    summary?: string;
    topics?: string[];
    sentiment?: string;
    entities?: string[];
    error?: string;
  };
  cached: boolean;
}