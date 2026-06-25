[2026-06-17T14:31:52Z] BSTD mirror-edit BSTD-036 Get a free Google Cloud API key for PageSpeed Insights (TO DO, NEW)
2026-06-17T14:51:04Z BSTD create-task BSTD-036 'Get a free Google Cloud API key for PageSpeed Insights' (GID: 1215806122078819)

## 2026-06-23 15:30 — The Nature of Real Estate session

**Done:**
- Fixed broken site: gitignore was too aggressive (tracked CSS deleted on branch merge) - corrected to only ignore `.min.css`/`.min.js`, restored compiled CSS tracking, recovered `youtube.css` from git history
- Updated Sass watcher command in CLAUDE.md to cover all 9 block Sass entry points
- Pulled prod DB to local, ran FSE sync, reviewed all 6 template/part diffs - client made significant nav/footer/blog index updates since last sync
- Left template diffs uncommitted for manual review; saved diff report at `context/prod-sync-2026-06-23.md`
- MemberPress confirmed removed from project; orphan template deleted from disk and DB

**Next action:** Review the 6 template diffs one by one using `context/prod-sync-2026-06-23.md` as the guide, then clear DB overrides (7 tasks queued)

**Blockers:** None - diffs are staged, report is written, tasks are clear

## 2026-06-23 17:30 — Khyentse Foundation Website session

**Done:**
- Investigated WP Engine storage overage (~2.1 GB over allowance)
- Deleted duplicate theme copies (kf-21_x, kf-21_xx, kf-21_2.7.2, kf-21_2.8.0, theme.zip) - freed ~387 MB
- Deleted wpallimport/wpallexport leftovers - freed ~88 MB
- Total freed: ~475 MB, production now at ~1.6 GB
- Logged KF-WEB-031 (local-only) for remaining 404 MB uploads S3 offload

**Next action:** Create KF-WEB-031 in Asana manually, then run WP Offload Media bulk offload from WP admin to clear the remaining 404 MB from uploads/

**Blockers:** None
