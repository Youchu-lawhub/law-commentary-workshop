# 检索通道目录

本目录只提供冷启动候选，不构成安装指令。每次配置前回到官方页面核对端点、收费、鉴权、资格和使用条款。目录最近校核日：`2026-10-03`；陈旧判定按 [通道分级配置与重校验流程](channel-setup-workflow.md) §四的重校验窗口执行（托管/OAuth 与第三方自动化访问类通道 30 天，官方公开来源 90 天），超期应标记陈旧并复核。

配套 [通道分级配置与重校验流程](channel-setup-workflow.md)：本目录的每个候选都按 `install_path`（`open_source_self_hosted` / `open_source_hosted_oauth` / `commercial_subscription` / `browser_workflow` / `official_public_web`）与 `tier`（A 官方或稳定托管；B 第三方活跃；C 需订阅或凭证；D 第三方自动化访问或稳定性存疑）标注，帮助冷启动分层决策。凡 `tier=C/D` 的通道，写入 `research-profile.yaml` 前必须在当前会话跑通最小真实用例；仅"工具可见"不能标 `available`。

## 〇、通道卡片与闸门

境外法与学术通道的**事实**（可用性、安装方式、覆盖、鉴权、验收 Prompt）登记在 `assets/foreign-law-sources.json`，用 `scripts/foreign_sources.py` 查询；本目录只保留导航与说明，不复制会过期的事实。方法与验收见 [境外法研究与引注核验协议](foreign-law-research-protocol.md)。

```bash
python3 scripts/foreign_sources.py report
python3 scripts/foreign_sources.py plan --jurisdiction DE --layer norm
python3 scripts/foreign_sources.py judge --url <候选URL>
python3 scripts/foreign_sources.py check --id <通道id> --allow-network
```

每条通道卡片至少回答：谁运营（provider）、实际读哪份权威源（upstream）、是主源还是镜像（role）、覆盖哪些法域与层（jurisdictions / commentary_layers）、需要什么鉴权（auth）、上次核验状态与日期（state / checked）、首次验收 Prompt（acceptance）、已知局限（caveat）、替代路径（fallback）。

三条选路纪律：

1. **`plan` 是唯一选路出口**，不凭记忆推荐通道；`check` 结论超过刷新周期须重测。
2. **独立性看 provider 与 upstream**：两家镜像读同一份官方文本，只能互相发现抓取错误，不能独立证明文本版本；关键命题需另一条 upstream 不同的来源或降为 medium。
3. **官方域名只看托管方**：律所、文库、NGO 转载的完整条文仍是二次文献；`judge` 返回 `UNVERIFIED_HOST` 时不得当 tier 1 引注。

取不到文本要区分三种情形，不得混为一谈：非官方域名（`SECONDARY_ONLY`，只能定位）；官方但被站点访问限制或鉴权拦（`BLOCKED`，登记由使用者在自有授权范围内通过官方页面或人工路径完成）；官方但本机网络不可达（不得写成“该国没有公开文本”，只登记人工路径并注明须在可直连环境重测）。

## 一、中国法

### 1.1 华宇元典 MCP（首选候选）

- 官方入口：`https://open.chineselaw.com/mcp-config/`；GitHub 参考实现：`yuandian-mcp-server`（元典智库）。
- 候选能力：法规、案例、企业、证券与幻觉校验。
- 当前分类端点：`https://open.chineselaw.com/mcp/law/stream`、`https://open.chineselaw.com/mcp/case/stream`、`https://open.chineselaw.com/mcp/company/stream`、`https://open.chineselaw.com/mcp/securities/stream`、`https://open.chineselaw.com/mcp/hallucination/stream`。
- `install_path`: `commercial_subscription`；`tier`: A。
- 验收：返回一条带版本/效力信息的现行规范和一个带案号、法院、日期及全文定位的案例。API Key 由用户保存。
- `last_verified`: `2026-10-03`

### 1.2 其他中国法检索 MCP

- 冷启动按**能力槽**映射会话中已安装的 MCP，不按品牌预设：凡能返回规范原文与效力、案例全文与案号的通道，均可登记为 `norm.*` / `case.*`。
- 用户自行选择的中国法检索后端同样可用且不降级；登记时记录 provider、覆盖范围、鉴权方式与最小用例结果即可。
- 未安装时优先 §1.4 官方公开来源做最终核验，或使用 §1.3 的社区方案作发现与补充。
- 验收：与 1.1 相同——一条现行规范（含版本/效力）＋一件可打开原文的裁判（含案号、法院、日期）。

### 1.3 中文学术与本地语料

- CNKI、中文期刊数据库、学校图书馆、用户 Zotero 与本地 PDF/Markdown 均可选择。
- CNKI 浏览器工作流：`cookjohn/cnki-skills`。优先页面结构化数据；验证码、登录和下载授权由用户处理；下载后验证文件；题录/摘要不冒充全文。`install_path`: `browser_workflow`；`tier`: C。
- 中文法条/案例检索的社区补充：`ZongziForu/cn-law-hub`（聚合国家法律法规数据库/最高法等公开检索）、`Golden2002/legal-research-skill`（Claude Skill 形态）、`NEU-ZHA/legal-ai-skills`、`moyupeng0422/legal-tools`。`install_path`: `open_source_self_hosted`；`tier`: B。均为第三方封装，最终仍应回官方源核验。
- 验收：搜索、题录、详情和全文能力分别测试并分别标状态。
- `last_verified`: `2026-10-03`

### 1.4 官方公开来源

- 国家法律法规数据库（`https://flk.npc.gov.cn/`）、中国人大网、中国政府网、最高人民法院、最高人民检察院、国务院部门与地方立法机关/政府官网。
- 用途：现行法最终逐字核验；指导性案例、人民法院案例库、公报/典型案例和官方裁判资料核验。
- `install_path`: `official_public_web`；`tier`: A。始终作为 `primary_verified` 的最终依据，商业数据库只是发现与交叉核验。
- `last_verified`: `2026-10-03`

### 1.5 中文期刊文献数据库 MCP（scholarship 槽候选，端点已核验）

本节仅登记**期刊文献检索**通道（`scholarship.*` / `journal.*` 槽）。法律规范与案例检索（`norm.*` / `case.*` 槽）的默认候选为华宇元典（§1.1），不在本节配置。以下通道以客户端连接器 / API 密钥形态接入，任何支持 streamable HTTP 或 OAuth 的 MCP 客户端均可配置，不绑定特定宿主产品。**端点与鉴权方式已核验，各条 `last_verified` 标注核验时点**；密钥一律用环境变量占位符，不落项目文件（隐私边界见 [通道分级配置与重校验流程](channel-setup-workflow.md) §六）。仅"已连接"不等于可用，写入 `research-profile.yaml` 前必须在当前会话跑通最小真实用例；配置引导步骤见该流程 §1.5。

#### 1.5.1 知网·法律 MCP（cnki-law）

- 官方入口：my.cnki.net「我的账户 - MCP Key 管理」生成 MCP Key。
- 端点（已核验）：`https://mcp.cnki.net/mcp/law`（streamable HTTP）；鉴权 `X-MCP-Key` 请求头。
- 候选能力：`norm.search`（法规/法条，关键词与语义双路）、`case.search`（相似案例）、`scholarship.search`（法律期刊文献：题名/来源/时间/摘要 + 知网节链接）、`citation_check`（法条与政策溯源）。
- 注意：**按量计费**，消耗知网账户检索额度；同一查询条件不得无差别重复请求，检索结果页链接为知网节而非全文。
- 客户端配置模板（密钥放环境变量，勿写入文件）：

```json
{
  "mcpServers": {
    "cnki-law": {
      "type": "streamableHttp",
      "url": "https://mcp.cnki.net/mcp/law",
      "headers": { "X-MCP-Key": "${CNKI_MCP_KEY}" },
      "timeout": 30000
    }
  }
}
```

- 验证状态：端点健康（无密钥与错误密钥均快速返回 401，鉴权网关正常），但持有效配置时端到端调用未通过（连接关闭）；连接器展示的工具清单来自静态元数据而非实时握手，密钥是否完成过 `initialize` 未确证。因此登记为 `UNVERIFIED`，不得标 `available`。配置前先到 my.cnki.net 核对密钥状态与剩余额度。
- `install_path`: `commercial_subscription`；`tier`: A（官方，CNKI）。
- 验收 Prompt："用 `search_law_journal_keyword` 检索 `显失公平,民法典`，确认返回题录（TI/LY/PT/AB）与知网节链接，且账户额度有对应消耗提示。"
- `last_verified`: 未通过（2026-11-01，连接关闭，待重测）。

#### 1.5.2 万方数据 MCP（wanfang）

- 官方入口：my.wanfangdata.com.cn（含 MCP 套餐购买页）。
- 端点（已核验）：`https://api.wfdata.com/mcp/wf-search-download`（HTTP + OAuth）。
- 候选能力：`scholarship.search`（PQ 检索式；中文期刊/学位/会议/专利/标准/法规等库）、`scholarship.fulltext`（期刊与学位论文全文下载，须先通过 `HasFulltext` 布尔门槛）、期刊趋势分析。
- 注意：全文下载当前仅开放期刊与学位论文；余额不足时服务端拦截；题录/摘要不冒充全文；**OAuth 授权必须在客户端走完浏览器登录流程**——凭据库只有 client_id 没有令牌时连接器会反复掉线。
- 客户端配置模板（OAuth 由客户端托管，无需手填密钥）：

```json
{
  "mcpServers": {
    "wanfang": {
      "type": "http",
      "url": "https://api.wfdata.com/mcp/wf-search-download"
    }
  }
}
```

- 验证状态：**检索通过（2026-11-01，客户端托管 OAuth）**——PQ 检索式返回真实题录（标题/作者/关键词/摘要/刊名/年份），且精确检索结果与百晓核验交叉验证一致（两个独立 upstream）。**全文下载待测**——显式请求 `HasFulltext` 字段仍未见返回，按连接器自身门槛规则（缺少判定字段不盲调下载），下载能力暂不标可用。
- `install_path`: `commercial_subscription`；`tier`: B（官方，检索已核验；下载待证）。
- 验收 Prompt："检索 `标题:民事法律行为 AND 关键词:有效要件`（中文期刊库），确认返回题录与 `HasFulltext` 字段；再对一条 `HasFulltext=true` 的记录走全文下载并验证文件可打开。"
- `last_verified`: 检索通过（2026-11-01）；全文下载未通过（HasFulltext 字段未返回，待重测）。

#### 1.5.3 百晓智能 MCP（baixiao）

- 官方入口：chat.know-pa.cn → 设置 → MCP 接入，生成 `bxk_` 开头的 API 密钥。
- 端点（已核验）：`https://mcp.know-pa.cn/mcp`（streamable HTTP）；鉴权 `Authorization: Bearer <密钥>`。
- 候选能力：`scholarship.search`（中文人文社科自建语料，法学为强项）、`citation_check`（单条/整表参考文献核验、残缺引文补全元数据）、引用图谱、`journal.metadata`（投稿期刊匹配）、审稿人推荐。
- 注意：不提供文献全文正文（`get_pdf` 仅限语料内可下载条目）；检索词会发送给服务方，敏感材料不入检索词；结果中的上游来源信息按服务方要求不对外披露；`verify_reference` 参数为字段化（title 必填，可选 authors/journal/year/doi），不是整段引文字符串。
- 客户端配置模板（密钥放环境变量，勿写入文件）：

```json
{
  "mcpServers": {
    "baixiao-mcp": {
      "type": "streamableHttp",
      "url": "https://mcp.know-pa.cn/mcp",
      "headers": { "Authorization": "Bearer ${BAIXIAO_API_KEY}" },
      "timeout": 30000
    }
  }
}
```

- 验证状态：**密钥级验收通过（2026-11-01，端点直连）**——`initialize` 握手正常；`baixiao_corpus_search` 检索"民法典 民事法律行为 有效要件"返回带题名/作者/刊物/年份/页码/ISSN 与摘要的可引用元数据；`baixiao_verify_reference` 字段化核验返回 `matched / confidence: high`。该结果与万方检索交叉验证一致（两个独立 upstream）。
- `install_path`: `commercial_subscription`；`tier`: B。
- 验收 Prompt："用 `baixiao_corpus_search` 检索 `民法典 民事法律行为 有效要件`，确认返回带题名/作者/刊物/年份的可引用元数据；再用 `baixiao_verify_reference`（title/authors/journal/year 字段化参数）核验一条真实存在的中文期刊引文。"
- `last_verified`: 密钥级通过（2026-11-01，端点直连）。

> 组合提示：法律规范与案例检索默认走华宇元典（§1.1）；本节三通道主 `scholarship.search`/`fulltext` 与期刊适配（cnki-law、wanfang 主文献检索与全文，baixiao 主引文核验与期刊匹配），全部跑通后可支撑第六节"中文学术文献 ≥5 篇 + 引注核验"门禁。任一通道未过验收时，对应能力槽退回 §1.4 官方公开来源 + §1.3 浏览器工作流。


## 二、全球初筛与跨法域聚合

### 2.1 Legal Data Hunter

- 端点：`https://legaldatahunter.com/mcp`，OAuth（GitHub / Google 登录，无 API Key）。
- 客户端配置：任一支持 streamable HTTP 的 MCP 客户端均可接入该端点，按所用客户端的远程 MCP 配置方式填入上述 URL 即可；发行方另提供 `npx legal-data-hunter setup --yes` 一步写入配置。
- 用途：多法域初筛，先 `discover_countries` → `discover_sources` → `search` → `get_document`，再回官方原文核验。
- `install_path`: `open_source_hosted_oauth`；`tier`: A（作为发现层）。
- 首次验收 Prompt："用 Legal Data Hunter 搜索新加坡关于数据跨境传输的法规，给出来源和原文链接。"
- `last_verified`: `2026-10-03`

### 2.2 Ansvar 系列

Ansvar 按法域拆分为多个独立 MCP 包，同时提供本地 npx 与远程托管两种模式。

- 命名规则：`@ansvar/<country>-law-mcp`；远程托管 `https://mcp.ansvar.eu/<package>/mcp`（旧聚合端点 `https://gateway.ansvar.eu/mcp` 仍可用，建议核对官方 `https://ansvar.eu/docs/quickstart`）。
- 已见包名：`@ansvar/eu-regulations-mcp`、`@ansvar/us-regulations-mcp`、`@ansvar/security-controls-mcp`、`@ansvar/china-law-mcp`、`@ansvar/germany-law-mcp`、`@ansvar/japan-law-mcp`、`@ansvar/saudi-law-mcp`、`@ansvar/uae-law-mcp`、`@ansvar/brazil-law-mcp`。
- 通用 stdio 模板：
  ```json
  {
    "mcpServers": {
      "<name>": {"command": "npx", "args": ["-y", "@ansvar/<package>"]}
    }
  }
  ```
- 相关 GitHub：`Ansvar-Systems/German-law-mcp`（2026-07-07 已归档，官方推荐切换到 hosted gateway）。
- `install_path`: `open_source_hosted_oauth` 或 `open_source_self_hosted`；`tier`: A/B（视法域覆盖而定；德国/欧盟/美国为 A，其余为 B）。
- 验收：每接入一个包，用目标法域的一个真实条文或判例跑通"精确全文 + 版本/效力 + 官方定位"三步。
- `last_verified`: `2026-10-03`

### 2.3 TCoder920/open-legal-compliance-mcp

- GitHub：`https://github.com/TCoder920/open-legal-compliance-mcp`。
- 覆盖：GovInfo / EUR-Lex / UK Legislation / CanLII / SEC EDGAR / FDA / CourtListener / Congress.gov / Open States 等聚合初筛。
- 部署：本地 Node stdio，`git clone` → `npm install` → `npm run build`；env 至少需要 `GOVINFO_API_KEY`，可选 `COURTLISTENER_API_KEY`、`CONGRESS_GOV_API_KEY`、`OPEN_STATES_API_KEY`、`CANLII_API_KEY`。
- `install_path`: `open_source_self_hosted`；`tier`: B。配置较重，官方源直连可用时优先级低于 §2.1/§2.2。
- `last_verified`: `2026-10-03`

## 三、德国法

### 3.1 Beck-Online MCP（speydril/beck-online-mcp）

- GitHub：`https://github.com/speydril/beck-online-mcp`。3 个工具：`beck_search`、`get_document`、`get_toc`；输出 Markdown 全文。
- 覆盖：Beck 全库（ZivilR / OeR / StrafR 等部门法评注、期刊、判决、法规）。
- 前置：使用者本人持有有效的 Beck-Online 订阅（高校或执业）+ 2FA + Node ≥ 20；登录与验证环节一律由用户本人在官方页面完成。
- 访问限制：官方站点与订阅库对自动化访问有限制，订阅范围外的文档不可获取；本包只登记公开可核查的接入方式，实际访问须由使用者在其自身授权（订阅、令牌、法定许可）范围内通过出版社官方页面或其指定的客户端完成，不得绕过验证码、访问控制或付费边界。仅题录/摘要可用时不得冒充全文。
- `install_path`: `browser_workflow` + `commercial_subscription`；`tier`: C。
- 状态上限：`partial`（受官方站点自动化访问限制与订阅范围波动影响，不得标 `available`）；引用 Beck 内容写入正文前必须回到出版社官方页面二次核验后才允许 `verified_fulltext`。
- `substitute_for_verified_citation`: false（仅作为发现与阅读辅助，不作为引注核验唯一来源）。
- `last_verified`: `2026-10-03`

### 3.2 ayunis-core/ayunis-legal-mcp

- GitHub：`https://github.com/ayunis-core/ayunis-legal-mcp`（第三方德语法律检索 MCP，覆盖 gesetze-im-internet.de 与部分判例）。
- `install_path`: `open_source_self_hosted`；`tier`: B。作为 Beck 不可用时的开放替代，或作为 `norm.exact_article` 的官方源封装。
- 验收：BGB §823 Abs. 1 逐字命中 + 官方公布日期 + 最新版本。
- `last_verified`: `2026-10-03`

### 3.3 官方公开来源

- `https://www.gesetze-im-internet.de/`（联邦法规）、`https://www.rechtsprechung-im-internet.de/`（联邦判决）、`bverwg.de` / `bgh.de` 等联邦法院官网、各州 `landesrecht` 门户。
- `install_path`: `official_public_web`；`tier`: A。现行法最终逐字核验通道。
- `last_verified`: `2026-10-03`

## 四、欧盟法

### 4.1 EUR-Lex 与 CELLAR

- 官方门户：`https://eur-lex.europa.eu/`；SPARQL 端点：`https://publications.europa.eu/webapi/rdf/sparql`；REST：`https://eur-lex.europa.eu/EURLexWebService`（需注册）。
- 社区 MCP：`cyanheads/eur-lex-mcp-server`（Node stdio，EUR-Lex 全文 + CELEX 号解析）、`Lex-API`（Python 封装）。
- `install_path`: `official_public_web` + `open_source_self_hosted`；`tier`: A（官方 SPARQL）/ B（社区封装）。
- 验收：给定 CELEX 号返回现行有效版本 + 生效日期 + 官方 PDF/HTML 定位。
- `last_verified`: `2026-10-03`

### 4.2 Ansvar EU Regulations MCP

- 见 §2.2；覆盖 GDPR / AI Act / DORA / NIS2 等。`tier`: A（对合规类欧盟条例），法规逐字仍需回 EUR-Lex 核验。

## 五、美国法

### 5.1 CourtListener（Free Law Project 官方）

- 官方端点：`https://mcp.courtlistener.com/`，OAuth。API Key 申请：`https://www.courtlistener.com/api/`。
- 覆盖：美国判例、RECAP/PACER 案卷、口头辩论、法官信息、引注网络。
- `install_path`: `open_source_hosted_oauth`；`tier`: A。
- 客户端配置：任一支持 streamable HTTP 的 MCP 客户端均可，把 `https://mcp.courtlistener.com/` 作为 HTTP 端点加入并走 OAuth 授权。
- 验收：查一个真实案号 → 返回多数意见正文 + 引用关系 + 后续处理状态；仍须区分多数/协同/反对意见。
- 首次验收 Prompt："用 CourtListener 查 'data breach' 相关判例，确认引注是否真实，并给出原文链接。"
- `last_verified`: `2026-10-03`

### 5.2 CourtListener 自托管替代

- `blakeox/courtlistener-mcp`（MIT，约 52 tools）：完整覆盖 CourtListener API 端点。
- `@cyanheads/courtlistener-mcp-server`（Node/TypeScript，stdio + `COURTLISTENER_API_KEY`）。
- `install_path`: `open_source_self_hosted`；`tier`: B。官方托管不可用或需批量本地检索时使用。
- `last_verified`: `2026-10-03`

### 5.3 DingDuff

- 官网：`https://www.dingduff.com`；官方 Claude Connector，可选 `uvx dingduff-mcp` 自托管。
- 覆盖：美国判例、成文法、PACER 联邦法院文件。
- 服务条款曾限定美国执业律师个人使用；只有用户符合最新资格并主动选择时使用。
- `install_path`: `commercial_subscription`；`tier`: C。
- `last_verified`: `2026-10-03`

### 5.4 官方开放 API

- GovInfo：`https://api.govinfo.gov/`（`GOVINFO_API_KEY`，免费）——联邦公报、US Code、CFR、国会文档。
- Congress.gov：`https://api.congress.gov/`（免费 Key）——立法史。
- Open States：`https://openstates.org/`（免费 Key）——州立法。
- SEC EDGAR / FDA / 各州法院官网。
- `install_path`: `official_public_web` + 可选 MCP 封装；`tier`: A。
- Ansvar US Regulations MCP 见 §2.2；Security Controls MCP 用于 ISO 27001 / NIST CSF / SOC 2 映射，非法学评注主用途。
- `last_verified`: `2026-10-03`

## 六、英国法

### 6.1 legislation.gov.uk 与 i-dot-ai/lex

- 官方 API：`https://www.legislation.gov.uk/developer`（无需 Key）。
- 社区 MCP：`i-dot-ai/lex`（英国立法检索封装）。
- `install_path`: `official_public_web` + `open_source_self_hosted`；`tier`: A/B。
- 验收：给定年份和章节号返回现行有效条文 + 修订历史。
- `last_verified`: `2026-10-03`

### 6.2 BAILII 与判例

- `paulieb89/bailii-mcp`：BAILII 判例检索封装。
- 官方源：`https://www.bailii.org/`、The National Archives、Judiciary.uk、UKSC 官网。
- `install_path`: `open_source_self_hosted` / `official_public_web`；`tier`: B/A。BAILII 覆盖不如 Westlaw/Lexis，重要判例仍应回 The National Archives 或法院官网核验。
- `last_verified`: `2026-10-03`

## 七、法国法

### 7.1 Légifrance

- 官方 API：PISTE 平台 `https://developer.aife.economie.gouv.fr/`（Légifrance API v3，需注册免费 Key）。
- 社区 MCP：`pylegifrance/mcp-server-legifrance`（Python，Légifrance 检索封装）。
- `install_path`: `official_public_web` + `open_source_self_hosted`；`tier`: A/B。
- 验收：Code civil 某条 → 现行版本 + 生效日 + 官方 URL。
- `last_verified`: `2026-10-03`

### 7.2 FR-ELI 与 matematicsolutions/fr-eli-mcp

- GitHub：`matematicsolutions/fr-eli-mcp`；基于 ELI（European Legislation Identifier）元数据。
- 与 Légifrance 官方 API 互补：ELI 便于跨法域链接，Légifrance 提供全文。
- `install_path`: `open_source_self_hosted`；`tier`: B。
- `last_verified`: `2026-10-03`

### 7.3 商业评注

- Dalloz、Doctrine.fr：无官方 MCP。官方站点与订阅库对自动化访问有限制；本包只登记公开可核查的接入方式，使用者如需，须凭其本人持有的订阅，在其自身授权（订阅、令牌、法定许可）范围内通过其订阅方官方页面或其指定的客户端完成访问，不得绕过验证码、访问控制或付费边界。`install_path`: `browser_workflow`；`tier`: C/D，并遵守 §3.1 Beck 的相同核验纪律。
- `last_verified`: `2026-10-03`

## 八、日本法

### 8.1 e-Gov 法令 API 官方

- 官方：`https://laws.e-gov.go.jp/api/`（v2，2024 起，无需 Key 但需注册获取更高限额）。
- 用途：现行法逐字核验的唯一权威源。
- `install_path`: `official_public_web`；`tier`: A。
- `last_verified`: `2026-10-03`

### 8.2 社区 e-Gov 封装

- `kentaroajisaka/tax-law-mcp`：税法条文 MCP。
- `kentaroajisaka/labor-law-mcp`：劳动法条文 MCP。
- `groundcobra009/hourei-mcp-server`：通用法令检索 MCP。
- `install_path`: `open_source_self_hosted`；`tier`: B。均为 e-Gov API 封装，最终回官方核验。
- `last_verified`: `2026-10-03`

### 8.3 判例与学术

- 裁判所判例集：`https://www.courts.go.jp/app/hanrei_jp/search1`（无稳定官方 API；官方站点与订阅库对自动化访问有限制，本包只登记公开可核查的接入方式，实际访问须由使用者在其自身授权（订阅、令牌、法定许可）范围内通过官方页面或其指定的客户端完成，不得绕过验证码、访问控制或付费边界。相关社区工具属第三方自动化访问，稳定性与授权由使用者自行确认，不得用于形成引注依据）。
- CiNii：`https://ci.nii.ac.jp/`；MCP 封装 `ckgerteis/cinii-mcp`（题录/摘要，全文需回 CiNii 或订阅数据库）。
- 有斐閣、判例時報、Westlaw Japan、LEX/DB：均无官方 MCP。官方站点与订阅库对自动化访问有限制；本包只登记公开可核查的接入方式，使用者如需，须在其自身订阅授权范围内通过其订阅方官方页面或其指定的客户端完成访问，不得绕过验证码、访问控制或付费边界（`browser_workflow`；`tier`: C/D）。
- `install_path`: 混合；`tier`: B（CiNii 题录）/ D（判例的第三方自动化访问）/ C（商业订阅）。
- `last_verified`: `2026-10-03`

## 九、韩国法

### 9.1 korean-law-mcp

- GitHub：`korean-law-mcp`（社区活跃度最高的韩国法 MCP，与韩国法制处关联开发者维护）。
- 覆盖：现行法令、法令沿革、部分司法判例。
- `install_path`: `open_source_self_hosted`；`tier`: A（对成文法）。
- 验收：给定法令名 + 条文号返回现行文本 + 施行动态 + 官方 URL。
- `last_verified`: `2026-10-03`

### 9.2 官方源

- 国家法令信息中心 `https://www.law.go.kr/`；综合法律信息 `https://glaw.scourt.go.kr/`（判例）。
- `install_path`: `official_public_web`；`tier`: A。
- `last_verified`: `2026-10-03`

## 十、加拿大法

### 10.1 CanLII

- 官方 API：`https://developer.canlii.org/`（免费 Key）。
- 社区 MCP：`Alhwyn/canlii-mcp`（CanLII 检索封装）。
- `install_path`: `official_public_web` + `open_source_self_hosted`；`tier`: A/B。
- 验收：一个真实 citation → 判决全文 + 后续处理（CanLII 提供 subsequent history）。
- `last_verified`: `2026-10-03`

## 十一、瑞士法

### 11.1 opencaselaw

- GitHub：`opencaselaw`（CC0，瑞士联邦法院判例开放数据）。
- 官方源：`https://www.bger.ch/`（联邦法院）、`https://www.admin.ch/`（联邦法规）。
- `install_path`: `open_source_self_hosted` + `official_public_web`；`tier`: A/B。
- 瑞士成文法无稳定免费 MCP；德语条文可交叉 `gesetze-im-internet.de` 或 Ansvar Germany 定位。
- `last_verified`: `2026-10-03`

## 十二、台湾地区法

### 12.1 mcp-taiwan-legal-db

- GitHub：`lawchat-oss/mcp-taiwan-legal-db` 与 `oldbear-meme/mcp-taiwan-legal-db-integrated`。
- 客户端配置（uvx 推荐）：
  ```json
  {"mcpServers": {"taiwan-legal-db": {"command": "uvx", "args": ["mcp-taiwan-legal-db"]}}}
  ```
- 工具：`search_judgments` / `search_regulations` / `get_judgment` / `query_regulation` / `get_interpretation`（宪法法庭）。
- 注意：司法院裁判系统对自动化访问有限制；本包只登记公开可核查的接入方式，实际访问须由使用者在其自身授权（订阅、令牌、法定许可）范围内通过官方页面或其指定的客户端完成，不得绕过验证码、访问控制或付费边界。Windows 下 `python` 改为 `.venv\Scripts\python.exe`。
- `install_path`: `open_source_self_hosted` + 部分 `browser_workflow`；`tier`: B。
- `last_verified`: `2026-10-03`

### 12.2 tw-legal-rag

- GitHub：`aa0101181514/tw-legal-rag`：以 RAG 方式检索台湾法规与判决。
- `install_path`: `open_source_self_hosted`；`tier`: B。
- `last_verified`: `2026-10-03`

### 12.3 官方源

- 全国法规资料库 `https://law.moj.gov.tw/`；司法院 `https://www.judicial.gov.tw/`；宪法法庭 `https://cons.judicial.gov.tw/`。
- `install_path`: `official_public_web`；`tier`: A。所有 MCP 输出须回上述源核验。
- `last_verified`: `2026-10-03`

## 十三、其他法域

- 印度尼西亚：`pasal`（印尼法规 MCP，`open_source_self_hosted`，`tier`: B）。
- 巴西：`brlaw`（`tier`: B）；官方 `https://www.planalto.gov.br/` 与 `https://www.lexml.gov.br/`。
- 西班牙：`BOE`（官方公报封装，`tier`: A/B）；官方 `https://www.boe.es/`。
- 波兰：`legal-cite-pl`（`tier`: B/D，社区活跃度低）。
- 沙特/阿联酋：Ansvar `@ansvar/saudi-law-mcp` / `@ansvar/uae-law-mcp`（见 §2.2）。
- `last_verified`: `2026-10-03`

## 十四、通用学术（跨法域论文/期刊/预印本）

### 14.1 openags/paper-search-mcp

- GitHub：`openags/paper-search-mcp`（MIT）；聚合 arXiv / bioRxiv / medRxiv / PubMed / SSRN（via OpenAlex）/ Google Scholar（可选）等约 25 个来源。
- 候选能力：`scholarship.search`、`scholarship.fulltext`（限开放获取源）。
- `install_path`: `open_source_self_hosted`；`tier`: A（开放学术首选）。
- 验收：给定关键词 → 返回带 DOI/arXiv ID 的题录 + 至少一条可下载全文的开放来源。
- `last_verified`: `2026-10-03`

### 14.2 blazickjp/arxiv-mcp-server

- GitHub：`blazickjp/arxiv-mcp-server`（Apache-2.0）；arXiv 专用，含全文下载与本地缓存。
- 候选能力：`scholarship.search`、`scholarship.fulltext`（arXiv 领域，法学交叉学科如 Law-and-AI、Empirical Legal 有用）。
- `install_path`: `open_source_self_hosted`；`tier`: A。
- `last_verified`: `2026-10-03`

### 14.3 Semantic Scholar / OpenAlex

- `zongmin-yu/semantic-scholar-fastmcp`：Semantic Scholar API 封装。
- `oksure/openalex-research-mcp`：OpenAlex 元数据 + 引文网络。
- `install_path`: `open_source_self_hosted`；`tier`: A（API 免费）。
- 验收：给定 DOI → 返回摘要 + 引文关系 + 开放获取链接（若有）。
- `last_verified`: `2026-10-03`

### 14.4 中文学术

- 见 §1.3：CNKI 走 `cookjohn/cnki-skills`（`browser_workflow` + `tier`: C）；中文期刊库通过已配置的学术通道；本地 Zotero/PDF 走 `local.corpus`。

## 十五、出口与排版工具

### 15.1 Pandoc

- CLI 与 MCP：`vivekVells/mcp-pandoc`（MIT）；本项目脚本 `scripts/export_docx.py` 直接调用 `pandoc` CLI。
- `install_path`: `open_source_self_hosted`；`tier`: A（`export.docx` 首选）。
- 注意：`mcp-pandoc` 是社区封装，最终能力仍取决于本机是否安装 Pandoc 可执行文件；`scripts/probe_channels.py` 自动探测本机 `pandoc`。
- `last_verified`: `2026-10-03`

### 15.2 LibreOffice headless

- `soffice --headless --convert-to pdf`；`scripts/probe_channels.py` 自动探测 `soffice` / `libreoffice`。
- `install_path`: `open_source_self_hosted`；`tier`: A（`export.pdf_render`）。
- `last_verified`: `2026-10-03`

## 十六、跨条目的通用注意事项

1. **官方来源核验**：所有 MCP 返回的结果都应引导用户回到官方公报/数据库核验原文（EUR-Lex / 司法院 / GovInfo / e-Gov / Légifrance / law.go.kr / CanLII 等）。
2. **网络环境**：部分服务（如台湾法 MCP、Beck-Online、Doctrine）在特定网络环境下需要额外配置或代理，用户须自行处理并遵守当地法律法规与订阅条款。
3. **鉴权安全**：API Key 通过环境变量传入，不硬编码在配置文件中；`research-profile.yaml` 只记录"已配置/未配置"，不写凭证。
4. **客户端差异**：不同 MCP 客户端的配置语法不同，引导时须按使用者实际使用的客户端确认，不按特定厂商绑定。
5. **陈旧检测**：目录 `last_verified` 超过适用重校验窗口（托管/OAuth 与第三方自动化访问类通道 30 天，官方公开来源 90 天；窗口定义见 [通道分级配置与重校验流程](channel-setup-workflow.md) §四），或某条目 `revalidate_before` 已到期，须回官方页面重新核校后方可用于新项目；`scripts/probe_channels.py` 会给出目录级陈旧警告，但每条目重校验由 Agent 完成。
6. **归档仓库**：例如 `Ansvar-Systems/German-law-mcp` 已于 2026-07-07 归档，官方推荐切换到 hosted gateway；引用仓库前先查 Archive 状态。
7. **社区活跃度**：Star 数只作为参考，最终以最近 commit 时间、issue 响应、上游 API 是否仍开放为准；本目录不硬编码 Star 数以降低过期风险。
8. **禁止**：不得基于本目录的 MCP 结果直接签署 `primary_verified` 或 `verified_fulltext`；所有引用必须回到官方源或原始出版社页面二次核验。

## 十七、参考文档来源

本目录的条目按来源类别汇编，均可公开回溯：

- 官方出版方、政府与国际组织页面（端点、鉴权方式、覆盖范围与使用条款以官方页面为准）；
- 公开的 MCP / 注册表目录（如 mcp.so、mcp.world、Smithery、PulseMCP）与代码托管仓库，用于发现社区封装与替代实现；
- 使用者提供的配置笔记，仅作为候选线索，写入前须按官方页面复核。

可追溯性由各条目自身承载：每条通道卡片记录自己的 `last_verified` 与官方 URL。来源之间出现分歧时，以官方端点（或仓库当前 README）为准，并在下一次复核时更新 `last_verified`。
