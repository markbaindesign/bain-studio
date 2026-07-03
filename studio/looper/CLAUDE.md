# Studio Looper

Asana project for BainBot's cross-project task queue. Tasks from any studio project are
multi-homed here by Mark. BainBot works them in Queue order, moving each through the sections.

## Asana

ASANA_PROJECT_GID: FILL_IN_AFTER_CREATING_ASANA_PROJECT
ASANA_TASK_PREFIX: SL
ASANA_PROJECT_NAME: Studio Looper

## Behaviour

PRESERVE_FOREIGN_IDS: true

Tasks multi-homed into this project already have a Local ID from their home project (e.g.
MCF-007). sync.py must preserve those IDs rather than assigning new SL-NNN ones. This lets
the studio-looper skill route each task to the correct project directory by prefix.

## Sections

- Queue        — Mark adds tasks here; drag order = execution priority
- In Progress  — BainBot is currently working this task
- Blocked      — BainBot hit a blocker; assigned back to Mark with notes
- Review       — BainBot finished; Mark reviews before marking done
- Done         — Mark confirmed; closed in Asana

## Members

- Mark Bain (owner)
- bainbot (must be a member for sync to work)

## Setup

1. Create this project in Asana with the 5 sections above
2. Add bainbot as a project member
3. Copy the project GID and paste it into ASANA_PROJECT_GID above
4. Run: python3 studio/sync.py --setup --project SL
5. Multi-home tasks from any project into Queue to start the queue
