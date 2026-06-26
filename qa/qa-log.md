# QA Log — BSTD

Append-only event log. One line per lifecycle event.
Format: [YYYY-MM-DD HH:MM] {ref} {event} — {details}

To check status of an item: grep {ref} qa/qa-log.md
To list all open items: grep -v "passed\|wontfix" qa/qa-log.md | grep "registered"

