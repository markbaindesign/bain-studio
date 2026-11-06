---
tags: [utility, security, registry]
god: periphetes
command: python3 studio/scripts/gen-denylist.py
description: Emits the client-data denylist from the out-of-repo registry, for the commit guards that keep client identity out of this public repo.
---

# gen-denylist

Prints one literal term per line — client names, project names, domains, hosting
install hostnames, repository slugs, client-owned organisations, Asana GIDs and
analytics property IDs — for `grep -F` to match against.

```bash
python3 studio/scripts/gen-denylist.py
git grep -lIiwF -f <(python3 studio/scripts/gen-denylist.py) -- . ':!CHANGELOG.md'
```

The second command is the acceptance test for BSTD-875. When it returns nothing,
this repo carries no client identity. **Don't write its result down anywhere** —
it moved four times in one afternoon as discovery widened, and a recorded count
is stale by the next commit.

## Why it generates rather than reads a file

A list of client names and domains, committed so a hook can grep for it, is the
exact data the hook exists to keep out. Every term is read at run time from
outside the repo:

| Input | Default |
|---|---|
| Registry | `$XDG_DATA_HOME/bain-studio/registry.json` (`BAIN_REGISTRY`) |
| Extra terms | `$XDG_DATA_HOME/bain-studio/denylist-extra.txt` (`BAIN_DENYLIST_EXTRA`) |

The extra file holds terms with no registry home: client contact names and email
addresses, hosting and search provider application IDs, the Asana workspace GID,
client-owned organisations, and clients or sites with no project file of their
own.

## The registry is the weak link, not the script

The script is only as good as what the registry knows. Both counts this work
started from were wrong, and a denylist built from frontmatter alone was still
wrong: it had no domains for four projects, missed two projects that live only
in `projects.json`, and missed a named client contact, a client PM, two client
email addresses, a client site that appears only in prose and two search
application IDs. Those were found by sweeping the tree for domains, email
addresses and capitalised names near the word "contact" — not by reading the
registry.

**A new client entry must carry its domains, or the guard cannot see them.**
Re-run a discovery sweep when adding one:

```bash
git grep -hIoE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' -- . | sort -u
git grep -hIoE '\b[a-z0-9][a-z0-9-]*\.(com|org|net|io|es)\b' -- . | sort -u
```

## It refuses rather than returning nothing

Exit 2, with nothing on stdout, when the registry is missing, unparseable or
holds no client entries. A fresh clone or another
machine has no registry, and an empty denylist would let everything through
while appearing to pass. Callers must treat exit 2 as a failure, never as "no
terms matched".

## What it deliberately omits

- **Project prefixes.** Once the prefix-to-client mapping is out of the repo a
  bare prefix identifies nobody, and the toolchain speaks in prefixes
  throughout. A prefix in the denylist would refuse every commit carrying a task
  ID. See the ADR 021 addendum, decision 3.
- **Internal projects.** The studio names its own work freely in a public
  tooling repo. Entries are filtered on `kind`.
- **The studio's own accounts**, which appear in every repository URL.
- **Terms under four characters**, which substring-match ordinary English, and
  which at that length are prefixes anyway.
- **Container path segments** above the client folder.

## Related

- [ADR 021](../adr/021-studio-state-and-registry-leave-the-repo.md) — the
  registry leaves the repo; the 2026-11-06 addendum records why this exists.
- [ADR 026](../adr/026-one-session-per-checkout.md) — enforcement is a hook, not
  a rule.
