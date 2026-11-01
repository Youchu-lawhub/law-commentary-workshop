# mcp-configs

本目录是**使用者侧的运行输出位置**，发布包内不含任何配置文件。

按 [通道分级配置](../../references/channel-setup-workflow.md) 层级 C 跑通一个开源 MCP 通道后，把核验结果写入本目录的 `<slug>.json`，字段至少包含 `source_repo`、`source_ref`（commit OID 或 release tag）、`tested_at`、`minimal_probe_summary` 与 `config_template`。

规则：

- **不写入凭证**。密钥一律用环境变量占位符（如 `${CNKI_MCP_KEY}`），实际值留在客户端凭证库。
- 本目录内容属于本机状态，**不进入交付包**，也不应提交回仓库（见根目录 `.gitignore`）。
- 每次使用前须重新与上游 README 核对；即使本目录已有历史模板，也不得直接沿用（见 `channel-setup-workflow.md` 层级 C）。
