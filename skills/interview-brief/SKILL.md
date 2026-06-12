---
name: interview-brief
description: >
  Prepares a comprehensive interview brief after Mark receives an interview request on Upwork
  or elsewhere. Covers: project scope review, client background, tech stack deep-dive, key
  talking points from Mark's experience, smart questions to ask, rate/timeline discussion prep,
  and red flags. Invoke when Mark gets an interview invitation on a job he has applied for.
  Trigger phrases: "interview brief", "prep me for an interview", "got an interview", "/interview-brief".
---

# Interview Brief

Prepares Mark for a client interview by combining proposal context with fresh research on the
client and their project.

---

## Step 1 — Gather context

Ask for the following if not already provided. Collect all before proceeding.

1. **Job title / Upwork job URL** (required — to locate the proposal and job details)
2. **Client name or company name** (required — for research)
3. **Client website URL** (optional but useful)
4. **Interview format** (Upwork video call / Zoom / phone / async messages — if known)
5. **Any specific questions or topics the client mentioned** (paste them if you have them)
6. **When is the interview?** (to calibrate urgency)

If the job URL is provided and matches a file in `context/proposals/`, read that proposal now.
Also check `pipeline/pending_briefs.json` for the full job dict (title, description, budget, skills, client details).

---

## Step 2 — Load the proposal

Find the matching proposal file in `context/proposals/` (match by slug derived from job title or date).
Read the full file — both PROJECT BRIEF and PROPOSAL OUTPUT sections.

Extract and note:
- What was promised in the proposal (deliverables, approach, timeline, rate range)
- Which of Mark's projects were cited as relevant
- Any flags or concerns noted in the PROJECT BRIEF
- Screening question answers if any were included

If no proposal file is found, ask Mark to paste the proposal text or describe what was sent.

---

## Step 3 — Research the client

Use WebSearch and WebFetch to find real, current information. Do not invent facts.

### 3a. Company / client background
Search: `"[client name]" about site:[client URL domain]`
Search: `"[client name]" LinkedIn`
Search: `"[client name]" Upwork profile` (if individual)
- Is this an individual or a company?
- What do they do / what is their business?
- Size: solo operator, small team, established company?
- Industry and sector
- Any prior Upwork history visible (hires, spend, reviews)

### 3b. Project and tech context
Search: `"[client name]" WordPress` (or relevant stack from job description)
Search: `"[client name]" [main technology from job description]`
Fetch the client's website if URL provided — look for:
- CMS / platform in use (check page source, BuiltWith headers, footer credits)
- Current state of what they want to build or improve
- Any design references or existing work they linked in the job post

### 3c. Red flags check
Search: `"[client name]" reviews scam complaint` (optional, do if Upwork history is thin)
Check the Upwork job dict for:
- Payment verified? Rating? Hires? Spend?
- Is this a repeat client or new to Upwork?

---

## Step 4 — Build the interview brief

Produce the full brief as a markdown file. Structure:

```
# Interview Brief: [Job Title]
Client: [Client name]
Date: [today's date]
Interview: [format + date/time if known]

---

## Project scope (from proposal)

[2–3 sentences summarising what was quoted, what approach was proposed, and what rate/timeline
was discussed. Pull directly from the proposal — not from memory.]

---

## Client background

[What was found: individual vs company, industry, size, relevant history.
If Upwork client: their rating, total spend, number of hires. Tone: direct, no padding.]

---

## Their tech stack (confirmed + likely)

[What is confirmed from research. What is inferred from the job description.
Group: Current setup / What they want to build / Gaps to fill.]

---

## Key talking points

[5–7 specific points Mark should hit in the interview, grounded in what was found.
Each one links back to a real project from project-database.csv or a verified skill.
These are NOT generic — they should be specific to THIS client and THIS project.]

- **[Point]**: [One sentence on what to say and why it lands here]
- ...

---

## Questions to ask them

[6–8 smart questions. Ordered: project clarity first, then working style, then longevity/fit.
These should be specific to what was found — not generic interview questions.]

1. [Question] — *why ask: what this reveals*
2. ...

---

## Rate and timeline prep

[Based on the job's budget range and the proposal sent:
- What rate was proposed? Is there room to move?
- What's the likely project duration based on scope?
- Hourly vs fixed: which is better here and why?
- How to handle rate questions if they push back]

---

## Things to probe / potential concerns

[Any flags from the proposal, from research, or from the Upwork job dict that warrant
gentle probing during the interview. E.g.: vague scope, low budget for complexity,
first-time Upwork client, missing technical clarity, unrealistic timeline.]

---

## If they ask about [common interview scenarios]

Quick prep for the questions Mark is most likely to get:

**"Have you done something like this before?"**
[Which specific project(s) to reference and what to say]

**"What would your process look like?"**
[2–3 sentences on Mark's standard discovery → design/build → delivery flow]

**"What's your availability / when can you start?"**
[Standard answer prep: lead time, hours per week, timezone note]

**"Can you do it for less?"**
[One or two sentences on how to handle rate pushback without caving immediately]

---

## One-line summary

[Single sentence Mark can use to open: "I applied because..." — specific to this job.]

```

---

## Step 5 — Save the brief

Save to: `context/applications/[client-slug]-interview-[YYYYMMDD].md`

If a folder already exists for this application (from `apply.py`), save inside it instead:
`context/applications/[existing-folder]/interview-brief-[YYYYMMDD].md`

Confirm the save path to Mark.

---

## Notes

- Pull facts from the proposal and project-database.csv — do not fabricate experience.
- Keep talking points concrete: name the project, year, what was built. Vague claims lose trust.
- The "Questions to ask" section is often the most valuable part — smart questions signal expertise.
- If the interview is in under 2 hours, cut Step 3 research to the most essential searches only and flag this in the output.
- Do not include certifications or skills that are not in PROFILE.md or project-database.csv.
