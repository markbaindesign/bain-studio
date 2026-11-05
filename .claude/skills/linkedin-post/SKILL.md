---
name: linkedin-post
description: "Publish an approved post to Mark's LinkedIn profile and mark it published in the Kairos broadcast log."
allowed-tools: [Read, Edit, Bash]
---

# LinkedIn Post

A thin trigger for `/media/data/dev/bain-studio/studio/linkedin_post.py`. The script does the work.

## Steps

1. **Get the final text.** Use the exact text Mark approved, plus an image path and alt text if there is one. Write the text to a temp file in the scratchpad so line breaks survive.

2. **Dry run.**
   `python3 /media/data/dev/bain-studio/studio/linkedin_post.py post --file <file> [--image <path> --alt "<alt>"]`
   Show Mark the preview and any WARNING lines (m-dash, length, more than 2 hashtags). Fix warnings with him first.

3. **Ask for explicit approval of that exact text.** Publishing is public and immediate. Never add `--yes` without a clear "post it" for this text in this conversation.

4. **Publish.** Re-run the same command with `--yes --json`. Report the post URL.

5. **Update the broadcast log** at `/media/data/Dropbox/Work/Studio/context/social/broadcast-log.md`: change the post's row to `published` and add the URL, or append
   `| {YYYY-MM-DD} | {first line} | LinkedIn | published |` if it has no row.

## Errors

- "Not authorised" or "expired": the token lasts about 60 days. Ask Mark to run
  `! python3 /media/data/dev/bain-studio/studio/linkedin_post.py auth` (it opens a browser, so he must run it).
- Version error: set `LINKEDIN_API_VERSION` (YYYYMM) in `studio/.env` to a current version.
