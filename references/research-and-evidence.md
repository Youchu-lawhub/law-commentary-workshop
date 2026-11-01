# 研究与证据协议

本协议用于把“搜过”变成可复核的研究过程。核心对象是条文、来源、案例、命题和检索批次，而不是一份无法追踪来历的参考文献列表。

## 一、来源层级与用途

### 1. 中国现行规范

优先级一般为：

1. 制定或发布机关的公报、正式数据库、官网原文；
2. 权威商业法律数据库的版本化文本与效力信息；
3. 权威出版物、释义和汇编；
4. 新闻、公众号、博客或搜索摘要。

第 4 层只能用于发现线索。现行法直接引文至少由第 1 层逐字核验；官方页面不稳定时，可由两个独立权威来源交叉核验并在报告说明限制。

### 2. 中国案例

按规范意义而非简单数量组织：指导性案例、人民法院案例库案例、最高人民法院公报/典型案例、最高人民法院及高级人民法院裁判、其他可核验裁判。层级不等于结论正确，但决定其说服力与使用方式。

必须读取完整裁判文书或官方案例文本后，才能归纳裁判理由。题录、摘要和数据库“裁判观点”标签只能用于检索与初筛。

### 3. 学术文献

优先直接专题论述、经典或开创性文献、最新实质研究、权威评注/专著，再到一般教材、会议资料和网络评论。期刊级别、引用次数和作者身份只作相关性信号，不能代替内容评价。

境外学术文献不是数量指标。是否使用取决于该条是否存在可查明的继受脉络、规范目的是否具有普遍性，以及境外研究能否检验中国法解释方案；纯本土规则或境外资料无法取得原文时，不设“外文文献下限”，也不得用外文文献充数。确需使用时，按 [比较法协议](comparative-law.md) 核验原文并标注语种与版本。

### 4. 外国法

优先官方法令、判决、立法材料和正式评注/权威数据库。二手中文介绍可帮助定位，但不得作为外国法现状的唯一依据。

## 二、检索矩阵

围绕条文建立多组可组合的检索词：

- 标识词：法律全称、简称、条号、旧法条号、司法解释条号；
- 教义词：规范性质、请求权、抗辩、构成要件、法律效果、举证责任、竞合制度；
- 事实词：典型交易、行为、主体、损害、救济和争议事实；
- 学说词：主要学说名称、代表作者、通说/有力说/反对说；
- 案例词：案由、争议焦点、裁判理由短语、上位概念与同义词；
- 比较法词：目标法域原文术语、法条号、制度功能与代表评注。

检索先宽后窄：发现术语和来源 → 用字段与时间筛选 → 沿脚注、引用和被引用网络扩展 → 回到原始文献。记录每次检索式和筛选规则，避免只保存“漂亮案例”。

## 二之一、检索工具链

按“发现 → 核验 → 管理 → 综述”排列，工具只承担流水线中的一段：

| 环节 | 工具类型 | 作用 | 纪律 |
| --- | --- | --- | --- |
| 建候选池 | 综合学术检索 | 按主题、作者、DOI 找文献 | 结果是候选，不是已读 |
| 补中文证据 | CNKI 类通道 | CSSCI、中文期刊、学位论文、会议 | 法学优先；关键题录回期刊官网/DOI |
| 引文追踪 | Google Scholar、Web of Science | 被引、相关文献、引文链 | 引文数不作质量判断 |
| 全文精读 | ScienceDirect、HeinOnline、Beck、CiNii | 订阅内全文与页码 | 权限合规，不绕过订阅 |
| 批量取文 | DOI/OpenAlex → PDF、BibTeX/RIS | 下载、题录、推送文献库 | 只取合法可得全文 |
| 系统综述 | PRISMA 类流程 | 去重、筛选、提取、质量评价 | 保留检索式、纳入/排除理由 |
| 文献管理 | Zotero、Juris-M | 条目、笔记、引注样式 | 库藏可检索≠全文已读 |

选择原则：中文证据优先补 CNKI 类通道；外语材料先用开放索引发现，再回官方原文或出版商页核验；不把任何单一工具的输出当作“检索已饱和”。

## 三、证据状态

`03-source-ledger.jsonl` 每行一个 JSON 对象，`source_id` 唯一。允许状态：

- `discovered`：仅发现题名或链接；
- `metadata_verified`：题录已从可靠页面核对；
- `abstract_read`：只读摘要；
- `partial_read`：已读能够精确定位的实质部分，但未读全文；只能支持所读范围内的命题，必须记录 `read_scope` 与 `source_form`，不得外推作者完整立场；
- `fulltext_read`：完整阅读学术/实务文献并记录定位；
- `primary_verified`：已核对官方规范、裁判原文或其他原始材料；
- `excluded`：因重复、无关、不可核实、失效或质量不足排除。

禁止把状态倒推：有 PDF 文件不自动等于 `fulltext_read`；数据库宣称有原文不自动等于 `primary_verified`。

每条至少包含：

```json
{"source_id":"S001","type":"statute","title":"","authors":[],"publication":"","date":"","status":"primary_verified","authority":"official","locator":"第X条/第X页/边码X/段落X","read_scope":"","source_form":"official_text","url_or_identifier":"","checked_at":"YYYY-MM-DD","supports":[],"contradicts":[],"notes":""}
```

`type` 建议使用 `statute`、`judicial_interpretation`、`legislative_material`、`case`、`article`、`book`、`commentary`、`thesis`、`official_report`、`foreign_law`、`foreign_case`、`web`。`locator` 对拟引用来源不得为空。

## 四、命题—证据绑定

`05-claim-evidence.csv` 每行一个可检验命题：

```text
claim_id,proposition,claim_type,source_ids,counter_source_ids,draft_location,verification_status,notes
```

`claim_type` 可为：`norm_text`、`history`、`case_holding`、`scholarly_attribution`、`empirical`、`author_inference`、`comparative`。多个证据 ID 必须用英文分号分隔，不能用英文逗号；CSV 单元格内部的逗号会造成列错位。

规则：

- 规范文本、历史事实、裁判理由、作者观点、统计或外国法现状必须有相称来源；
- `author_inference` 可以没有直接支持来源，但必须建立在已列明的前提上，不得伪装成通说或实务现状；
- 反方的重要证据填入 `counter_source_ids` 并在正文回应；
- `verification_status` 仅允许 `draft`、`verified`、`blocked`、`withdrawn`；最终成稿不得引用 `draft` 或 `blocked` 命题。

## 五、案例矩阵

`04-case-matrix.csv` 至少包含：

```text
case_id,source_id,case_name,case_number,court,decision_date,document_type,authority_level,procedure,material_facts,issue,holding,reasoning,rule_extracted,law_version,subsequent_status,source_url,verified_at,included,exclusion_reason
```

不要把数据库摘要直接放入 `reasoning`。`material_facts` 只记录决定规范适用的事实；`rule_extracted` 应写成带条件的规则，而非脱离案情的口号。对同一问题持不同立场的案例必须进入同一矩阵比较。

类案样本需说明：数据库、检索式、日期范围、法院层级、案由/全文字段、去重方法、纳入/排除标准、可获得性偏差。不能把数据库检索数量当作真实案件总量。

成稿应在文首脚注或“案例搜集情况说明”中交代完整口径，至少包含：案例来源（如人民法院案例库、已配置的案例数据库）、检索日期、该条命中数、剔除重复/被撤销/无关案例的数量与理由、剩余有效案例数，并按案型、案由或法院层级给出分布。该说明随稿保留，不并入致谢。

## 六、规范档案

`01-norm-dossier.md` 的每条规范至少记录：

- 正式名称、制定/发布机关、文号（如有）、公布日、施行日、修订日和效力状态；
- 精确条款层级与全文；
- 官方 URL 或可复核定位；
- 与相邻条款、定义、特别法、司法解释和时间效力规范的关联；
- 历史文本与现行文本的差异；
- 法律事实、构成要件、法律效果、证明责任的初步拆分；
- 本次核验使用的来源 ID 和核验日期。

旧法、草案、征求意见稿和域外法必须醒目标记，禁止与现行中国法混写。

## 七、学说史与文献综述

按“问题—立场—理由—后果—代表来源—演变”整理，而非逐作者摘录。确认首倡或学说影响关系时，应核对发表时间、原文脚注和被引用关系；无法证明“首次提出”时改用“较早主张”“代表性主张”等可证表述。

对观点作内在理解：先假定其能自圆其说，重构前提和理由，再作外部评价。不要因只读摘要而批评全文，也不要把二手文献对某作者的概括写成该作者原话。

## 八、检索停止条件

不要用固定篇数冒充全面。满足以下条件方可结束主检索：

1. 规范网络和主要版本已覆盖；
2. 权威案例层级和相反裁判均被主动检索；
3. 核心学说的代表文献、较早文献和最新研究已覆盖；
4. 每个核心命题在账本中有相称证据或被明确撤回；
5. 连续至少两轮新检索主要返回已收录来源，且没有出现新的核心学说或案例类型；
6. 比较法材料已经达到回答具体中国法问题所需的深度，不为“国际视野”无限扩张。

若时间、权限、全文或法域语言造成缺口，停止状态是 `blocked` 或“有范围限制的完成”，不是假称饱和。

主检索达到停止条件后，不能立刻搭大纲。先形成 `03a-research-brief.md`，由用户在研究闸 `G2_research`（合并原资料覆盖闸与证据取舍闸）决定：按当前范围继续、定向补检、提供本地资料、调整比较法法域、缩小命题或停止。用户提出补充后应重新检索和确认。

## 九、三校机制

沿用“存真、辨伪、统系”的三轮校勘：

1. 来源校：题录、原文、页码、案号、条号、链接和日期；
2. 解释校：观点是否准确、案例规则是否受事实与程序限定、反方是否被公平呈现；
3. 统稿校：术语、规范简称、结构层级、立场、交叉参照、脚注与正文是否一致。

每轮由不同视角完成并在 `quality-signoff.json` 记录。发现错误时修正文稿和账本，不只在报告中提示。


## 附：来源账本（03-source-ledger.jsonl）字段规范

审计脚本（audit_commentary.py）对账本的硬性要求如下，缺任一项将无法通过放行审计：

| 字段 | 必填范围 | 说明 |
|---|---|---|
| `source_id` | 全部 | 唯一 ID（建议 N=规范、C=案例、S=学术） |
| `type` | 全部 | 枚举：statute/regulation/norm/judicial_interpretation/legislative_material/case/official_report/foreign_law/foreign_case/article/book/commentary/thesis |
| `title` | 全部 | 标题 |
| `status` | 全部 | 枚举：discovered → metadata_verified → abstract_read → partial_read → fulltext_read → primary_verified（以及 excluded）。**可引用判定**：statute/regulation/norm/judicial_interpretation 类须达 primary_verified；article/book/commentary/thesis 类须达 partial_read 或 fulltext_read；case 类须达 partial_read 及以上 |
| `checked_at` | 可引用来源 | 核验日期，YYYY-MM-DD |
| `locator` | 可引用来源 | 定位：条号/页码/案号 |
| `url_or_identifier` | 可引用来源 | URL 或其他标识（案号/DOI 可用） |
| `read_scope` | partial_read 来源 | 已读范围说明（如"题名、作者、刊物、年份与摘要"） |
| `source_form` | partial_read 来源 | 来源形态（如"数据库题录与摘要"/"MCP 返回摘录"） |

规范类来源另需至少一条满足：`authority` ∈ {official, official_cross_check} 且 `validity_status` ∈ {current, in_force, 现行有效} 且 `as_of` 为 YYYY-MM-DD（CURRENT_OFFICIAL_NORM_MISSING 检查）。
纳入案例矩阵的每件案例还要求 case.fulltext 与 case.subsequent 能力槽通过真实探测，否则只能走 --draft 工作稿通道。

**语义提示**：partial_read 意为"已读该来源的部分文本"（如判决书摘录、论文摘要），须在 read_scope 中如实记录已读边界；题录/摘要不得冒充全文。
