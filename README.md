# 中国法律评注论文工作坊（law-commentary-workshop）

面向中国法学条文评注：完整条文评注、争点型评注与规范群评注。把"写一条法条评注"拆成可执行、可核验、可交付的工序，并保留人工判断与最终责任。

当前版本见 `SKILL.md` 头部与 `CHANGELOG.md`；发布名称"中国法律评注论文工作坊"与包标识 `law-commentary-workshop` 指同一作品。

## 适用与不适用

**适用**：完整条文评注、争点型评注、规范群评注；为评注服务的外语材料检索、翻译与核验。

**不适用**：评注以外的体裁、替代律师出具法律意见、预测裁判结果、无规范基础的策论、需要实地调查或当事人访谈的实证研究。

## 能不能拿来办案

**能。** 本包采用 PolyForm Noncommercial 1.0.0，并由作者追加授权：**个人执业使用（含律师以收费方式承办案件）与组织内部使用均可直接进行，署名为唯一持续条件**；只有对外商业化（出售、嵌入对外产品或服务）需要书面授权。完整文本见 `SUPPLEMENTARY-GRANT.md`。

## 运行要求

- Python 3.9+（CI 覆盖 3.9–3.13），脚本仅使用标准库；
- 可选：Pandoc（生成 DOCX）、LibreOffice 或 Pages/Word（逐页目检）；
- 法律检索、学术检索与本地知识库通过使用者自行配置的 MCP/API/本地目录接入。

## 安装

将本目录放入你的 skills 目录，或直接在目录内运行脚本。无需安装 Python 依赖。

```bash
python3 scripts/preflight.py   # 安装前自检：Python、外部工具、包内文件完整性
```

## 快速开始

```bash
# 0) 首次使用前：建立并确认用户级通道注册表（安装态，跨项目持久）
python3 scripts/channel_registry.py init
python3 scripts/channel_registry.py ack
python3 scripts/channel_registry.py status

# 1) 建立项目
python3 scripts/new_commentary_project.py --output ./my-project --law "中华人民共和国民法典" --article "第1165条"

# 2) 导入已 ack 的通道注册表，并复验能力槽
python3 scripts/channel_registry.py import --project ./my-project
python3 scripts/probe_channels.py ./my-project --corpus-root /path/to/materials

# 3) 选择或生成版式配置
python3 scripts/format_profile.py init --preset journal-cn-default --output ./my-project/format-profile.json
python3 scripts/format_profile.py validate ./my-project/format-profile.json

# 4) 导出 Word（默认交付；PDF 仅按需）
python3 scripts/export_docx.py ./my-project/07-paper.md ./my-project/07-paper.docx \
  --format-profile ./my-project/format-profile.json

# 5) 重新审计、统一命名并打包交付；随后独立复验完整性
#    前置：07-paper.md 必须已写入正文（仍是空模板时会被拒绝，含 --draft）；
#    正式交付还须通过全部质量闸门，否则只能显式使用 --draft 导出工作稿。
python3 scripts/package_delivery.py --project ./my-project --slug art1165
python3 scripts/verify_delivery.py --delivery ./my-project/delivery

# 6) 一手材料已合法保存时，可做快照复验
python3 scripts/verify_evidence.py --project ./my-project
```

境外法与学术通道（`report` / `plan` / `judge` 全程离线）：

```bash
python3 scripts/foreign_sources.py report
python3 scripts/foreign_sources.py plan --jurisdiction DE --layer norm
python3 scripts/foreign_sources.py judge --url https://www.gesetze-im-internet.de/
```

`foreign_sources.py check` 会向登记表中的第三方端点发起一次真实 HTTP 请求，因此必须显式加 `--allow-network`；未加时返回 `NETWORK_NOT_AUTHORISED`（退出码 3）。涉密或未授权项目请勿运行。

## 目录

| 路径 | 用途 |
| --- | --- |
| `SKILL.md` | 主入口：元原则、流程、引注体例、排版、门禁、交付 |
| `references/` | 方法、检索、通道配置、境外法、比较法、翻译、伦理、编校与交付细则 |
| `assets/format-profiles/` | 版式预设（默认/通用） |
| `assets/foreign-law-sources.json` | 境外法与学术通道登记表 |
| `assets/templates/` | DOCX 参考模板 |
| `assets/project-template/` | 新项目模板与签署表 |
| `scripts/` | 探测、导出、审计、版式、打包与复验工具 |
| `agents/openai.yaml` | 跨宿主代理调用配置 |
| `PRODUCTION-READINESS.md` | 工程回归与真实环境验收的区分矩阵 |
| `RELEASE.md` | 维护者的发布与复验流程 |

## 质量门禁

正式放行以 `scripts/audit_commentary.py` 与 `quality-signoff.json` 的 44 项人工签署为准。`scripts/validate-skill.py` 只是成稿快速体检，不替代审计。门禁覆盖：规范准确性、结构、注/评双层、案例真实性、引注、比较法必要性、版式、翻译与学术伦理。

## 隐私与数据

- 本地知识库默认只读；不修改 Zotero 数据库，不回写 Obsidian 笔记。
- 凭证只存放在客户端凭证库或环境变量，项目文件不记录密钥。
- 使用 hosted MCP/API 时，检索词会发送给相应服务；敏感材料不得上传未授权平台。
- 通道探测只做最小用例；`UNVERIFIED` 条目不等于可用，须按验收 Prompt 实测。
- **交付包脱敏**：`channel-probe.json` 与交付清单中的本机绝对路径在打包时替换为末级名称并标记 `[已脱敏]`；项目内原件不变。对外分发前仍须人工复查。

## 测试

```bash
python3 -m unittest discover -s scripts/tests -v
```

CI 定义在 `.github/workflows/ci.yml`（Linux/macOS × Python 3.9–3.13）。

## 许可

本包采用 **PolyForm Noncommercial License 1.0.0**（标准全文以 URL 提供，见 `LICENSE`），并由著作权人另行追加许可授予，**允许个人执业使用（含收费办案）与组织内部使用，署名是唯一持续条件**；仅对外商业化需书面授权。详见 `SUPPLEMENTARY-GRANT.md`（A 导读／B 补充授权／C 第三方内容边界／D 版权声明）。

**注意**：这不是 OSI 认可的开源许可；对外表述请使用"公开发布 / source-available"，不要称为"开源版"。第三方名称与端点仅作为配置指针，权利归各自所有者（见 `NOTICE`）。

## 限制

- 技能不提供法律意见；所有结论须由具备资格的人核验。
- 通道登记表中标 `UNVERIFIED` 的条目尚未在本机实测；MCP 端点须在客户端完成握手。
- 未安装 Pandoc 时不会伪装生成 DOCX（返回 `EXPORT_UNAVAILABLE`），只交付 Markdown 与版式说明。
- 期刊规则、法条版本与判例后续状态会变化，投稿前须重新核对官方来源。
- 正式交付必须重新通过全部质量闸门，并同时具备 Markdown 与 DOCX；工作稿须显式用 `--draft`，并生成 `DRAFT-NOT-FOR-SUBMISSION.txt`。`--force` 会把旧交付目录整体改名保留，覆盖前请自行归档。
- 交付哈希只证明打包后文件未变，**无法**证明学术创新、文献真实或同行评审水平。当前版本不能保证自动调用每一个外部学术数据库，或无人工同行评议即达到顶级期刊发表水平。

尚未完成的生产级验收事项见 `PRODUCTION-READINESS.md`；维护者发布流程见 `RELEASE.md`。
