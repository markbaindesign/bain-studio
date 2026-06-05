---
name: scaffold-dir
description: Create a new project directory and initialise it as a git repo. Standalone step — callable directly or by /commission. Args: path [name]
allowed-tools: [Bash, Write]
---

# Scaffold Dir

Create a project directory and git repo at the given path.

Arguments: $ARGUMENTS
- First arg: absolute path for the new project directory
- Second arg (optional): project name, used in the initial commit message

## Steps

### 1. Validate

- If the path already exists and is non-empty, stop and report: "Directory already exists and is non-empty — aborting to avoid overwriting."
- If the path already exists and is empty, continue.
- If a parent directory doesn't exist, stop: "Parent directory {parent} does not exist. Create it first."

### 2. Create directory

```bash
mkdir -p {path}
```

### 3. Git init

```bash
cd {path} && git init
```

### 4. Write .gitignore

Write a minimal `.gitignore` at the project root:

```
.env
.env.local
node_modules/
__pycache__/
*.pyc
.DS_Store
```

### 5. Initial commit

```bash
cd {path} && git add .gitignore && git commit -m "init: scaffold {name or basename}"
```

### 6. Report

```
scaffold-dir: {path}
  ✓ directory created
  ✓ git init
  ✓ .gitignore written
  ✓ initial commit
```
