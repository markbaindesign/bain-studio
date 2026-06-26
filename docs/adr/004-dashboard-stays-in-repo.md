# ADR 004 — Studio Dashboard stays in bain-studio repo

**Date:** 2026-06-12  
**Status:** Accepted

## Decision

Keep `studio/dashboard/` in this repo rather than splitting it into a separate project.

## Context

The Studio Dashboard (~2k lines: Flask server, Harvest client, GnuCash parser, HTML frontend) shares data sources and operational context with the rest of the studio tooling. The question of splitting it out arose as the dashboard grew in size.

## Reasoning

- The dashboard reads from the same sources (GnuCash, Harvest) that the rest of the studio tooling depends on — co-location keeps that relationship explicit.
- No concrete deployment, open-source, or independent versioning requirement exists to justify a second repo.
- Managing two repos adds overhead with no current benefit.

## Consequences

If a future need arises to deploy the dashboard independently or share it publicly, revisit this decision at that point.
