# AutoPrism - AI-Driven Intelligent Scraper (Fixed Linkage)
import random
import json
from app.models.sql import RawIntelligence, IntelligenceStatus

class SpecializedScraper:
    """
    重构后的抓取器：所有任务委托给外部传入的 AI 服务进行实时检索。
    """

    @staticmethod
    async def _ai_driven_search(ai_service, panel_id: str, topic: str, keywords: list):
        """
        核心 AI 搜索逻辑：使用传入的 ai_service 实例进行检索。
        """
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        search_query = f"最新的关于 {topic} 的汽车产业情报，重点关注 {', '.join(keywords)}"

        prompt = f"""你是一个具备搜索能力的汽车产业分析专家。
        当前北京时间：{current_time}
        请针对主题：'{search_query}' 在互联网上搜索最新的、属于当前时间点附近的真实情报。如果主题是关于未来某个时间点发生的事情，你可以根据主题进行搜索。
        并形成你的自己的判断和理解，重新组织语言进行输出，你自己的综合判断和理解单独做一条情报条目，来源媒体名和 URL 就用 AUTOPRISM 来代替。
        要求返回至少 10 条高质量、来源不同的情报条目，确保覆盖不同的品牌或地区。
        格式为 JSON 数组：
        [
          {{
            "title": "情报标题",
            "source_name": "来源媒体名",
            "source_url": "来源 URL",
            "content": "情报的完整详细文本内容，请尽可能提供全文或详尽摘要"
          }}
        ]
        """

        try:
            # 使用传入的 ai_service 调用 AI
            ai_raw = await ai_service._call_ai(prompt)
            print(f"DEBUG: AI Search Raw Result Type: {type(ai_raw)}")
            if isinstance(ai_raw, dict) and "choices" not in ai_raw:
                # 打印前 200 个字符看看内容
                print(f"DEBUG: AI Search Content Preview: {str(ai_raw)[:200]}...")

            # 强化解析逻辑
            if isinstance(ai_raw, str):
                try:
                    ai_items = json.loads(ai_raw)
                except: ai_items = []
            elif isinstance(ai_raw, dict):
                # 某些 AI 接口可能把结果包在 choices 或 data 字段里，这里做兼容处理
                ai_items = ai_raw.get("choices", [{}])[0].get("message", {}).get("content", [])
                if isinstance(ai_items, str):
                    try: ai_items = json.loads(ai_items)
                    except: ai_items = []
                # 如果 AI 直接返回了 metrics 字典或列表
                if not isinstance(ai_items, list):
                    ai_items = ai_raw.get("data", ai_raw.get("results", []))
            else:
                ai_items = ai_raw

            if not isinstance(ai_items, list):
                ai_items = []
        except Exception as e:
            print(f"DEBUG: AI Search Logic Error: {str(e)}")
            ai_items = []

        results = []
        for item in ai_items:
            # 提取 URL，如果没有则生成一个伪随机 URL 以满足 L1 唯一性约束
            url = item.get("source_url") or item.get("url")
            if not url:
                import uuid
                url = f"https://ai-intel.internal/{panel_id}/{uuid.uuid4().hex[:8]}"

            results.append(RawIntelligence(
                title=item.get("title", f"AI 实时捕获: {topic}"),
                source_name=item.get("source_name", "AI_Global_Search"),
                source_url=url,
                raw_content=item.get("content", "AI 正在深度检索详情..."),
                target_panel_ids=[panel_id],
                status=IntelligenceStatus.PENDING_AI
            ))
        return results

    # --- 1. 宏观决策视角 (9个) ---
    @staticmethod
    async def fetch_policy_radar(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p1", "全球汽车政策与准入", ["贸易壁垒", "关税", "补贴政策"])

    @staticmethod
    async def fetch_price_adjustments(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p2", "全球车型价格异动", ["价格战", "特斯拉降价", "比亚迪调价"])

    @staticmethod
    async def fetch_geopolitics_risk(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p3", "地缘政治汽车出海", ["出口管制", "海外工厂准入", "地缘摩擦"])

    @staticmethod
    async def fetch_market_share(ai):
        """
        p13: 全球销量市占率大盘 (专项链路加固)
        要求 AI 搜索并返回一个完整的品牌市占率矩阵。
        """
        prompt = """你是一个专业的汽车产业分析师。
        请在全网搜索最新的、属于 2026 年或最近的“全球新能源汽车品牌市场份额”数据。

        要求返回结果必须包含至少 10 个领先品牌（如比亚迪、特斯拉、丰田等）及其对应的百分比份额。

        请以 JSON 格式返回：
        [
          {
            "title": "2026Q1 全球新能源汽车市场格局快报",
            "source_name": "权威机构统计 (如 MarkLines/乘联会)",
            "source_url": "https://stats.authority.com/auto-market-2026",
            "content": "2026年第一季度，全球新能源汽车销量维持高速增长。比亚迪凭借...",
            "metrics": {
               "type": "market_share_matrix",
               "data": [
                 {"brand": "BYD", "share": 22.1, "growth": "+4.5%"},
                 {"brand": "Tesla", "share": 18.5, "growth": "-1.2%"},
                 {"brand": "Toyota", "share": 9.2, "growth": "+12.0%"},
                 {"brand": "Geely", "share": 7.8, "growth": "+6.3%"},
                 {"brand": "VW Group", "share": 6.5, "growth": "+2.1%"}
               ]
            }
          }
        ]
        """
        try:
            ai_items = await ai._call_ai(prompt)
            if not isinstance(ai_items, list): ai_items = []
        except Exception: ai_items = []

        results = []
        for item in ai_items:
            results.append(RawIntelligence(
                title=item.get("title", "全球销量市占率大盘更新"),
                source_name=item.get("source_name", "AI_Matrix_Scanner"),
                source_url=item.get("source_url", "https://ai-search.internal/p13"),
                raw_content=item.get("content", "正在解读市场份额详细矩阵..."),
                target_panel_ids=["p13"],
                status=IntelligenceStatus.PENDING_AI
            ))
        return results

    @staticmethod
    async def fetch_supply_chain_risks(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p14", "汽车供应链断链风险", ["物流中断", "关键零部件短缺", "原材料供应"])

    @staticmethod
    async def fetch_carbon_compliance(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p21", "汽车碳配额排放法规", ["碳价", "ETS", "零排放政策"])

    @staticmethod
    async def fetch_energy_network(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p22", "全球充电换电网络", ["桩数统计", "超充建设", "换电站布局"])

    @staticmethod
    async def fetch_consumer_confidence(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p23", "中国汽车消费信心指数 东方财富 国家统计局", ["信心指数", "环比变动", "宏观趋势"])

    @staticmethod
    async def fetch_ad_legal_framework(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p24", "自动驾驶法律法规", ["L3准入", "责任判定", "测试许可"])

    # --- 2. 战略与产品视角 (9个) ---
    @staticmethod
    async def fetch_ota_evolution(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p4", "重点车型 OTA 版本演进", ["功能更新", "系统升级", "智能座舱迭代"])

    @staticmethod
    async def fetch_tech_roadmap(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p5", "汽车技术路线图演进", ["固态电池", "800V", "滑板底盘"])

    @staticmethod
    async def fetch_ad_benchmarking(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p6", "全球智驾对标性能", ["NOA", "算力水平", "开城进度"])

    @staticmethod
    async def fetch_spec_comparison(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p15", "新车型参数对标", ["零百加速", "续航里程", "智能硬件"])

    @staticmethod
    async def fetch_launch_countdown(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p16", "全球新车型上市倒计时", ["上市日期", "预售价格", "谍照发布"])

    @staticmethod
    async def fetch_cabin_experience(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p25", "智能座舱交互体验评价", ["UXUI", "人机交互", "车载大模型"])

    @staticmethod
    async def fetch_battery_tech(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p26", "动力电池能量密度排行", ["麒麟电池", "电芯技术", "半固态"])

    @staticmethod
    async def fetch_lightweight_data(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p27", "整车轻量化与材料", ["一体压铸", "碳纤维", "高强钢"])

    @staticmethod
    async def fetch_patent_layout(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p28", "汽车竞品专利布局", ["技术壁垒", "专利授权", "IP监控"])

    # --- 3. 供应链与采购视角 (9个) ---
    @staticmethod
    async def fetch_commodity_prices(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p7", "大宗原材料行情", ["碳酸锂", "钴镍价格", "钢材铝材", " copper", "lithium", "nickel", "steel", "aluminum", " aluminium", "graphite", "boron", "neodymium", "tin", "zinc", "lead", "chromium", "titanium", "vanadium", "molybdenum", "cobalt", "nickel", "tungsten", "tantalum", "hafnium", "zirconium", "niobium", "yttrium", "rare earth elements"])

    @staticmethod
    async def fetch_tier1_risks(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p8", "核心 Tier-1 经营风险", ["财务状况", "工厂停产", "信用评级"])

    @staticmethod
    async def fetch_port_congestion(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p9", "全球港口物流状况", ["拥堵指数", "船只延误", "运力紧张", "汽车港口积压", "港口效率"])

    @staticmethod
    async def fetch_semiconductor_intel(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p17", "半导体供应短缺", ["MCU周期", "SiC 产能", "交付延迟", "半导体厂商供应状况"])

    @staticmethod
    async def fetch_logistics_costs(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p18", "汽车物流通道成本", ["航运报价", "海运费率", "物流附加费", "物流通道"])

    @staticmethod
    async def fetch_battery_recycle_intel(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p29", "动力电池回收链条", ["回收率", "黑粉行情", "溯源合规"])

    @staticmethod
    async def fetch_rare_metal_inventory(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p30", "稀有金属库销比", ["库存水位", "供需预测", "开采限制"])

    @staticmethod
    async def fetch_roro_schedules(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p31", "全球滚装船排期", ["船期表", "到港预测", "运力调度"])

    @staticmethod
    async def fetch_chip_capacity_utilization(ai):
        return await SpecializedScraper._ai_driven_search(ai, "p32", "车规芯片产能利用率", ["晶圆厂负载", "制程瓶颈", "供应缺口"])
