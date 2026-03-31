# 7-Day Python Agent Harness Plan

## Summary

This project uses Python as the only implementation language and follows a staged approach:

1. build the smallest working agent loop
2. make it structurally clean
3. add planning
4. add session state
5. add subagents
6. add compaction
7. test, reflect, and plan v2

The main constraint is intentional:

- the core implementation should be written by hand
- AI support should focus on guidance and review, not replacing the learning process

## Day 1: Minimal Working Prototype

Goal: get a full end-to-end loop working.

Implement:

- a tiny runtime entrypoint
- a tool registry
- three local tools:
  - `read_file(path)`
  - `write_file(path, content)`
  - `run_shell(command)`
- a loop where the model can request tools and receive tool results

Acceptance:

- read a file and summarize it
- modify a file
- run a shell command and explain the result

Deliverables:

- initial runtime code in `src/`
- first note in `docs/notes/`

## Day 2: Clean Up Into a Real Harness Skeleton

Goal: separate concerns before complexity grows.

Refactor into modules for:

- runtime
- tools
- prompts
- types
- state

Define minimal typed objects for:

- `ToolSpec`
- `ToolResult`
- `Message`
- `SessionState`

Acceptance:

- the codebase has clear boundaries
- adding planning tomorrow does not require restructuring everything

Deliverables:

- cleaner package layout
- note on module responsibilities

## Day 3: Add Planning and Todo State

Goal: move from plain tool use to task-oriented execution.

Implement:

- a simple planner step
- a todo list state with statuses
- injection of current plan into the runtime context

Keep it small:

- no graph planner
- no approval UI
- no multi-mode planning flow

Acceptance:

- the runtime can break a task into a few steps
- todo items change state as work progresses

Deliverables:

- hand-written planning subsystem
- note on why simple todo state is enough for v1

## Day 4: Session State and Recovery

Goal: make the harness survive across turns.

Implement:

- a persistent session file, likely JSON
- separation between raw history and model-facing context
- recovery of recent session state

Store at minimum:

- goal
- recent messages
- current todo list
- recent tool outputs

Acceptance:

- a second turn can continue prior work
- a stopped run can resume from local session data

Deliverables:

- session state implementation
- note on storage vs context projection

## Day 5: Subagent Delegation

Goal: allow the main runtime to hand off bounded work.

Implement:

- a single-layer delegation pattern
- a limited tool set for subagents
- a structured subagent result

Suggested first delegation tasks:

- search candidate files
- summarize a module
- gather evidence before a main-thread decision

Acceptance:

- the main runtime can invoke a subagent and consume its result
- failure in the subagent does not break the whole run

Deliverables:

- subagent path
- note comparing main agent vs subagent responsibilities

## Day 6: History Compaction

Goal: stop treating history as an ever-growing raw message array.

Implement:

- a projection layer for model context
- rules for what to keep vs summarize vs drop

Keep:

- user goal
- current todo state
- constraints
- high-value tool results
- key findings

Compress or drop:

- verbose shell output
- outdated intermediate search traces
- low-value repeated turns

Acceptance:

- longer runs still remain coherent
- context size does not grow linearly with all raw history

Deliverables:

- compaction module
- note on why compaction is more than summarization

## Day 7: Tests, Reflection, and v2 Plan

Goal: stabilize what was built and turn it into understanding.

Add tests for:

- tool execution
- planning updates
- session persistence
- delegation
- compaction behavior

Then write:

- what works
- what feels weak
- what is still missing compared to a mature harness
- what v2 should add next

Suggested v2 order:

1. permissions and approvals
2. better tool failure handling
3. stronger session persistence
4. MCP integration
5. async or parallel subagents
6. richer memory and retrieval

Acceptance:

- the repo contains a working learning prototype
- the design gaps are explicit and well understood

## Collaboration Rules

The implementation of core logic should stay learning-first.

Default rule:

- I write the core code.
- AI gives structure, review, debugging support, and limited local examples.

The AI may provide:

- signatures
- pseudocode
- scaffolding
- isolated sample functions
- test cases

The AI should not, by default, write entire core subsystems end-to-end.

## End State

At the end of the week, this repository should function as:

- a small but real Python agent harness
- a record of how it was learned
- a springboard for building a stronger v2
