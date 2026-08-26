# Studio Looper

Asana project for BainBot's cross-project task queue. Tasks from any studio project are
multi-homed here by Mark. BainBot works them in Looper Status order (Queue first), moving
each through the statuses via the Looper Status custom field.

## Asana

ASANA_PROJECT_GID: 1216260498940192
ASANA_TASK_PREFIX: SL
ASANA_PROJECT_NAME: Studio Looper

## Behaviour

PRESERVE_FOREIGN_IDS: true

Tasks multi-homed into this project already have a Local ID from their home project (e.g.
MCF-007). sync.py must preserve those IDs rather than assigning new SL-NNN ones. This lets
the studio-looper skill route each task to the correct project directory by prefix.

## Looper Status field

Workspace-level enum custom field: **Looper Status** (set ASANA_LOOPER_STATUS_FIELD_GID in studio/.env).

Values:
- Queue        — Mark adds tasks here; execution order = Priority field (High first), then drag order
- In Progress  — BainBot is currently working this task
- Blocked      — BainBot hit a blocker; assigned back to Mark with notes
- Review       — BainBot finished; Mark reviews before marking done
- Done         — Mark confirmed; task complete in Asana

Tasks added to this project with no Looper Status are automatically defaulted to "Queue" by
sync.py on the next sync run. No Asana automation rule required.

BainBot reads the field to build the queue and writes it to advance tasks through statuses.

## Members

- Mark Bain (owner)
- bainbot (must be a member for sync to work)

## Artifacts & file references

Any artifact (research document, analysis, code, etc.) created while working a looper task should be saved to `docs/looper/` or to the relevant project's own docs directory — **not** to `studio/looper/`. This keeps the studio docs organized by subject and makes them easier to find and reference later.

Examples:
- Research documents → `docs/looper/`
- Project-specific docs → `{PROJECT_DIR}/docs/`
- Proposal/template docs → `docs/utilities/` (if studio-wide)

**Always use full file paths** when referencing files in progress notes and task descriptions. Examples:
- Full: `/media/data/dev/bain-studio/docs/looper/sl-120-proposal-examples-research.md`
- Full: `/media/data/dev/vvv/clients/www/kf-21/includes/custom-fields.php`
- **Not** relative paths like `studio/looper/file.md` or `../docs/file.md`

This makes it unambiguous where the file is located and easier for Mark (and future looper runs) to find it.

## Setup

1. Create "Looper Status" custom field in Asana workspace (enum, values above)
2. Add the field to this project
3. Copy the custom field GID → set ASANA_LOOPER_STATUS_FIELD_GID in studio/.env
4. Add bainbot as a project member
5. Run: python3 studio/sync.py --setup --project SL
6. Multi-home tasks from any project and set their Looper Status to "Queue"
