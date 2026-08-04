---
tags:
- checklist
- performance
god: themis
member: eirene
description: Pre-delivery performance checklist — run by Eirene before Themis gates a project
---

# Performance Checklist (Eirene)

Run before Themis sign-off. All items must pass or be explicitly accepted by Mark.

## Infrastructure

- [ ] CDN configured and active
- [ ] HTTPS enforced, HTTP redirects to HTTPS
- [ ] Gzip / Brotli compression enabled

## Cloudways (if applicable)

- [ ] PHP 8.2+ set (Cloudways → Server → PHP Settings)
- [ ] Varnish enabled and "Enable Varnish" ticked in Breeze — purges don't clear Varnish without it
- [ ] Breeze: minify HTML/CSS/JS enabled (off by default)
- [ ] Breeze: lazy load images enabled (off by default)
- [ ] Breeze: browser cache TTL set to 1 year for static assets
- [ ] Cloudflare Enterprise CDN added ($4.99/domain/month via Cloudways dashboard — Cloudflare Enterprise resold through Cloudways) — 330+ edge locations, edge page caching, Argo Smart Routing, DDoS protection, managed WAF. Includes 100 GB bandwidth/month ($0.02/GB overage). First 30 days free for new domains.

## Images

- [ ] All images served in WebP or AVIF
- [ ] Images sized to display dimensions (no oversized assets)
- [ ] Lazy loading on off-screen images
- [ ] No images with missing `width`/`height` attributes (causes CLS)

## Caching

- [ ] Browser caching headers set (static assets: 1 year)
- [ ] Server-side page caching active (e.g. WP Rocket, LiteSpeed, Redis)
- [ ] Cache-busting in place for CSS/JS (versioned filenames or query strings)

## Core Web Vitals

- [ ] LCP under 2.5s (mobile)
- [ ] INP under 200ms
- [ ] CLS under 0.1
- [ ] No render-blocking resources in `<head>` (defer/async JS, preload critical CSS)
- [ ] `/perf-audit` run against live/staging URL and P1s resolved

## Code

- [ ] CSS and JS minified
- [ ] Unused CSS removed or scoped
- [ ] Third-party scripts (analytics, chat, fonts) deferred where possible
- [ ] Web fonts: `font-display: swap` set, preloaded if critical
