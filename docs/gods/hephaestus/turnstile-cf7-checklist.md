---
tags:
- checklist
- wordpress
- security
god: hephaestus
description: "Add Cloudflare Turnstile to a WordPress + Contact Form 7 site: widget creation, keys, placement, WP Engine live, verification"
---

# Turnstile on Contact Form 7 — Setup Checklist

A reusable method for adding Cloudflare Turnstile spam protection to a WordPress + Contact Form 7 (CF7 5.9 or later) site. It was first applied on TSTY (2026-10-15) after a phishing "formal enquiry" came through the contact form, and then on EBIZG.

Turnstile blocks automated submissions. It does **not** stop hand-typed phishing.

**Why Turnstile, not reCAPTCHA:**
- Most visitors never see it.
- It sets no Google cookies, which helps with GDPR.
- The site doesn't need to be on Cloudflare.
- Key setup is simpler.

Full write-up: the TSTY `Dev Ops/` note in that client's Dropbox folder.

## 1. Create the widget (studio Cloudflare account)

- [ ] Load the credentials from `~/.config/cloudflare/turnstile.env`.
  - The file holds `CF_API_TOKEN` and `CF_ACCOUNT_ID` and has mode 600.
  - The token is account-owned, with only the permission Account > Turnstile > Edit.
  - Load it with `set -a; . file; set +a`.
  - Never print the file or its values.
- [ ] Send `POST https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/challenges/widgets` with this body:
  `{"name":"<Client> - contact form","domains":["<live domain>","<ddev domain>"],"mode":"managed"}`
- [ ] Write `result.sitekey` and `result.secret` straight to `~/.config/cloudflare/<client>-turnstile.env` (mode 600), using a Python one-liner.
  - Print only the sitekey, which is public.
- [ ] Record in the client's Dev Ops notes that the widget lives in Mark's account.
  - Until handover, the client's form depends on an account they don't control.
  - At handover, the client creates their own widget and swaps both keys.
- To rotate a leaked secret: `POST .../challenges/widgets/<sitekey>/rotate_secret` with `{"invalidate_immediately":true}`.

## 2. Configure CF7

- [ ] Set the keys with `WPCF7::update_option('turnstile', [$sitekey => $secret])`.
  - CF7 stores them under option `wpcf7`, as `['turnstile' => [sitekey => secret]]`.
- [ ] Confirm `WPCF7_Turnstile::get_instance()->is_active()` returns true.
- [ ] Add `[turnstile]` on its own line before `[submit]`.
  - Without the tag, CF7 puts the widget at the **top** of every form.

## 3. Handle secrets safely

- [ ] Never pass a secret as an argument to `ddev wp` or `ddev exec`, because ddev echoes the full command when it fails. Pipe it in on stdin instead:
  `printf '%s\n%s' "$K" "$S" | ddev wp eval '[$k,$s]=array_map("trim",explode("\n",stream_get_contents(STDIN))); ...'`
- [ ] When checking a credentials file, look only at names and line counts (`cut -d= -f1`).
  - Never dump it through a regex filter.

## 4. Apply on live (WP Engine over SSH)

- [ ] SSH hosts are `ssh_<client>` and `ssh_<client>_stg` in `~/.ssh/config`. The site root is `~/sites/<install>`.
- [ ] Mark must add a `/permissions` rule for each project, e.g. `Bash(ssh ssh_<client>:*)`.
  - Auto mode blocks prod SSH without it, and Claude can't add the rule itself.
- [ ] WP Engine's SSH gateway strips quoting, so send PHP on stdin:
  `cat script.php | ssh ssh_<client> 'cd ~/sites/<install> && wp eval-file -'`
- [ ] Read the live form and Additional CSS before writing anything, so client edits aren't overwritten.
- [ ] Afterwards, run `wp cache flush && wp page-cache flush`.

## 5. Verify

- [ ] **Stale cache.** WP Engine's Cloudflare edge (max-age=600) can keep serving the form without the widget while the server already requires a token. When that happens, every real submission fails as "spam".
  - Flush the caches first.
  - Then confirm the public HTML contains `data-sitekey="<sitekey>"`.
  - Use curl with a full browser user agent; a bare UA gets a 403 at the WP Engine edge.
- [ ] **Negative test.** `POST /wp-json/contact-form-7/v1/contact-forms/<ID>/feedback` with `_wpcf7`, `_wpcf7_unit_tag` (scraped from the page) and the form fields, but no token. Expect `spam`.
- [ ] **Positive test.** Submit in a browser and expect `mail_sent`.
  - Locally, confirm the mail arrives in Mailpit.
  - Check first that no SMTP plugin is active.
- [ ] **Visual check.** Themes can clip the widget.
  - On Norebro, the form has `margin: 0 -30px` inside `overflow: hidden`. The fix was this Additional CSS: `.norebro-contact-from-sc .wpcf7-turnstile { padding: 0 30px; }`.
  - To diagnose, use `elementFromPoint` at the widget's left edge. The iframe sits in a closed shadow root, so you can't inspect it directly.
  - Some themes also replace CF7's submit input with their own button.

## Notes

- The free-plan widget limit is believed to be about 20 widgets per account, with 10 hostnames each. This is **unverified**, so check it before scaling across clients.
- **Candidate for a studio script:** create widget → save keys → set keys locally via ddev (stdin) → add `[turnstile]` before submit → set keys on live via SSH (stdin) → flush caches → verify public sitekey and spam rejection. A skill would only be a trigger for it.

## See also

- [[wordpress-plugins]]
- [[hephaestus]]
