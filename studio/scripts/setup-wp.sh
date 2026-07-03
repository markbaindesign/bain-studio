#!/usr/bin/env bash
#
# setup-wp.sh — Per-project WordPress dev environment setup
#
# Idempotent. Safe to re-run. Only adds what's missing.
#
# Usage:
#   studio/scripts/setup-wp.sh --slug beato-properties [--root /path/to/project] \
#     [--acf-key KEY] [--dry-run]
#
# --slug    VVV project slug (e.g. "beato-properties") — required
# --root    Path to project root (default: current dir)
# --acf-key ACF Pro license key
# --dry-run Preview changes, don't write anything

set -euo pipefail

SLUG=""
PROJECT_ROOT="$(pwd)"
ACF_KEY=""
DRY_RUN=false

# ── Argument parsing ───────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --slug)    SLUG="$2";         shift 2 ;;
        --root)    PROJECT_ROOT="$2"; shift 2 ;;
        --acf-key) ACF_KEY="$2";      shift 2 ;;
        --dry-run) DRY_RUN=true;      shift   ;;
        *) echo "Unknown option: $1"; exit 1  ;;
    esac
done

if [[ -z "$SLUG" ]]; then
    echo "Error: --slug is required (e.g. --slug beato-properties)"
    exit 1
fi

WP_ROOT="$PROJECT_ROOT/public_html"
WP_CONFIG="$WP_ROOT/wp-config.php"
MU_PLUGINS="$WP_ROOT/wp-content/mu-plugins"
MU_DEV="$MU_PLUGINS/mu-dev"
VSCODE_DIR="$PROJECT_ROOT/.vscode"

# ── Helpers ────────────────────────────────────────────────────────────────────
msg()  { echo "  $1"; }
ok()   { echo "  [=] $1 (exists)"; }
add()  { echo "  [+] $1"; }
skip() { echo "  [~] $1 (skipped — dry-run)"; }

rel() { echo "${1#$PROJECT_ROOT/}"; }

write_file() {
    local path="$1"; local content="$2"
    local label; label=$(rel "$path")
    if [[ "$DRY_RUN" == true ]]; then
        skip "$label"
    else
        mkdir -p "$(dirname "$path")"
        printf '%s' "$content" > "$path"
        add "$label"
    fi
}

ensure_dir() {
    local dir="$1"
    if [[ -d "$dir" ]]; then
        ok "${dir#$PROJECT_ROOT/}"
    elif [[ "$DRY_RUN" == true ]]; then
        skip "${dir#$PROJECT_ROOT/}"
    else
        mkdir -p "$dir"
        add "${dir#$PROJECT_ROOT/}"
    fi
}

# ── Patch wp-config.php ────────────────────────────────────────────────────────
patch_wp_config() {
    if [[ ! -f "$WP_CONFIG" ]]; then
        echo "  [!] wp-config.php not found at $WP_CONFIG — skipping"
        return
    fi

    local patch=""

    # Debug block
    if ! grep -q "WP_DEBUG_LOG" "$WP_CONFIG"; then
        patch+="
/* Debug */
if (!defined('WP_DEBUG')) {
    define('WP_DEBUG', true);
    define('WP_DEBUG_LOG', true);
    define('WP_DEBUG_DISPLAY', false);
    define('WP_DISABLE_FATAL_ERROR_HANDLER', true);
}
define('SCRIPT_DEBUG', true);
"
    else
        ok "wp-config: WP_DEBUG block"
    fi

    # Memory limits
    if ! grep -q "WP_MEMORY_LIMIT" "$WP_CONFIG"; then
        patch+="
define('WP_MEMORY_LIMIT', '256M');
define('WP_MAX_MEMORY_LIMIT', '512M');
"
    else
        ok "wp-config: WP_MEMORY_LIMIT"
    fi

    # Auto-update disable
    if ! grep -q "AUTOMATIC_UPDATER_DISABLED" "$WP_CONFIG"; then
        patch+="
define('AUTOMATIC_UPDATER_DISABLED', true);
define('WP_AUTO_UPDATE_CORE', false);
"
    else
        ok "wp-config: AUTOMATIC_UPDATER_DISABLED"
    fi

    # max_input_vars
    if ! grep -q "max_input_vars" "$WP_CONFIG"; then
        patch+="
@ini_set('max_input_vars', 10000);
"
    else
        ok "wp-config: max_input_vars"
    fi

    # ACF Pro license
    if [[ -n "$ACF_KEY" ]]; then
        if ! grep -q "ACF_PRO_LICENSE" "$WP_CONFIG"; then
            patch+="
define('ACF_PRO_LICENSE', '$ACF_KEY');
"
        else
            ok "wp-config: ACF_PRO_LICENSE"
        fi
    fi

    if [[ -n "$patch" ]]; then
        if [[ "$DRY_RUN" == true ]]; then
            skip "wp-config.php patch"
            echo "$patch" | sed 's/^/      /'
        else
            python3 - "$WP_CONFIG" "$patch" <<'PYEOF'
import sys
cfg_path, patch = sys.argv[1], sys.argv[2]
with open(cfg_path) as f:
    content = f.read()
marker = "/* That's all, stop editing"
if marker in content:
    content = content.replace(marker, patch.strip() + "\n\n" + marker, 1)
else:
    content = content.rstrip() + "\n" + patch.strip() + "\n"
with open(cfg_path, "w") as f:
    f.write(content)
PYEOF
            add "wp-config.php (patched)"
        fi
    fi
}

# ── mu-plugins dev loader ──────────────────────────────────────────────────────
setup_mu_plugins() {
    ensure_dir "$MU_DEV"

    local loader="$MU_PLUGINS/load-mu-dev.php"
    if [[ -f "$loader" ]]; then
        ok "mu-plugins/load-mu-dev.php"
        return
    fi

    write_file "$loader" '<?php
/*
 Plugin Name: Bain Design Dev Plugins
 Description: Loader for local-only dev tools. Paths in mu-dev/ — enable by uncommenting.
*/

// require WPMU_PLUGIN_DIR . '"'"'/mu-dev/debug-bar/debug-bar.php'"'"';
// require WPMU_PLUGIN_DIR . '"'"'/mu-dev/query-monitor/query-monitor.php'"'"';
// require WPMU_PLUGIN_DIR . '"'"'/mu-dev/wordpress-importer/wordpress-importer.php'"'"';
'
}

# ── .vscode ────────────────────────────────────────────────────────────────────
setup_vscode() {
    ensure_dir "$VSCODE_DIR"

    local launch="$VSCODE_DIR/launch.json"
    if [[ ! -f "$launch" ]]; then
        write_file "$launch" '{
   "version": "0.2.0",
   "configurations": [
      {
         "name": "VVV Listen for Xdebug",
         "type": "php",
         "request": "launch",
         "port": 9003,
         "pathMappings": {
            "/srv/www/'"$SLUG"'/": "${workspaceFolder}"
         }
      },
      {
         "name": "Listen for Xdebug",
         "type": "php",
         "request": "launch",
         "port": 9003
      },
      {
         "name": "Launch currently open script",
         "type": "php",
         "request": "launch",
         "program": "${file}",
         "cwd": "${fileDirname}",
         "port": 0,
         "runtimeArgs": ["-dxdebug.start_with_request=yes"],
         "env": {
            "XDEBUG_MODE": "debug,develop",
            "XDEBUG_CONFIG": "client_port=${port}"
         }
      }
   ]
}'
    else
        ok ".vscode/launch.json"
    fi

    local settings="$VSCODE_DIR/settings.json"
    if [[ ! -f "$settings" ]]; then
        write_file "$settings" '{
   "editor.detectIndentation": false,
   "editor.tabSize": 4,
   "editor.insertSpaces": true,
   "php.suggest.basic": false,
   "files.associations": {
      "*.php": "php"
   },
   "files.exclude": {
      "**/node_modules": true,
      "**/vendor": true,
      "**/.git": true,
      "**/.DS_Store": true
   },
   "search.exclude": {
      "**/import": true,
      "**/export": true,
      "**/release": true
   }
}'
    else
        ok ".vscode/settings.json"
    fi
}

# ── VSCode workspace ───────────────────────────────────────────────────────────
setup_workspace() {
    # Try to detect theme name from themes dir
    local theme_dir
    theme_dir=$(find "$WP_ROOT/wp-content/themes" -maxdepth 1 -mindepth 1 -type d \
        ! -name "twenty*" 2>/dev/null | head -1)
    local theme_name="${theme_dir:+themes/$(basename "$theme_dir")}"

    # Check for any existing workspace file before creating one
    local existing_ws
    existing_ws=$(find "$PROJECT_ROOT" -maxdepth 1 -name "*.code-workspace" 2>/dev/null | head -1)
    if [[ -n "$existing_ws" ]]; then
        ok "$(basename "$existing_ws")"
        return
    fi
    local ws_file="$PROJECT_ROOT/$SLUG.code-workspace"

    local folders=''
    if [[ -n "$theme_name" ]]; then
        folders+='{
         "name": "Theme",
         "path": "public_html/wp-content/'"$theme_name"'"
      },'
    fi
    folders+='{
         "name": "Root",
         "path": "."
      }'

    write_file "$ws_file" '{
   "folders": [
      '"$folders"'
   ],
   "settings": {
      "editor.tabSize": 4
   }
}'
}

# ── wp-cli.yml ─────────────────────────────────────────────────────────────────
setup_wpcli() {
    local yml="$PROJECT_ROOT/wp-cli.yml"
    if [[ -f "$yml" ]]; then
        ok "wp-cli.yml"
        return
    fi
    write_file "$yml" "# auto-generated file
path: \"/srv/www/$SLUG/public_html\"
\"@vvv\":
  ssh: vagrant
  path: /srv/www/$SLUG/public_html
\"@$SLUG\":
  ssh: vagrant
  path: /srv/www/$SLUG/public_html
"
}

# ── Deploy config template ─────────────────────────────────────────────────────
setup_scripts() {
    ensure_dir "$PROJECT_ROOT/scripts"
    ensure_dir "$PROJECT_ROOT/log"
    ensure_dir "$PROJECT_ROOT/qa"
    ensure_dir "$PROJECT_ROOT/release"
    ensure_dir "$PROJECT_ROOT/import"

    local cfg_example="$PROJECT_ROOT/scripts/deploy.config.example.sh"
    if [[ -f "$cfg_example" ]]; then
        ok "scripts/deploy.config.example.sh"
        return
    fi
    write_file "$cfg_example" '# -----------------------------
# Project-specific configuration — '"$SLUG"'
# -----------------------------

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOCAL_WP_CONTENT="$SCRIPT_DIR/../public_html/wp-content"

# VVV (local MySQL lives here)
VVV_DIR="FIXME_PATH_TO_VVV_VAGRANTFILE_DIR"
VVV_WP_PATH="/srv/www/'"$SLUG"'/public_html"
VVV_SHARED_DIR="/srv/www/'"$SLUG"'"

# Cloudways staging
REMOTE_USER="FIXME_SSH_USER"
REMOTE_HOST="FIXME_SSH_HOST"
REMOTE_WP_CONTENT="FIXME_REMOTE_WP_CONTENT"
REMOTE_WP_ROOT="${REMOTE_WP_CONTENT%/wp-content}"
STAGING_URL="FIXME_STAGING_URL"
LOCAL_URL="'"$SLUG"'.test"

# Production
PROD_USER="FIXME_SSH_USER"
PROD_HOST="FIXME_SSH_HOST"
PROD_WP_CONTENT="FIXME_PROD_WP_CONTENT"
PROD_WP_ROOT="${PROD_WP_CONTENT%/wp-content}"
PROD_URL="FIXME_PROD_DOMAIN"
PROD_URL_HTTPS="https://FIXME_PROD_DOMAIN"

RSYNC_EXCLUDES=(
    --exclude='"'"'.git*'"'"'
    --exclude='"'"'node_modules/'"'"'
    --exclude='"'"'*.map'"'"'
    --exclude='"'"'.DS_Store'"'"'
    --exclude='"'"'cache/'"'"'
    --exclude='"'"'debug.log'"'"'
)
'
}

# ── Main ───────────────────────────────────────────────────────────────────────
echo ""
echo "WP Project Setup — $SLUG${DRY_RUN:+ [DRY RUN]}"
echo "Root: $PROJECT_ROOT"
echo ""

echo "── wp-config.php ─"
patch_wp_config

echo ""
echo "── mu-plugins ─"
setup_mu_plugins

echo ""
echo "── .vscode ─"
setup_vscode

echo ""
echo "── workspace ─"
setup_workspace

echo ""
echo "── wp-cli.yml ─"
setup_wpcli

echo ""
echo "── scripts & dirs ─"
setup_scripts

echo ""
echo "Done."
