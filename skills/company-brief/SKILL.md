---
name: company-brief
description: >
  Research a target company and produce a structured brief for interview or application prep.
  Covers culture, history, leadership, values, products, audience, tech stack, financials,
  VC/IPO history, blog, socials, public statements, and positioning tips. Use when the user
  says "research [company]", "brief me on [company]", "company brief", or asks for
  interview/application prep on a specific employer.
---

# Company Brief

Researches a target company and produces a structured brief for interview or application prep.

## Inputs

Ask the user for the following if not already provided:

1. **Company name** (required)
2. **Company URL** (optional — speeds up research)
3. **Role being applied for** (optional — tailors the tech stack and positioning sections)

---

## Research Process

Use WebSearch and WebFetch to gather real, current information. Do not invent or assume facts — if something cannot be confirmed, say so.

Run all searches. Fetch pages where search results alone are thin.

### 1. Core identity
Search: `"[company name]" about history founded`
- Full legal name, founding year, headquarters location
- What the company does in one sentence
- Business model (SaaS, agency, marketplace, etc.)
- Company size (headcount range, funding stage or public/private)

### 2. Products and services
Search: `"[company name]" products services features`
Fetch the homepage and /products or /services page.
- Main product(s) or service lines
- Key features or differentiators
- Pricing model if visible
- Notable integrations or platforms they build on/for

### 3. Target audience and customers
Search: `"[company name]" customers case studies`
- Who they sell to (B2B/B2C, industry verticals, company size)
- Named customers or case studies if public
- Geographic markets

### 4. Tech stack
Search: `"[company name]" tech stack site:stackshare.io`
Search: `"[company name]" engineering blog`
Search: `"[company name]" site:github.com`
Also try BuiltWith or Wappalyzer data via WebFetch on their domain.
- Languages, frameworks, platforms
- Infrastructure and cloud providers
- Open-source contributions or public repos
- CMS, e-commerce, or headless stack if relevant

### 5. Culture and values
Search: `"[company name]" culture values mission`
Fetch: /about, /careers, /culture pages
- Stated values and mission
- Remote/hybrid/in-office stance
- Team size and structure hints
- Awards (Best Place to Work, etc.)

### 6. Leadership
Search: `"[company name]" CEO founder leadership team site:linkedin.com`
Search: `"[company name]" CEO interview`
- CEO: name, background, tenure, any notable public interviews or statements
- CTO or Head of Engineering (key for dev roles)
- Co-founders if relevant
- Any hiring manager or team lead named in the job post
- Notable advisors or board members

### 7. Financial position and investment history
Search: `"[company name]" funding raised series valuation`
Search: `"[company name]" IPO OR "went public" OR "stock ticker"`
Search: `"[company name]" site:crunchbase.com OR site:pitchbook.com OR site:techcrunch.com funding`
- Public or private; if public: stock ticker, exchange, approximate market cap
- If private: total funding raised, most recent round (amount, date, lead investors)
- Valuation if reported
- Key VC backers or strategic investors
- Any M&A activity (acquisitions made or acquired by)
- Burn rate concerns, profitability signals, or runway notes if findable

### 8. Blog and thought leadership
Fetch: /blog, /insights, /resources, or equivalent
Search: `"[company name]" blog engineering`
- Topics they write about (reveals priorities and culture)
- Posting frequency (signals team investment in public writing)
- Any posts directly relevant to the role or stack
- Named authors — often indicates who is senior/influential on the team

### 9. Social media and public presence
Search: `"[company name]" site:linkedin.com/company`
Search: `"[company name]" site:twitter.com OR site:x.com`
Fetch their LinkedIn company page if accessible.
- LinkedIn follower count, recent posts, tone
- Twitter/X activity — what they post about, how they engage
- Any other active channels (YouTube, newsletters, podcasts)
- Signals of momentum: frequent posts, active engagement, product announcements

### 10. Public statements and press
Search: `"[company name]" press release announcement 2025 2026`
Search: `"[company name]" CEO interview podcast`
Search: `"[company name]" site:techcrunch.com OR site:wired.com OR site:forbes.com`
- Official press releases and what they signal about direction
- CEO/founder interviews — their stated vision, priorities, challenges
- Trade press coverage and sentiment
- Any notable controversies, data breaches, or legal issues

### 11. Recent news and developments
Search: `"[company name]" news 2025 2026`
- Product launches or pivots
- Headcount changes (hiring spree or layoffs)
- Partnerships or integrations announced
- Any controversies worth knowing about

### 12. Employee sentiment
Search: `"[company name]" reviews site:glassdoor.com`
Search: `"[company name]" interview experience`
- Overall Glassdoor rating if available
- Common praise themes
- Common criticism themes
- Interview process notes (format, difficulty, common questions)

---

## Output Format

Produce a clean brief using this structure. Plain prose under each heading — no padding, no invented facts. If a section has nothing reliable to report, write "Not confirmed."

```
COMPANY BRIEF: [Company Name]
Prepared: [today's date]
Role: [role if provided, else "General prep"]

## Overview
[2–3 sentences: what they do, who for, business model, size/stage]

## Products & Services
[Bullet list of main offerings with one-line descriptions each]

## Target Audience
[Who they sell to — industry, company size, geography]

## Tech Stack
[Confirmed technologies only. Group by: Frontend / Backend / Infrastructure / CMS/Platform]

## Financial Position
[Public/private. If public: ticker, market cap. If private: total raised, last round, lead
investors, valuation if reported. Profitability signals. Any M&A.]

## Culture & Values
[Stated values. Remote stance. Culture signals from careers page, blog tone, and reviews.]

## Leadership
[CEO: Name — background, tenure, notable quotes or stated priorities
CTO/Engineering lead: Name — background
Co-founders or key execs if relevant
Any hiring manager named in the job post]

## Blog & Thought Leadership
[Topics covered, posting frequency, any posts relevant to this role]

## Social & Public Presence
[LinkedIn follower count and tone. Twitter/X activity. Other active channels.
Overall signal: growing voice, quiet, or stagnant?]

## Public Statements & Press
[2–3 key things said publicly by leadership (with source/date).
Notable press coverage. Any controversies.]

## Recent News
[4–6 bullet points, most recent first, with approximate dates]

## Employee Sentiment
[Glassdoor rating if found. 2–3 themes from reviews — both positive and negative.
Interview process notes if available.]

## Red Flags
[Anything worth being cautious about: funding concerns, layoffs, poor reviews,
leadership churn, legal issues. Omit section if nothing notable found.]

## Positioning Tips
[4–6 specific, tactical talking points tailored to this company and role.
What should the applicant emphasise? What pain points can they speak to?
Any tech, cultural, or strategic alignment worth calling out explicitly?]

## Questions to Ask Them
[4–6 smart, specific questions grounded in what was found — not generic interview questions]
```

---

## Notes

- Prioritise accuracy over completeness. A short honest brief beats a padded one with invented facts.
- If the company is very small or new and little is findable, say so clearly and work with what exists.
- The Positioning Tips section should reference the applicant's background where context is available.
- Never omit the Red Flags section if something was found — honest prep is the goal.
- Save the brief as `context/applications/[company-slug]-brief-[date].md` if the applications directory exists.
