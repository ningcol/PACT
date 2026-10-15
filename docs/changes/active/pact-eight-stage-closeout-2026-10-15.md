+++
[pact]
type = "change"
id = "CHANGE-PACT-EIGHT-STAGE-20261015"
status = "active"
domains = []
+++

# PACT 原始八阶段路线：执行与验收计划（修订版，PACT-only）

> **版本**：2026-10-15 · 修订 2；**状态**：计划待实施，非实现完成报告。  
> **唯一允许写入的仓库**：`ningcol/PACT`。本计划及 PR #185 仅授权**修改和审查计划文档**；不构成 S0～S7 实施、合并或 tag/Release 的授权。  
> **原始历史基线**：`28d8a77e8bbc4fca6db320b4e1a95ac62079385b`；**计划创建时主分支**：`b67d7a725774d8404ad253b43cfca3dd35874fdf`。S0 开始时必须另外固定**实际实施起点 SHA**，不可把上述历史 SHA 冒充届时 HEAD。  
> **来源/约束**：Owner 原始阶段 0～7 要求、PR #178～#184 已有工作、Issues #28/#32/#63；不以 PR 数量或机器 PASS 抵消未通过的原始验收。

## 0. 不可突破的边界、范围与判定语义

### 0.1 只写 PACT；现实证据不得模拟冒充

1. **只允许 PACT 写入**：分支、提交、PR、Issue、测试夹具、文档、Workflow、CI Artifact 和 release asset 仅在 `ningcol/PACT` 或其 PACT 自有临时测试空间。绝不修改、推送、创建 PR 或回写 `ziliu`、`zx-zsb`、`DouBaoFreeImageGen` 等外部仓库。外部历史仅可在已有授权下只读获取；获取失败就是 `blocked/unverified`。
2. **禁止未经授权的生产接入**：不访问外部项目的真实工作目录、私人生产数据、在线业务服务或凭证。真实 Codex / Claude Code / OpenCode runner 只有在**已经合法提供、经 Owner 授权且只访问 PACT 受控夹具**的环境才能调用；否则将对应测试格标 `blocked`，不得使用模拟 Agent 输出替代。计划不自动授予新账号、密钥或在线访问权限。
3. **事实与结论分层**：单元/CI、已安装 `pact.pyz`、历史 replay、真实 Agent 工作流、Owner 观察是不同级别的证据。历史 Smoke 不能被描述为“真实生产闭环”；未采集的人工耗时/问询/Token 不得填 0 或估算为改善。
4. **最小控制面**：优先复用 `task prepare/status/draft/verify/finish`、`discover/context/impact`、`audit`、`run/evidence/complete/eval`；不创建第二套 Product Truth、Decision 库、Beads/向量库或无必要的强制工作流。**原始必须具备的能力不能未经 Owner 同意降级为可选**；实现手段（新增子命令还是扩展旧命令）可以由实测成本决定。
5. **信任边界只加强，不稀释**：保留 Task Contract / Task Context SHA、受管理工作区指纹、Evidence Claim↔AC↔Owner Report 的精确绑定、Convergence/changed-file coverage、风险门禁及路径边界。发现假 pass、安全边界绕过或破坏安装/回退时，阻断下一阶段。
6. **阶段单独签收**：S0→S7 顺序验收，每阶段 1～3 个小 PR；每阶段完成三轮**不同角度的**审查，保留具体证据。三次同一助手检查不等于三名独立 reviewer；独立 Agent 审查需要真实输出和 SHA 绑定，未执行就标阻断。

### 0.2 四类验收项与唯一的状态规则

| 类型 | 含义 | 进入哪种完成判定 |
| --- | --- | --- |
| **E** | PACT 单仓可执行的**强制工程 AC**，包括原始路线要求的实际功能和回归 | `Engineering Complete` |
| **V** | 必须由真实 Agent/真实用户/授权真实任务观察验证的**强制实证 AC** | `Pilot Validated` 和相应阶段整体签收 |
| **X** | 经过冻结实验才能决定**实现路径**的候选方案（非独立功能要求） | 必须记载 adopt/reject 和依据；拒绝无收益方案不视为缺失原始能力 |
| **R** | 只有经 Owner 另外授权才执行的正式发行操作 | `Release Approved`；从不自动触发 |

- 每个 E/V AC 必须有唯一 ID、固定输入/预期、至少一个 RED 反例、复跑命令或人工观察协议、实际证据 URI、base/head SHA、责任主体及状态。
- **AC 状态仅允许** `not-started / in-progress / passed / failed / blocked / unverified`。无证据是 `unverified`；已知依赖（账号、样本、权限、Runner）不可用是 `blocked`，并写明解除条件；实测未达标准为 `failed`，不能改写成“允许警告”。X 方案用 `adopt/reject/defer` 单独登记，不伪装为 E/V 通过状态。
- **阶段状态聚合**：有任一强制 E/V `failed` → `failed`；否则有 `blocked` → `blocked`；否则有 `unverified` 或 `not-started` → `unverified/not-started`（保持实际状态）；全部强制 E/V `passed` 且三轮审查有证据 → `passed`。某个工程子目标可以先达到，但**不能把阶段整体标 passed**。
- **Engineering Complete**：S0～S7 所有 E 类 AC `passed`，工程三轮审查与兼容性证据齐全，已知安全 P0/P1 均关闭。它不代表 V 类已验证。
- **Pilot Validated**：所有 V 类 AC `passed`，并明确观察样本和外推边界；历史重放及模拟 Owner 不能顶替。
- **Eight-stage Accepted**：Engineering Complete + Pilot Validated，且全部阶段强制 AC 与审查通过。缺任何 V 项均不得宣布“八阶段全部完成”。
- **Release Approved**：Eight-stage Accepted + 发布前 R 类检查通过 + Owner 明确批准版本和 tag 范围。`GO/NO-GO` 是一次**决策结果**，不是 AC 状态：缺证据时可输出 `NO-GO: missing evidence`，但相关 S6/S7 V 仍是 `blocked/unverified`；实测失败时输出 `NO-GO: failed criteria`，不能称验收通过。无发布授权时不得打 tag。

**统一 Evidence Ledger**：每阶段在 PACT `docs/evaluation/` 或 PR 内维护表格 `AC-ID | E/V | baseline SHA | head SHA | input/fixture | command or observation | RED/GREEN | run ID/link | result | state | reviewer | rollback | unverified reason`。每次检查写新行，不改写历史 RED 为 GREEN。人工指标使用 `null` + 状态，不接受空缺默认为 0。

## 1. 已确认基线与尚未完成的差额

| 现有 PR | 已实现/证明的部分 | **不得据此核销**的原始要求 |
| --- | --- | --- |
| #178 | Decision 五问瘦身、历史软降权、检索建议简化 | rejected 前提变更、全/部分 supersession 与生命周期全部通过 |
| #179 | 忽略感知扫描、有限重试、失败不发布混合索引 | OS 级原子源码快照或任意并发写入都可无损识别 |
| #180 | `task draft/verify`、明确 AC-ID 的真实命令收据 | 综合收尾诊断、确定性报告回填、导出、跨会话恢复 |
| #181 | 本地验证输入 SHA、外部输入告警和限制 | 任意环境可重放、任意隐式依赖已被证明 |
| #182 | mixed confirmed/pending Rule 告警与注入边界 | 任意 Markdown 章节级规范状态机 |
| #183 | superseded Decision 候选、Knowledge Gardening Skill | 完整/部分取代引用保留的语义验收 |
| #184 | 历史 `ziliu` 临时副本上的 Evidence Smoke | 真实业务 A/B、Owner 减负或跨 Agent 完成闭环 |

**源码对齐事实（以 `b67d7a7` 为准，S0 要重新验证）**：

- `convergence_coverage.py` 与 Schema 已允许 `removed`，但 `.agents/skills/convergence-review.md` 对删除/更新的指引需要修正。
- `run.py` 的 `workspace_changed` 仅比较**执行前、执行后**指纹，不是持续监视器；`evidence.py` 已验证运行后工作区 SHA，却还需显式拒绝中高风险 required pass 依赖 `workspace_changed=true` 的收据。**执行中改动随后恢复**未必可检测，计划不得声称已覆盖。
- Context Envelope v1 `additionalProperties: false`；添加治理锚点/README/意图字段可能使旧读取方拒绝新文件；不能只靠“新字段 optional”声称协议兼容。
- `task` 当前拥有 `prepare/status/draft/verify/finish`；缺综合诊断、最小导出、checkpoint/resume 和真实 A→B 场景证据。
- 现有 OS×Python `9/9` Core Matrix 运行**选定**跨平台测试，并不是“全量单测跑满 9 环境”；Agent×兼容层另有独立九格，不能混写。
- `.pact/VERSION` 仍为 `0.4.0-dev.1`。Issues #28（真实试点）、#32（实际收益）、#63（产品化）仍开放；#63 中 Legacy YAML 迁移要求需结合 `CHANGELOG.md` 已删除未发布旧解析支持的记录，逐项作“实现/历史废止有据/仍阻断”判定，不能静默遗漏。
- PR #185 是计划 PR，不包含 S0～S7 功能实现；Copilot / Codex 独立 Plan Review 曾因额度受限而未产生有效报告。

## 2. 八阶段实施包与原子验收

下列 `AC-Sx-yy` 是**预先登记的结果门槛**。详细测试用例复用现有代码和测试文件，防止在计划中另造第三套可执行真值。每项的具体命令、运行 SHA/ID 和观察者在实施 Ledger 中落地。

### S0 — 双基线、故障回放和盲测设计（P0；仅 PACT）

**工作范围**：`docs/evaluation/`、`scripts/pact/tests/`、`scripts/benchmark/`、`benchmarks/brownfield/`，必要时仅 PACT CI。保存历史 RED 的原始触发条件，新增测试不得改写历史结果。

| AC | 类型 | 强制通过条件 |
| --- | --- | --- |
| **AC-S0-01** | E | 分开记录原始 `28d8a77...`、计划基线 `b67d7a7...` 及 S0 实际实施 HEAD；每条案例给触发 SHA、命令、来源、期望、当前状态和缺失条件，不把旧失败改名为旧成功 |
| **AC-S0-02** | E | 旧/新架构、Domain 无 confirmed Rule、rejected 复用、删除误写 updated、任务中断、stale Evidence、并发探针、来源异常、宿主白名单等都有可重放 RED 或明确阻断原因；已有测试只引用、不复制 |
| **AC-S0-03** | E | 固定全量 unittest、schema/workflow/check/audit、PACT Check、**OS×Python 九格选定测试**、发行包源码/安装版 Smoke 的实际 run ID；准确标注不同测试覆盖范围和未知项 |
| **AC-S0-04** | E | 冻结 A/B 原话、源 commit、风险/Token/count/查询预算、工具版本、评分规则；把 PR #184 已见历史案例留作**回归集**，建立独立 holdout/盲评案例；oracle 在候选冻结后才向评估者揭示 |
| **AC-S0-05** | E | 在看 holdout 结果前登记零容忍安全阈值、召回非退化界限、成本/时延容忍界限、随机 Agent 重复运行规则、失败样本保留策略；阈值无证据时标待定且禁止提前跑正式 A/B |
| **AC-S0-06** | E | 完成 Runner、授权、真实 Owner 数据、外部样本的**可行性清单**：可用/无权限/需谁提供，区分 PACT dogfood、授权历史副本与真实 Brownfield Pilot；缺少真实 `zx-zsb` 输入只用 PACT 脱敏夹具并记不可外推 |

**S0 产出**：`docs/evaluation/eight-stage-baseline-2026-10-15.md`（按日期/SHA 追加结果）、固定 fixture 清单与人类观察字段定义。**不得把旧基线要求为绿色**。

### S1 — 协议一致性与 Evidence 信任（P0）

**调用链**：`.pact/schema/convergence-report.schema.json` → `convergence_coverage.py/converge.py` → `run.py/evidence.py` → `report.py/complete.py` → `readiness.py/status.py` → Skill/文档。

| AC | 类型 | 强制通过条件 |
| --- | --- | --- |
| **AC-S1-01** | E | 从 Schema 枚举与 Runtime `VALID_DISPOSITIONS` 进行机械一致性检查；Skill 正确说明 `aligned/updated/removed/stale/owner-decision/not-applicable`；删除必须用 `removed`，旧文件消失不能当 `updated` |
| **AC-S1-02** | E | `pact-ready`、命令成功、业务语义、环境依赖、Owner Report 分别有不混淆的说明/输出；不为这些概念另造冗余状态字段 |
| **AC-S1-03** | E | 中高风险 required pass **不能**由 `workspace_changed=true` 的 passing run 单独支持；先有真实 RED、排除合法忽略/生成物，再补门禁；前后稳定的合法任务保持 GREEN |
| **AC-S1-04** | E | 明确写出监测上限：指纹仅证明采样时点一致；“执行中修改后恢复”不被误报成已侦测。若原始威胁模型要求抵御这种瞬态写入，另开真实 RED 和可行性决策；不能靠改文案宣称防护完成 |
| **AC-S1-05** | E | Claim/任务/风险/Contract/Context/外部来源/SHA 不匹配、旧 v2 收据、伪造完成、错误 Convergence/Owner 关联的正反例均通过；不以迁移兼容放松门禁 |
| **AC-S1-06** | E | Source 与已安装 `pact.pyz` 同语义通过；协议、安全策略变更必须有 RED/GREEN、Schema/Skill 一致性及必要的旧数据重验指引 |

**停机条件**：任何已知假 pass 未关闭，不得进入 S2。若误挡了非受管理测试产物，应修正工作区分类并留反例，不能删除信任门禁。

### S2 — Decision 最小化、否决理由、取代与清理（P0）

**入口**：`.agents/decisions/`、`docs/governance/decision-authority.md`、`audit/check/impact` 和关联 Skills；不建设新的知识数据库。

| AC | 类型 | 强制通过条件 |
| --- | --- | --- |
| **AC-S2-01** | E | 五问准入清单可供 Agent 评审：未来具体错误、为何不可从普通代码/测试/文档推导、持久期限、唯一归属、删除代价；普通 Bug/UI/重构不自动产生 Decision |
| **AC-S2-02** | E | rejected 记录能检索方案、拒绝理由、当时前提、证据来源和重新考虑条件；前提改变时不误作永久禁令，未确认理由不伪装确认 |
| **AC-S2-03** | E | “完全 superseded”和“部分 superseded”各有固定夹具；前者保留仍重要理由/风险与历史链接，后者不丢仍有效约束；规范引用、ID、路径无悬空 |
| **AC-S2-04** | E | Audit 只给解释充分的 review candidates；已完成 Change/Drift 先查引用和保留义务，不按年龄/引用量自动删除 |
| **AC-S2-05** | E | Source/已安装 Skill 的准入与清理指引一致；Agent 语义复核证明不会为了“多记忆”重复造永久 Note |

**回退**：候选噪声升高则删启发式而非增加大量必填标签。

### S3 — 检索意图、治理锚点、Rule 缺口与 README（P0）

**调用链**：`map.py/repository_files.py` → `discover.py/context.py` → `inspect_project.py/explain.py` → `task prepare` → `context-envelope.schema.json`。默认不引入向量库或整仓 README 全文注入。

| AC | 类型 | 强制通过条件 |
| --- | --- | --- |
| **AC-S3-01** | E | 在固定输入/预算下实验 `work / decision / history` 三种意图；work 偏当前规范，decision 可见 relevant rejected/implemented 理由，history 能找回旧理由；明确记录是否采用可选 `--intent` 和采用依据 |
| **AC-S3-02** | E | Context 能给已有 `truth-ownership / decision-authority / completion-contract` 的**路径锚点**，不让锚点参与普通排名/吞掉任务预算，不冒充业务 confirmed Rule；优先复用现有输出字段 |
| **AC-S3-03** | E | 对调用方显式要求的 Rule-ID 有准确的 `confirmed / absent / pending / mixed / budget-excluded` 结果；**明确强制请求不能悄悄通过**。采用显式可选 `--require-rule RULE-ID` 或等价安全接口，不从自由文本推测强制 Rule |
| **AC-S3-04** | E | 对已选代码模块的最近邻 README 提供限深/限量 metadata hint 和缘由；覆盖缺失、忽略路径、symlink、超大文件、无 Git；不得追加全仓扫描或自动加载全文 |
| **AC-S3-05** | E | Context Envelope v1 为封闭 Schema（`additionalProperties: false`）；新增结构字段前提交**新旧生产者×消费者×源码/安装版**兼容矩阵。若旧 reader 不能读新输出，则采用不增字段的表示，或明确版本升级/迁移/旧任务读取方案；禁止“optional 字段即兼容”的假设 |
| **AC-S3-06** | E | candidate/confirmed、hard count/soft token、authority overage、fallback hints、known_unknowns 保留；holdout 验证关键文件召回与成本不超 S0 预注册界限，强制 Rule 缺失不误宣称 context sufficient |
| **AC-S3-07** | E | 结构级 Context / Ranking 实验有 adopt/reject 记录；**无可验证收益则回退实验**，已有默认 CLI 不变，新的默认必须通过冻结评估后才能启用 |

**实验方案 X**：`--intent` 是否做成新 CLI 参数、额外 ranking 层是否保留、治理锚点是否复用现有字段。这些是实现选择，不允许借“拒绝方案”跳过上述 E 级结果门槛。

### S4 — Evidence 收尾诊断、机械回填与最小导出（P0）

**调用链**：`task prepare/status/draft/verify` → Contract → `run/evidence` → Convergence/Owner Report → `finish/complete/eval`。

| AC | 类型 | 强制通过条件 |
| --- | --- | --- |
| **AC-S4-01** | E | 有**只读**的完成前诊断（优先扩展 `task status --json`，不足时再加 `task assist`），逐 AC 列出未证实/失败的 Claim、缺失 Convergence 与 changed-file coverage、Contract/Context SHA、过期收据和建议重验原因 |
| **AC-S4-02** | E | 只从显式 AC↔真正 passing Claim 拷贝 Owner Report 的 criterion ID、合同原文、原样 Claim、verification ref/Task ID/SHA；不从命令名猜业务效果，不把失败/未验证 Claim 改成 pass |
| **AC-S4-03** | E | 只有显式写入模式才能创建/填空草稿；绝不覆盖 Agent 编辑过的内容，不自动设 `owner.status=completed`、`convergence=aligned`。重复调用、半写入、坏 JSON、中断均不留下假已完成 |
| **AC-S4-04** | E | 实际顺序强制验证：持久化代码/知识 → 稳定工作区 → 最后一次真实验证 → Evidence/Convergence/Owner 语义复核 → finish；验证后更改受管理文件或 `workspace_changed` 的中高风险必需证据不允许 finish |
| **AC-S4-05** | E | 最小 `export` 仅导出协议版本/合同摘要/必要收据元数据和校验和，不含 stdout/stderr、密钥或原始敏感输入；输出仅到 PACT 受控目录（优先现有 `.pact/runs/` 排除区）或 PACT 自有临时目录，防路径逃逸/symlink/部分写；导出副本不升级证据权威 |
| **AC-S4-06** | E | 原有 `draft/verify/finish` 仍可用；源码与安装版在缺 AC、错误归因、外部输入、坏状态、二次运行时的阻断一致，不新增强制填写步骤 |

**实验方案 X**：实现 `assist` 新子命令还是扩展 `status`；证据导出采用现有 JSON 元数据还是薄封装。**不建设导入/同步协议**，除非另获新需求授权。

### S5 — 增量 Checkpoint 与无聊天记录恢复（P1）

| AC | 类型 | 强制通过条件 |
| --- | --- | --- |
| **AC-S5-01** | E | `.pact/tasks/<TASK-ID>/` 下有最小可选、带版本的交接记录：已做/待做、验证引用、未决假设、审查过的 Decision 路径；原子写、不覆盖其他任务、不储存聊天推理/密钥/完整对话 |
| **AC-S5-02** | E | 显式 `task checkpoint`（或既有接口等价能力）允许保存**部分进度**，无需提前完成 Owner Report/Convergence，不改变准备时 Contract/Context 冻结 SHA |
| **AC-S5-03** | E | 只读 `task resume <ID> --json` 能返还目标/AC、真实状态、已证/未证、当前代码差异、收据重验结果、待判断假设、下一步；交接内容被标作**非权威 Agent 叙述**，不可执行其携带的命令 |
| **AC-S5-04** | E | 独立 Python 进程模拟 A 中断→B 无 Chat 接管；分别覆盖稳定/过期 Evidence、rejected 前提不变/已变、坏路径/坏 JSON/重复 checkpoint，B 不会擅自完成或改写旧 SHA |
| **AC-S5-05** | E | 交接输入限长度/类型/路径/Claim ID 与收据数量；旧 Manifest 无交接字段仍可读，坏交接受控报错；跨设备不同步 PACT 本地 `.pact/tasks/.pact/runs`，不得用“导出过”代替重验 |

**边界**：不做跨设备自动同步、持久 Chat Memory 或独立任务数据库。

### S6 — 宿主接线与三 Agent 实证（P1）

**两个不同九格绝不可混淆**：工程的 Linux/macOS/Windows×Python 3.11/3.12/3.13；真实 Agent 的 Codex/Claude Code/OpenCode×CLI/指令加载/完整工作流。

| AC | 类型 | 强制通过条件 |
| --- | --- | --- |
| **AC-S6-01** | E | PACT 自有夹具测试已有 `AGENTS.md`、`CLAUDE.md`、OpenCode 配置均**不覆盖、不重写**；只输出薄路由或手工合并建议，不复制第二套 Constitution |
| **AC-S6-02** | E | `doctor` 的静态接线预检识别 PACT 新目录是否可能被主项目静态白名单/CI/代码检查视为未知，发现明确循环/冲突即报错，未知标 `needs-manual-review`；不执行宿主 CI、安装依赖或扫描生产目录来“证明”接线 |
| **AC-S6-03** | E | PACT 夹具覆盖安装、重复安装、升级预览/应用、配置冲突拒绝、部分失败、回滚、旧 Manifest 和 Compact Runtime；源/安装版本一致，无写出外部项目 |
| **AC-S6-04** | E | 三种 Agent 各自都有**可复跑的受控真实运行脚本或人工执行指南**；每格明确 Runner 版本、授权条件、可见指令、命令、日志位置和可观察成功标准，不能把通用 Python CLI 通当“Agent 已遵循” |
| **AC-S6-05** | V | **三 Agent×三层九格均由真实 runner 执行、证据可打开**；CLI 格需真实 Agent 调用 PACT，指令格需证明加载/遵循正确路由，E2E 格需 Contract→Evidence→Convergence→Owner→finish 全链；缺 Runner/账号的格子保持 `blocked`，**S6 整体不得 passed** |

**授权不足时**可以取得 S6 的 E 级工程结论，但不能以 `9 个 blocked 格已列出` 冒充 V 通过。所有执行限于 PACT-owned 受控环境；无权启动外部 Agent 时保留复跑指南。

### S7 — 冻结对照、真实试点、裁剪与发行判断（P0 发布关口）

**S7 的工程评估和真实 Pilot 是两条独立证据链**，不能在单个“CI 全绿”里合并。真实试点以授权条件为前提，不对其他项目产生提交或任何回写。

| AC | 类型 | 强制通过条件 |
| --- | --- | --- |
| **AC-S7-01** | E | 复跑 S0 冻结的历史回归与 holdout；固定 source/task/提示/风险/budget/工具，oracle 后揭示；随机 Runner 若可用按预注册重复运行，原成功/失败样本都保留 |
| **AC-S7-02** | E | 分别报告 **A：ziliu 历史副本** 的关键文件定位/Context/完成 Gate、**B：PACT 内脱敏 zx-zsb 夹具** 的 Domain/Rule/README/宿主接线、**C：PACT 内 A→B 无 Chat 接力**；每份结论明确“历史 replay/合成测试”，不是生产验证 |
| **AC-S7-03** | E | 逐案例机器指标有原始日志与分母：关键文件 Recall/Precision、规则漏检、Context 个数/Token 估算、假完成拦截、Claim/Convergence/changed-file coverage、Agent CLI 操作次数、PACT 附加耗时/开销；没有实测的列为 `null/unverified` |
| **AC-S7-04** | E | 按 S0 预注册阈值判定：已知假完成/必需 Rule 漏注入=0；错误权威提升直接 FAIL；召回/开销越线需失败或回退；无收益的额外 ranking/命令保持可选或裁剪，不能事后移动阈值 |
| **AC-S7-05** | E | 完成 PACT 发行准备**只读/干跑审查**：源/安装版 Schema 行为同版、升级/回滚、固定 Action SHA、LICENSE/SECURITY/CONTRIBUTING、资产/校验和、OS×Python 9 格相关回归；#63 Legacy YAML 迁移诉求有明确处理决定；**不改版本、不打 tag、不发布** |
| **AC-S7-06** | V | 至少存在经授权的**真实任务**和真实 Agent 行为观测；实际任务与历史回放严格区分，不能把 PACT dogfood 推广成其他 Brownfield 项目完成验证；如原始真实项目试点不允许访问，记录缺口，保持此项 blocked |
| **AC-S7-07** | V | Owner 技术问询、产品决策升级、澄清轮次、理解成本/耗时有真实交互观察和记录方法；未提供数据时保持 blocked/unverified，不填 0、不从 CI 或 Agent 自评推断 |
| **AC-S7-08** | V | 在允许的样本范围内有可审计的对照结论、局限性及无需保留功能的裁剪决定；任何被证实的假 pass 或未解释的 P0/P1 缺陷均阻断 Pilot Validated 和发布 |

**R 类独立发行关口（只有新授权才能操作）**：

- **R-01**：Owner 明确批准版本、tag/Release 范围、候选变更列表以及是否关闭 #28/#32/#63 的对应 AC；没有授权则保持 `not-authorized`（发行决策字段，**不是** AC passed）。
- **R-02**：发行前把 `.pact/VERSION`、CHANGELOG、发布清单、完整矩阵、正式构建来源和 SHA256 校验和按批准范围校验；注意当前 `.github/workflows/release.yml` 由 `v*` tag 触发，**打 tag 本身可能触发发布**，所以未授权绝不创建 tag。
- **R-03**：通过后才在 **PACT** 发布；任何缺证据输出 `NO-GO: missing evidence`，任何负向结果或已知安全缺陷输出 `NO-GO: failed criteria`；决策记录可完成，但未通过的 AC 仍保持真实状态。

## 3. 依赖、PR 包与停机条件

**严格阶段签收顺序**：S0 → S1 → S2 → S3 → S4 → S5 → S6 → S7。可以在 S0 **提前核实**外部 Runner/Owner 数据能否取得；不能提前把 S7 的真实结果写成“已通过”。只允许在 S0/S1 进行构建夹具、测量等基础工作，不跨阶段混入未经批准的功能。

| PR 包（建议编号，非已存在 PR） | 对应 AC | 工作边界 | 出口 |
| --- | --- | --- | --- |
| PR-00 | S0 E01～E06 | 双基线、反例、盲测/资源预检 | RED/历史/未知项可追溯 |
| PR-01a/01b | S1 E01～E06 | 枚举/Skill；前后指纹与 required Evidence Gate | 假 pass 关闭、合法案例仍绿 |
| PR-02 | S2 E01～E05 | Decision/rejected/supersession/引用候选 | 无丢失、无自动删除 |
| PR-03a/03b（03c 可取消） | S3 E01～E07 | 意图与锚点、显式 Rule/README、可回退实验 | 原始结果满足，X 采纳有证据 |
| PR-04a/04b | S4 E01～E06 | 诊断/草稿填充、最小导出 | 不写假完成、不泄露、不覆盖 |
| PR-05 | S5 E01～E05 | checkpoint/resume/A→B | 无 Chat 可恢复且重新验真 |
| PR-06a/06b | S6 E01～E04，V05 单独评估 | Host doctor/兼容及真实 Runner 九格 | V 缺失则 S6 blocked |
| PR-07a/07b（07b 仅发行授权后） | S7 E01～E05、V06～V08；R 单独 | holdout/A-B/Owner、裁剪、发行准备 | 实证不足即 NO-GO，不发版 |

**STOP**：任一安全假通过、仓库外写入、破坏安装/升级、源码/运行时协议不兼容、盲测污染、采集未经授权的数据、当前阶段三轮审查未通过 → 暂停下一阶段，修复后对受影响 AC 和下游基线重跑。

**回退**：只在 PACT 新建修复/回退提交，禁止改写公开 `main` 或强推。单亲/squash commit 可用 `git revert <commit>`；真正双亲 Merge Commit 先确认主线再用 `git revert -m 1 <merge-commit>`（按真实父节点判定）；记录反例重跑、安装版 Smoke、历史协议/已存收据是否需迁移或重验。**不能通过回退丢失安全门禁**。

## 4. 测试矩阵与可审计证据

**通用本地门禁（每阶段在实际 PACT head 记录输出和 exit code）**：

```bash
python3 scripts/pact/pact.py schema-lint
python3 scripts/pact/pact.py workflow-lint
python3 scripts/pact/pact.py check
python3 -m unittest discover -s scripts/pact/tests -p 'test_*.py'
python3 scripts/pact/pact.py audit --json
```

**按修改范围附加差异性门禁**：

- `discover/context/map/code_map`：冻结检索回放、同源同预算 Recall/Precision/Token、必要 Rule 不漏、README hint 边界/性能；无后验关键词与整仓扫描。
- `run/evidence/task/complete/convergence/schema`：源码及安装版、前后变更拒绝、后续编辑 stale、外部输入、坏 SHA、漏 AC/changed-file、不匹配 Claim/Owner、旧版合法收据、瞬态写恢复的**已知检测限制**。
- `init/upgrade/distribution/bootstrap/doctor`：重复安装、宿主文件保护、路径逃逸、symlink、坏 manifest、部分写/中断/回滚、PACT 受控环境静态 Host 预检、Compact runtime。
- `.github/workflows`：schema/workflow lint + 相关 workflow **最终 head SHA** 成功运行；不能借之前 commit 的绿灯。
- **OS×Python 9 格**：Linux/macOS/Windows × 3.11/3.12/3.13，记录每格 Job ID 和选定测试覆盖；全量 unittest 另保留其真正执行的环境/日志，不能混称九格全量。
- **Agent×兼容层 9 格**：三 Agent × CLI/指令/E2E，另列 `verified/blocked/unverified`、runner 版本、真实调用/可见指令、日志/证据；CLI Python Smoke 不等于 Agent 遵循协议。
- **证据层次**：每个完成报告分开写①机器行为已验证；②Agent/审阅者语义判断与不确定性；③用户/真实项目观察及缺证据，互不代填。

**必留横向反例**：`removed vs updated`；受管理工作区前后不稳定；`pact-ready` 与业务完成混淆；仅 Domain 无 Rule；显式缺 RULE-ID；rejected 前提变化；被删/旧架构污染 Context；预算裁掉强制证据；README 的忽略路径；漏 changed-file coverage；外部脚本；中断恢复；宿主 AGENTS/CLAUDE 冲突；真实 Runner 未授权；Owner 观测缺失。

## 5. 三轮阶段 Review、独立复审与验收签字

**Review 1 — Contract/Scope**：逐个 AC 对原始 Owner 阶段、当前主干和 PR 差异；检查是否超出 PACT、Schema/Runtime/Skill 是否形成多个互斥权威、V 是否被机器偷换、X 是否错误降级原始功能。记录 reviewer、发现问题、修复 SHA 和证据。

**Review 2 — Call-chain/Adversarial**：按入口 → 遍历/解析 → 状态/SHA → 执行/收据 → Schema/Convergence → Owner/Eval 调用链，重新构造并发、symlink、路径越界、半写、中断、stale、旧安装版和宿主冲突反例。先 RED 再修正，不以 unittest 通过替代敌对测试。

**Review 3 — Acceptance/Regression/Rollback**：在**PR 最终 head**核对 AC、运行 ID、选定 9 格/全量测试差异、冻结 holdout、成本、回退可操作性、人工指标及不可外推项；每阶段给出 `passed/failed/blocked/unverified` 和后续解锁条件。

独立审查另列：真实 Copilot/Codex 或其他被授权 Reviewer **实际输出**才能标 `independent-reviewed`；仅发出 `@codex review` 不算完成。独立复审不可用时标 `blocked`，注明需在当前 PR head 重发、读取意见并修复；不得杜撰“启动过子 Agent”。

**每阶段签收模板**：

```text
Stage: Sx  | base_sha: ... | final_head_sha: ...
Engineering AC: AC-Sx-.. passed/failed/blocked/unverified + evidence URL
Validation AC:  AC-Sx-.. passed/failed/blocked/unverified + authorization/data gap
X decisions: adopted/rejected/deferred + frozen comparison
Tests: commands, exit codes, CI workflow/run/job IDs, source + installed runtime
Reviews: R1/R2/R3 reviewer and findings; independent review separate
Boundary: changed PACT paths only; other repositories zero writes
Rollback: actual commit(s), protocol/data migration or reverify instructions
Decision: stage status; Engineering Complete? Pilot Validated? Release Approved?
```

## 6. 计划本身的修订记录和未关闭关口

- **2026-10-15 原计划**：PR #185 交付计划草稿，三轮同一助手按不同维度复核；这是自审，不是独立 Agent 审查。
- **2026-10-15 本次修订 Review 1（范围/可验收性，同一助手）**：拆分 E/V/X/R，定义 `Engineering Complete / Pilot Validated / Eight-stage Accepted / Release Approved`；修正 S6 未验证却可能算成功、S7 `NO-GO` 与 `passed` 混淆；增原子 AC 与责任证据槽。
- **2026-10-15 本次修订 Review 2（源码/敌对路径，同一助手）**：确认 `workspace_changed` 仅前后指纹、Context v1 封闭 Schema、矩阵全量覆盖表述、证据导出工作区边界、Git Merge 回退差异；分别加反例或明确上限，未声称瞬态写可侦测。
- **2026-10-15 本次修订 Review 3（实验/发布，同一助手）**：先冻结 holdout 和阈值、历史 Smoke 与真实试点分开、Runner/Owner 资源前置核实、Legacy YAML Issue #63 显式处理、tag 自动 Release 风险与 Owner 独立授权。
- **独立 AI 复审：blocked**。Copilot 与 Codex 在 PR #185 的既有请求因额度限制没有有效独立审查结论；本修订不声称它们已通过。需在**修订后 PR head**获取真正审查，再修复意见。若其他 Reviewer 也不可用，如实报告阻断。
- **实施/发布均未授权**：提交本文只修改计划文件；S0～S7 的代码、CI、其他项目、版本、tag、Release 均未随本修订实施。

### 执行后最小最终报告（不得再写成“全部完成”而缺数据）

分别输出：

1. **工程**：E 总数、passed/failed/blocked、源码与安装版、OS×Python 范围、回退可用性。
2. **真实验证**：V 总数、Agent 真实九格、真实任务/Owner 观测、不可外推范围。
3. **发行**：GO 或 `NO-GO: missing evidence / failed criteria / not authorized`，以及任何实际 tag/Release（若未授权应为“无”）。

**不满足 Eight-stage Accepted 时只能按实际门槛报告“工程完成、实证仍 blocked”之类的部分状态，不能宣布整个 PACT 八阶段完成。**
