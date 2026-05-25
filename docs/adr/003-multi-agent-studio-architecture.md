# ADR 003 — Multi-agent studio architecture

**Date:** 2026-05-22  
**Status:** Under consideration

## Decision

Defer full SDK-based persistent agents in favour of a skills + separate sessions hybrid. Revisit if workload grows to justify the infrastructure cost.

## Context

The studio PM tooling works well for a single operator, but there's a desire to split responsibilities across dedicated "agents" — a PM, a coding agent, a CFO, a biz-dev manager — each with its own persona, tools, and memory. The question is how to implement this without over-engineering.

Three approaches were evaluated:

### Option A — Skills (extended)
Define a skill file per role (`/pm-morning`, `/cfo-review`, `/biz-dev-pipeline`). Each has its own persona, allowed tools, and workflow steps. They run inside the same Claude Code session. Persistence comes from CLAUDE.md + the file-based memory system already in place.

**Pro:** No infrastructure. Fits the existing pattern. Cheap.  
**Con:** All roles share one session context. No true isolation.

### Option B — Separate Claude Code sessions per role
Each agent is a `claude` session in a dedicated directory with its own CLAUDE.md and memory. A coding agent lives in the repo, the PM lives in `studio/`, a CFO agent lives in `finance/`. They share state via files (mirrors, JSON ledgers, markdown logs).

**Pro:** Real isolation. No SDK. Each agent has its own context and memory.  
**Con:** Manual to coordinate. Handoffs require discipline, not automation.

### Option C — Claude Agent SDK (persistent processes)
Build real agents using the Anthropic API. Each runs as a long-lived process with its own tool set, memory, and trigger mechanism (hooks, cron, API). Agents can call each other.

**Pro:** Full automation. True persistence. Parallel execution.  
**Con:** Real engineering cost. Token burn multiplies with agent count. Need a coordination/state layer.

## Cost model (API)

The SDK is free (open source). Cost is token consumption:

| Model | Input | Output | Best for |
|-------|-------|--------|----------|
| Opus 4.7 | ~$15/MTok | ~$75/MTok | Complex reasoning, architecture decisions |
| Sonnet 4.6 | ~$3/MTok | ~$15/MTok | General-purpose agents |
| Haiku 4.5 | ~$0.80/MTok | ~$4/MTok | Summaries, transforms, routine syncs |

For a small fleet (PM sync + coding review + CFO summary) running a few times a day on Sonnet: **~$10–50/month**. Continuous or research-heavy agents climb fast. Key lever: match model to task — most routine agents don't need Opus.

The hard part of multi-agent is **coordination**, not the agents themselves: how does the PM hand off to coding? How does the CFO see biz-dev's pipeline? A shared file-based state layer (same pattern as Asana mirrors) is the simplest answer before investing in a message queue or database.

## Consequences

- Start with Option A + B: extend skills for each role, dedicate a working directory per agent, use the file system as the coordination layer
- Revisit Option C if agents need to run autonomously on a schedule or trigger each other without human intervention
- When building SDK agents: default to Sonnet, drop to Haiku for routine tasks, reserve Opus for decisions that need it
- Token cost should be reviewed after any new agent is added — persistent agents with long contexts are the main cost driver
