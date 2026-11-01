# 冷启动访谈与能力探测

冷启动只做三件事：**扫描已有能力 → 只问无法推知的事 → 为真实缺口给出配置或注册路径**。1.3.0 起访谈分为安装轮（通道与授权，写入用户级注册表）与任务轮（研究决策，每项目三问）。不把任何商业数据库写成强制依赖，不先安装一组“可能有用”的服务，不在项目文件里保存凭证。

## 一、能力槽清单

按六组管理。每个槽位只回答一个问题：**这项能力现在由谁提供、能否跑通、跑不通会砍掉什么论证**。

### A. 规范

| 槽位 | 应证明的能力 |
| --- | --- |
| `norm.exact_article` | 按规范全称与条号返回准确全文 |
| `norm.validity` | 返回效力、公布/施行、修改与文号 |
| `norm.history` | 查到沿革版本或草案/立法材料 |

### B. 案例

| 槽位 | 应证明的能力 |
| --- | --- |
| `case.search` | 按关键词、案由或语义检索案例 |
| `case.authority` | 识别指导性案例、人民法院案例库、公报/典型案例层级 |
| `case.fulltext` | 读取裁判/官方案例原文及定位 |
| `case.subsequent` | 检查再审、改判、停参或后案处理 |

### C. 学术与期刊

| 槽位 | 应证明的能力 |
| --- | --- |
| `scholarship.search` | 检索中文论文、专著、评注及题录 |
| `scholarship.fulltext` | 在授权范围内读取学术全文与页码 |
| `journal.metadata` | 目标期刊的栏目、周期、字数与收录信息 |
| `journal.recent_articles` | 近几期目录与代表篇目 |
| `journal.submission_rules` | 投稿须知、格式要求、AI 使用政策 |

### D. 外语材料

| 槽位 | 应证明的能力 |
| --- | --- |
| `foreign.official_text` | 读取指定法域官方规范原文 |
| `foreign.case` | 读取外国判例及意见类型/后续状态 |
| `foreign.scholarship` | 检索并读取外语学术文献题录或全文 |
| `translation.assist` | 术语预检、译文生成与自动校验（见翻译协议） |

### E. 本地知识库

| 槽位 | 应证明的能力 |
| --- | --- |
| `local.corpus` | 扫描并检索用户授权的普通目录（PDF/DOCX/MD/TXT） |
| `local.zotero` | 读取 Zotero 文献库、条目、笔记与附件 |
| `local.obsidian` | 检索 Obsidian 库的 Markdown 笔记与双链 |
| `local.notebook` | 读取用户的知识库/Notebook（本地知识库类 MCP） |
| `local.terms` | 读取个人/机构术语表与译名表 |

### F. 输出

| 槽位 | 应证明的能力 |
| --- | --- |
| `export.docx` | 生成带原生脚注和样式的 DOCX |
| `export.pdf_render` | 将 DOCX 渲染为 PDF/逐页图像供目检；PDF 仅按需交付 |
| `format.profile` | 读取用户确认的版式配置（字体、字号、行距、边距、层级） |
| `format.journal_spec` | 读取目标期刊上传的排版要求（DOCX/PDF/图片/网页/文本） |

## 二、先自动扫描，再提问

### 1. 扫描三层

1. **会话层**：枚举当前可调用的 MCP、连接器、skill 与浏览器工具，按槽位映射（按能力，不按品牌猜）。
2. **本机层**：`scripts/probe_channels.py` 自动探测 Pandoc、LibreOffice、Zotero 数据库、Obsidian 库、授权语料目录。
3. **项目层**：若为恢复项目，读取既有 `channel-probe.json` 与 `research-profile.yaml`，核对 `tested_at` 是否超过重校验阈值。

### 2. 扫描产物

生成 `channel-probe.json`，每个槽位至少含：

```json
{
  "status": "available|partial|auth_required|missing|unknown",
  "source": "auto_detected|agent_probe|user_declared|none",
  "tool": "",
  "probe_case": "",
  "probe_assert": "",
  "probe_ok": false,
  "auth_required": false,
  "guidance": "给用户的下一步配置或注册路径",
  "impact": ""
}
```

规则：自动发现只说明“存在”，不说明“可用”；只有跑通最小真实用例才是 `available`。工具存在但用例未过，只能是 `partial` 或 `unknown`。

### 3. 自动扫描命令

```bash
python3 scripts/probe_channels.py /absolute/path/to/project \
  --corpus-root /absolute/path/to/authorized/materials \
  --inventory /absolute/path/to/agent-mcp-observations.json

python3 scripts/scan_corpus.py \
  --root /absolute/path/to/authorized/materials \
  --output /absolute/path/to/project/corpus-index.jsonl
```

Zotero 与 Obsidian 的自动发现结果写入 `local.zotero`、`local.obsidian`；扫描默认只读，不修改库文件，不回写笔记。

## 三、访谈：安装轮与任务轮（1.3.0 起分离）

访谈原则不变：**能从材料或扫描报告推知的，不问；一次只问会改变工序的事；每个问题在提问前先说明"为什么问"和"不回答的默认处理"。**

1.3.0 起访谈拆分为两层，分别对应两类决策：

- **安装轮**（一次性）：通道与授权类决策——答案写入**用户级通道注册表**（`scripts/channel_registry.py` 管理，默认 `~/.law-commentary/channel-registry.json`），跨项目持久，不落任何项目文件；
- **任务轮**（每项目）：研究类决策——每篇评注各不相同，收窄至三问，由 G1 闸门材料（02a 的 `comparative_law_decision` 字段）强制留痕。

分离的理由：通道配置"问一次"才有执行基础——要求 agent 每个项目重问全部问题，等于诱导它压缩访谈；而"装过什么、授权过什么"本就不随项目改变。

### 3.1 安装轮（首次使用或注册表过期时）

触发条件：注册表不存在、通道故障、或 `revalidate_before` 过期。流程：

1. **展示扫描报告**：能力槽状态表（可用/需登录/缺失/未知），请用户确认"是否按此继续"；
2. **只问真实缺口**：对仍为 `missing`/`partial`/`auth_required` 的槽位，逐项询问——是否同意代装开源通道（给出名称、覆盖、许可、隐私边界）；是否愿意现在完成登录/OAuth；本地知识库是否授权只读扫描及排除目录；
3. **敏感边界**：哪些材料不得离开本机；检索词是否含可识别当事人信息；是否允许把查询词发送给 hosted 端点。

结论落地：

```bash
python3 scripts/channel_registry.py init            # 创建注册表
python3 scripts/channel_registry.py ack --by "用户"  # 记录用户对安装访谈的确认
# （Agent 将逐槽验收结果写入注册表 channels 字段后）
python3 scripts/channel_registry.py import --project <项目目录>
```

纪律：`ack` 必须由用户本人确认后才能执行；注册表未 ack 时 `import` 拒绝工作（exit 3）——未经用户确认的通道不得进入任何项目。不把"同意安装"泛化为永久授权；同意项逐条记录在 `consents`。

### 3.2 任务轮（每项目三问）

| # | 问题 | 为什么问 | 不回答时 | 留痕 |
| --- | --- | --- | --- | --- |
| 1 | 研究对象（条文/案件/命题）、文献时点、希望解决的争议是什么？ | 决定检索词、规范版本与目录 | 由材料推知并记录假设 | 01-norm-dossier |
| 2 | 目标期刊、篇幅、交付格式与时间要求？ | 决定体式、版式与投稿规则 | 用学术工作稿基线，标注"待目标确定" | research-profile |
| 3 | 本文是否需要境外规范/判例/文献对照（比较法）？**免费开源通道也须一并确认** | 决定 `foreign.*` 槽是否纳入本任务范围 | 视为不启用，正文比较法论述只能转引 | 02a 的 `comparative_law_decision` 字段（须含"用户确认"字样，audit 强制） |

任务轮结束即开始主检索；不因期刊偏好未定而停工。

### 3.3 任务期降级处置

项目开始时从注册表导入通道并做**活性复验**；导入未覆盖或复验失败的槽位进入降级处置，三选一并写入 `02b-channel-decisions.md`（audit 强制逐槽检查）：

| 处置 | 适用 | 决定者 |
| --- | --- | --- |
| ① 官方公开源兜底 | 通道故障但不改变成果范围 | 可自动执行，留痕即可 |
| ② 请用户补充语料/全文 | 需要该槽产出且用户可能持有 | 必须询问 |
| ③ 收窄任务范围 | 如比较法不启动、学说降摘要级 | 必须用户确认 |

任务期通道故障（如 MCP 连接中断）同样记入 02b 复验记录；不得假装可用，不得静默换源。

## 四、能力槽的配置与注册引导路径

每个缺口都给出**一条可执行路径**，而不是一句“请自行配置”。下表是默认引导；具体端点、许可与维护状态以 [检索通道目录](channel-catalog.md) 为准。

| 槽位 | 自动探测信号 | 引导动作 | 官方入口（示例） | 登记字段 |
| --- | --- | --- | --- | --- |
| `local.corpus` | 用户给定目录 | 请用户授权只读目录；运行 `scan_corpus.py` | 无 | 根目录、索引路径、排除规则 |
| `local.zotero` | `zotero.sqlite` 存在 | 安装 Zotero；在首选项启用本机应用通信；建议配 Better BibTeX；提供库路径 | zotero.org | 库路径、条目数、只读确认 |
| `local.obsidian` | `obsidian.json` 中的 vault 路径 | 让用户选择库；只索引 `.md`，跳过 `.obsidian/` 与附件缓存 | obsidian.md | vault 路径、排除目录 |
| `local.notebook` | 会话内存在知识库类 MCP | 列出 Notebook，请用户指定项目所用 Notebook 与 Source | 以实际连接器为准 | notebook id、source 数 |
| `local.terms` | 项目 `terms/` 或用户提供文件 | 导入 CSV/JSON 术语表，登记来源与置信度 | 无 | 文件、条目数、维护人 |
| `norm.*` | 元典等已安装的中国法检索 MCP（按能力映射） | 无 MCP 时引导接入官方/开源通道，或回官方数据库网页逐字核验 | 国家法律法规数据库、最高人民法院官网 | 工具、版本、用例 |
| `case.*` | 案例类 MCP | 同上；权威层级另需人民法院案例库/指导性案例目录 | 人民法院案例库、裁判文书网 | 工具、覆盖层级 |
| `scholarship.search` | CNKI/学术 MCP | 未配置时用开放学术源发现，再回期刊官网/DOI 核验 | CNKI、SSRN、CiNii、Semantic Scholar | 工具、检索式 |
| `scholarship.fulltext` | 订阅或 OA | 请用户提供合法全文；或使用 OA 版本 | 出版商平台、机构库 | 来源、许可 |
| `journal.metadata` | 无（需用户指定） | 请用户给出目标期刊；未定则用通行引注规范基线 | 期刊官网、CSSCI/CLSCI 目录 | 期刊名、栏目、周期 |
| `journal.recent_articles` | 无 | 浏览目标期刊官网近几期目录，记录 3–5 篇代表篇目 | 期刊官网 | 期号、篇目、访问日 |
| `journal.submission_rules` | 无 | 打开投稿须知与 AI 政策页，记录字数、格式、匿名与披露要求 | 期刊官网投稿页 | URL、访问日、要点 |
| `foreign.official_text` | 外语法域 MCP | 按法域选择官方源或开源通道；跑一条现行条文用例 | 各法域官方公报 | 法域、工具、版本 |
| `foreign.case` | 判例 MCP | 同上；记录法院层级与意见类型 | 各法域司法官网 | 法域、工具、覆盖 |
| `foreign.scholarship` | 学术 MCP/订阅 | 先用开放源发现，再回原文或出版商页核验 | SSRN、HeinOnline、CiNii、Beck-Online | 工具、语种、版本 |
| `translation.assist` | 会话内模型/翻译工具 | 无专用工具时按翻译协议执行，并登记术语表 | 无 | 术语表、校验报告 |
| `export.docx` | Pandoc/官方 docx 工具 | 缺失时请用户安装或改用支持的导出路径 | pandoc.org | 工具、版本 |
| `export.pdf_render` | LibreOffice | 缺失时请用户安装 | libreoffice.org | 工具、版本 |
| `format.profile` | 项目 `format-profile.json` | 选择默认/通用预设，或让用户自定义字体字号；生成配置文件并回显摘要 | `assets/format-profiles/` | 预设名、文件路径、确认日期 |
| `format.journal_spec` | 用户上传的投稿须知/样文 | 能读文本则抽取要点并回显确认；图片或扫描件无文本层时，请用户粘贴要点或提供 DOCX/Markdown | 期刊官网投稿页 | 文件、URL、访问日、抽取字段 |

引导话术统一为三步：**现状（缺什么）→ 影响（会砍掉哪类论证）→ 最小动作（装什么/登录什么/授权哪个目录）**。不代用户注册、不代付款、不代填 2FA。

**中国法检索的候选原则**：默认候选为华宇元典；会话中已安装的其他中国法 MCP，或用户自行选择的后端，只要通过最小用例，就按能力槽登记，不因品牌不同降级或排除。

### 4.1 本地知识库的最小配置

| 库 | 最小动作 | 只读边界 |
| --- | --- | --- |
| Zotero | 安装 Zotero；在首选项的高级设置中允许本机其他应用通信；如需稳定引注键可装 Better BibTeX；确认库路径（默认 `~/Zotero`） | 不写条目、不改标签、不改附件；只读统计与导出 |
| Obsidian | 打开目标库，记录 vault 路径；确认是否排除日记、附件、模板目录 | 不写回笔记、不改双链、不触碰 `.obsidian/` |
| 普通目录 | 指定 PDF/DOCX/MD/TXT 根目录 | 不复制全文进项目，只建索引与预览 |
| Notebook/知识库 MCP | 在会话中连接并列出 Notebook，指定项目所用 Source | 不向外部上传未授权内容 |
| 术语表 | 放入项目 `terms/`（CSV/JSON/JSONL/TSV/YAML）或指定路径 | 术语须经人工确认后才作为标准译法 |

### 4.2 期刊槽的最小配置

未指定期刊时，不虚构期刊规则，用通行法学引注规范与通用学术工作稿基线；指定后按三步登记：

1. **期刊信息**：官网栏目、周期、篇幅区间、收录情况；
2. **近期目录**：近几期目录，记录 3–5 篇同栏目代表篇目；
3. **投稿规则**：投稿须知、格式与匿名要求、AI 使用政策；记录 URL 与访问日期。

三项均写入 `research-profile.yaml`；规则可能变动，投稿前重新核对官网，不以旧记录为准。

### 4.3 版式配置（可在每次任务覆盖）

版式优先级：**用户上传的期刊要求 > 用户自定义/选择的预设 > 默认预设 > 通用基线**。

1. 冷启动询问用户：使用默认预设、通用预设、自定义，还是上传目标期刊的排版要求；
2. 上传 DOCX/Markdown/文本时直接抽取；上传 PDF/图片时先判断有无文本层，无文本层不得猜，改请用户粘贴关键条目；
3. 将结果写入项目 `format-profile.json`（可从 `assets/format-profiles/` 复制后修改），运行 `scripts/format_profile.py validate` 校验，再向用户回显“页面/正文/标题/脚注/引文”五项摘要并请其确认；
4. 导出时使用 `scripts/export_docx.py --format-profile format-profile.json`，转换后由 `apply_format_profile.py` 写入样式；
5. 期刊规则或用户要求变化时，重新确认并覆盖配置，不沿用旧版式。

## 五、最小真实用例

每层每次配置都独立跑，用例与本项目相邻：

| 槽位 | 最小用例 | 通过断言 |
| --- | --- | --- |
| `norm.exact_article` | 查研究对象条号现行文本 | 逐字全文＋规范全称＋条号一致 |
| `norm.validity` | 同上 | 现行效力＋公布/施行日＋最新修订 |
| `norm.history` | 最近一次修订前文本 | 历史版本＋修订说明 |
| `case.search` | 已知案由或关键词 | ≥1 条可解析裁判 |
| `case.authority` | 已知指导性案例/入库案例 | 层级标识正确 |
| `case.fulltext` | 打开其中一案 | 裁判正文＋法院/日期/案号 |
| `case.subsequent` | 该案后续字段 | 明确“有后续/无后续” |
| `scholarship.search` | 已知论文标题 | 题录含作者、出处、年份、DOI |
| `scholarship.fulltext` | 打开一篇合法全文 | 全文片段＋页码定位 |
| `journal.metadata` | 目标期刊主页 | 栏目、周期、字数可读 |
| `journal.recent_articles` | 近一期目录 | 可列出篇目与作者 |
| `journal.submission_rules` | 投稿须知页 | 格式、匿名、AI 政策可读 |
| `local.corpus` | `scan_corpus.py` | 索引非空、路径可读、预览可抽 |
| `local.zotero` | 读取条目与附件路径 | 条目数>0，可定位 PDF |
| `local.obsidian` | 检索一个已知笔记 | 命中文件与标题 |
| `local.notebook` | 列出一个 Notebook | 返回 source 列表 |
| `foreign.official_text` | 目标法域一条现行条文 | 官方源逐字＋版本日 |
| `foreign.case` | 目标法域一件判决 | 正文＋法院层级＋意见类型 |
| `export.docx` | `pandoc --version`＋样张 | DOCX 生成，目检脚注/样式 |
| `export.pdf_render` | 样张转 PDF | PDF 生成且逐页可读 |
| `format.profile` | `format_profile.py validate <文件>` | 校验通过，五项摘要与用户确认一致 |
| `format.journal_spec` | 抽取一份上传的投稿须知 | 至少提取页面、正文、标题、脚注四类要求；无法读取时明确告知 |

## 六、能力降级规则

| 缺失能力 | 强制影响 |
| --- | --- |
| `norm.validity` | 规范不得标 `primary_verified`，项目 `BLOCKED` |
| `scholarship.fulltext` | 不得产生超出实际阅读范围的归属；只能按 `partial_read` 限缩 |
| `case.fulltext` | 不得产生 `case_holding` 或归纳裁判理由 |
| `case.subsequent` | 案例只能作待核线索，不能支撑关键结论 |
| `journal.submission_rules` | 不得声称符合目标期刊要求；按通用学术工作稿交付并标注待核 |
| `local.zotero` / `local.obsidian` | 仅使用用户手工提供的文件；不得声称已检索其全部库藏 |
| `foreign.official_text` | 外国法现状不得伪装直接核验；必要时“转引自”并限缩 |
| `translation.assist` | 不得生成译文作为论证依据；只保留原文引用与待译标记 |
| `export.docx` | 不交付声称具有最终版式的 DOCX |
| `export.pdf_render` | 无法逐页目检，`layout_rendered` 不得签署，最高 `REVIEW_REQUIRED`；Word 仍可按默认预设交付 |
| `format.profile` | 按默认预设导出，但标注“版式未确认”；不得声称符合用户要求 |
| `format.journal_spec` | 不得声称符合目标期刊格式；按通用工作稿交付并标注待核 |

`missing` 不必终止项目；它必须机械地缩小相应命题，并在 `03a-research-brief.md` 写明。

## 七、鉴权、隐私与失败

- 需要登录、验证码、OAuth、付费或安装时停止，请用户完成或授权；不绕过访问控制，不代替购买。
- 凭证只放客户端 credential store 或环境变量；项目文件只记“已配置/未配置”。
- 本地知识库默认只读：不修改 Zotero 数据库，不回写 Obsidian 笔记，不上传未授权内容。
- 普通网页搜索只是发现渠道，不自动取得专业数据库的效力、全文或后续状态。
- 无法取得全文时保留题录并降低证据状态，不用搜索摘要补写作者观点。
- 通道全部不可用时，可以完成研究设计与待核清单，不生成虚构脚注的投稿成稿。

## 八、探测后报告模板

向用户报告时固定四段：

1. **可用**：哪些槽位已跑通用例；
2. **待配置**：哪些需登录/安装/授权，各自的最小动作；
3. **影响**：缺失会砍掉哪类论证（引用降级规则表）；
4. **建议最小组合**：完成本项目所需的最少通道，按“已有→免费开源→订阅”排序。

只有条号的用户可先启动探索；缺少期刊与商业数据库偏好不阻断。
