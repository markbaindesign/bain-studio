---
tags: [utility, social, linkedin, kairos]
command: studio/linkedin_post.py
invoke: /linkedin-post
description: Publishes an approved post to Mark's personal LinkedIn profile, with a dry-run lint pass and an explicit approval step before anything goes public
---

# linkedin-post

Publishes a post to Mark's personal LinkedIn profile. Last step of the broadcast chain:
[Aura](../gods/) drafts, [Kairos](../../.claude/skills/kairos/SKILL.md) times it, this
publishes it. The `/linkedin-post` skill is a thin trigger - `studio/linkedin_post.py` does the
work and can be run on its own.

```bash
python3 studio/linkedin_post.py post --file draft.txt              # dry run, lints, publishes nothing
python3 studio/linkedin_post.py post --file draft.txt --yes --json # publish, print {urn, url}
python3 studio/linkedin_post.py post --file d.txt --image x.jpg --alt "..."
python3 studio/linkedin_post.py whoami                             # token owner and days left
python3 studio/linkedin_post.py auth                               # one-time OAuth login
```

| Flag | Meaning |
|---|---|
| `--file` | read the post text from a file (keeps line breaks intact) |
| `--image` / `--alt` | attach one JPG, PNG or GIF, with alt text |
| `--yes` | actually publish. **Without it every run is a dry run.** |
| `--json` | print `{urn, url}` on success |

## Publishing is public and immediate

There is no draft state and no undo. `--yes` posts to Mark's real profile. The skill requires
an explicit "post it" for that exact text in that conversation before adding `--yes`; a general
earlier approval does not carry over to a changed draft.

## Lint pass

The dry run warns on m-dashes (see the typography rule - they do not belong in anything the
public reads), post length, and more than two hashtags. Resolve warnings with Mark before
publishing rather than overriding them.

## Auth

OAuth, with the token cached locally and valid for about 60 days. `whoami` shows the days left.
When it expires, **Mark** must run `python3 studio/linkedin_post.py auth` himself - it opens a
browser. `LINKEDIN_CLIENT_ID` and `LINKEDIN_CLIENT_SECRET` live in `studio/.env`;
`LINKEDIN_API_VERSION` (format `YYYYMM`) is set there too and needs bumping when LinkedIn
retires a version, which surfaces as a version error.

## After publishing

Record it in the broadcast log at
`$STUDIO_CONTENT_DIR/social/broadcast-log.md` - set the row to `published` and add the URL, or
append a new row. Kairos reads that log, so skipping this makes it re-propose a published post.

## Tests

`python3 -m pytest studio/tests/test_linkedin_post.py` - 14 tests, no network.
