# 交付与版式

目标是形成可审阅、可复核、可继续更新的投稿包，而不只是一个正文文件。目标期刊现行规则始终优先。

**版式权限顺序**：用户上传的目标期刊要求 > 用户自定义/选择的预设 > 默认预设 > 本文件的保守基线。具体参数落在项目 `format-profile.json`，由 `format_profile.py` 校验、`export_docx.py --format-profile` 应用；本文件只规定交付流程与检查项。macOS 模板以 `Songti SC` 实现宋体、`Hiragino Sans GB` 实现黑体/标题，换机器时按可用字体替换并复查渲染。

## 一、先建立期刊版式画像

在生成成品前，将下列信息写入 `research-profile.yaml` 并注明核验日期与来源：栏目、总字数、标题层级、摘要和关键词、脚注或尾注、是否需要文后参考文献、中英文信息、图表要求、匿名规则、基金和作者信息、文件格式、模板、投稿声明。

未指定期刊时使用保守基线：中文标题；中文摘要和关键词；正文按“一、（一）、1.”三级层级；页下脚注；不自动生成与脚注重复的参考文献；A4 版面；作者信息与匿名稿分离。该基线只是工作稿，不应冒充任何期刊的正式格式。

## 二、交付包

统一使用 `delivery/{slug}-{类型}.{ext}`，由 `scripts/package_delivery.py` 生成。默认交付 Word；PDF 仅在用户要求时纳入。

```text
delivery/
  art1165-commentary.docx          # 默认交付
  art1165-commentary.md
  art1165-commentary.pdf           # 仅按需
  art1165-format-profile.json
  art1165-quality-report.md
  art1165-quality-signoff.json
  art1165-channel-probe.json
  art1165-ai-usage.md              # 如适用
  art1165-ethics-checklist.md      # 如适用
  art1165-delivery-manifest.json
```

加 `--include-support` 时另含来源账本、案例矩阵、引注审计、比较法备忘录、决策日志、通道探测与翻译工件。项目内的 `01–16` 编号文件是工作工件，不直接作为交付名。对外只需投稿件时，仍保留内部证据文件，除非用户要求删除。

## 三、DOCX 生成（PDF 按需）

优先使用当前环境已有的文档生成能力、目标期刊模板或稳定的 Pandoc/Word 工作流。生成时：

- 使用样式而非手工空格控制标题、正文、引文和脚注；
- 设置中文字体回退，避免在另一台机器上乱码；
- 脚注采用文档原生脚注，不把脚注伪造成正文小字；
- 标题编号、交叉引用、目录和图表编号应可更新；
- 超链接显示文本与实际目标一致，打印稿仍能识别来源；
- 清除批注、修订、隐藏文本、作者姓名和路径等文档元数据后再生成匿名版。

如果无法可靠生成原生脚注或渲染检查，应交付结构清晰的 Markdown、证据包和明确的版式待办，不得把未经核验的 DOCX 称为最终投稿版。

本 Skill 提供稳定、可失败的导出链路：`scripts/export_docx.py` 调用 Pandoc 和 reference DOCX，生成后按 `--format-profile` 写入样式与页面配置，再由 `scripts/render_check.py` 检查 OOXML 结构、样式契约、原生脚注关系与匿名元数据。内置模板是 `assets/templates/journal-cn.docx`；目标期刊有模板时以期刊模板替换它。

内置模板的样式表只承担两件事：给 Pandoc 提供可挂接的样式名（Title、Heading1–3、Body Text、FootnoteText 等），以及提供 Normal 与页面设置基线。**各级标题与正文的最终字号、行距、边距一律由 `format-profile.json` 在导出时写入**（`scripts/apply_format_profile.py`）。因此直接打开模板文件看到的样式值不构成规范依据，版式契约的唯一来源是 `SKILL.md` 第五节与项目所用的 profile；两者不一致时以 profile 为准，并按 §四 逐页目检确认成品。

```bash
# 1) 选择或生成配置
python3 scripts/format_profile.py init --preset journal-cn-default --output format-profile.json
# 2) 校验并向用户回显摘要
python3 scripts/format_profile.py validate format-profile.json
# 3) 导出时应用
python3 scripts/export_docx.py 07-paper.md 07-paper.docx --format-profile format-profile.json
```

```bash
python3 scripts/export_docx.py 07-paper.md submission/anonymous-manuscript.docx \
  --template /path/to/target-journal.docx --anonymous --render \
  --render-dir submission/rendered
```

脚本找不到 Pandoc 时返回 `EXPORT_UNAVAILABLE`；找不到渲染器时返回 `RENDER_UNAVAILABLE`。两者都是需要配置或降级的诚实状态，不启动脆弱的手工 OOXML 兜底。`STRUCTURE_OK` 或 `RENDER_CREATED` 不等于人工版式签署。

## 四、逐页视觉检查

DOCX 生成后必须渲染为 PDF 或逐页图像以供目检；PDF 只是检查载体，默认不作为交付物。至少检查：

- 首页面貌、标题、摘要、关键词和正文起始位置；
- 中文、英文、数字和标点字体是否一致，生僻字是否缺字；
- 各级标题不落在页末，正文无大面积异常留白；
- 脚注标记与脚注内容清楚，长脚注跨页合理，无脚注覆盖页码；
- 引文块、表格、公式和长 URL 不越界；
- 页码、页眉、分节和最后一页正常；
- 匿名稿页面与文件属性不泄露身份。

修复后重新渲染，而不是只在编辑器中目测。`layout_rendered` 只有在最后一版完成逐页检查后才能签署。

内置通用模板已经过 A4 单页样张渲染检查，包含标题、三级标题、摘要、关键词、块引文、图表题、脚注文本和页码样式。不同操作系统的中文字体回退仍须在实际投稿机器上复查；模板使用 `Songti SC` 与 `Hiragino Sans GB`，必要时根据期刊和运行环境替换为可用字体。

## 五、匿名版与作者版

匿名版应删除或中性化：作者姓名、单位、邮箱、基金编号、致谢、明显自我指涉、文件属性、批注和修订历史。不要删除理解文章所必需的真实引用；自引仍按学术规范处理，只避免暴露作者身份的措辞。

作者版保留真实信息占位，交由用户确认。Agent 不应推测作者单位、职称、基金、通讯方式、贡献声明、利益冲突或 AI 使用政策。

## 六、最终交付说明

交付消息应简明列出：

- 研究对象与截止日；
- 放行状态；
- 投稿文件与证据/质量文件；
- 已核验的期刊规则日期；
- 仍存限制、无法取得的全文或需要作者作出的价值选择；
- 若法规、案例或投稿规则更新，最先需要重跑的步骤。

避免使用“顶刊必录”“绝对无误”等承诺。可以准确表述为：“已通过本工坊的证据、引注、编校和版式门禁，达到技术上的投稿准备状态。”
