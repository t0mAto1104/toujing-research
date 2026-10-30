<p align="center"><b>简体中文</b> | <a href="README.en.md">English</a></p>

# Toujing Research · 透镜研究 Skill

让你的 Agent 完成 **A 股公司基本面研究、财务分析与核验、研究报告审阅、公告与财报取证**。

从[透镜 V3.12.2](https://github.com/t0mAto1104/toujing-fundamental-copilot)的研究方法与数据适配中独立整理。自带选定的公开取数工具，不依赖透镜网站、网站数据库或单独安装 a-stock-data；分析与写作由使用者自己的 Agent 完成。

版本：**0.1.0**。这是独立的首版工具包，不是网站完整运行时的复制品。仓库保持 **private**；其他使用者需要获得仓库访问权限才能安装。

## 包含什么

| 能力 | 实现 |
|---|---|
| 公司研究 | 公司与竞争、财务质量、行业政策、估值风险四专业工作流；共享证据、集中补证、审阅和综合 |
| 财务分析 | 财务科目映射、单位归一、同期间同比、TTM、三表勾稽、部分现金质量指标；保留公式、输入和来源 |
| 报告审阅 | 证券身份、证据版本、引用、计算值／单位／期间检查，以及由 Agent 完成的语义与事实审阅 |
| 公告取证 | 公告目录、明确选择的 PDF 读取、用户 PDF／TXT／Markdown 导入、主机搜索资料导入 |
| 数据获取 | 腾讯快照和日线、新浪三表、巨潮公告，带有限备用入口；可选使用者自己的同花顺财务备用源 |

默认研究七模块：核心结论、公司与业务、财务质量、行业与政策、同业比较、估值与情景、风险与跟踪。可以遵循用户的其他模板。

## 安装

先通过自己已登录的 GitHub 客户端取得私有仓库，不要把访问令牌放进 URL 或聊天：

```bash
git clone https://github.com/t0mAto1104/toujing-research.git
```

将完整 `toujing-research` 目录放到 Agent 支持的 skill 目录。例如 Codex 的 `~/.codex/skills/toujing-research/`，或 Claude Code 的 `~/.claude/skills/toujing-research/`。不要只复制 `SKILL.md`；脚本和参考资料也是必需的。若同名目录已存在，先检查版本，不要直接覆盖用户修改。新会话中确认客户端已发现该 skill。

直接指定仓库中的 `SKILL.md` 让 Agent 使用也可以，无需全局安装。其他 Agent 的安装路径和执行权限按其客户端设置；支持 Markdown 并不意味着拥有脚本执行、联网、搜索或并行能力。

基础工具只需 **Python 3.10+ 标准库**，无需额外数据 API Key。运行：

```bash
python3 scripts/toujing_cli.py doctor
```

如果 `trusted_ca_certificates_available` 为 `false` 或请求返回 `tls_certificate_error`，应修复当前 Python 的可信 CA 配置，或改用已有有效证书的 Python。不要使用 `verify=False` 或关闭 TLS 校验。此环境问题不能解释为所有上游数据源都故障。

只有 PDF 文字读取需要可选依赖，建议放进自己的虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-pdf.txt
```

Windows 可使用虚拟环境的 `Scripts/python.exe`。无 PDF 依赖时，行情、财务、文本资料和报告核验照常使用。脚本不会自动安装软件或更新上游。

## 使用

对 Agent 说：

> 使用 $toujing-research 研究凯赛生物。先确认证券身份，解释业务和发展历程，再分析财务、竞争、行业和估值；有条件地给出明确结论，缺口统一放在文末，保留来源。

或者：

> 使用 $toujing-research 审阅这份报告，逐项检查数字、口径、来源支持和分析结论；先列出可定位的问题，不重写原文。

公开取数可独立运行：

```bash
python3 scripts/toujing_cli.py collect 600519.SH --out /path/to/task/evidence.json
python3 scripts/toujing_cli.py financials /path/to/task/evidence.json --industry industrial --out /path/to/task/workpaper.json
python3 scripts/toujing_cli.py plan /path/to/task/evidence.json --industry industrial --out /path/to/task/plan.json
```

请替换输出路径。数据和报告存放在技能仓库外的独立任务目录，不提交到 Git。Agent 按技能流程补充搜索、阅读原文、完成专业分析、审阅和写作；`collect` 或 `plan` 本身不会自动调用模型生成报告。

详细入口：[SKILL.md](SKILL.md) · [命令](references/commands.md) · [数据格式](references/data-contract.md) · [财务方法](references/financial-methods.md) · [审阅](references/report-review.md)。

## 数据源与费用

- **默认公开来源：** 选定的腾讯、新浪、巨潮及东方财富备用接口，无需使用者注册数据账号。接口仍可能限流、超时、变更或不可达，不能保证持续可用。
- **可选增强：** 仅在使用者主动指定 `--hithink` 时，读取其进程环境变量 `HITHINK_FINANCE_API_KEY`，用于部分缺失财务数据的备用获取。不携带透镜网站的凭据，不自动启用付费服务。
- **模型与联网搜索：** 使用宿主 Agent 已授权的模型及搜索工具；这些服务可能按使用者自身套餐计费。skill 不内置模型 API、不替使用者购买服务，不承诺固定费用或必然成功。
- **离线资料模式：** 网络不可用时，可分析用户的文本／PDF 和明确标记的旧缓存。没有搜索能力时，只分析已经取得的资料，不能宣称资料完整。

默认采集是研究起点：单公司快照、最近最多 28 期财务、约 550 个自然日的日线、最近最多 40 篇公告目录。它不等于上游全部 87 项能力，不提供自动五年估值历史、OCR、证券交易、全市场数据库或严格时点回测。

## 边界与真实性

- 不将缺失值填零，不把总净利润当归母，不混用母公司／合并、累计／单季、静态／TTM／预测估值。
- 财务计算与 AI 写作分离；冲突字段保留并排除受影响计算，已有独立事实仍可用于分析。
- 区分资料链接、目录、片段、文字提取与人工核验；PDF 读取不等于视觉核验、OCR 或全文事实审计。
- 历史截止日期按“当时可知”处理；发布日期未知的财务接口值不参与历史分析。当前数据仍可能被重述，不承诺无前视偏差的历史数据集。
- 纯取数缺口放报告末尾；会改变判断的条件保留在正文。标题加入 AI 辅助分析及非投资建议声明。
- 并行须宿主支持且获得授权，否则顺序完成相同分工；最多两个专业同时运行。脚本不会自行创建 Agent 或后台任务。
- 结构化审阅检查不是准确率保证。引用是否真正支持论点、因果推断及遗漏问题仍需要 Agent 对照原文审阅。

安全机制包括固定 HTTPS 主机、禁跟随重定向、凭据仅发送指定服务、来源限流和请求预算、密钥不进入公开 HTTP 缓存、按用户本地存储、输入来源隔离及保守 PDF 读取。提示词注入防护仍依赖宿主工具权限；skill 不能提供绝对安全保证。详见[安全边界](references/safety-and-boundaries.md)。

## 验证与开发

```bash
python3 -m unittest discover -s tests -v
```

基础测试不联网、不使用真实密钥、不调用模型，财务样本均为合成数据。可选 PDF 测试需要 `pypdf`。当前验证范围和真实接口结果记录在 [VALIDATION.md](VALIDATION.md)。不得把离线测试通过说成已经实测报告准确率、所有数据源可用或成本下降。

## 上游与许可

采用 **Apache-2.0**。a-stock-data 的固定原版入口及许可证放在 `vendor/a-stock-data/`，版本和校验值见 [UPSTREAM.json](vendor/a-stock-data/UPSTREAM.json)。运行适配器是经过收敛的独立脚本，不动态执行上游 Markdown，不自动追踪 `main`。

感谢 [Simon Lin 的 a-stock-data](https://github.com/simonlin1212/a-stock-data)；研究方法与适配经验来自[透镜项目](https://github.com/t0mAto1104/toujing-fundamental-copilot)。作者归属、改动和再分发说明见 [NOTICE](NOTICE) 与 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。代码许可不包含第三方数据、新闻、研报或 API 服务的再授权。
