# Handoff Template: CAD-Physics One-Sample FEA Prototype

Use this template when Pi stops mid-task, after a checkpoint, or before context may be lost.

Write the filled handoff to:

```text
docs/session_state.md
```

Overwrite the previous session state. Do not append.

## Template

```markdown
# Session State

**Last updated:** YYYY-MM-DD
**Agent:** Pi coding agent
**Feature:** One-sample CADCodeVerify to FEA-ready CAD
**Spec:** docs/execution-plans/01-basic-sample-fea-confirmed-spec.md
**Architecture:** docs/execution-plans/02-basic-sample-fea-architecture.md
**Tasks:** docs/execution-plans/03-basic-sample-fea-pi-microtasks.md
**Checkpoints:** docs/execution-plans/04-basic-sample-fea-checkpoints.md
**Sequential prompt:** docs/execution-plans/06-pi-sequential-execution-prompt.md
**Documentation taxonomy:** docs/ai_context/DOC_TAXONOMY.md

---

## Current Status

**Phase:** <number> — <phase name>
**Phase status:** Not Started | In Progress | Checkpoint Passed | Blocked | Complete
**Current task:** <exact task id and title from microtasks file>

## Completed Tasks

- [x] <exact completed task id and title>
- [x] <checkpoint if passed>

## Next Task

- [ ] <copy exact next task text from 03-basic-sample-fea-pi-microtasks.md>

## Current Codebase State

| File or Directory | Status | Notes |
|---|---|---|
| <path> | Created | <what exists> |
| <path> | Modified | <what changed> |
| <path> | Pending | <what remains> |

## Verification Run This Session

| Command | Result | Notes |
|---|---|---|
| `<command>` | PASS | <short output> |
| `<command>` | FAIL | <failure summary> |

## Decisions Made This Session

- <decision and reason>

## Blockers

If none:

None — proceed to the next task.

If blocked:

- **Blocker:** <clear blocker>
- **Needed from user:** <specific missing input>
- **Do not proceed past:** <task id>

## Environment

- Python command: `/opt/homebrew/Caskroom/miniconda/base/envs/cad_physics/bin/python`
- Required env vars for next phase:
  - `CAD_DB_CONNECTION_STRING`: required for DB phases and end-to-end run
  - `OPENAI_API_KEY`: required for GPT-5.4-mini generation phases
  - `OPENROUTER_API_KEY`: required only if using OpenRouter config

## How To Resume

1. Read `docs/execution-plans/06-pi-sequential-execution-prompt.md`.
2. Read `docs/execution-plans/00-pi-execution-protocol.md`.
3. Read `docs/ai_context/DOC_TAXONOMY.md`.
4. Read `docs/session_state.md`.
5. Run the last passing checkpoint command again:
   `<command>`
6. Start with the exact task listed in **Next Task**.
```

## Handoff Rules

- Copy the next task exactly from `03-basic-sample-fea-pi-microtasks.md`.
- Record actual file state, not intended file state.
- Record actual command outputs or paths to logs.
- If blocked, state the exact task Pi must not pass.
- Include environment variable requirements for the next phase.
- Do not include API keys, DB credentials, or model response contents.
- If stopping because context is near 60-70 percent, say so in **Current Status** and make the next task exact enough for a new session.
