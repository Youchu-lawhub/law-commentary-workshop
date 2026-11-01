# Changelog

本文件遵循 Keep a Changelog 约定与语义化版本。版本号以 `SKILL.md` 头部 `metadata.version` 为准。

## [1.3.1] — 2026-11-01

公开发布前的许可与质量返修。不改变方法论与闸门语义，只修复"文档说的与代码做的不一致"以及不宜对外发布的内容。

### Added

- **许可**：`SUPPLEMENTARY-GRANT.md` 重写为四段结构（A 导读／B 补充授权／C 第三方内容边界／D 版权声明）。在 PolyForm Noncommercial 1.0.0 之上，由著作权人追加授予**个人执业使用（含律师收费办案）与组织内部使用**，署名为唯一持续条件，只扩权不缩权，终止触发仅挂在保留行为与署名条件上。`LICENSE`、`NOTICE`、`README` 与 `SKILL.md` 同步为双轨表述。
- **路由层**：`SKILL.md` 新增"加载路由"表，把全部 `references/` 文件按任务时机接入。此前有 7 个参考文件不被任何入口引用、运行时永不加载，而 `layout_rendered`、`anonymization_checked` 等签署项的规程正在其中。
- **脱敏**：`package_delivery.py` 打包时把 `channel-probe.json` 与交付清单中的本机绝对路径替换为末级名称并标记 `[已脱敏]`。
- **发布治理**：新增 `.github/workflows/ci.yml`（Linux/macOS × Python 3.9–3.13）与 `.gitignore`；维护者发布流程从 `references/` 移出为根目录 `RELEASE.md`。

### Changed

- **版本一致性**：全包统一为 1.3.1。`SKILL.md` 不再保留叠在正文之上的历史版本节（原"1.1.0 必读"块拆入路由表与硬规则，原"RC2 发布前保护"块改写为"十、交付复验"）；`README`、`PRODUCTION-READINESS` 去内嵌版本号；本文件重排为单一起点。
- **版式契约三方对齐**：`assets/format-profiles/journal-cn-default.json` 的段码由 `［N］`、独立成段改为 `【N】`、段首连排且不独立成段，与 `SKILL.md` §5 一致；页面边距、正文字号与行距同 `SKILL.md` §5 及内置 DOCX 模板对齐，模板样张的说明文字同步。
- **交付契约与代码一致**：`channel-probe.json` 归入支撑材料（与 `package_delivery.py` 的实现一致）；slug 推导只认单个"第N条"的阿拉伯数字（款次不影响推导），出现两个及以上条文或中文数字条文号时要求显式 `--slug`；`--force` 帮助文本改为"整目录改名替换并保留备份"；工作工件编号范围更正并补齐 14/15/16 三个研究资产模板。

### Fixed

- `validate-skill.py` 注密度：原先只从 `[^1]:` 切分正文并只数 `\[\^\d+\]:`，使用具名脚注（`[^alpha]:`）的合规稿件会被报成"0.00 注/千字"；现与 `audit_commentary.py` 同口径接受任意脚注标签。`--help` 不再被当作文件名处理。
- `gate.py` 路径边界：`project-state.json` 中的 `review_files`／`brief`／`artifact` 名称此前可用 `../` 让闸门把项目外文件全文打印进会话；现一律限定在项目目录内并拒绝符号链接。
- `foreign_sources.py` 网络申报：`check` 实际会向登记表中的第三方与付费端点发出请求，而模块文档自称"只读取本地 JSON"；现须显式 `--allow-network`，User-Agent 如实标识本工具而不伪装浏览器，不可达／需鉴权等结论返回非零退出码。
- `package_delivery.py`：`--draft` 不再把仍含 `{{占位符}}` 的空模板打成"交付包"。
- `audit_commentary.py`：不再在"无结论章"是硬门的同时提示用户补写结语／结论。
- 测试可发现性：补 `scripts/tests/__init__.py`，`discover -s scripts/tests` 与加 `-t .` 两种写法均可运行；消除两处只能恒真通过的断言与测试输出泄漏；为脱敏、路径边界、脚注口径、slug 推导与网络授权各新增回归用例，回归规模由 49 项增至 114 项（macOS × CPython 3.9 实测全绿）。
- `scan_corpus.py`：存在 `read_error` 行时不再返回 0，避免流水线把部分失败当成功。
- `foreign-law-sources.json`：删除跨项目遗留的实测叙事与宿主品牌绑定、GitHub star 数等易失效断言（改为"以官方现行说明为准"）；移除指向未登记第三方转载镜像的引注路径；修正 GB／CN 法域键与 `official_hosts` 不匹配导致的静默查无。

### Removed（对外发布适格性）

- 删除实名学者、实名期刊与真实检索命中的文献记录：发表体例规则不再挂靠于任何具体作者与刊物，改为"对中国法学期刊已刊条文评注印刷体例的归纳观察"（`references/commentary-method.md` 附节、`SKILL.md` §5）。
- 删除"可绕开官方站点反爬""受限环境需 Playwright 绕过 WAF""订阅库第三方爬虫"一类表述：改为记录官方限制确实存在、并由使用者在其自身授权（订阅、令牌、法定许可）范围内经官方页面或其指定客户端访问，不得绕过验证码、访问控制或付费边界。与 `SECURITY.md` 的"不得绕过登录、验证码、付费墙或访问控制"自洽。
- 删除私有开发过程叙事：`references/channel-catalog.md` 的"参考文档来源"不再点名本地文件与某次代理深查；通道条目的验证状态不再记录会话内掉线、密钥重发等调试经过。
- 删除示例中的真实付费出版物名（德国期刊与评注系列名），改回占位符形式，符合 `CONTRIBUTING.md`"示例不使用真实作者、书名或期刊名"。
- `NOTICE` 的原创保证与第三方内容边界改写，使其与实际内容来源一致，并补充名称对照（发布名与包标识）。

## [1.3.0] — 2026-11-01

### Added

- **安装态/任务态分离**：新增 `scripts/channel_registry.py`（init / ack / import / status）管理用户级通道注册表（默认 `~/.law-commentary/channel-registry.json`）。通道与授权类决策（代装授权、语料目录、外发边界）一次配置、跨项目持久；注册表未 ack 时 `import` 拒绝工作——未经用户确认的通道不得进入任何项目。
- **任务期降级决策表**：`channel-setup-workflow.md` 新增节；unknown／故障槽三选一处置（① 官方源兜底＝自动留痕 ② 请用户补充＝必须询问 ③ 收窄范围＝必须用户确认），写入项目 `02b-channel-decisions.md`。
- **访谈拆分**：`cold-start.md` 拆为安装轮（一次性，→ 注册表）与任务轮（每项目三问：研究对象、期刊格式、比较法需求）。
- **审计强制点**：`CHANNEL_SOURCE_MISSING`（非 unknown 槽缺来源标记）、`DEGRADATION_DECISION_MISSING`（unknown 槽无 02b 处置）、`COMPARATIVE_LAW_DECISION_MISSING/_UNCONFIRMED`（比较法决定缺用户拍板，占位符剥离后校验）。

### Changed

- 项目模板：02a 增 `comparative_law_decision` 强制字段；新增 `02b-channel-decisions.md`；`10-decision-log.md` 增"通道导入与降级处置"行。
- 背景：端到端实测发现访谈无闸门强制、代理可绕过境外通道询问；本版将"绕过访谈"从靠自觉改为过不了审计。

## [1.2.1] — 2026-11-01

### Fixed

- **跨平台**：`package_delivery.py` 交付路径符号链接检查改为仅豁免操作系统创建的系统级别名链接本体（macOS 的 `/tmp`、`/var`、`/etc` → `/private/...`），深层符号链接照拦；回归测试首次在 macOS 全绿。
- **自检工具**：`audit_commentary.py` 与 `validate-skill.py` 的案例搜集情况说明检测正则由字符类（永远无法匹配双字词）修正为 `案例(搜集|收集|检索)情况说明|案例来源说明`，两个校验器口径统一。
- **许可证**：`SKILL.md`、`README`、`SUPPLEMENTARY-GRANT` 的许可证表述统一为 PolyForm Noncommercial 1.0.0，与 `LICENSE` 一致（1.3.1 在此基础上补作者追加授权）。
- **版本元数据**：`validate-skill.py` 横幅版本号与包版本对齐。

### Added

- **通道目录 §1.5**：中文期刊文献 MCP 通道卡片（知网·法律／万方数据／百晓智能），含已核验端点、通用 MCP 客户端配置模板、验收 Prompt 与诚实实测状态；法律规范与案例检索默认候选维持华宇元典（§1.1），不在本节配置。
- **配置流程**：`channel-setup-workflow.md` 新增"中文期刊文献三通道引导配置"五步流程与登记示例。
- **发表体例纯化规范**：`commentary-method.md` 附节 9 条（注评不外显、条文前置、案例说明入脚注、同前注用印刷数字上标等）；`SKILL.md` §5.6 正文纯化节。
- **导出增强**：`export_docx.py` 脚注证据状态标记自动转灰色斜体（工作稿可溯性），新增 `--purify` 参数供投稿稿移除。
- **文档**：`research-and-evidence.md` 补来源账本字段规范（status 枚举、locator／read_scope／source_form 等）。

### Verified

- 端到端工作流实测两篇评注工作稿：G1–G3 用户闸门、机器审计、`--draft` 打包、交付完整性校验全部通过。

## [1.2.0] — 2026-10-31（工程加固）

- 事务式交付：提前检查文件，暂存后整体发布；覆盖采用目录备份和失败回退。
- 正式交付必须具有正文 Markdown 与 Word，并重新执行质量审计。
- 新增 `verify_delivery.py`，独立检查交付内容、SHA-256、缺失及篡改。
- 新增发布与安全回归测试；明确自动化测试的边界与尚未完成的端到端验证。

## [1.1.0] — 2026-10-31（rc1）

- 正式交付新增实时审计强制阻断；单独工作稿模式与风险标注。
- 增加证据快照哈希检查器、对抗式学术贡献审查、跨 Agent 能力契约。
- 排除源包缓存及操作系统附属文件，新增工程回归测试。
- 许可证确定为 PolyForm Noncommercial 1.0.0；保留作者署名。

## [1.0.0] — 2026-10-31

首个公开发布版。

- 五条元原则：请求权基础框架、注／评双层、四项特质、五级证据防护、六类场景披露。
- 四种评注目录骨架：一般型、不完全规范型、制度型、义务违反型。
- 案例类型化、案型矩阵、案例搜集情况说明；规范组合表、制度界分、除外规则。
- 检索与证据：来源账本、案例矩阵、命题—证据绑定、三校机制。
- 境外法：六步核验、置信度分层、14 项引注核验、反幻觉纪律、通道登记表与取文阶梯。
- 外语材料：五阶段翻译流程、术语优先级、法学翻译硬约束、四层记忆与质检。
- 冷启动：六组能力槽，自动扫描本地知识库（Zotero／Obsidian／语料目录）与期刊槽，三轮访谈。
- 版式：可配置 `format-profile.json`，默认 Word，PDF 按需；样式与页面设置写入 DOCX。
- 质量门禁：44 项人工签署，机器审计与快速体检分离。
- 交付：`delivery/{slug}-{类型}` 统一命名，附交付清单与 sha256。
