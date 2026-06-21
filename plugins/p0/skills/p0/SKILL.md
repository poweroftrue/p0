---
name: p0
description: Use when the user invokes $p0, starts a plan request with p0, says P0 gate, or asks Codex to plan, review for missed P0 blockers, revise the plan, and repeat until no P0 blockers remain before implementation.
---

# P0 Plan Gate

Use this skill for plan-only work. Do not implement code while the P0 gate is active.

## Workflow

1. Understand the requested change and inspect the repository enough to draft a concrete implementation plan.
2. Review the plan for P0 blockers by reading the code paths, contracts, data flows, tests, and external interactions that the plan itself makes relevant.
3. Do not use a fixed checklist. Let each round decide what to inspect next from the plan, the code just read, suspicious boundaries, missing invariants, and unresolved assumptions.
4. If a P0 blocker is found, revise the plan to remove it, explain the blocker and the adjustment, then run another review pass over the revised plan.
5. If no P0 blockers remain, stop. The user will decide whether to implement.

## P0 Definition

Treat a P0 as a blocker that would make the implementation direction invalid or dangerous: data loss/corruption, broken authorization or tenant isolation, double charging or wrong money behavior, irreversible destructive side effects, major production outage risk, impossible migration/deployment path, or a plan that cannot work after reading the actual code.

Do not classify ordinary polish, missing nice-to-have tests, local style issues, or small refactors as P0.

## Required Footer

Every P0-gate response must end with this exact footer so the local stop hook can decide whether to continue:

```text
P0_GATE:
status: clear|revised|blocked
p0_count: <integer>
rounds_completed: <integer>
code_paths_read: <short comma-separated list>
```

Use `status: clear` only when `p0_count: 0` and the plan is ready for the user to approve for implementation.
Use `status: revised` when any P0 was found and the plan was changed; another review pass is required. Continue until the gate is clear or blocked; there is no fixed round cap.
Use `status: blocked` only when you cannot make meaningful progress without user input.
