+++
[pact]
type = "change"
id = "CHANGE-PACT-EIGHT-STAGE-20261015"
status = "active"
domains = []
+++

# PACT 原始八阶段路线：补齐、逐项验收与发布计划（PACT-only）

> 计划版本：2026-10-15；状态：待实施，**不是已完成报告**。
> 来源：Owner 最初的「阶段 0～7 八阶段实施计划」，不以之后的 PR 数量代替原始验收项。
> 原始历史基线：`28d8a77e8bbc4fca6db320b4e1a95ac62079385b`。
> 本次计划冻结起点：`b67d7a725774d8404ad253b43cfca3dd35874fdf`（2026-10-15 主分支）。
> 唯一允许提交的仓库：`ningcol/PACT`；本计划不授权直接实施这些阶段，也不授权发版。

## 0. 不可突破的边界与完成定义

1. **只写 PACT。** 所有分支、提交、PR、Issue、文档、代码、测试、CI Workflow、Artifact 必须归属 `ningcol/PACT`；不修改、不推送、不创建 PR 到 `ziliu`、`zx-zsb`、`DouBaoFreeImageGen` 或其他任何仓库；不访问私人生产数据、线上服务或凭证。
2. **可做只读/隔离验证。** 允许读取已授权的公开历史提交；允许在 PACT 自己的测试夹具、容器或 GitHub Actions 的一次性目录里重建样本。一次性副本的操作不得回写来源仓库，不得把生产行为测量与本地模拟混淆。若原始 `zx-zsb` 资料不在 PACT 中，先用 PACT 内脱敏夹具复现机制，标注「真实 zx-zsb 复核未执行」，绝不修改真实项目补齐指标。
3. **证据先于完成。** PR 合并、CI 全绿、历史 Benchmark 通过、`run` 收据、Agent 的业务判断、Owner 的实际反馈是不同证据。人工耗时、Token、澄清轮数、跨 Agent 行为未实测时标记 `unverified`，不得填 0、编造改善或称阶段 7 通过。
4. **不扩大控制面。** 优先复用 `task prepare/status/draft/verify/finish`、`discover/context/impact`、`audit`、`run/evidence/complete/eval`、现有 Schema/Skill；新入口必须消除反复的机械操作，不能创建第二套产品真值、Decision 数据库、Beads 克隆、向量库或强制复杂流程。
5. **保留信任边界。** Task Contract/Context 的 SHA、受管理工作区身份、显式 Evidence Claim、Convergence 覆盖、Owner Report 和完整性检查不能弱化；中高风险门禁不因兼容或「自动化方便」而降级。
6. **每阶段单独审查/可回退。** 一个阶段可拆 1～3 个小 PR，但不得跨阶段混入未经授权的功能。每个 PR 以具体 commit SHA、差异、RED/GREEN 反例和 CI run ID 为证据；阶段通过三轮审查后才进入下一阶段。普通计划和进度留在本 Change；只有长期、不可从代码/测试/文档推导的取舍才新增 Decision。

### 怎样定义「完成」

- **实现完成**：代码和测试合并、相关兼容性验收通过。
- **阶段验收完成**：本文件对应的全部强制 AC 满足，且具备可打开的证据链接和三轮 Review 记录；未覆盖的项不能凭「类似能力已有」核销。
- **整轮完成**：阶段 0～6 的硬门槛完成，阶段 7 的真实对照证据足以作出明确 go/no-go 判断；若真实 Owner/Agent 实测缺少数据，阶段 7 必须保持 `blocked/unverified`，不得宣布八阶段完成。发布需另外核准版本/Release 范围。

**单项 AC 状态只允许 `not-started / in-progress / passed / failed / blocked / unverified`**。每个阶段的状态是 AC 的聚合：只有强制 AC 全部 `passed` 才能标 `passed`；机器测试不能代填人类观察。适用时将外部运行条件缺失列为 `blocked` 并写出可解除条件，不得为了完成阶段降级为「警告已接受」。阶段出口必须在 PACT 内提交一份 `docs/evaluation/` 或 PR Review Ledger，记录 AC-ID、base/head SHA、回归/验证命令、CI run、观测结果、未知项、回退 commit、审查意见和下一阶段依赖。

## 1. 现状与剩余差额：只把已经验证的记为已完成

已合并的相关工作：

| 已有证据 | 可以认定的结果 | **不能**因此认定 |
| --- | --- | --- |
| PR #178 | Decision 准入瘦身、历史软降权、Agent 查询建议简化 | 2.x 生命周期、3.x 检索意图与治理引用全部完成 |
| PR #179 | 忽略感知扫描、有限重试、失败不发布混合索引 | 获得操作系统级原子源码快照 |
| PR #180 | `task draft`、`task verify` 及明确 AC-ID 的真实执行收据 | 存在完整 `task assist`、机械报告回填与证据导出 |
| PR #181 | 显式本地验证输入 SHA、外部输入警告/约束 | 任意环境可复现，或已实现 `run --replay` |
| PR #182 | 混合 confirmed/pending Rule 警告及 `applicable_rules` 边界 | 任意 Markdown 章节级规范状态模型 |
| PR #183 | superseded Decision 审核候选、Knowledge Gardening Skill | 完全/部分取代与引用保留场景均通过验收 |
| PR #184 | 在固定历史 `ziliu` 临时副本上的 Evidence Smoke、误完成拒绝和收据留存 | 真实业务变更 A/B、跨 Agent 接力或 Owner 减负已有证据 |

当前待完成或待重新验收的事实（以起点主分支为准）：

- `convergence_coverage.py` 与 Schema 均支持 `removed`，但 `.agents/skills/convergence-review.md` 的 coverage 清单仍未写 `removed`，且旧文字把「文件被删除」也混入 `updated` 说明。
- `run.py` 记录 `workspace_changed`；需要检查 `evidence.py` 中高风险必需 pass 的策略是否拒绝执行时改变受管理工作区的收据，不得只看最后工作区指纹。
- `discover/context` 尚无完整的 `work / decision / history` 意图模式；治理引用、显式请求 RULE-ID 的必需检查、模块 README 线索仍需补齐或实验验收。
- `task` 已有 `prepare/finish/status/draft/verify`；尚无计划所述综合收尾诊断、确定性 Owner Report 回填、证据导出、跨会话 `resume` 与增量交接。
- 对 Codex / Claude Code / OpenCode 的 **真实** CLI、指令、工作流三级验收尚无统一通过证明；宿主的 `CLAUDE.md` 等保护和接线预检需要明确测试。
- `docs/evaluation/` 已有 ziliu / DouBao 等历史基线和机械 Evidence Smoke，但真实 A/B、人类工作负担指标和发布关口未通过。当前版本仍是 `0.4.0-dev.1`；Issues #28、#32、#63 尚未关闭。

## 2. 执行工单、依赖和强制验收

下文的 S0～S7 **逐一对应原始八阶段**，不是此前 PR #178～#184 的自定义「三子阶段」。每个 Sx 是独立阶段验收包，可以拆小 PR，但不能以「测试存在」代替行为证明。

### S0 — 固定双基线和 RED 回归夹具（P0）

**目标**：在改动核心代码之前保留真实失败和指标；为后续阶段提供不会被后验答案污染的回归样本。

**允许修改（仅 PACT）**：`docs/evaluation/`、`scripts/pact/tests/`、`scripts/benchmark/`、`benchmarks/brownfield/`、PACT 自有 `.github/workflows/`。

**操作**：

1. 固定原始起点 `28d8a77...` 与最新起点 `b67d7a7...` 的分别可复核状态；每条旧回归注明最早触发的提交/问题、当前是否修复、回放输入和预期输出。不得把旧的 RED 样本回写成当前 GREEN。
2. 记录完整 PACT Check、Schema/Workflow lint、9 格 Python/OS 矩阵、发布包源/安装后运行测试的 run ID；记录 Benchmark 任务、固定源提交、召回、候选个数和估算 Context Token，而不是无来源的效果百分比。
3. 在 PACT 内建立可重放的 **最小** 测试清单：旧/新架构同时出现；仅 Domain 无 confirmed Rule；rejected 决策复用；执行后改工作区导致旧 Evidence 失效；删除误标 `updated`；Schema/Skill 取值矛盾；准备中断后仍不能标 completed；临时文件并发扫描；配置/脚本来源异常。已有覆盖要引用具体测试，不复制测试。
4. 对 `zx-zsb` 的接线事故仅使用用户已提供的事实、已有 PACT 资料和脱敏合成目录夹具；缺少实际样本就登记 `unverified` 和取得样本条件，不读取/修改另一个项目来「补成功」。
5. 为后续 A/B 写冻结的任务输入、相同风险/预算/查询提示、评估脚本和字段；人工 Owner 次数/耗时等保持 `null/unverified`，并明确谁在什么真实任务中可以提供数据。
6. 建立 `docs/evaluation/eight-stage-baseline-2026-10-15.md` 作为**不可回写历史结果**的基线清单；测试需要实际源文件/命令时引用 `scripts/pact/tests/`、`benchmarks/brownfield/cases.json` 或 PACT 内最小 fixture。所有后续指标用新日期与 SHA 另增结果行，不原位覆盖旧 RED。

**AC-S0**：一份基线证据索引含固定 commit/命令/run/指标及未知项；所有原始反向案例要么能重放，要么有明确、可验证的未达条件；新代码之前的 RED 不能被隐藏。**不得要求旧基线本身绿色**。

**Review 特别检查**：样本有没有泄露其他项目真实敏感数据、是否事后提示、历史/当前结果混淆、是否增加不必要的整仓扫描。

### S1 — 收敛协议权威与验证信任（P0）

**目标**：Schema 定义协议、Runtime 执行约束、Skill 仅解释用法；不能从「机器运行 pass」跳跃为「生产业务已验证」。

**代码入口与影响链**：`.pact/schema/convergence-report.schema.json` → `convergence_coverage.py/converge.py` → `evidence.py` → `report.py/complete.py` → `readiness.py/status.py` → `.agents/skills/convergence-review.md`、`docs/governance/completion-contract.md`。

**操作**：

1. 增加**机械枚举一致性测试**：从现有 Schema 的合法 `coverage.disposition` 枚举与 Runtime `VALID_DISPOSITIONS` 比对，修正 Skill 对 `aligned/updated/removed/stale/owner-decision/not-applicable` 的说明；`removed` 只能用于真实删除，`updated` 不能用于消失文件。不要人工维护第三套独立枚举。
2. 为 `pact-ready`、运行收据、语义确认、环境边界建立独立输出/文档字段的含义映射。若现有 Owner Report 可以通过明确 wording 表达，不新增冗余 Schema 状态；基线审查 `pact-ready` 不推导 E2E/生产有效。
3. 中高风险 **required pass**：当 `pact run` 的受管理工作区在验证期间确实发生变化（`workspace_changed`，对 PACT 生成/忽略文件遵循现有 `workspace_snapshot` 规则），即使运行成功且最终 SHA 匹配，也拒绝其作为最终完成证据；给出「持久化变更 → 稳定工作区 → 重验」建议。先用真实 RED 复现并检查之前的合法编译/测试输出是否已经被正确排除。
4. 保留已有 Evidence Claim ↔ Owner Report 精确匹配；拒绝 claim、task_id、风险、工作区、外部来源/声明哈希不匹配和伪造完成。兼容旧版 v2 收据需明确迁移/再次验证策略，不放宽安全门禁。

**AC-S1**：Schema/Runtime/Skill 对合法状态无矛盾；删除/不稳定运行/旧收据/证据夸大均失败；正常受管理工作区未变的已有任务仍通过；已安装 `pact.pyz` 同样执行新协议。**未关闭任何已知假 pass 前不得进入 S2**。

**回退**：若发现误挡非受管理生成物，修正指纹分类并加回归，而非简单删除 Evidence 门禁。

### S2 — 长期知识瘦身、否决复用、取代/清理（P0）

**目标**：只保留未来可避免具体错误的长期、不可推导理由；正确复用被否决的方案和仍有效的局部约束。

**主要文件**：`.agents/decisions/{README,TEMPLATE}.md`、`docs/governance/decision-authority.md`、`docs/{product,changes,drift}/`、`audit.py/check.py/impact.py`、Skill。

**操作**：

1. 把 Decision 的五问准入（具体未来错误、为何不可从代码/测试/文档推导、长期有效期、知识唯一归属、删除损失）写成可执行 Agent Review 清单；普通 Bug/局部 UI/例行重构不得自动生成 Decision。
2. 对保留的 `rejected` 决策建立**非强制、只写真实证据**的内容提示：备选方案、为什么考虑、反对原因、适用前提/范围、实测/确认/假设来源、重新评估触发条件。检索被否决理由不意味着永远禁止重新考虑。
3. 对完全取代和部分取代分别设计夹具：完全取代时新权威记录继承仍重要理由/风险、旧记录变历史并更新关联；部分取代时仍有效的约束不被删。引用检查必须确认 ID/路径和链接不会悬空。
4. Audit 在既有 `decision_retention_candidates` 基础上提供**解释充分的 review 候选**；普通已完成 Change、已解决 Drift 的清理仍先检查当前引用、保留义务和产品权威。禁止按文件年龄/引用次数自动删除，不新增清理数据库。
5. 清理相关 Skill/文档的重复规则，由一处权威引述，确保安装后指引一致。

**AC-S2**：固定夹具下，普通任务不强制 Decision；可找回 rejected 理由并识别其条件是否改变；完全/部分替代不遗失有效约束；低价值已完成历史可以安全提出清理候选但没有悬空引用或自动删除。所有结论均经 Agent 语义复核。

**回退**：如候选噪声增加，关闭/删掉候选启发式而非给每个文档新增必填标签。

### S3 — 任务意图、治理锚点、Context 缺口与模块 README（P0）

**目标**：明确「检索命中」不等于「依据足够」；历史不污染默认工作 Context，必要依据不会静默丢失。

**关键链**：`map.py/repository_files.py` → `discover.py` → `context.py` → `inspect_project.py/explain.py` → `task prepare` → `context-envelope.schema.json`。

**分包实施**：

- **S3-A 意图实验**：设计 `work/decision/history` 三种轻量意图；先新增**可选** `--intent`，保留既有无参行为，固定同输入/预算后与原基线比较。work 优先当前有效约束、decision 同时检索相关 rejected/implemented 理由、history 保留旧理由与 Git。rejected 只是决策证据而非 confirmed Product Rule；没有真实对照改善就不改变默认策略。
- **S3-B 最小治理锚点**：Context 输出简短、固定的 `truth-ownership`、`decision-authority`、`completion-contract` 已存在路径引用，区分「治理入口」和「任务检索候选」。引用不参与普通词法排序/Token 预算、不会偷偷强行 materialize 全文；不得把治理锚点冒充某条业务 Rule。
- **S3-C 缺口与召回**：保留现有 candidate/confirmed 区分、`known_unknowns`、hard count/soft tokens、authority overage、fallback hints；对**调用方明确指定的 RULE-ID**不存在、非 confirmed、或在强制集合被数量限制挤出，给出明确的阻断/错误。对机器只推测的未知规则仅提示 `unverified`，不发明必需规则。
- **S3-D 局部 README 提示**：从 Code Map 选中的候选模块路径就近找 README，限制条数/目录层级、输出相对路径与找到理由；默认只做 metadata hints，不自动全文注入或重复扫描整个仓库。留出单元/集成反例：README 缺失、忽略目录、符号链接、巨大文件、无 Git 仓库。
- **S3-E 结构级 Context 实验**：复用现有 `ziliu` 历史 fallback hint 案例，在完全相同 task、source、风险、count、Token 预算和冻结查询下对比关键文件召回、正确性与成本。无可靠收益或明显性能退化则回退实验，不制造长期复杂 ranking 层。

**AC-S3**：旧/新决策使用范围正确；原有历史默认召回和关键源文件召回不发生**未解释**退化；明确要求的 Rule 缺失可见且不能被当作 confirmed；相关模块 README 可以按需定位；Context 不因治理锚点膨胀，预算/截断/hints 可见。兼容旧 CLI/Schema 和已安装 runtime。

**回退**：意图检索和结构级实验保留旧行为可选回切；默认切换必须有冻结 benchmark 支撑。

### S4 — Evidence 与任务收尾辅助（P0）

**目标**：进一步减少 Agent 机械重复填写，不让机器代替业务语义判断。

**影响链**：`task prepare/status/draft/verify` → `Task Contract` → `run/evidence` → `Convergence/Owner Report` → `task finish/complete/eval`。

**操作**：

1. 在现有 `task` 下实现小而只读的 `assist <TASK-ID> --json`（若代码 Review 证实 `status` 组合能以更小变更提供同等能力，优先扩展 `status`）：校验准备时 Contract/Context SHA、当前 Evidence 引用有效性、按 AC 汇总未证实项、实际 task delta 未覆盖路径、需要重验的收据及原因、可安全机械填充的报告字段。
2. 从**现有真实 passing Claim** 生成待审 Owner Report 的 `verification` 引用和原样 Claim 文案、Task ID/合同 SHA/相对路径；仅在显式 `--write-draft` 下创建或填空，永不覆盖 Agent 已编辑内容，也不自动将 `owner.status` 设为 completed、`convergence` 设为 aligned。
3. 执行推荐顺序：**先持久化代码/知识 → 取得稳定工作区指纹 → 最后一次真实验证 → Evidence/Convergence/Owner Report 语义 Review → finish**。如果验证后改受管理文件或验证执行时有写入，`assist` 在 finish 前给可操作的 stale/reverify 清单。
4. 提供显式证据 `export`（可放在 `task` 下）：默认输出到用户指定的受控位置、只导出最小元数据/已验证收据/协议版本/合同摘要/校验和，不含原始 stdout、stderr、密钥或凭据；导出副本不升级证据可信度。对路径越界、符号链接、半写文件和在工作区产生新受管理变更进行防护；没有明确需要不新增复杂归档 Schema。**本轮所有写出与失败注入只允许针对 PACT 仓库或它自己的临时测试目录**，不得调用导出命令向任何其他项目的真实目录写入。

**AC-S4**：缺失 AC/Convergence/change_coverage 有完整机器诊断；机械字段能自动填，失败/未验证 Claim 无法变 pass；stale/外部来源/不稳定验证仍不允许完成；中断/重复调用/坏 JSON/写失败不会留下虚假的已完成状态；导出的副本和本地工作区状态严格区分。

**回退**：保持 `draft/verify/finish` 原路径可用，新增入口应可独立撤销。

### S5 — 增量保存和无聊天记录恢复（P1）

**目标**：Agent A 中断后，Agent B 只靠 PACT 的可校验持久化事实继续工作，且不会错误使用旧证据。

**文件**：`task.py/status.py/task_contract.py/evidence.py`、必要的最小 Schema、`docs/design/human-interface-runtime.md`、PACT-owned `scripts/pact/tests/`。

**操作**：

1. 在现有 `.pact/tasks/<TASK-ID>/` 下定义**最小可选交接记录**（明确版本、任务 ID、已完成工作/待办、最近验证收据引用、已查决定/仍待判断的假设和时间），原子写入/不覆盖其他任务；不保存聊天推理、密钥或完整对话，不建设独立数据库。**交接摘要是未经授权的 Agent 叙述，不是 Product Truth 或通过证明**；路径、列表、Claim ID、收据引用必须类型验证与限制大小，避免从被污染的本地文件注入命令或推高可信级别。
2. 提供显式 `task checkpoint`（或复用已有可扩展能力）写入**部分进度**，不要求最终 Owner Report/Convergence 全部有效，不更改准备时 Task Contract/Context SHA。
3. 提供 **只读** `task resume <TASK-ID> --json`：返回原始目标与验收项、准备/完成状态、事实性已做和待办、相关当下 Decision 路径、已有收据重新验真结果、当前工作区差异、待复核假设以及建议下一步。未知/未确认不得变成 confirmed。
4. 无 Chat 上下文模拟 Agent A→B：A 写进度、收据，然后进程中断；B 在独立 Python 进程/隔离会话中 resume，复核 Git/Context/证据并完成新验证，失败快照必须显式提示；历史 rejected 前提必须重新核对而不是当永久禁令。
5. 明确跨设备：项目长期知识随 Git；本地 `.pact/tasks/.pact/runs` 是独立状态，**不会**因为换机器自动同步。若使用 S4 的导出，恢复前必须重新校验工作区/外部依赖。

**AC-S5**：在受控 A/B 接力用例里 B 不读 A 的聊天即可得目标、当前已证/未证和下一步；能发现 stale Evidence/不存在的路径/过期准备状态；不会重写冻结 SHA、丢已有任务、假称 completed 或悄悄同步本地私有状态。

**回退**：交接字段可选，旧任务 Manifest 可直接读取；新增无效交接只报受控错误，不损坏原任务。

### S6 — 跨 Agent 和宿主接线（P1）

**目标**：真正验证 **Codex / Claude Code / OpenCode** 的三级兼容（CLI/指令/完整工作流），不依赖「它们都认识 AGENTS.md」这一推断。

**文件**：`bootstrap.py`、`init/upgrade/distribution/doctor.py`、`AGENTS.md`、`docs/initialization.md`、安装/升级/宿主集成测试、PACT CI。

**操作**：

1. 建立 Agent×兼容层次的**九格验证矩阵**。每格必须分别标 `verified`、`blocked`、`unverified` 并附命令、受控运行记录、实际 Agent 版本/模式、退出结果；不能把静态 CLI 可运行当作完整 Agent 工作流。
2. `AGENTS.md` 及已有 `CLAUDE.md` / OpenCode 配置一律不覆盖、不替换、不复制第二套 Constitution；PACT 仅生成最小的路由引用/手工合并建议，保证单一 Product Truth 和协议。
3. 在 `doctor` 加**非破坏性宿主接线预检**：检查 PACT 新增路径是否被主项目已有文档/代码/CI 检查实际覆盖，是否被静态白名单视为未知，是否构成循环调用；只能机器确认的才 `pass`，无法解析的宿主规则标 `needs-manual-review`，不能为所有语言/CI 做启发式假通过。预检只静态读取允许的元数据，**不得为探测兼容性执行宿主 CI 命令、安装依赖、改写其配置或触发递归检查器**。
4. 在 PACT 的临时样本和可获得的受控 Agent 执行环境测试安装、重复安装、升级预览、冲突拒绝、回滚、旧配置保护、Agent 指令加载、Task Contract → Evidence → Convergence → 完成门禁。
5. 若某 Agent runner/账号/API 在 PACT CI 不可用，不模拟它的回答后声称兼容：写明未验证的九格、可重跑脚本/人工复核指南和接入所需条件。**只有真实执行过的格子才能打勾。**

**AC-S6**：三种 Agent 的三层真实测试均有独立证据才算完整完成；所有安装/升级/回滚与不覆盖宿主文件的强制回归通过；任何不可验证 Agent 明确标 `unverified`。非破坏性适配失败不得修改另一个仓库来「修好」。

**回退**：把宿主预检保留为诊断，未知时不要硬性阻止原安全安装流程。

### S7 — 冻结对照、真实项目验证、裁剪与发布（P0 关口）

**目标**：用可核实的实际收益判定是否发布，而非靠新增字段和测试数量。

**必须独立建立的三类验证**：

- **A. ziliu**：固定一组历史任务/源码/风险/Agent 可见查询；复用现有发布 API/Editor 历史样本，分别检验 work Context 直接召回、fallback 定位与任务完成 Gate。现有 PR #184 README Evidence Smoke **不是**完整业务变更闭环，不能充当发布成功。
- **B. zx-zsb**：仅使用 PACT 内经过脱敏的输入夹具进行 Domain/Rule 区分、中文搜索、治理锚点、模块 README、旧架构隔离、宿主文档/代码白名单接线和收尾；若缺失经用户允许的真实基准，列出限制，不修改也不推送 `zx-zsb`。
- **C. Agent A→B 接力**：A 在相同任务上记录被否决的重要方案和前提；B 在无 A Chat 的独立会话里检索；分别测试前提不变/已变、证据未过期/已过期。必须区分「读到历史」与「正确判断是否仍有效」。

**A/B 规范**：

1. 固定相同任务文字、源 commit、风险级别、预算、测试工具和 Agent 搜索提示；把「事后人工补的关键词」单列诊断，不记入无偏 A/B。
2. 报告每案例关键源文件 Recall/Precision、Context 数与估算 Token、必需规则遗漏数、Evidence 假通过拦截、Convergence/Claim 覆盖、Agent 额外 CLI/操作步骤、总耗时及 PACT 开销。用可复核的机器 log 记录事实，不凭估计填数字。
3. Owner 技术升级提问、产品决策、澄清轮数、理解程度必须用**实际用户交互观察**；如果用户没有提供或无法合法采集，保留 `human_required/unverified`，即便机器指标好看也不声称减负已证明。
4. 对不改善召回/任务正确性、只增加负担的 feature 回退、禁用或删去；记录变更与实验的对应关系。
5. 候选版本仅当 S0～S6 全部强制 AC 通过、上述 A/B 可复核、无未说明的安全 P0/P1 缺陷时，才准备发行：正式 `.pact/VERSION`、CHANGELOG、已固定 Actions SHA、LICENSE/SECURITY/CONTRIBUTING、`pact.pyz`/bootstrap 的构建来源/校验和、Linux/macOS/Windows×3 Python，安装升级/回滚、原版/安装版 Schema 与行为一致。
6. Release/tag/版本变化是**明确的 go/no-go 选择**；没有经批准的范围和真实数据时输出 `NO-GO: missing evidence`，不自动推版本或宣布 v0.4.0 已发布。只允许向 PACT 仓库打 tag、发布 PACT 自己的资产。

**AC-S7**：有冻结实验对照、异常/无改善结论、三种 Agent 的实测状态、真实 Owner 指标或明确阻断、通过的发行验收矩阵、可审计 release decision；只有真实证据足以支持时关闭 #28/#32/#63 的相应验收。不能把一份 CI PASS 当作真正使用收益。

## 3. 执行顺序、PR 拆分、依赖与回退点

| 序号（建议） | 阶段 | 推荐 PACT PR 范围 | 前置 | 不能省的退出门槛 |
| --- | --- | --- | --- | --- |
| PR-00 | S0 | 双基线、固定 RED 样本、评估索引 | 主干 `b67d7a7` | AC-S0 可重放、既有失败仍显式 |
| PR-01a | S1 | 枚举/Skill 合同一致性及 README 解释 | PR-00 | Schema/Runtime/Skill 对齐 |
| PR-01b | S1 | workspace_changed 中高风险 Evidence Gate | PR-01a | 变化后旧通过收据必须失败 |
| PR-02 | S2 | rejected/取代/引用清理夹具与候选治理 | S1 | 不丢拒绝前提，不误删 |
| PR-03a | S3 | 意图检索和治理入口可选方案 | S2 | 冻结同预算不退化 |
| PR-03b | S3 | 显式 Rule-ID 与模块 README 提示 | PR-03a | 强制缺失可见/受控 |
| PR-03c（可取消） | S3 | 结构级 Context 实验 | PR-03b | 没收益则不保留 |
| PR-04a | S4 | 只读任务收尾诊断/重验清单 | S1/S3 | 假 pass、覆盖遗漏不能过 |
| PR-04b | S4 | 显式机械报告草稿/证据导出 | PR-04a | 不覆盖、不泄密、可回退 |
| PR-05 | S5 | checkpoint/resume、A→B 恢复用例 | S4 | 不用 Chat 可接力并能检 stale |
| PR-06a | S6 | Host Doctor 预检和薄路由建议 | S5 | 非破坏接入与回滚 |
| PR-06b | S6 | 三 Agent × 三层矩阵与运行记录 | PR-06a | 全格真实执行，否则阶段未完成 |
| PR-07a | S7 | 三路固定 A/B、收敛/删无效机制 | S0～S6 | 数据可复核、人类指标明确 |
| PR-07b（须发布授权） | S7 | 候选版本、资产/升级/Release Review | PR-07a | Release go/no-go 可审计 |

- 允许把逻辑紧耦合的 PR 合并，但 **S0～S7 每阶段仍须单独保留验收表、三轮 review、起点 SHA 和回退指令**。
- 改造中如发现 P0 假 pass、脆弱安装/升级、数据写出目录边界、错误业务权威提升，**暂停下一阶段**，先在 PACT 内修复并回跑受影响全部验证。
- **回退必须可执行且只修改 PACT**：回退入口是单独的 PACT `git revert <已合并 PR 的 merge SHA>`（或关闭可选新默认 + 回退提交）；禁止重写公开 `main` 历史/强推。记录回退前后的受影响测试和安装后 `pact.pyz` Smoke。因协议不兼容需要迁移时，先验证旧记录可读或给明确迁移/重验说明，不能静默回滚信任策略。
- 不在「发布最后一步」才补协议说明：Schema/Runtime/Skill 一致性应在 S1 守住，后续有意新增协议字段时同步测试、Skill、compact runtime。

## 4. 各阶段强制验证矩阵（不是一份笼统 PASS）

**基础门禁**（涉及对应模块时运行并保存准确 run ID）：

```bash
python3 scripts/pact/pact.py schema-lint
python3 scripts/pact/pact.py workflow-lint
python3 scripts/pact/pact.py check
python3 -m unittest discover -s scripts/pact/tests -p 'test_*.py'
python3 scripts/pact/pact.py audit --json
```

**差异性门禁**：

- 修改 `discover/context/map/code_map`：固定 historical Brownfield Benchmark，冻结相同 source/query/budget，比对召回与 Context cost；不得用后验扩展查询冒充 Agent A/B。
- 修改 `run/evidence/task/complete/Convergence/Schema`：合法已安装 runtime 与源码均跑通过；有受管理文件修改后证据失效、测试写 PACT 忽略目录仍可用、旧 Bundle 合法读取、不匹配 Claim 和不完整报告全部阻断的反例。
- 修改 `init/upgrade/distribution/bootstrap/doctor`：重复安装、不覆盖 AGENTS/CLAUDE、自有配置不被替换、旧 Manifest、路径逃逸、断电式失败/回滚、发布精简 runtime 均跑回归。
- 修改 `.github/workflows`：`workflow-lint`、固定 Action SHA、相关 CI 自身在最终 head 的 PASS；凡更新了流程即重新验证 final head，不沿用旧 SHA 的绿灯。
- 阶段完成前核查 Ubuntu/macOS/Windows × 3.11/3.12/3.13 = **9/9** 相关矩阵；对实际不可用环境明确阻断，不省略行。
- 每阶段报告三项：**行为事实**（代码和机器结果）、**语义审查结论**、**没有验证的真实环境/人类指标**。

**发布前横向反例**：

| 反例 | 预期 |
| --- | --- |
| `removed` 误写 `updated`；Schema/Skill 枚举不一致 | FAIL / 静态一致性阻断 |
| `run` 执行中修改受管理源码后返回 0 | 中高风险 required pass 不足 |
| `pact-ready` 但没有运行/产品 Evidence | 不得推断「已验证」 |
| 只有 Domain 无 confirmed Rule；显式 RULE-ID 缺失 | 明确 unknown / 阻断 explicit requirement |
| rejected 决策前提变化 | 允许重新评估，不当永久禁令 |
| 被删除源码或旧架构说明竞争当前 Context | 当前工作意图不误用，历史仍可查 |
| 模块 README 存在于选中代码的父级 | 返回有界 hint，不默认全文载入 |
| 一个 required Evidence/changed file 无对应 coverage | 任务不能 finish |
| run/source/Context SHA 不匹配、外部输入 | Evidence 按风险阻断、建议重验 |
| Agent A 被 SIGINT、B 换进程恢复 | 可重获事实/待办，不自动完成 |
| 既有 AGENTS/CLAUDE/宿主 CI 的接入 | 不覆盖、不循环、未知不假通过 |
| 对外项目没有写权限或样本无法读取 | 报 `blocked/unverified`；不写其他仓库 |
| 历史 benchmark 绿色但 Owner 指标空缺 | Release 效果关口不得填「已证明减负」 |

## 5. 三轮 Code Review 与证据签收规范（每阶段执行）

### Review 1 — 合同与范围（Protocol/Authority）

Reviewer 对照原始计划、本 Change、真实主干 SHA：检查实现是否偏离、是否新增重复状态/规则；确认只有 PACT 改动，机器产物/人工声明边界明确；必要时修正文档和协议定义。没有 Sx AC 列表与 RED 场景，不能进入 Review 2。

### Review 2 — 调用链、敌对路径与兼容（Call-chain/Failure）

按「CLI/Agent 入口 → 文件枚举/解析 → 状态和 SHA → 执行/收据 → Schema/Convergence → Owner/Eval 输出」做独立复审。针对中断、并发、符号链接/路径越界、部分写、stale 证据、混合规则、旧 Runtime 和宿主覆盖保护寻找可复现反例；发现问题先 RED，再修复，重新审查，不以测试全绿替代这一轮。

### Review 3 — 验收、A/B 和回退（Acceptance/Release）

独立核对 PR 差异、AC、准确 CI 运行 SHA/ID，9× OS/Python、影响范围、Benchmark 非退化及是否不必要复杂；核验 rollback 和未验证项。三轮结果写入同一阶段 Review Ledger，记录 reviewer、证据、发现问题、修复 SHA、复核结论。**一次同一人的三次阅读不是三名独立 reviewer**：可增加 Copilot/Codex 等真实可用的独立 review，但必须有实际输出，不能声称开过不存在的子 Agent。

## 6. 统一退出条件与禁止的「提前完成」

| 指标 | 通过定义 |
| --- | --- |
| 协议正确性 | Schema/Runtime/Skill 同意；既有合法 case 不退化 |
| Evidence 安全 | stale、不匹配、执行期受管理工作区变化不支撑 required pass |
| 知识生命周期 | 不自动造 Note；rejected 条件可检索；取代和引用安全 |
| Context | 明确缺口、计数/Token 截断、fallback、README hints，固定任务无不解释召回退化 |
| 自动收尾 | 减少机械复制，不自动赋予产品/收尾完成 |
| 跨会话 | A→B 不读聊天能恢复可核实事实、发现过期收据 |
| 跨 Agent | Codex、Claude Code、OpenCode 的 9 格均有真实执行证据或明确 `unverified` |
| 外部宿主 | 原始仓库**零提交、零推送、零 PR**；PACT CI 隔离验证可重复 |
| Owner 负担 | 用真实交互统计技术问询、产品决策、澄清轮数、额外用时；无则 `unverified` |
| 发行 | 仅 PACT 授权发布、source/pyz/schema 同版、资产完整、可追溯、没有隐瞒的 P0/P1 |

**整轮 STOP / NO-GO**：

- 样本依赖其他项目真实代码变更才能「通过」；
- 任一已知假完成案例被接受；
- 为追求绿色将旧 RED 改写或把未知 Owner 指标填 0；
- Agent 平台尚未真实执行却标全兼容；
- 原始 S0～S7 强制 AC 任一缺证据；
- 用户未授权本次正式发行的 tag/Release 范围。

**有条件的工程验收**：若所有可由 PACT 单仓完成的阶段都通过，但外部真实 Agent runner / Owner 人工数据不可用，输出「工程实现阶段完成；S6/S7 部分真实验收 blocked」，具体列出证据缺口、复现入口和阻断原因，**绝不宣布八阶段整体已完成**。

## 7. 当前计划 Review/落地记录

- 2026-10-15：本文件是计划，不是功能实施或版本发布。
- 此处记录三轮 **计划本身** 的审查：原始八阶段对齐、攻击性可执行性/边界、验收/回退。只有真正发生的独立 Agent 反馈才可标成「独立」。
- 未来每个实施阶段单独追踪基准 SHA、PR、三轮 Review、测试 run ID、未完成 AC、回退路径。
