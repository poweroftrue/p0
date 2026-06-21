# P0

P0 packages a Codex skill that turns planning into a hard gate before implementation. Use it when a change should be planned, reviewed for P0 blockers, revised, and reviewed again until the plan is clear or blocked.

## Install

Recommended Codex plugin install:

```bash
codex plugin marketplace add poweroftrue/p0 --ref main && codex plugin add p0@p0
```

This adds the repository marketplace, installs the P0 plugin, and enables the bundled skill. Start a new Codex thread and invoke:

```text
/plan p0
```

You can also invoke the skill directly:

```text
$p0
```

Fallback direct skill install:

```text
$skill-installer install https://github.com/poweroftrue/p0/tree/main/plugins/p0/skills/p0
```

## What It Does

The skill tells Codex to:

1. Draft a concrete implementation plan from the actual repository.
2. Review that plan for P0 blockers across relevant code paths, contracts, data flows, tests, and external interactions.
3. Revise the plan whenever a P0 blocker is found.
4. Stop before implementation once no P0 blockers remain.
5. Draft a `/goal` candidate when a clear plan is broad enough for long-running execution.

Every P0 gate response ends with a machine-readable `P0_GATE` footer so local hooks can detect whether the gate is clear, revised, or blocked.

## Package Layout

```text
.agents/plugins/marketplace.json
plugins/p0/.codex-plugin/plugin.json
plugins/p0/skills/p0/SKILL.md
plugins/p0/skills/p0/agents/openai.yaml
```

This follows the Codex plugin distribution model while keeping the underlying skill installable directly.
