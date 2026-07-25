# AutoPrism V1 可靠性重构说明

## 目标与分支边界

本次只修复 `main` 的 V1 本地版，不把认证、组织、Redis Worker 或动态面板体系反向移植进来。

- `main`：无需认证的本地版，保持 V1 界面风格。
- `v2`：可靠采集、证据计算和动态面板的演进版本。
- `saas`：组织、角色权限、每组织数据库、加密凭证库和供应商无关模型配置。

## 数据分层

1. **L1 / `raw_intelligence`**：原始数据库快照。
2. **INFO / `intelligence_info`**：按面板要求生成的结构化记录。
3. **L2 / `strategic_insights`**：仅分析已有数据库内容生成的战略洞察。

INFO 与 L1 通过 `intelligence_info_evidence` 多对多关联。API 返回证据 URL、来源、摘要、内容哈希、抓取时间、验证状态和修订号。

## 不可变历史

L1 使用 `source_url + content_hash` 识别快照：

- 内容未变化：不重复插入。
- 内容变化：新增记录，`revision + 1`，并用 `supersedes_id` 指向旧版本。
- 旧记录不覆盖、不删除。
- 重构前的数据统一回填为 `legacy_unverified`。

数据库版本由 Alembic 管理：

- `8a9c3d4e5f60`：兼容曾由 V2 使用过的本地数据库。
- `0001_v1_evidence_chain`：创建或升级 V1 证据字段与关联表。
- `0002_backfill_legacy_evidence`：回填旧 INFO 的 L1 关联和验证标记。

## 数值可信度

- 模型只能返回候选字段和数值。
- 类型、范围和枚举由代码校验。
- `impact_score`、`sentiment` 等核心字段缺失或越界时，整条结果拒绝。
- 不使用 `0`、`50`、`NA`、随机序列或默认地图热点冒充缺失事实。
- 失败的 L1 保持 `PENDING_AI` 并记录尝试次数和错误，便于重试或人工复核。

## 本地安全边界

- CORS 只允许配置中的明确来源。
- 本地免认证 WebSocket 仅开放 `/ws/local`。
- L1、INFO、L2 清空接口需要精确的确认头，前端也会二次确认。
- 调度时间和间隔拒绝非法输入。
- `/ready` 会实际检查数据库连接。

`main` 仍是本地无认证产品，不应直接作为公网 SaaS 部署。

## 运行与验证

```bash
docker compose up -d --build

cd backend
pytest -q

cd ../frontend
npm run lint
npm run build
npm audit
```

浏览器入口是 `http://localhost:5173`，API 和文档统一使用后端端口 `8000`。

## 已知限制与后续路线

- V1 的 AI 候选发现不是搜索引擎/HTML/动态网页/PDF/API 的真实采集器。
- `legacy_unverified` 记录仅保留浏览和兼容用途。
- L2 当前依赖 INFO/L1 数据库快照，但还未建立字段级计算运行记录。
- 前端主包较大，生产构建会给出 chunk 体积告警，后续可按面板懒加载。
- 真实采集、robots/条款策略、登录凭证、独立 Worker、跨源核验、人工审核队列和 JSON Schema 动态面板留在 V2/SaaS 实现。
