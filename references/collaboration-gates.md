# 共创确认闸

本工坊不是一次性代写器。确认闸用于让用户在真正改变论文方向的节点作决定，同时避免对每个机械步骤反复追问。

原设计有七个闸，实践中切得过碎、且多数闸只给用户一份摘要简报而看不到待确认的完整文档。现合并为**四个实质决策点**，并强制每个闸把**全部待确认文件的完整内容**呈现给用户。合并只减少打断次数，不降低任何一个决策的严肃性：四闸全部为 `hard`，必须由用户亲自批准。

## 一、交互原则

1. 已知信息不再询问；把相关决定合并成一轮，通常每轮不超过三个短问题。
2. 问用户之前先给判断：已完成什么、发现什么、推荐什么、各方案代价是什么。
3. **闸门必须呈现完整待确认文档，不能只给摘要。** 每个闸在 `project-state.json` 里声明一组 `review_files`；请求确认时，Agent 必须在对话中把这些文件的实质内容完整展示出来（大纲给全文、初稿给全文、研究闸给来源账本与命题-证据表的关键内容），再链接文件供复核。只说“请确认附件”或只贴一段简报都不合规。底层 JSONL/CSV 仍保留供逐条复核，但不能要求用户去读原始账表才能作决定。
4. `hard` 闸必须由用户作出 `approved` 决定。Agent 展示可判断的完整材料与具体问题；待决定的动作暂停，独立的材料核验与准备可继续。允许异步询问，实际授权可来自既有会话或本轮自然语言。
5. 四闸均为 `hard`，不再设可自动通过的 soft 闸；`auto_approve_soft_gates` 对这四个闸无效，Agent 自批一律无效。
6. 用户提出新增资料、观点或要求时，先写入 `10-decision-log.md`，再判断实质影响；只有方向、前提或主要结构变化才回滚相应确认闸。局部补引注和措辞修改保留有效批准。
7. 有明确修改条件且授权修改后继续时，按条件修改并记录条件式授权；方向尚不明或需再次决定的才列为 `rework`。

## 二、四个确认闸

| ID | 时机 | 覆盖的原闸 | 用户确认 | 返工回退到 |
|---|---|---|---|---|
| `G1_topic` | 规范档案 + 问题地图与暂定命题完成 | 原 G1_norm_scope + G2_thesis | 条款范围、相邻规范、研究截止日；核心争点、文体、暂定立场、最强反方 | `norm_locked` |
| `G2_research` | 主检索、证据整理与命题-证据取舍完成 | 原 G3_research + G4_evidence | 各类资料覆盖是否足够、正反材料是否平衡、撤回命题与证据缺口；是否补充资料、案例、作者、观点、法域或写作要求 | `retrieval_complete` |
| `G3_outline` | 大纲调试完成 | 原 G5_outline | 结构、章节功能、论证顺序、篇幅和知识增量 | `outline_approved` |
| `G4_final` | 完整初稿 + 编校放行 + 导出前 | 原 G6_draft + G7_delivery | 论证是否成立、是否遗漏反方、质量报告是否可接受；期刊体例、匿名/作者版、DOCX/PDF 文件组合 | `draft_complete` |

每个闸的 `review_files`（须全部填妥、无 `{{占位符}}`、非空，并在请求确认时全文呈现）：

- `G1_topic`：`02a-thesis-brief.md`、`01-norm-dossier.md`、`01a-norm-brief.md`
- `G2_research`：`03a-research-brief.md`、`04a-evidence-brief.md`、`03-source-ledger.jsonl`、`05-claim-evidence.csv`、`04-case-matrix.csv`、`02-search-log.csv`
- `G3_outline`：`06a-outline-brief.md`、`06-outline.md`
- `G4_final`：`07a-draft-brief.md`、`07-paper.md`、`09-quality-report.md`、`09a-delivery-brief.md`

## 三、阶段简报与全文呈现

每个闸仍有一份人类可读简报（`brief`，即上列 `review_files` 的第一项），开头给简要结论，回答：

- 本阶段完成了什么；
- 当前最重要的三项发现；
- 尚存缺口、不确定性或冲突；
- 推荐选项及理由；
- 另一个合理选项及代价；
- 请用户决定的具体问题。

简报之外，**必须同时呈现该闸其余 `review_files` 的实质内容**。`scripts/gate.py --request <GATE>` 会把这些文件逐份全文打印（超长文件头尾截断并给出完整路径），Agent 据此在对话中向用户展示，而不是仅转述简报。判据：用户在批准前，应当已经能读到自己在批准的东西——大纲闸能看到完整大纲，终稿闸能看到完整初稿与质量报告。

## 四、研究与证据闸 `G2_research`

在进入大纲设计前，必须提交 `03a-research-brief.md` 与 `04a-evidence-brief.md`，并呈现来源账本、命题-证据表、案例矩阵与检索日志的关键内容。至少说明：

- 已检索通道、检索日期、检索式范围和停止理由；
- 规范、案例、中文学术、实务材料和比较法分别覆盖到什么程度；
- 支持与反对暂定命题的代表材料；
- 命题-证据取舍：哪些命题被撤回或限缩、正反是否平衡、证据缺口在哪；
- 无全文、权限受限、样本偏差及尚未核验事项；
- 哪些新材料可能改变中心命题或文章结构。

向用户明确询问：

> 在进入大纲设计前，您是否还希望补充任何资料、案例、作者、学说、比较法法域、实践经验或写作要求？如无补充，请明确确认按当前资料范围继续。

用户补充后执行定向检索，更新账本和简报，再次请求确认。只有用户明确批准，`G2_research` 才能通过。

## 五、大纲确认闸 `G3_outline`

必须按 [大纲共创与调试](outline-collaboration.md) 完成候选结构、章节论证卡、覆盖矩阵和压力测试，并在请求确认时呈现 `06-outline.md` 全文。结合完整会话解释用户实际意思；“按推荐结构写”是授权，“继续看看别的方案”不是。仅在确实存在会改变执行的歧义时澄清，不要求固定批准词。

## 六、脚本与留痕

使用：

```bash
python3 scripts/gate.py /absolute/path/to/project --status
python3 scripts/gate.py /absolute/path/to/project --request G2_research
python3 scripts/gate.py /absolute/path/to/project --approve G2_research --by user --note "按当前资料范围继续"
python3 scripts/gate.py /absolute/path/to/project --rework G3_outline --by user --reason "第三部分与第四部分重复"
```

`--request` 与 `--check` 会打印该闸全部 `review_files` 的完整内容。脚本同步更新 `project-state.json` 并追加 `10-decision-log.md`。Agent 不得手工把闸改成 approved 来代替用户确认。

脚本中的 approver 只是操作者填写的记录，不能验证真实身份。登记用户批准必须记录用户原话和对话定位；不得以填写 `--by user` 制造批准。

> 迁移说明：本版本把 `project-state.json` 的 gates 从七个改为四个（schema_version 仍为 2）。用旧七闸模板创建的既有项目，其 `project-state.json` 需按 §二 的四闸结构重建 gates 段后，才能用新版 `gate.py` 继续；已完成交付的旧项目无需回改。
