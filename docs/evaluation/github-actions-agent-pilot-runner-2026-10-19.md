# GitHub Actions coding-Agent A/B runner — no-model preflight

**2026-10-19. PACT-only experimental infrastructure.** GitHub-hosted ephemeral Linux Actions runners can host real coding-Agent sessions; a dedicated permanent server is not required. This PR verifies that the A/B sandboxes can be prepared safely, **without** using any model/provider credential and **without** running a real Agent.

## Implemented by this preflight

- Workflow: .github/workflows/agent-runner-preflight.yml, activated on changes to its own files and by manual workflow_dispatch.
- Exact reviewed PACT checkout, github.token limited to repository contents:read and no persisted checkout credentials. No GitHub secret/model call, no provider login, no privilege escalation requested.
- Public PrivacyFence source pinned to 6a03856a6e1819b2eacd3963154ebc7d02923296, cloned into disposable runner scratch, then copied into two **independent local worktrees** A and B.
- A: original project documents/code only. B: exact same original tracked bytes plus source-identical compact installed PACT runtime and generated project Agent instructions. **No test oracle, task labels or PACT source checkout is intentionally copied into either workspace.** Both original tracked trees and the original SHA are hashed and compared.
- No third-party upstream test, Gmail/Slack/Salesforce call, production access, Code Agent invocation or external push in the preflight. Only PACT-owned local install code is executed, in a disposable copy. Test failure and symlink escapes fail closed.
- A sanitized JSON receipt is uploaded with 14-day retention, always explicitly marked real_agent_executed=false and release_gate=HOLD. Workspaces are deleted at job end; this is a setup validation, not yet a persistent agent-workspace artifact.
- Important: this preflight does **not** yet distribute the complete source-faithful PACT Decision projections to future B-agent jobs. Preparing B's scoped knowledge under independent custody, only from documented source, remains necessary before the comparison.

## What the next *manual* real-Agent workflow needs

1. **Model authentication:** use the official OpenAI Codex GitHub Action with a narrowly scoped provider API key stored as an Actions **environment secret** (not in repository text, issue comments, chat or pull_request jobs). The repository's built-in GITHUB_TOKEN authenticates to GitHub itself; it is not the OpenAI Codex provider key. GitHub Models may support alternative inference through models:read, but that is not proof an official Codex Action can run without provider authorization.
2. **Explicit approval and model budget:** use workflow_dispatch only, branch and trusted actor gate, protected environment with required reviewer, dedicated provider project and its enforced hard spend limit. An Actions timeout limits wall time but does NOT enforce tokens or dollars per session. Provider project hard spend limits may overshoot slightly during enforcement; original formal #214 study needs independently verifiable per-run token/spend hard stops (trusted metered proxy), not just a monthly alert. No cost-bearing job is enabled by this PR.
3. **Isolation:** one fresh VM or audited sandbox per task/arm. Agent sees only a pinned read-only source snapshot, arm-specific safe instructions, for B a standalone PACT runtime/minimal source-faithful metadata, and the exact natural-language task. Do not mount the PACT source repository, published benchmark, prewritten oracle or previous Agent transcripts in Agent-readable paths. The model broker credential must not be visible to untrusted upstream shell/tests. No GitHub write/push permissions or provider API accounts.
4. **Independent fresh task custody:** authorize a separate case custodian to freeze three unseen task/answer pairs outside the Agent workspaces (2 decision conflicts + 1 unrelated routine negative). Past public #225 cards and labels are already exposed, so are ineligible for claims of independent holdout. Both A and B get identically worded tasks, same model/version/tools, balanced order and matched time ceilings. Do not change case wording after looking at results.
5. **Actual coding receipts:** the Agent must modify code and run relevant offline tests, not merely return a Context. Preserve authentic sanitized full tool/command transcript, source SHA, the application diff (not PACT scaffolding), tests, provider-billed tokens, wall time, selected source IDs and false-done/authorization evidence for all attempts including failures. Only blinded external semantic reviewers can decide which arm better obeyed constraints; genuine Owner observation requires actual opt-in. Do not log raw credentials/private Owner texts or publish an answer key.

## Admission and interpretation

This infrastructure is not yet a real Codex/Claude Code/OpenCode execution. It is a safe proof of disposable GitHub-hosted runner *capacity and source/workspace preparation*. We cannot verify from GitHub's publicly exposed connector whether the repository currently has a Codex API secret; no secrets are read by this work.

The smaller six-session experiment, once separately authorized, is a **nonconfirmatory** behavior smoke. The formal 72-session independent study documented in docs/evaluation/decision-memory-real-agent-blind-trial-2026-10-18.md remains subject to all original blind/Owner gates in #214 and #28.

No default routing changes; no release or tag; #221/#214/#28/#32 remain open and #63 Release HOLD. Poorly targeted decisions and excess context found in #225 remain negative product evidence, regardless of setup success.

## Trusted references

- Official OpenAI Codex GitHub Action: https://github.com/openai/codex-action
- GitHub Actions runner/token documentation: https://docs.github.com/en/actions/concepts/security/github_token
- GitHub protected environments and secrets: https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments
- OpenAI API project hard spend limits: https://developers.openai.com/api/docs/guides/spend-limits
