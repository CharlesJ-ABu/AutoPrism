# AutoPrism V2

AutoPrism V2 是一个 local-first、证据优先的产业研究面板平台。它把原始
网页、PDF、CSV/Excel、RSS 与公开 API 保存为不可变历史快照，再按冻结的
JSON Schema 形成结构化数据。核心数值可以回到原始文件、来源 URL、抓取时间
和精确定位器。确定性代码负责计算与重放；通用单位/货币换算、舍入和误差传播
仍属于 M7，不会在当前版本中伪装为已完成。

V2 界面延续 V1 的深色科技驾驶舱、紫青光效和高密度情报终端风格，底层则替换为
真实数据、版本化契约和可审计证据链。

当前分支策略：

- `main`：冻结的 V1 本地版。
- `v2`：本仓库当前开发线，本地/内网/Docker Compose 可运行。
- `saas`：长期独立版本；认证、RBAC、组织隔离、加密凭证库和对象存储在该分支建设。

## 已实现

- 内容寻址原始文件存储（SHA-256）和不可变来源快照。
- HTML、RSS、PDF、CSV、XLSX、JSON API 解析及可重现定位器。
- Redis 采集队列与独立 Worker。
- 来源池、可信度、主题权威度、抓取策略和人工处理队列。
- 冻结的主面板/子面板版本、JSON Schema、UI DSL、组件源码哈希、
  提示词版本和模型设置。
- OpenAI-compatible 与 Google Gemini 的供应商无关模型适配器。
- 确定性 JSON 映射、Schema 校验、数值核算、交叉验证和审核记录。
- `evidence-extraction-v3` 冻结抽取输入清单、文本/清单哈希、运行输出位置，
  并通过规范化关联表保存一条观测的多声明、多证据片段及直接 ExtractionRun 血缘。
- `numeric-v2-source-artifact-publisher` 验证规则与
  `trust-eligibility-v3-validation-replay` 可信策略；旧规则、非确定性抽取、
  过期 peer 和不可重放来源均 fail closed。
- 证据审计 UI：原始来源、JSON Pointer、抓取时间、文件/文本哈希及原始文件下载。
- V1 延续型情报驾驶舱：共享 design tokens、角色/视角切换、可信态势图、
  专业面板容器、全证据抽屉以及统一空/错/加载状态。
- 三个真实 NHTSA 汽车面板，默认展示品牌、Tesla 2024 车型和安全评级车型。

## 快速启动

要求 Docker Desktop。API Key 是可选项；三个内置汽车面板不需要大模型。

```bash
cp backend/.env.example backend/.env
docker compose up -d --build
docker compose exec web python -m app.seeds.automotive --collect
```

访问：

- 前端：[http://localhost:5173](http://localhost:5173)
- API 文档：[http://localhost:8000/docs](http://localhost:8000/docs)
- 健康检查：[http://localhost:8000/health](http://localhost:8000/health)
- 就绪检查：[http://localhost:8000/ready](http://localhost:8000/ready)

端口固定为前端 `5173`、后端 `8000`、PostgreSQL `5432`、Redis `6379`。

## 模型配置

`backend/.env` 只供本机使用且被 Git 忽略：

```dotenv
AI_PROVIDER=openai-compatible
AI_API_BASE=https://api.openai.com/v1
AI_API_KEY=
AI_MODEL=gpt-4o
```

也可在“新建主面板”中临时提供供应商、模型、Base URL 和 API Key。临时 Key
只用于该次设计请求，不会写入面板版本。SaaS 的组织级加密凭证库尚未在 V2 实现。

## 数据语义

- **L1**：原始文件、HTTP 元数据、不可变快照和定位片段。
- **INFO**：绑定到面板 Schema 版本的结构化观察值。
- **L2**：只分析数据库中合格 L1/INFO 的战略洞察，不自行浏览或补充事实。
- **legacy_unverified**：V1 遗留数据，保留但默认不进入可信计算与 L2。

错误值不覆盖。修订创建新观察值，并用 `supersedes_id` 指向被替代版本。
人工修订会保存完整历史，但在当前策略下不能替代可重放的直接抽取证明而晋级可信。

M6 对真实保留数据库先完成备份再升级：6 条历史观测中仅 3 条满足唯一、精确的
run/output/evidence 匹配并标记为 `backfill_exact`，其余 3 条保持 unresolved；迁移没有
猜测运行 ID、复制伪证据或改写旧观测。

## 测试

```bash
# 前端类型检查与生产构建
cd frontend
npm ci
npm run typecheck
npm run build
npm audit

# 后端快速测试
docker compose exec -T web python -m unittest discover -s tests -v

# 完整数据库集成测试（必须使用一次性数据库）
docker compose exec -T \
  -e AUTOPRISM_RUN_DB_TESTS=1 \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/autoprism_v2_migration \
  -e DATABASE_SYNC_URL=postgresql://postgres:postgres@postgres:5432/autoprism_v2_migration \
  web python -m unittest discover -s tests -v

# 迁移漂移检查
docker compose exec -T web alembic check
```

2026-08-09 M6 验证记录：一次性 PostgreSQL 完整后端套件最终 39/39 通过，
前端 typecheck、production build 与依赖审计通过；空数据库和已填充数据库迁移门禁
均通过。当前执行环境没有可用 browser runtime，因此本轮新同尺寸截图、控制台与
桌面/移动视觉交互冒烟尚未完成，不能沿用旧截图冒充本轮结果。

详见 [运行手册](docs/V2_RUNBOOK.md)、[测试记录](docs/V2_TESTING.md)、
[安全说明](docs/V2_SECURITY.md)、[架构](docs/V2_ARCHITECTURE.md)、[路线图](docs/V2_ROADMAP.md) 和
[待办](docs/V2_TODO.md)。

V1/V2 验收差距见
[差距矩阵](docs/V1_V2_GAP_MATRIX.md)，持续变更见
[V2 Changelog](docs/V2_CHANGELOG.md)，动态面板契约见
[JSON Schema / UI DSL 规范](docs/V2_SCHEMA_UI_DSL.md)，可信状态边界见
[数据可信度契约](docs/V2_DATA_TRUST_CONTRACT.md)，发布门禁见
[V2 Release Checklist](docs/V2_RELEASE_CHECKLIST.md)。
