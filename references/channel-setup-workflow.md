# 通道分级配置与重校验流程

本流程规范冷启动阶段如何构建可用检索通道，覆盖从"探测已有能力"到"代用户安装开源 MCP"再到"降级处理"的完整决策链。核心原则：不擅自安装、不擅自登录、不把凭证写入项目文件、每次配置前重新核验上游是否变化、任一开源 MCP 无法跑通即诚实降级。高质量目标不因缺通道而降格，但**论证范围随通道可用性显式缩小**。

## 一、四级决策树

每个新项目开始时先做**注册表导入与活性复验**：`python scripts/channel_registry.py import --project <项目目录>`（注册表未 ack 时该命令拒绝执行）；导入未覆盖或复验失败的槽位按"任务期降级决策表"处置（见 §降级决策表）。此后对新增能力槽逐项走完 A→B→C→D（槽位清单见 [冷启动访谈与能力探测](cold-start.md)）。任一层成功即停止该项的下一层询问；任一层失败则记录并降级。层级结果一律写入 `channel-probe.json` 与 `research-profile.yaml`，来源标签分别为 `probe_existing` / `probe_user_provided` / `probe_agent_installed` / `fallback_web_only` / `fallback_user_supplied`。

### 层级 A：探测用户已装已配

枚举当前会话可用的 MCP 服务器与已安装 skill（以客户端给出的能力清单、系统技能列表与连接器状态为准，不依赖某个特定工具 id），按 capability 归类。中国法默认候选为元典；探测到其他已装 MCP 或用户自选后端时，照常登记，不按品牌排除。对拟用通道跑一次最小真实用例（见"三、最小真实用例规范"）。工具可见但用例未过 → 状态只能是 `partial` 或 `unknown`；用例通过才是 `available`。本地 CLI 通道（`pandoc`、`soffice`、`--corpus-root`）由 `scripts/probe_channels.py` 自动探测；MCP/Skill 由 Agent 完成真实调用后将观察结果作为 `--inventory` JSON 交给脚本归一化。

### 层级 B：用户提供商业或订阅通道凭证

A 层未覆盖 `norm.*` / `case.*` / `scholarship.fulltext` / `foreign.*` 关键项时，用一段简洁话术询问用户是否已持有对应订阅——只列与缺项相关的品牌（如缺德国评注全文就问 Beck-Online，缺美国判例期刊就问 HeinOnline/Westlaw/Lexis，缺中文学术就问知网·法律/万方/百晓，见下方"层级 B 实例"），不铺全表。

用户提供凭证时，Agent 引导他将 Token/Cookie/密码保存在客户端 credential store 或环境变量；skill 项目文件只记录"已配置 / 未配置"与所用能力位。用户提供后立即在会话内跑一次最小真实用例；通过则 `available`，`tier` 记 `commercial_subscription`，`auth_ownership` 记 `user_provided_credential`。不代用户注册、不代付款、不代填 2FA。

#### 层级 B 实例：中文期刊文献三通道引导配置

`scholarship.search` / `scholarship.fulltext` / `journal.metadata` 缺项时，按下列引导流程逐个配置（端点、鉴权与配置模板见 [检索通道目录](channel-catalog.md) §1.5；当前核验状态以目录 `last_verified` 为准）。**只引导用户缺的能力槽对应的通道，不铺全表**。

1. **确认用户持有凭证**（只问缺项相关的）：
   - 知网·法律 → my.cnki.net「我的账户 - MCP Key 管理」的 MCP Key（按量计费，先看剩余额度）；
   - 万方 → my.wanfangdata.com.cn 的 MCP 套餐（OAuth 授权型，客户端须走完浏览器登录）；
   - 百晓 → chat.know-pa.cn「设置 → MCP 接入」生成的 `bxk_` 密钥。
2. **写入客户端配置**：把目录 §1.5 各通道卡片里的配置模板（密钥用 `${...}` 环境变量占位符）交给用户复制到其 MCP 客户端；**凭证不进项目文件、不进决策日志**。按所用 MCP 客户端的配置表单或 mcp.json 格式粘贴即可，不绑定特定客户端产品。
3. **重连并跑验收 Prompt**：按目录 §1.5 各卡片"验收 Prompt"原文执行，不自行降低断言。知网注意同一查询不重复请求（计费）；万方注意 `HasFulltext` 字段未返回时不得盲调下载工具；百晓 `verify_reference` 用字段化参数。
4. **登记能力槽**：验收通过后更新 `channel-probe.json`（status=available + probe_case/probe_assert）并在 `research-profile.yaml.capabilities` 落条目（格式见 §五，`auth_ownership: user_provided_credential`）；未通过的按 §四失败穷尽排查（先鉴权、再端点、再上游），仍不通则如实登记并进入层级 D。
5. **交叉验证提示**：万方与百晓的期刊题录可互为独立 upstream 交叉核验；两源命中同一题录时引注元数据可信度提升，但全文引用仍须取得原文。

### 层级 C：代用户安装开源 MCP/Skill

对 B 层未覆盖且存在成熟开源方案的 capability，向用户逐项列出候选：名称、覆盖范围、许可、最近维护日、依赖、隐私边界（是否需要本地浏览器自动化组件、查询词是否离开本机、是否命中第三方 hosted 端点）。用户显式同意后，对每个候选依次执行下列步骤：

1. **前置环境检查**。确认 Node/Python/UV 等依赖是否满足（含候选上游声明的浏览器自动化组件）；缺失时先告知用户并请授权安装。`scripts/probe_channels.py` 只自动检测 `pandoc` 与 `soffice`，其他依赖需 Agent 显式跑命令行确认。
2. **重新拉取上游配置**。访问候选仓库当前默认分支 README 或 release，读取安装命令、示例配置与鉴权说明；把仓库 URL、当前 commit OID 或 release tag 与访问日期记入 `channel-probe.json.source_ref`。**禁止直接沿用 `assets/mcp-configs/` 里的历史模板**——即使模板存在，也必须先与上游核对。
3. **本地跑通**。按上游说明在用户授权环境下安装或启动，然后执行"三、最小真实用例规范"。任一断言失败即进入"四、失败穷尽与再校验"。
4. **落配置文件**。跑通后写入 `assets/mcp-configs/<slug>.json`，字段至少包含 `source_repo`、`source_ref`（commit OID 或 tag）、`tested_at`、`tested_by_agent`、`minimal_probe_summary`、`config_template`（不含凭证）。同一份内容以可读形式回显给用户，让他复制到自己的 MCP 客户端配置（例如任一支持该传输协议的 MCP 客户端，或本会话）。**不静默修改全局 MCP 注册表**。
5. **登记 profile**。`research-profile.yaml` 对应 capability 条目下记 `tier: open_source_self_hosted` / `open_source_hosted_oauth`，`install_path: agent_installed`，绑定 `source_ref` 与 `tested_at`；用户可选择让下一次恢复项目时自动重校验或人工确认。

用户拒绝安装、安装被系统权限阻断、或跑通失败穷尽后仍不通 → 进入层级 D。

### 层级 D：降级处理

未通过 A/B/C 的 capability 按下列顺序降级，任何降级都在 `03a-research-brief.md` 与 `12-contribution-review.md` 明示砍掉的论证范围：

- 一般网页搜索/WebFetch/浏览器 skill 只作**发现渠道**，不充当 `norm.validity`、`case.fulltext`、`scholarship.fulltext` 或 `foreign.official_text` 的权威来源；题录/摘要不冒充全文。
- 用户手工准备的资料：由用户自行下载 PDF/DOCX/Markdown 放入 `local.corpus` 授权目录，`scan_corpus.py` 建立候选索引；实际阅读并按阅读范围写入来源账本后才能引用。文件存在不等于已读。
- 比较法：`foreign.official_text` 保持 `missing` 时，只能明确标注"转引自 X"，`12-contribution-review.md` 记录覆盖限制；不得用二手陈列冒充一手核验。

## 二、每项 capability 的默认候选池

候选具体端点、维护状态与安装路径以 [检索通道目录](channel-catalog.md) 为准；下表只列每层默认策略。

| capability | A 已装常见对应 | B 商业订阅 | C 开源候选（Tier A 优先） | D 降级 |
|---|---|---|---|---|
| `norm.exact_article` | 元典 MCP 等已安装的中国法 MCP | 威科先行、法信 | `ZongziForu/cn-law-hub`、国家法律法规数据库官方接口浏览器 | WebFetch 官方源逐字 |
| `norm.validity` | 同上 | 同上 | 全国人大网/国务院/最高人民法院官网 | 手工核对施行日 |
| `norm.history` | 元典历史法规 | 威科先行/法信修订库 | 全国人大网历次修正公告、司法部草案页 | 手工比对历史文本 |
| `case.search` | 元典等已安装的中国法 MCP | Westlaw/Lexis/Beck/Dalloz | CourtListener 官方 MCP、`eur-lex-mcp-server`、`hourei-mcp-server`、`librejustice` | WebSearch 案由 |
| `case.authority` | 人民法院案例库/指导性案例目录（网页或 MCP） | 威科先行/法信权威案例库 | 最高法官网、人民法院案例库公开页 | 仅用案号与公开来源，不宣称层级 |
| `case.fulltext` | 同上 | 同上 | 同上 + `bailii-mcp`（本地跑） | 手工下载裁判文书 |
| `case.subsequent` | 元典后续效力字段 | Westlaw KeyCite / Lexis Shepard's | CourtListener 引证网络 | 明示"未核后续" |
| `scholarship.search` | 知网·法律、万方、百晓（目录 §1.5） | 同左 + HeinOnline / JSTOR | `openags/paper-search-mcp`、`semantic-scholar-fastmcp`、`arxiv-mcp-server` | Google Scholar 网页搜索 |
| `scholarship.fulltext` | 万方（期刊与学位论文，须过 `HasFulltext` 门槛） | CNKI 已授权全文、出版商平台 | paper-search-mcp OA PDF、SSRN/CORE/PMC/HAL 直链 | 请用户提供全文 |
| `journal.metadata` | 百晓（期刊匹配与审稿人推荐，目录 §1.5） | CNKI 期刊导航 | 期刊官网、CSSCI/CLSCI 目录页 | 用通行引注规范基线，标注待目标确定 |
| `journal.recent_articles` | — | CNKI 期刊库 | 期刊官网近几期目录 | 请用户提供样文 |
| `journal.submission_rules` | — | — | 期刊官网投稿须知与 AI 政策页 | 标注"未核期刊规则"，不得声称符合 |
| `foreign.official_text` | — | Westlaw International / Beck | `Ansvar Gateway` hosted、`eur-lex-mcp-server`、`de-eli-mcp`、`mcp-server-legifrance`、`hourei-mcp-server`、`ris-mcp-ts`、`swiss-courts-mcp` | 官方公开网页 |
| `foreign.case` | — | 同上 | CourtListener、`eur-lex-mcp-server`（CJEU）、`beck-online-mcp`（BVerfG/BGH）、`librejustice`（CE/Cass/ECHR）、`Constitutional-Court-decision-mcp`（韩）、`canlii-mcp` | 官方裁判公开库网页 |
| `foreign.scholarship` | — | HeinOnline / Beck / Dalloz | paper-search-mcp、SSRN、CiNii、OpenAlex | 题录发现＋标注转引 |
| `translation.assist` | 会话模型/翻译工具 | DeepL 等翻译 API | 本地开源模型＋术语表 | 仅保留原文与待译标记，不生成译文依据 |
| `local.corpus` | — | — | 用户授权目录 + `scan_corpus.py` | 无索引时仅按用户明示文件名引用 |
| `local.zotero` | Zotero 数据库 | — | 用户安装 Zotero＋Better BibTeX，启用本机通信 | 用户手工导出 BibTeX/RIS |
| `local.obsidian` | Obsidian vault | — | 用户指定库，只读索引 `.md` | 用户手工提供笔记 |
| `local.notebook` | 知识库类 MCP | — | 连接 MCP，添加项目 Source | 用户导出 Markdown |
| `local.terms` | 项目 `terms/` | — | 导入 CSV/JSON 术语表 | 人工维护 |
| `export.docx` | `pandoc` 存在 | — | 建议用户 `brew install pandoc` / 使用官方 docx skill | 仅交付 Markdown + 版式说明 |
| `export.pdf_render` | `soffice` 存在 | — | 建议用户装 LibreOffice | 不签署 `layout_rendered`，最高 `REVIEW_REQUIRED` |

## 降级决策表（任务态，1.3.0）

任务运行期，任何能力槽为 unknown / 故障 / 复验失败时，必须获得一项处置并写入项目 `02b-channel-decisions.md`（audit 逐槽强制）：

| 处置 | 适用条件 | 决定者 | 留痕 |
| --- | --- | --- | --- |
| ① 官方公开源兜底 | 不改变成果范围（如商业库故障回 flk.npc.gov.cn） | 可自动执行 | 02b 该槽行 + 检索日志 |
| ② 请用户补充语料/全文 | 需要该槽产出且用户可能持有（如文献全文、本地 PDF） | 必须询问 | 02b + 03a 缺口说明 |
| ③ 收窄任务范围 | 槽位不可用且用户同意放弃该类论证（如比较法不启动） | **必须用户确认** | 02b + 02a `comparative_law_decision` + 决策日志 |

纪律：不得假装可用；不得静默换源；任务期通道故障记入 02b 复验记录（故障时间、降级去向、是否影响已写内容）。

## 三、最小真实用例规范

每一层每一次配置都独立跑，不与相邻能力混合。用例必须与本项目研究对象相邻。

| capability | 最小用例 | 通过断言 |
|---|---|---|
| `norm.exact_article` | 查询研究对象条号的现行文本 | 逐字全文 + 规范全称 + 条号一致 |
| `norm.validity` | 同上 | 现行效力 + 公布/施行日期 + 最新修订文号 |
| `norm.history` | 研究对象最近一次修订前的文本 | 返回历史版本 + 修订说明或立法理由字段 |
| `case.search` | 用已知案由或关键词 | ≥1 条相关裁判，字段可解析 |
| `case.fulltext` | 打开其中一案 | 裁判正文（非仅摘要）+ 法院/日期/案号定位 |
| `case.subsequent` | 该案再审/改判/停参字段 | 明确"有后续 X"或"无后续" |
| `scholarship.search` | 一篇已知论文标题或主题词 | 题录（作者、出处、年份、DOI/handle） |
| `scholarship.fulltext` | 打开一篇用户可合法访问的文献 | 全文片段或整篇 + 页码/边码/段落定位 |
| `foreign.official_text` | 目标法域一条现行条文 | 官方发布源逐字 + 版本日期 |
| `foreign.case` | 目标法域一件判决 | 判决正文 + 法院层级 + 意见类型（多数/协同/反对） |
| `local.corpus` | `--corpus-root` 指向授权目录后跑 `scan_corpus.py` | 索引条目非空、路径可读、预览可抽 |
| `local.zotero` | 读取 Zotero 条目与附件路径 | 条目数>0，可定位 PDF；未修改数据库 |
| `local.obsidian` | 检索一个已知笔记标题 | 命中文件与标题；未写入 vault |
| `local.notebook` | 列出一个项目 Notebook | 返回 source 列表与可读状态 |
| `local.terms` | 读取项目术语表 | 条目可解析、含来源与置信度 |
| `journal.metadata` | 打开目标期刊主页 | 栏目、周期、字数可读 |
| `journal.recent_articles` | 打开近一期目录 | 可列出篇目与作者 |
| `journal.submission_rules` | 打开投稿须知与 AI 政策页 | 格式、匿名、披露要求可读 |
| `foreign.scholarship` | 检索一篇已知外文论文 | 题录含作者、出处、年份、DOI |
| `translation.assist` | 对一段含术语的外文条文试译 | 术语命中、引证完整、可回原文核对 |
| `export.docx` | `pandoc --version` 与样张转换 | DOCX 生成 + 目检原生脚注/样式（脚本通过不等于版式通过） |
| `export.pdf_render` | LibreOffice headless 转换样张 | PDF 生成 + 逐页可读 |

## 四、失败穷尽与再校验

开源 MCP 因上游依赖、API 变更、鉴权模式或仓库归档而失效是常态。规则如下：

- **每次用户请求"帮我配置 X"时**都重新拉取上游 README 与示例配置，不复用旧模板；即便 `assets/mcp-configs/x.json` 存在也要重新核验，核验通过再落新 `source_ref` 与 `tested_at`。
- 用例失败时按下列顺序穷尽，不得一次失败即放弃：
  1. 判定是否仅鉴权问题（Token 过期、Cookie 未刷新、2FA 待完成、hosted 端点 OAuth flow 未走）。
  2. 判定是否运行环境问题（Node/Python 版本、浏览器自动化组件未装、`uv`/`npx` 不在 PATH、`pip` 与 `python3` 混淆、macOS 系统 Python 与 Homebrew Python 混用）。
  3. 查上游 Issues 与最近 Commit，找同类问题与官方修复方案；必要时切到 release 稳定版而非 main。
  4. 检查仓库是否 `archived`。归档后寻找同数据源的活跃 fork 或 hosted 端点（示例：`Ansvar-Systems/German-law-mcp` 仓库 2026-07-07 归档，但 hosted gateway `https://gateway.ansvar.eu/mcp` 仍运营——配置时优先走 hosted）。
  5. 上游数据源官方页确认是否发布官方 MCP（如 Free Law Project 官方 MCP、华宇元典官方 MCP）；有则替换到官方实现。
  6. 若仍不通，转浏览器工作流并明确降为 D 层。
- 失败穷尽后如实登记 `missing` 或 `partial`，绝不伪装成功；`12-contribution-review.md` 与 `03a-research-brief.md` 记录因通道缺失而砍掉的论证类型（例如"因缺 `case.fulltext`，本项目无法归纳裁判理由，仅能引用公开案号与当事人主张"）。
- **周期性重校验（重校验窗口的唯一定义处）**：`research-profile.yaml.channel_revalidate_days` 默认 30，适用于托管/OAuth 与第三方自动化访问类通道；官方公开来源（`official_public_web`）按 90 天复核。恢复项目时若任一通道的 `tested_at` 超过其适用阈值，Agent 先提示"上次核验于 X 日，是否需要现在重跑最小用例"，用户选择继续则重跑；商业订阅过期时即时降级，不等到下次冷启动。
- **上游版本变更**：Agent 在核验时若发现仓库 commit OID 或 release 相较 `source_ref` 更新，主动询问用户是否升级；升级后重新跑用例，用例通过才更新 `source_ref` 与 `tested_at`。

## 五、`research-profile.yaml` 通道条目扩展

现有顶层 `channels:` 块（`prc_norms / prc_cases / chinese_scholarship / foreign_law`，每块记 `primary`/`secondary` 品牌名）保持不变，负责"用户选哪家"；`capabilities:` 块的每一项承载"该能力实际由哪个通道跑通、配置来源、上次核验时间与下次重校验阈值"。每次层级 A/B/C 通过后，对应 capability 条目至少填下列字段：

```yaml
capabilities:
  "foreign.official_text":
    status: available
    tool: "https://gateway.ansvar.eu/mcp"
    jurisdiction: DE
    install_tier: open_source_hosted_oauth       # open_source_self_hosted / open_source_hosted_oauth / commercial_subscription / browser_workflow
    install_path: agent_installed                # probe_existing / user_provided_credential / agent_installed / manual_browser_fallback
    auth_ownership: oauth_managed_by_client      # none / user_provided_credential / oauth_managed_by_client / agent_installed_token
    source_repo: "https://github.com/Ansvar-Systems/German-law-mcp"
    source_ref: "b614f14"                        # commit OID 或 release tag，禁止留空
    tested_at: "2026-10-03"
    revalidate_before: "2026-11-02"              # tested_at + channel_revalidate_days（默认 30）
    probe_case: "查询 BGB §823 Abs. 1 现行文本"
    probe_assert: "逐字命中 + 官方公布日期 + 最新版本"
    impact: ""
    tos_notes: "GitHub 仓库 2026-07-07 归档；hosted gateway 由 Ansvar 运营，免费额度有限，具体以官网为准"
  "scholarship.search":
    status: available
    tool: "https://api.wfdata.com/mcp/wf-search-download"
    jurisdiction: CN
    install_tier: commercial_subscription
    install_path: user_provided_credential
    auth_ownership: oauth_managed_by_client      # 万方为客户端托管 OAuth
    source_ref: "目录 §1.5.2 已核验快照（2026-11-01）"
    tested_at: "2026-11-01"
    revalidate_before: "2026-12-01"
    probe_case: "PQ 检索式'标题:民事法律行为 AND 关键词:有效要件'（中文期刊库）"
    probe_assert: "返回真实题录（标题/作者/关键词/摘要/刊名/年份）；与百晓核验交叉验证一致"
    impact: "引注可标[题录核实]；全文引用仍须取得原文"
    tos_notes: "全文下载仅开放期刊与学位论文；检索词发送服务方；题录/摘要不冒充全文"
  "scholarship.fulltext":
    status: partial                              # 受官方站点访问限制或订阅范围约束的通道最高只能标 partial
    tool: "beck-online-mcp"
    jurisdiction: DE
    install_tier: commercial_subscription
    install_path: user_provided_credential
    auth_ownership: user_provided_credential
    source_repo: "https://github.com/speydril/beck-online-mcp"
    source_ref: "v0.x 或 tested commit OID"
    tested_at: "2026-10-03"
    revalidate_before: "2026-10-24"              # 商业订阅变动频繁，允许缩短
    probe_case: "检索 <期刊名> <年份>, <起始页>"
    probe_assert: "题录命中 + 订阅范围内文档全文；订阅范围外文档须明确不可访问"
    impact: "自动化访问受限或订阅范围外文档降为 partial_read"
    tos_notes: "第三方自动化访问，稳定性与授权由使用者自行确认，不得用于形成引注依据；订阅资格与使用条款由使用者本人确认，不得绕过验证码、访问控制或付费边界"
    substitute_for_verified_citation: "域外权威评注的页码须回原始纸质版或出版社官方页核验"
  "local.zotero":
    status: available
    tool: "~/Zotero/zotero.sqlite（只读）"
    install_tier: open_source_self_hosted
    install_path: probe_existing
    auth_ownership: none
    source_ref: "本机安装版本"
    tested_at: "2026-10-31"
    revalidate_before: "2026-11-30"
    probe_case: "读取 1 个条目并定位其 PDF 附件"
    probe_assert: "条目数>0；附件路径可读；数据库未被修改"
    impact: "仅证明库藏可检索，不证明全文已读"
    tos_notes: "只读；不上传条目或附件到外部服务"
  "journal.submission_rules":
    status: available
    tool: "目标期刊官网投稿页"
    install_tier: browser_workflow
    install_path: manual_browser_fallback
    auth_ownership: none
    source_ref: "URL + 访问日期"
    tested_at: "2026-10-31"
    revalidate_before: "2026-11-30"
    probe_case: "打开投稿须知与 AI 使用政策"
    probe_assert: "字数、格式、匿名与披露要求可读"
    impact: "未核期刊规则时不得声称符合投稿要求"
    tos_notes: "仅记录公开页面要点，不复制受版权保护的内容"
```

字段缺任一项即视为通道条目未填完，研究闸 `G2_research` 不放行。顶层新增两项配置：

```yaml
channel_revalidate_days: 30                     # 用户可调；托管/OAuth 与第三方自动化访问类通道 ≤30，官方公开来源 90 天（见 §四）
allow_agent_install: false                       # 用户在访谈阶段勾选层级 C 时改为 true
```

`permissions.may_install_connectors`（旧字段）与 `allow_agent_install` 语义重叠，保留旧字段兼容脚本，新流程以 `allow_agent_install` 为准；两者冲突时以 `false` 优先。

## 六、隐私与安全边界

- 不绕过登录、验证码、付费墙；不代替用户注册、付款或填 2FA。
- 敏感案情的检索词、上传文件与本地路径按用户设定的敏感度处理；未授权不得离开本机。商业数据库 hosted 端点会记录查询词，须在访谈阶段告知用户。
- 项目文件、日志、决策记录一律不落凭证。Token/Cookie 只放客户端 credential store 或环境变量。
- 商业数据库的 ToS 若限定"仅个人执业/学术使用"，Agent 不代判资格；用户须自证并显式确认。
- 开源 MCP 若声称"数据源为官方开放许可"（如 UrhG §5、EU Decision 2011/833），Agent 仍要独立核对当前官方许可状态，不轻信 README。

## 七、与其他参考的接口

冷启动访谈的提问顺序与降级规则以 [冷启动与检索通道](cold-start.md) 为准；品牌、端点与许可信息以 [检索通道目录](channel-catalog.md) 为准；本文件只规定"如何把候选变成可用通道"以及"如何维护已配置的通道"。三者交叉引用不一致时以本文件的决策树为操作依据，并在 `10-decision-log.md` 记录冲突与取舍。
