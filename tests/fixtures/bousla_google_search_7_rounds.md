# Bousla Google Search P0 Seven-Round Regression

Source session:
`/Users/mostafa/.codex/sessions/2026/06/08/rollout-2026-06-08T23-53-03-019ea902-a379-7311-b8a7-09845f2eaabf.jsonl`

Seed prompt:
The user asked P0 to revise a Bousla plan so Google Search creatives use only
the operator brief, LLM output, and Google Keyword Planner/API data. The flow
must ignore local store data, accountant data, synced ad metrics, and previous
campaign context that caused BBQ World creatives to be built from unrelated
past campaigns.

Real missed blocker classes found in that thread:

- Product-shaped preview, publish, workflow-tool, planner, and persistence contracts still expected product/card data.
- `Strategy::Build`, `LaunchManagedAds`, and recent-purchaser user-list paths would still run or be bypassed unsafely.
- `AdSetupUploader` and publish payloads still assumed product/card ad group structures.
- Broad-match keyword generation lacked spend-safety constraints and negative/exact/phrase guardrails.
- Existing Google account history and local synced creative intelligence could still enter prompts.
- UI and workflow error paths could silently fall back to local research or expose raw provider errors.

The fixture below forces those classes across seven review rounds. Rounds 1-6
must keep the gate running with `status: revised`; round 7 is the first valid
clear after the revised plan has been re-reviewed.

## Round 1

P0 blocker: remove product-card research without replacing product-shaped
contracts in preview, publish, planner, workflow tools, and persistence.

P0_GATE:
status: revised
p0_count: 1
rounds_completed: 1
code_paths_read: CreativeResearch, GenerateSearchCreatives, AdSetupWorkflow, AdLab::Preview, persistence

## Round 2

P0 blocker: the revised plan still bypasses or collides with `Strategy::Build`,
`LaunchManagedAds`, and recent-purchaser user-list construction.

P0_GATE:
status: revised
p0_count: 1
rounds_completed: 2
code_paths_read: LaunchManagedAds, Strategy::Build, GoogleRecentPurchaserUserList, workflow context

## Round 3

P0 blocker: upload/publish still assumes product/card ad group payloads, so the
planner-only Search output cannot be launched safely.

P0_GATE:
status: revised
p0_count: 1
rounds_completed: 3
code_paths_read: AdSetupUploader, AdLab::Publish, Google search publish payloads

## Round 4

P0 blocker: Keyword Planner output can produce broad-match spend risk without
exact/phrase defaults, negative keywords, geo/language constraints, and review
guards.

P0_GATE:
status: revised
p0_count: 1
rounds_completed: 4
code_paths_read: Google planner tools, keyword match strategy, budget safety

## Round 5

P0 blocker: existing account creative intelligence and synced campaign metrics
can still enter prompts, violating the "Google API research only, no past
campaign context" requirement.

P0_GATE:
status: revised
p0_count: 1
rounds_completed: 5
code_paths_read: ExistingCreatives, GoogleAccountCreativeIntelligence, SearchPromptBuilder

## Round 6

P0 blocker: UI and workflow errors can silently fall back to local research or
surface raw Google/LLM provider errors, making failures unsafe and hard to
operate.

P0_GATE:
status: revised
p0_count: 1
rounds_completed: 6
code_paths_read: Ad Lab views, workflow tools, service errors, request specs

## Round 7

No remaining P0 blocker after re-reading the revised planner-only plan against
the launch, publish, prompt, keyword, data-source, and error-handling paths.

P0_GATE:
status: clear
p0_count: 0
rounds_completed: 7
code_paths_read: CreativeResearch, LaunchManagedAds, Strategy::Build, AdSetupWorkflow, AdSetupUploader, planner tools, Ad Lab views
