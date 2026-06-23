---
tags: [utility, research, ai-agent, nous-research, external-tool]
god: hermes
description: Research note on Nous Research's Hermes Agent - an open-source multi-platform AI agent. Assessed for studio relevance.
---

# Nous Research - Hermes Agent

**Researched:** 2026-06-23  
**Task:** BSTD-037  
**Source:** https://hermes-agent.nousresearch.com/

---

## TL;DR

Hermes Agent is an open-source AI agent by Nous Research - a multi-platform personal agent with memory, scheduling, and sandboxed code execution. It is unrelated to the studio's internal Hermes (sync agent). Not immediately relevant to studio tooling, but worth monitoring as the model tier matures.

---

## What it is

An open-source (MIT) AI agent platform. Targets personal/power-user automation rather than developer tooling. Desktop app + CLI for macOS 12+, Windows 10/11, and Linux.

**Current version:** v0.17.0

---

## Key capabilities

- **Multi-platform messaging:** Telegram, Discord, Slack, WhatsApp, Signal, Email, CLI
- **Persistent memory:** learns from past interactions across sessions
- **Natural-language scheduling:** create recurring automations by describing them
- **Subagent delegation:** delegates tasks to isolated child agents
- **Code execution backends:** local, Docker, SSH, Singularity, Modal
- **Web browsing, image generation, text-to-speech**
- **300+ model access** via Nous Portal (paid tiers)

---

## Pricing

| Tier | Notes |
|------|-------|
| Free | Limited credits via Nous Portal |
| Plus | Monthly credits, 300+ models |
| Super | Higher limits |
| Ultra | Highest limits |

Paid tiers billed through the Nous Portal. Not self-hosted model access - it routes through Nous infrastructure.

---

## Naming conflict

The studio already has an internal agent named "Hermes" (the Asana sync agent, `studio/sync.py`). These are entirely separate things. The Nous product should be referred to as "Nous Hermes" or "Hermes Agent" to avoid confusion in docs and conversation.

---

## Relevance to Bain Studio

**Low at present.** The studio runs Claude Code (Anthropic) for all agentic work - Nous Hermes would add a second agent runtime with different models and infrastructure. The overlap with existing studio tooling is high; the marginal value is low.

Possible future interest:
- If Nous releases strong open-weight models that outperform Claude for specific tasks
- If multi-platform messaging integration becomes a studio need (currently handled by Slack notifier)
- If the self-hosted code execution model becomes attractive for cost reasons

**Recommendation:** No action. Monitor Nous Research model releases for open-weight quality.
