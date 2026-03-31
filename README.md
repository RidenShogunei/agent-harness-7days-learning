# agent-harness-7days-learning

A 7-day learning project for building a Python agent harness from a tiny working prototype upward.

This repository is intentionally learning-first. The goal is not to clone Claude Code or ship a production framework in one week. The goal is to understand the core moving pieces of an agent harness by implementing a minimal but real version step by step.

## Goal

By the end of 7 days, this repo should contain:

- a working local Python agent harness prototype
- notes explaining the runtime architecture and design tradeoffs
- a clear v2 roadmap for the next systems to add

The implementation path is:

1. single-agent tool loop
2. planning and todo state
3. session state and recovery
4. subagent delegation
5. history compaction
6. tests and reflection

## Learning Style

This project follows a strict rule:

- I write the core code by hand.
- The AI acts as architect, guide, reviewer, and debugger.
- The AI should not silently implement the whole system for me.

That means the AI is allowed to help with:

- module boundaries
- interface design
- pseudocode
- partial scaffolding
- debugging help
- code review
- test design

And the AI should avoid doing this by default:

- writing the full runtime for me
- writing the full planner for me
- writing the full subagent system for me
- replacing the learning value with end-to-end implementation

If a reference implementation is needed, it should be limited to a narrow local example, not the whole project.

## Why This Repo Exists

I want to learn agent harness design by doing, not only by reading.

Claude Code is the architecture reference for a mature product-grade harness.
DeepAgents is the reference for a practical deep/coding agent pattern.
PydanticAI is the reference for typed agent structure and clean Python design.

This repo uses:

- Claude Code as an architecture sample
- DeepAgents as a pattern reference
- PydanticAI as a modeling and structure reference
- Python as the only implementation language for the learning path

## Repository Layout

- `docs/7-day-plan.md`
  The detailed day-by-day learning and implementation plan.
- `docs/notes/`
  Daily notes, questions, architectural observations, and retrospective summaries.
- `src/`
  The Python harness implementation.
- `tests/`
  Tests for the runtime, tool loop, state, and later subsystems.

## What Counts As Success

Success after 7 days means:

- I can explain the core components of an agent harness from memory.
- I have written the core runtime code myself.
- This repo can run a small but real local agent loop.
- I understand what is still missing compared with a mature harness.

## First Implementation Scope

The first version should stay small. It should include only:

- an agent runtime loop
- a tool registry
- a few local tools
- a simple plan/todo state
- one-layer subagent delegation
- basic session state
- basic context compaction

It should not initially include:

- MCP
- remote workers
- browser automation
- durable execution
- complex permission UI
- distributed orchestration

## Daily Workflow

Each day should produce:

- at least one hand-written code milestone
- at least one note in `docs/notes/`
- one short review of what was learned and what remains unclear

## Next Step

Start with the detailed plan in [docs/7-day-plan.md](docs/7-day-plan.md), then implement the smallest possible working runtime before adding any advanced features.
