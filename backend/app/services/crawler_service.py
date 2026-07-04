# AutoPrism - Intelligence Crawler Service (Standardized & AI-Linked)
import asyncio
from typing import List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.sql import RawIntelligence, IntelligenceStatus
from app.api.v1.ws import manager

class CrawlerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_global_sync(self):
        # 延迟导入以防止循环依赖
        from app.services.scrapers.specialized import SpecializedScraper
        from app.services.ai_service import AIService

        # --- 1. 数据库架构自动校验 ---
        try:
            await self.db.execute(text("ALTER TABLE raw_intelligence ADD COLUMN IF NOT EXISTS target_panel_ids JSONB DEFAULT '[]'::jsonb;"))
            await self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS intelligence_info (
                    id UUID PRIMARY KEY,
                    raw_id UUID REFERENCES raw_intelligence(id) ON DELETE CASCADE,
                    title_brief VARCHAR(255) NOT NULL,
                    target_panel_ids JSONB DEFAULT '[]'::jsonb,
                    impact_score INTEGER DEFAULT 50,
                    sentiment FLOAT DEFAULT 0.0,
                    metrics JSONB DEFAULT '{}'::jsonb,
                    geolocation JSONB,
                    involved_entities JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """))
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            await manager.broadcast({"type": "log", "message": f"⚠️ DB Fix Error: {str(e)}", "level": "warning"})

        # --- 2. 准备任务清单 ---
        PANEL_TASKS = [
            {"id": "p1", "name": "全球汽车政策雷达", "scraper": SpecializedScraper.fetch_policy_radar},
            {"id": "p2", "name": "车型调价预警", "scraper": SpecializedScraper.fetch_price_adjustments},
            {"id": "p3", "name": "地缘政治与出海合规", "scraper": SpecializedScraper.fetch_geopolitics_risk},
            {"id": "p13", "name": "全球销量市占率大盘", "scraper": SpecializedScraper.fetch_market_share},
            {"id": "p14", "name": "重大断链风险预警", "scraper": SpecializedScraper.fetch_supply_chain_risks},
            {"id": "p21", "name": "碳配额与排放法规监测", "scraper": SpecializedScraper.fetch_carbon_compliance},
            {"id": "p22", "name": "全球能源补能网络版图", "scraper": SpecializedScraper.fetch_energy_network},
            {"id": "p23", "name": "主要市场消费信心指数", "scraper": SpecializedScraper.fetch_macro_indices},
            {"id": "p24", "name": "自动驾驶法律框架准入", "scraper": SpecializedScraper.fetch_ad_legal_framework},
            {"id": "p4", "name": "重点车型 OTA 演变追踪", "scraper": SpecializedScraper.fetch_ota_evolution},
            {"id": "p5", "name": "技术路径演进图谱", "scraper": SpecializedScraper.fetch_tech_roadmap},
            {"id": "p6", "name": "全球智驾对标", "scraper": SpecializedScraper.fetch_ad_benchmarking},
            {"id": "p15", "name": "重点车型参数对标矩阵", "scraper": SpecializedScraper.fetch_spec_comparison},
            {"id": "p16", "name": "新车型上市倒计时", "scraper": SpecializedScraper.fetch_launch_countdown},
            {"id": "p25", "name": "智能座舱交互体验评价", "scraper": SpecializedScraper.fetch_cabin_experience},
            {"id": "p26", "name": "动力电池能量密度排行", "scraper": SpecializedScraper.fetch_battery_tech},
            {"id": "p27", "name": "整车轻量化材料比例", "scraper": SpecializedScraper.fetch_lightweight_data},
            {"id": "p28", "name": "竞品专利布局强度监控", "scraper": SpecializedScraper.fetch_patent_layout},
            {"id": "p7", "name": "大宗原材料价格脉搏", "scraper": SpecializedScraper.fetch_commodity_prices},
            {"id": "p8", "name": "核心 Tier-1 经营性风险", "scraper": SpecializedScraper.fetch_tier1_risks},
            {"id": "p9", "name": "全球港口物流异常", "scraper": SpecializedScraper.fetch_port_congestion},
            {"id": "p17", "name": "半导体供应短缺指数", "scraper": SpecializedScraper.fetch_semiconductor_intel},
            {"id": "p18", "name": "物流通道成本趋势", "scraper": SpecializedScraper.fetch_logistics_costs},
            {"id": "p29", "name": "动力电池回收链条监测", "scraper": SpecializedScraper.fetch_battery_recycle_intel},
            {"id": "p30", "name": "稀有金属库销比动态", "scraper": SpecializedScraper.fetch_rare_metal_inventory},
            {"id": "p31", "name": "全球滚装船运力排期", "scraper": SpecializedScraper.fetch_roro_schedules},
            {"id": "p32", "name": "车规级芯片产能利用率", "scraper": SpecializedScraper.fetch_chip_capacity_utilization},
        ]

        total_new = 0
        ai_expert = AIService(self.db)
        await manager.broadcast({"type": "log", "message": "🚀 启动全量情报捕获引擎 (27 核心面板同步点火)...", "level": "info"})

        for i, task in enumerate(PANEL_TASKS):
            panel_id = task["id"]
            await manager.broadcast({
                "type": "log",
                "message": f"[{i+1}/{len(PANEL_TASKS)}] 正在委托 AI 进行全球搜索: {panel_id}...",
                "level": "info"
            })
            await asyncio.sleep(0.01)

            try:
                # 1. AI 全球搜索 (存入 L1)
                raw_items = await task["scraper"](ai_expert)
                new_count = 0
                for item in raw_items:
                    tags = set(item.target_panel_ids or [])
                    tags.add(panel_id)
                    item.target_panel_ids = list(tags)

                    stmt = select(RawIntelligence).where(RawIntelligence.source_url == item.source_url)
                    existing = await self.db.execute(stmt)
                    existing_item = existing.scalar_one_or_none()

                    if existing_item:
                        current_tags = set(existing_item.target_panel_ids or [])
                        existing_item.target_panel_ids = list(current_tags.union(tags))
                    else:
                        self.db.add(item)
                        new_count += 1

                await self.db.commit()
                total_new += new_count
                await manager.broadcast({"type": "log", "message": f"✅ {panel_id} 原始情报捕获 (+{new_count})，立即启动 AI 解读...", "level": "success"})

                # 2. 立即启动 AI 专家对该面板的数据进行解读 (存入 INFO 库)
                processed_count = await ai_expert.process_pending_intelligence(limit=50, target_panel_id=panel_id)

                await manager.broadcast({
                    "type": "log",
                    "message": f"✨ 面板 {panel_id} 已点火完毕: {processed_count} 条结构化指标已同步至 INFO 库。",
                    "level": "success"
                })

                # 3. 进度条与 WS 广播
                await manager.broadcast({
                    "type": "progress", "task": "CRAWLER_SYNC",
                    "progress": int(((i+1)/len(PANEL_TASKS))*100),
                    "message": f"ACTIVE_PANEL: {panel_id}"
                })
                await asyncio.sleep(0.01)

            except Exception as e:
                await self.db.rollback()
                await manager.broadcast({"type": "log", "message": f"❌ {panel_id} 链路中断: {str(e)}", "level": "error"})

        await manager.broadcast({"type": "log", "message": "🏁 全量情报链路同步圆满结束，27 个面板已全部进入实时监控状态。", "level": "info"})
        return total_new

    async def run_panel_sync(self, target_panel_id: str):
        from app.services.scrapers.specialized import SpecializedScraper
        from app.services.ai_service import AIService

        PANEL_TASKS = {
            "p1": {"name": "全球汽车政策雷达", "scraper": SpecializedScraper.fetch_policy_radar},
            "p2": {"name": "车型调价预警", "scraper": SpecializedScraper.fetch_price_adjustments},
            "p3": {"name": "地缘政治与出海合规", "scraper": SpecializedScraper.fetch_geopolitics_risk},
            "p4": {"name": "重点车型 OTA 演变追踪", "scraper": SpecializedScraper.fetch_ota_evolution},
            "p5": {"name": "技术路径演进图谱", "scraper": SpecializedScraper.fetch_tech_roadmap},
            "p6": {"name": "全球智驾对标", "scraper": SpecializedScraper.fetch_ad_benchmarking},
            "p7": {"name": "大宗原材料价格脉搏", "scraper": SpecializedScraper.fetch_commodity_prices},
            "p8": {"name": "核心 Tier-1 经营性风险", "scraper": SpecializedScraper.fetch_tier1_risks},
            "p9": {"name": "全球港口物流异常", "scraper": SpecializedScraper.fetch_port_congestion},
            "p13": {"name": "全球销量市占率大盘", "scraper": SpecializedScraper.fetch_market_share},
            "p14": {"name": "重大断链风险预警", "scraper": SpecializedScraper.fetch_supply_chain_risks},
            "p15": {"name": "重点车型参数对标矩阵", "scraper": SpecializedScraper.fetch_spec_comparison},
            "p16": {"name": "新车型上市倒计时", "scraper": SpecializedScraper.fetch_launch_countdown},
            "p17": {"name": "半导体供应短缺指数", "scraper": SpecializedScraper.fetch_semiconductor_intel},
            "p18": {"name": "物流通道成本趋势", "scraper": SpecializedScraper.fetch_logistics_costs},
            "p21": {"name": "碳配额与排放法规监测", "scraper": SpecializedScraper.fetch_carbon_compliance},
            "p22": {"name": "全球能源补能网络版图", "scraper": SpecializedScraper.fetch_energy_network},
            "p23": {"name": "中国市场消费信心指数", "scraper": SpecializedScraper.fetch_consumer_confidence},
            "p24": {"name": "自动驾驶法律框架准入", "scraper": SpecializedScraper.fetch_ad_legal_framework},
            "p25": {"name": "智能座舱交互体验评价", "scraper": SpecializedScraper.fetch_cabin_experience},
            "p26": {"name": "动力电池能量密度排行", "scraper": SpecializedScraper.fetch_battery_tech},
            "p27": {"name": "整车轻量化材料比例", "scraper": SpecializedScraper.fetch_lightweight_data},
            "p28": {"name": "竞品专利布局强度监控", "scraper": SpecializedScraper.fetch_patent_layout},
            "p29": {"name": "动力电池回收链条监测", "scraper": SpecializedScraper.fetch_battery_recycle_intel},
            "p30": {"name": "稀有金属库销比动态", "scraper": SpecializedScraper.fetch_rare_metal_inventory},
            "p31": {"name": "全球滚装船运力排期", "scraper": SpecializedScraper.fetch_roro_schedules},
            "p32": {"name": "车规级芯片产能利用率", "scraper": SpecializedScraper.fetch_chip_capacity_utilization},
        }

        task = PANEL_TASKS.get(target_panel_id)
        if not task:
            return False

        ai_expert = AIService(self.db)
        await manager.broadcast({"type": "log", "message": f"🎯 单点触发: 正在同步面板 {target_panel_id} ({task['name']})...", "level": "info"})

        try:
            # 1. 抓取 (AI 搜索)
            await manager.broadcast({"type": "log", "message": f"🔍 阶段 1/2: 正在委托 AI 引擎进行全球深度搜索...", "level": "info"})
            raw_items = await task["scraper"](ai_expert)
            new_count = 0
            for item in raw_items:
                tags = set(item.target_panel_ids or [])
                tags.add(target_panel_id)
                item.target_panel_ids = list(tags)

                stmt = select(RawIntelligence).where(RawIntelligence.source_url == item.source_url)
                res = await self.db.execute(stmt)
                existing_item = res.scalar_one_or_none()
                if existing_item:
                    current_tags = set(existing_item.target_panel_ids or [])
                    existing_item.target_panel_ids = list(current_tags.union(tags))
                else:
                    self.db.add(item)
                    new_count += 1

            await self.db.commit()
            await manager.broadcast({"type": "log", "message": f"📥 阶段 1/2 完成: 成功捕获 {new_count} 条潜在关联情报。", "level": "success"})

            # 2. AI 处理 (解读)
            await manager.broadcast({"type": "log", "message": f"🧠 阶段 2/2: 启动 AI 降噪与高保真数据结构化...", "level": "info"})
            processed_count = await ai_expert.process_pending_intelligence(limit=50, target_panel_id=target_panel_id)

            await manager.broadcast({
                "type": "log",
                "message": f"✨ 面板 {target_panel_id} 数据链路同步圆满成功! 已解析 {processed_count} 条核心指标。",
                "level": "success"
            })
            return True
        except Exception as e:
            await self.db.rollback()
            await manager.broadcast({"type": "log", "message": f"❌ 面板 {target_panel_id} 同步失败: {str(e)}", "level": "error"})
            return False
