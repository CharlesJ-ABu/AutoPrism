import httpx
import json
import logging
import random
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.sql import RawIntelligence, IntelligenceInfo, IntelligenceStatus, StrategicInsight
from app.core.config import settings
from app.api.v1.websocket import manager

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        # 同步前端 MOCK_PANELS 定义的角色与面板映射
        self.persona_panels = {
            "宏观决策": ["p1", "p2", "p3", "p13", "p14", "p21", "p22", "p23", "p24"],
            "战略与产品": ["p4", "p5", "p6", "p15", "p16", "p25", "p26", "p27", "p28"],
            "供应链与采购": ["p7", "p8", "p9", "p17", "p18", "p29", "p30", "p31", "p32"],
            "全量情报": ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p13", "p14", "p15", "p16", "p17", "p18", "p21", "p22", "p23", "p24", "p25", "p26", "p27", "p28", "p29", "p30", "p31", "p32"]
        }
        self.tech_hubs = [
            {"lat": 39.9, "lng": 116.4, "name": "Beijing, China"},
            {"lat": 31.2, "lng": 121.5, "name": "Shanghai, China"},
            {"lat": 34.0, "lng": -118.2, "name": "Los Angeles, USA"},
            {"lat": 48.8, "lng": 2.3, "name": "Paris, France"},
            {"lat": 35.7, "lng": 139.7, "name": "Tokyo, Japan"}
        ]

    async def generate_strategic_insight(self, role: str) -> bool:
        """
        基于角色触发 AI 降噪与战略洞察合成 (L2 生成逻辑)
        """
        await manager.broadcast({
            "type": "log",
            "message": f"🤖 角色 [{role}] 战略研判引擎启动：正在聚合跨面板情报...",
            "level": "info"
        })
        target_panels = self.persona_panels.get(role, self.persona_panels["全量情报"])

        # 1. 聚合 INFO 面板数据 (按面板分组各取 5 条)
        info_items = []
        for pid in target_panels:
            stmt = select(IntelligenceInfo).where(
                IntelligenceInfo.target_panel_ids.contains([pid])
            ).order_by(desc(IntelligenceInfo.created_at)).limit(5)
            res = await self.db.execute(stmt)
            info_items.extend(res.scalars().all())

        # 2. 聚合 L1 原始情报 (增加到 50 条全局快讯)
        l1_stmt = select(RawIntelligence).where(
            RawIntelligence.status == IntelligenceStatus.PROCESSED
        ).order_by(desc(RawIntelligence.created_at)).limit(50)
        l1_res = await self.db.execute(l1_stmt)
        l1_items = l1_res.scalars().all()

        if not info_items and not l1_items:
            return False

        # 构造聚合上下文 (增加对数据总量的统计反馈)
        context = f"### [视角: {role}] 最新面板指标数据 (共 {len(info_items)} 条):\n"
        for it in info_items:
            context += f"- [面板:{it.target_panel_ids}] {it.title_brief}: {json.dumps(it.metrics, ensure_ascii=False)}\n"

        context += f"\n### 最新原始情报快讯 (共 {len(l1_items)} 条):\n"
        for it in l1_items:
            context += f"- {it.title}: {it.raw_content[:300]}...\n"

        # 3. 构造战略 Prompt
        role_desc = {
            "宏观决策": "侧重全球政策、地缘政治风险、宏观经济指数与出海合规。",
            "战略与产品": "侧重竞品 OTA、技术路线图、参数对标矩阵、新车上市节奏与座舱体验。",
            "供应链与采购": "侧重原材料价格、Tier-1 风险、港口物流、半导体供应、轻量化材料与芯片产能。",
            "全量情报": "全视角扫描，寻找跨板块关联及全局系统性风险。"
        }

        prompt = f"""你是一个世界顶尖的汽车产业战略分析师。你现在的视角是：【{role}】({role_desc.get(role)})。

        ### 任务：
        请分析下述聚合情报，并可以根据你对你角色视角的理解，在网上进行搜索查阅最新的情报，综合所有的信息，提炼出至少 10 条对该角色最重要的【战略洞察和建议】，并将其映射到地图展示语义上。

        ### 数据背景：
        {context}

        ### 洞察生成与地图展示规范：
        每条洞察必须严格包含以下字段，用于地图弹窗和渲染：
        1. "title": 标题（需极具战略冲击力，并且需要给出行动建议）。
        2. "display_type": 必须从以下枚举中选择：
           - HOTSPOT: 脉冲热点，用于突发事件或风险预警。
           - FLOW: 动态轨迹，用于展示供应链转移、物流走向或技术扩散。
           - ZONE: 区域张力色块，用于政策影响区、碳配额成本区或宏观情绪分布。
           - MARKER: 精确坐标标杆，用于新车上市点、竞品专利中心或座舱实测口碑。
           - RIPPLE: 波纹扩散，用于展示爆款产品的虹吸效应或重大风险的事件传导。
           - COMPARISON: 竞争博弈连线，用于展示两地/两企之间的专利战、价格战或技术路线博弈。
           - SHIELD_UP: 国界壁垒光墙，用于展示关税壁垒、准入限制或合规封锁。
        3. "geo_coordinates": 存储关联地理位置。对于 FLOW/COMPARISON 类型需存储 {{"lat": 0.0, "lng": 0.0, "end_lat": 0.0, "end_lng": 0.0}}，其余为单点坐标 {{"lat": 0.0, "lng": 0.0, "label": "地区名"}}。
        4. "summary": 一句话核心结论。
        5. "analysis": {{
             "situation": "现状描述",
             "implication": "潜在影响",
             "horizon": "SHORT | MEDIUM | LONG",
             "impact_scale": "LOCAL | REGIONAL | GLOBAL"
           }}
        6. "strategic_advice": 针对该角色的专业行动建议。
        7. "priority": 1-4 (4最高)。
        8. "affected_panels": 关联到的面板 ID 列表。
        9. "sentiment": 情绪/风险评分。范围 -1.0 到 1.0。风险/负面影响为负数（-1.0最严重），机遇/正面影响为正数（1.0最大），中性为 0。

        请严格按 JSON 数组格式返回。}}
        """

        try:
            raw_res = await self._call_ai(prompt)

            # 智能解析：寻找数组字段 (支持 "insights", "results", "data" 等常见包装名)
            ai_results = []
            if isinstance(raw_res, list):
                ai_results = raw_res
            elif isinstance(raw_res, dict):
                # 寻找字典里第一个是列表的字段
                for val in raw_res.values():
                    if isinstance(val, list):
                        ai_results = val
                        break
                if not ai_results:
                    ai_results = [raw_res] # 兜底：单对象转列表

            for res in ai_results:
                if not res.get("title") and not res.get("summary"): continue # 跳过空结果

                insight = StrategicInsight(
                    role=role,
                    title=res.get("title", "战略合成洞察"),
                    summary=res.get("summary", ""),
                    sentiment=float(res.get("sentiment", 0.0)),
                    display_type=res.get("display_type", "HOTSPOT"),
                    geo_coordinates=res.get("geo_coordinates", {}),
                    priority=int(res.get("priority", 2)),
                    affected_panels=res.get("affected_panels", []),
                    analysis=res.get("analysis", {}),
                    strategic_advice=res.get("strategic_advice", "")
                )
                self.db.add(insight)
                await self.db.flush() # 获取 ID
                print(f"--- [DEBUG] StrategicInsight created: ID={insight.id}, Role={role} ---")

            await self.db.commit()
            print(f"--- [DEBUG] All insights committed successfully. ---")

            await manager.broadcast({
                "type": "log",
                "message": f"✨ 角色 [{role}] 的战略洞察合成完毕，已新增 {len(ai_results)} 条 L2 地图情报。",
                "level": "success"
            })
            return True
        except Exception as e:
            logger.error(f"Strategic insight generation failed: {str(e)}")
            await self.db.rollback()
            return False

    async def process_pending_intelligence(self, limit: int = 50, target_panel_id: str = None) -> int:
        """
        重构: 批量处理逻辑。
        target_panel_id: 如果传入，则仅处理该面板的积压任务。
        """
        stmt = select(RawIntelligence).where(RawIntelligence.status == IntelligenceStatus.PENDING_AI)
        if target_panel_id:
            # 使用 array_contains 的等效逻辑进行过滤
            stmt = stmt.where(RawIntelligence.target_panel_ids.contains([target_panel_id]))

        result = await self.db.execute(stmt.limit(limit))
        items = result.scalars().all()
        if not items: return 0

        # 按面板 ID 分组
        panel_groups = {}
        for item in items:
            pid = item.target_panel_ids[0] if item.target_panel_ids else "generic"
            if pid not in panel_groups: panel_groups[pid] = []
            panel_groups[pid].append(item)

        total_processed = 0
        for pid, group in panel_groups.items():
            # 聚合内容：把这组情报的标题和正文打包
            aggregated_content = "\n---\n".join([f"ID:{idx} | Title:{it.title} | Content:{it.raw_content[:500]}" for idx, it in enumerate(group)])

            handler = getattr(self, f"_handle_{pid}", self._handle_generic)
            prompt = handler(aggregated_content)

            try:
                # 调用 AI 获取 JSON 数组
                ai_results = await self._call_ai(prompt)
                if not isinstance(ai_results, list):
                    # 如果 AI 返回的不是列表，尝试看是不是包在 metrics 或 results 里
                    if isinstance(ai_results, dict):
                        ai_results = ai_results.get("results", ai_results.get("data", [ai_results]))
                    else:
                        ai_results = [ai_results]

                # 遍历 AI 生成的每一条结构化结果
                for res in ai_results:
                    if not isinstance(res, dict): continue

                    info_entry = IntelligenceInfo(
                        raw_id=group[0].id, # 批量模式下挂载到组内第一条
                        title_brief=res.get("title_brief", "AI 聚合解析结果"),
                        target_panel_ids=res.get("target_panel_ids", [pid]),
                        impact_score=int(res.get("impact_score", 50)),
                        sentiment=float(res.get("sentiment", 0.0)),
                        geolocation=res.get("geolocation"),
                        involved_entities=res.get("involved_entities", []),
                        metrics=res.get("metrics", res) # 兼容性处理
                    )
                    # 关键补丁：确保 reasoning 在 metrics 内部
                    if "reasoning" in res and "reasoning" not in info_entry.metrics:
                        info_entry.metrics["reasoning"] = res["reasoning"]

                    self.db.add(info_entry)
                    total_processed += 1

                # 标记这组原始情报为已处理
                for item in group:
                    item.status = IntelligenceStatus.PROCESSED

                await self.db.commit()

                await manager.broadcast({
                    "type": "log",
                    "message": f"🧠 面板 {pid} 批量解读完成: 解析出 {len(ai_results)} 条结构化情报。",
                    "level": "success"
                })

            except Exception as e:
                logger.error(f"Batch processing failed for {pid}: {str(e)}")
                await self.db.rollback()

        return total_processed

    async def _call_ai(self, prompt: str) -> any:
        import asyncio
        max_retries = 3
        retry_delay = 2.0

        async with httpx.AsyncClient(timeout=120.0) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(
                        f"{settings.AI_API_BASE}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {settings.AI_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": settings.AI_MODEL,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.3,
                            "response_format": {"type": "json_object"}
                        }
                    )

                    if response.status_code == 200:
                        result = response.json()
                        content = result["choices"][0]["message"]["content"]
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0].strip()

                        try:
                            return json.loads(content)
                        except:
                            print(f"⚠️ JSON Parse Error: {content[:200]}...")
                            return []

                    if response.status_code in [503, 429, 502] and attempt < max_retries - 1:
                        print(f"⚠️ AI API Busy/Overload ({response.status_code}), retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                        continue

                    print(f"❌ AI API Error: {response.status_code} - {response.text}")
                    return []

                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"⚠️ AI API Connection Exception ({type(e).__name__}): {str(e)}, retrying...")
                        await asyncio.sleep(retry_delay)
                        continue
                    return []
            return []

    def _simulate_ai_processing(self, raw_item: RawIntelligence) -> dict:
        return {
            "title_brief": f"[Sim] {raw_item.title[:30]}",
            "impact_score": 70,
            "sentiment": 0.5,
            "geolocation": random.choice(self.tech_hubs),
            "involved_entities": ["Auto-Analyst"],
            "target_panel_ids": raw_item.target_panel_ids,
            "metrics": {"status": "analyzed"}
        }

    # =========================================================================
    # 27 个面板专项处理器 (Handler Functions)
    # =========================================================================

    def _handle_p1(self, content):
        """p1: 全球汽车政策雷达 - 升级: 支持批量处理 L1 原始情报"""
        return f"""你是一个资深的全球贸易与汽车政策分析师。请分析下述一批原始政策情报。

        要求：
        1. 对这批情报进行深度解读，将其转化为一组结构化的政策信号。
        2. 如果多条原始情报指向同一个政策事件，请进行合并去重。
        3. 返回格式必须是一个 JSON 数组，数组中的每个对象必须包含以下 metrics 字段：
           - "title_brief": 15字以内的极简政策标题。
           - "impact_score": 0-100。
           - "sentiment": -1.0 到 1.0。
           - "reasoning": 政策核心内容的极简摘要 (20字以内)，供前端列表显示。
           - "region": 国家或地区 (如 "欧盟", "美国", "东南亚")。
           - "summary": 详细的政策解读。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p2(self, content):
        """p2: 车型调价预警 - 升级: 支持批量处理"""
        return f"""你是一个汽车市场价格分析师。请分析下述一批车型调价原始信息。

        要求：
        1. 提取所有涉及的车型调价事件，转化为 JSON 数组。
        2. 每个数组对象必须包含以下 metrics 字段：
           - "brand": 品牌名称。
           - "model": 具体车型。
           - "old_price": 调价前价格，请你用万为单位，带上货币符号，如¥15.5W。
           - "new_price": 调价后价格，请你用万为单位，带上货币符号，如¥15.5W。
           - "change": 变动绝对值或比例 (如 "¥15.5W" 或 "¥0.5W" 或 "5%")，一定要带单位和货币符号或者百分比%，W 代表万，K 代表千。
           - "type": 调价类型 ("Official" 官方调价 或 "Dealer" 终端优惠)。
           - "trend": "UP" (涨价) 或 "DOWN" (降价)。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p3(self, content):
        """p3: 地缘政治与出海合规 - 升级: 支持批量处理"""
        return f"""你是一个国际战略分析师。请分析下述一批涉及汽车出海的地缘政治原始情报。

        要求：
        1. 解读这些事件对车企出海的影响，转化为 JSON 数组。
        2. 每个数组对象必须包含以下 metrics 字段：
           - "region": 涉及国家或地区。
           - "risk_level": 必须是 "CRITICAL", "WARNING", 或 "MODERATE" 之一。
           - "tariff": 关税变动说明 (如 "25% -> 38.1%")。
           - "barrier": 具体的非关税壁垒描述。
           - "impact": 简短的行业影响分析。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p4(self, content):
        """p4: 重点车型 OTA 演变追踪 - 升级: 支持批量处理"""
        return f"""你是一个智能汽车软件专家。请分析下述一批 OTA 升级信息。

        要求：
        1. 提取所有 OTA 升级事件，转化为 JSON 数组。
        2. 每个数组对象必须包含以下 metrics 字段：
           - "brand": 品牌。
           - "model": 车型。
           - "version": 软件版本号。
           - "features": 核心升级内容列表 (如 ["新增自动泊车", "优化智驾算法"])。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p5(self, content):
        """p5: 技术路径演进图谱 - 升级: 支持批量处理"""
        return f"""你是一个前瞻技术分析师。请分析下述一批汽车技术路线图相关信息。

        要求：
        1. 识别关键的技术里程碑或演进节点，转化为 JSON 数组。
        2. 每个数组对象必须包含以下 metrics 字段：
           - "year": 预计发生的年份 (如 "2025", "2027")。
           - "track": 技术赛道 (必须是 "Energy", "AD", 或 "EE" 之一)。
           - "milestone": 里程碑事件描述。
           - "impact_score": 0-100 (量产/成熟 >80, 试点/预研 50, 基础研究 <30)。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p6(self, content):
        """p6: 全球智驾对标 - 升级: 支持批量处理"""
        return f"""你是一个自动驾驶评测专家。请从下述一批情报中提取各品牌智驾系统的对标数据。

        要求：
        1. 提取不同系统的核心性能指标，转化为 JSON 数组。
        2. 每个数组对象必须包含以下 metrics 字段：
           - "name": 系统名称 (如 "Tesla FSD v13", "Huawei ADS 4.0")。
           - "tops": 算力 (数值，如 508)。
           - "perception": 感知能力评分 (0-100)。
           - "iq": 智能交互评分 (0-100)。
           - "safety": 安全接管表现评分 (0-100)。
           - "coverage": 城市 NOA 覆盖率评分 (0-100)。
           - "ux": 用户体验评分 (0-100)。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p7(self, content):
        """p7: 大宗原材料价格脉搏 - 升级: 支持批量处理"""
        return f"""你是一个大宗商品分析师。请分析下述一批原材料价格情报。

        要求：
        1. 提取所有涉及的原材料价格变动，转化为 JSON 数组。
        2. 每个数组对象必须包含以下 metrics 字段：
           - "name": 原材料名称 (如 "锂", "钴", "镍", "铝")。
           - "price": 当前价格数值。
           - "unit": 价格单位 (如 "万元/吨")。
           - "change": 价格变动百分比 (如 "+2.3%")。
           - "sentiment": 1.0 (价格下跌利好) 到 -1.0 (价格上涨利空)。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p8(self, content):
        """p8: 核心 Tier-1 经营性风险 - 升级: 支持批量处理"""
        return f"""你是一个供应链风险管理专家。请分析下述一批供应商经营情报。

        要求：
        1. 识别各供应商的经营风险，转化为 JSON 数组。
        2. 每个数组对象必须包含以下 metrics 字段：
           - "name": 供应商名称 (如 "Bosch", "CATL", "Continental")。
           - "risk_score": 0-100 (分数越高风险越大)。
           - "margin": 利润率情况描述。
           - "rating": 内部风险评级 (A/B/C/D)。
           - "status": 运营状态 ("Stable", "Warning", "Crisis")。
           - "risks": 具体风险项列表。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p9(self, content):
        """p9: 全球港口物流异常 - 升级: 支持批量处理"""
        return f"""你是一个物流专家。请分析下述一批港口物流情报。

        要求：
        1. 识别港口异常情况，转化为 JSON 数组。
        2. 每个数组对象必须包含以下 metrics 字段：
           - "port": 港口名称 (如 "上海港", "鹿特丹", "长滩")。
           - "location": 坐标或具体位置。
           - "wait": 平均等泊天数 (数值，如 3.5)。
           - "status": 拥堵状态 ("Normal", "Congested", "Severe")。
           - "impact_score": 0-100。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p13(self, content):
        """p13: 全球销量市占率大盘 - 升级: 支持批量处理"""
        return f"""你是一个行业数据分析师。请分析下述一批销量与市占率情报。

        要求：
        1. 提取各品牌的市场份额数据，转化为 JSON 数组。
        2. 每个数组对象必须包含以下 metrics 字段：
           - "brand": 品牌名称。
           - "share": 市占率百分比数值 (如 15.2)。
           - "change": 份额变动 (如 "+0.8%")。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p14(self, content):
        """p14: 重大断链风险预警 - 升级: 支持批量处理"""
        return f"""你是一个供应链危机专家。请分析下述一批断链风险情报，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
		- "title": 风险标题 (如 "波斯湾局势升级").
        - "category": 必须是 "Logistics" (物流), "Material" (原材料), 或 "Production" (生产) 之一。
        - "impact": 具体的产能或影响描述 (如 "预计造成周产能下降15%")。
        - "delay": 预计延迟时间 (如 "14天" 或 "未知")。
        - "location": 风险发生地。
        - "impact_score": 0-100 (越严重分越高)。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p15(self, content):
        """p15: 重点车型参数对标矩阵 - 升级: 支持批量处理"""
        return f"""你是一个专业的汽车技术分析师。请提取下述一批车型的核心参数，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "brand": 品牌。
        - "model": 车型全称。
        - "acceleration": 0-100km/h 耗时 (只需数值，如 "3.3")。
        - "range": 续航里程 (只需数值，如 "750")。
        - "power": 峰值功率 (如 "495kW")。
        - "tech": 核心智驾/平台技术 (如 "Orin-X", "800V")。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p16(self, content):
        """p16: 新车型上市倒计时 - 升级: 支持批量处理"""
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""你是一个追踪新车动态的专家。请从下述内容中提取一批新车上市信息，转化为 JSON 数组。

        当前北京时间：{current_time}

        要求每个对象 metrics 字典必须包含：
        - "brand": 品牌。
        - "model": 车型。
        - "status": 状态关键词，必须是 "Spy shots" (谍照), "Announcement" (官宣), "Pre-sale" (预售), 或 "Delivery" (交付) 之一。
        - "date": 预计上市日期 (YYYY-MM-DD)。
        - "days": 距离上市的预估天数数值。
        - "price": 预估价格区间 (如 "25-30万")。
        - "impact_score": 0-100 (市场关注度/热度)。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p17(self, content):
        """p17: 半导体供应短缺指数 - 升级: 支持批量处理"""
        return f"""你是一个半导体产业分析师。请分析下述一批芯片供应情报，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "type": 芯片类别 (如 "MCU", "IGBT", "SiC")。
        - "lead_time": 交付周期 (如 "52周", "无库存")。
        - "stress": 0-100 压力值 (数值越大表示越短缺)。
        - "parts": 涉及的关键零部件名称 (如 "逆变器芯片", "车身控制器")。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p18(self, content):
        """p18: 物流通道成本趋势 - 升级: 支持批量处理"""
        return f"""你是一个物流成本控制专家。请分析下述一批物流成本情报，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "mode": 必须是 "Sea" (海运/滚装), "Rail" (中欧班列), 或 "Air" (空运) 之一。
        - "route": 航线或通道名称 (如 "中国-欧洲", "中国-墨西哥")。
        - "price": 运输价格，需要带货币符号与单位，例如 10000 USD/FEU，如果没有具体价格，可以不填。
        - "change": 变动字符串 (如 "+12%" 或 "-$200")。
        - "transit": 运输时长参考 (如 "35天", "12天")。
        - "sentiment": -1.0 到 1.0 (涨价为负)。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p21(self, content):
        """p21: 碳配额与排放法规监测 - 升级: 支持批量处理"""
        return f"""你是一个 ESG 与环境合规专家。请分析下述一批碳市场或排放法规信息，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "market": 市场名称 (如 "欧盟 ETS", "中国碳市场")。
        - "price": 当前价格数值。
        - "currency": 货币单位 (如 "EUR", "CNY")。
        - "change": 价格变动 (如 "+1.5%")。
        - "date": 关键日期 (YYYY-MM-DD)。
        - "title_brief": 极简法规名称。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p22(self, content):
        """p22: 全球能源补能网络版图 - 升级: 支持批量处理"""
        return f"""你是一个电动汽车补能专家。请分析下述一批补能网络情报，转化为 JSON 数组。
        请注意，同一个统计区域的数据请在一个对象进行数据的整合，例如小鹏在中国的充电站 2000 个，蔚来在中国充电站 3000 个，其实都属于中国的供能体系，这样才能算出来某个区域真正的供能情况。
        要求每个对象 metrics 字典必须包含：
        - "region": 统计区域。
        - "total": 累计充电桩/站总数。
        - "ratio": 车桩比。
        - "fast_percent": 快充占比 (0-100)。
        - "stations": 核心站点列表 (包含 brand, count, type)。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p23(self, content):
        """p23: 中国市场消费信心指数 - 升级: 支持批量处理"""
        return f"""你是一个宏观经济分析师。请分析下述一批宏观情报，转化为 JSON 数组。
        要求提取字段：
        1. metrics 字典必须包含：
           - "region": 目标市场+月份 (如 "中国 2026-01", "北美 2026-01", "西欧 2026-01")。
           - "score": 指数值 (如 "105.2")。
           - "change": 环比或同比变动 (如 "+1.2%")。
           - "factors": 影响信心的核心因素列表 (如 ["降息预期", "油价上涨"])。
        2. sentiment: -1.0 到 1.0 (信心提升为正)。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p24(self, content):
        """p24: 自动驾驶法律框架准入 - 升级: 支持批量处理"""
        return f"""你是一个自动驾驶法规专家。请分析下述一批法规情报，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "region": 国家或城市。
        - "level": 自动驾驶等级 (如 "L3", "L4")。
        - "status": 准入状态 ("Licensed", "Pilot", "Testing")。
        - "liability": 责任归属描述。
        - "speed": 最高限速。
        - "note": 核心条款摘要。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p25(self, content):
        """p25: 智能座舱交互体验评价 - 升级: 支持批量处理"""
        return f"""你是一个智能座舱专家。请对下述一批座舱系统进行评分，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "brand": 品牌/系统名。
        - "ai": AI 助手评分 (0-100)。
        - "fluidity": 流畅度分 (0-100)。
        - "ecosystem": 生态分 (0-100)。
        - "multimodal": 交互分 (0-100)。
        - "audio": 视听分 (0-100)。
        - "connectivity": 连接分 (0-100)。
        - "quote": 一句话核心评价。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p26(self, content):
        """p26: 动力电池能量密度排行 - 升级: 支持批量处理"""
        return f"""你是一个动力电池专家。请分析下述一批电池情报，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "model": 电池技术名称。
        - "brand": 制造商。
        - "density": 能量密度数值。
        - "type": 电池类型 ("LFP", "NCM", "Solid")。
        - "status": 当前状态。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p27(self, content):
        """p27: 整车轻量化材料比例 - 升级: 支持批量处理"""
        return f"""你是一个车身工程专家。请分析下述一批车身材料情报，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "model": 车型。
        - "brand": 品牌。
        - "composition": {{"aluminum": 0, "steel": 0, "carbon": 0, "magnesium": 0, "others": 0}}。
        - "reduction": 减重效果。
        - "tech": 核心技术。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p28(self, content):
        """p28: 竞品专利布局强度监控 - 升级: 支持批量处理"""
        return f"""你是一个 IP 分析师。请分析下述一批企业专利情报，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "brand": 企业名称。
        - "domain": 技术领域。
        - "intensity": 布局强度分值 (0-100)。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p29(self, content):
        """p29: 动力电池回收链条监测 - 升级: 支持批量处理"""
        return f"""你是一个电池回收专家。请分析下述一批情报，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "yield": 回收得率。
        - "volume": 处理规模。
        - "metal": 特定金属。
        - "rate": 提取率。
        - "trend": 趋势 ("up", "down")。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p30(self, content):
        """p30: 稀有金属库销比动态 - 升级: 支持批量处理"""
        return f"""你是一个金属产业研究员。请分析下述一批金属库存情报，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "name": 中文金属名称。
        - "ratio": 库销比数值。
        - "status": 供应状态 ("Deficit", "Surplus", "Balanced")。
        - "level": 库存水位 (0-100)。
        - "trend": 库存趋势 ("up", "down")。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p31(self, content):
        """p31: 全球滚装船运力排期 - 升级: 支持批量处理"""
        return f"""你是一个航运调度专家。请分析下述一批滚装船情报，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "vessel": 船名。
        - "fleet": 所属方。
        - "route": 航线。
        - "status": 状态 ("In Transit", "At Port", "Detouring")。
        - "eta": 到港日期 (YYYY-MM-DD)。
        - "utilization": 装载率。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_p32(self, content):
        """p32: 车规级芯片产能利用率 - 升级: 支持批量处理"""
        return f"""你是一个半导体制造专家。请分析下述一批芯片产能情报，转化为 JSON 数组。

        要求每个对象 metrics 字典必须包含：
        - "node": 工艺节点。
        - "utilization": 利用率数值。
        - "status": 状态 ("Critical", "Tight", "Healthy")。
        - "client": 涉及客户。

        待分析情报集合：
        {content}

        请严格按 JSON 数组格式输出。"""

    def _handle_generic(self, content):
        return [{"title_brief": "通用情报解读", "metrics": {"content": content[:500]}}]
