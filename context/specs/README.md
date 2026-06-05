# Spec Nursery

Specs live here until they're approved for build, then graduate to their project folder.

## Lifecycle

```
drafts/      ← being written, not ready for review
candidates/  ← complete, awaiting /review-spec
             ↓ approved → moves to project folder
             ↓ rejected → back to drafts/ with notes
```

## Graduation destinations

| Spec type | Destination |
|---|---|
| Studio tools | `context/internal/` |
| Client project | project path (e.g. `/home/bain/code/vvv/clients/www/nore/`) |
| Pipeline/infra | `context/pipeline/` |

## Promoting a draft to candidate

1. Spec is complete — sources, output, stack, phases all defined
2. Move file from `drafts/` to `candidates/`
3. Run `/review-spec` — it reads the spec and returns a verdict

## Running a review

```
/review-spec                    # reviews all candidates
/review-spec gestor-collector   # reviews a specific spec by name
```

Verdict: **approve** (graduate), **revise** (back to drafts with notes), or **defer** (valid but not now).
