# Studio TODO

## High priority
- [ ] Replace `ASANA_PAT` in `studio/.env` with bainbot account token — generate from Asana as bainbot user at app.asana.com → My Settings → Apps → Personal Access Tokens

## Low priority
- [ ] Set up Telegram notifications for rate limit reset
  Create a Telegram bot via BotFather, get token and chat ID, then wire up cron job to send notifications when Claude API rate limit resets.
- [ ] Create Asana template project for `sync.py --create`
  Set up a project in Asana with standard sections (DOING, NEXT UP, TO DO, DONE, SOMEDAY/MAYBE), configure preferred views/filters, then add its GID to `studio/.env` as `ASANA_TEMPLATE_PROJECT_GID`.
