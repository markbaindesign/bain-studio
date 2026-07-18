# Studio Looper — Test Queue

Sandbox Asana project for safely testing the `studio-looper` skill — headless runs, session-
collision fixes, new features — without touching the real Studio Looper queue or any client
project. Invoked via `/studio-looper --test`.

Tasks in this queue should describe trivial, harmless work confined to this directory (e.g.
"create a file", "edit this README") so a test run never risks a real commit to a client repo.

## Asana

ASANA_PROJECT_GID: 1216618878942979
ASANA_TASK_PREFIX: SLT
ASANA_PROJECT_NAME: Studio Looper (Test)

## Behaviour

PRESERVE_FOREIGN_IDS: false

## Setup (one-time, manual — requires Mark's Asana OAuth, not bainbot)

1. Add **bainbot** as a member of the "Studio Looper (Test)" Asana project.
2. Attach the existing workspace-level **Looper Status** custom field to this project
   (Add Field → search for "Looper Status" → attach existing, don't create new).
3. Run `python3 studio/sync.py --setup --project SLT` to wire Local ID / Last Synced fields.
4. Add a few SLT tasks with Looper Status = Queue to exercise a test run.
