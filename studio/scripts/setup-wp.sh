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
REMOTE_SSH_PORT="22"  # change if the host uses a non-standard port
REMOTE_WP_CONTENT="FIXME_REMOTE_WP_CONTENT"
REMOTE_WP_ROOT="${REMOTE_WP_CONTENT%/wp-content}"
STAGING_URL="FIXME_STAGING_URL"
LOCAL_URL="'"$SLUG"'.test"

# Production
PROD_USER="FIXME_SSH_USER"
PROD_HOST="FIXME_SSH_HOST"
PROD_SSH_PORT="22"  # change if the host uses a non-standard port
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

# ── ACF Local JSON sync ────────────────────────────────────────────────────────
#
# ACF Pro's "Local JSON" does NOT make a field group's JSON file automatically
# take priority over its stored database copy on every request. The DB copy is
# only bypassed once ACF has already resolved that group by its string key
# earlier in the same request; on a fresh request it falls back to the DB. A
# fix shipped only in acf-json/*.json can sit broken in the DB indefinitely
# after deploy. See acf-sync.php's own header comment for the full trace
# through ACF's source, and ~/dev/CLAUDE.md's "WordPress / ACF Pro" section.
setup_acf_sync() {
    local php_target="$PROJECT_ROOT/scripts/acf-sync.php"
    local sh_target="$PROJECT_ROOT/scripts/acf-sync.sh"

    if [[ -f "$php_target" ]]; then
        ok "scripts/acf-sync.php"
    else
        local php_content
        php_content=$(cat <<'PHPEOF'
<?php
/**
 * Syncs ACF Local JSON field groups (and post types/taxonomies, if any) into
 * the database - the same operation as clicking "Sync" in
 * Custom Fields > Field Groups > Sync available, just non-interactive.
 *
 * WHY THIS IS NEEDED: ACF's Local JSON does NOT make JSON take priority over
 * the DB automatically. A field group's location rules (and everything else)
 * are only actually read from JSON once ACF has, at some point in the same
 * request, resolved that group by its string key - which establishes an
 * alias from the DB's numeric post ID to the JSON version. On a fresh
 * request that alias doesn't exist yet, so ACF falls back to whatever is
 * still in the DB. A bug fixed only in the JSON file (e.g. a location rule
 * missing its "value") can sit broken in the DB indefinitely unless synced.
 * See scripts/acf-sync.sh.
 *
 * Deliberately does NOT replicate admin-internal-post-type-list.php's
 * setup_sync() timestamp check ("json modified newer than DB modified").
 * That comparison uses the "modified" field stored INSIDE the JSON file's
 * own content, which only gets bumped when ACF itself saves the file via
 * its export/save mechanism - not when the JSON is hand-edited with a text
 * editor (as a git commit normally would). A hand-edited JSON file can
 * easily have an older internal "modified" stamp than a DB copy that was
 * touched more recently by something else entirely, which would make the
 * timestamp check silently skip a real, needed fix. For a deploy script we
 * always want the DB to end up matching whatever JSON git just shipped, so
 * this imports every JSON-sourced group unconditionally instead.
 *
 * Usage: wp eval-file scripts/acf-sync.php
 */

if (!function_exists('acf_get_internal_post_type_posts')) {
    WP_CLI::error('ACF Pro is not active.');
}

$post_types = ['acf-field-group', 'acf-post-type', 'acf-taxonomy'];
$total_synced = 0;

foreach ($post_types as $post_type) {
    $files = acf_get_local_json_files($post_type);
    if (!$files) {
        continue;
    }

    $all_posts = acf_get_internal_post_type_posts($post_type);
    $to_sync = [];

    foreach ($all_posts as $post) {
        $local = $post['local'] ?? null;
        $private = $post['private'] ?? false;

        if ($private || $local !== 'json') {
            continue;
        }

        $to_sync[$post['key']] = $post;
    }

    if (!$to_sync) {
        WP_CLI::log("{$post_type}: nothing to sync.");
        continue;
    }

    // Prevent the JSON file from being rewritten as a side effect of import
    // (we're importing FROM json TO db, not exporting).
    acf_update_setting('json', false);

    foreach ($to_sync as $key => $post) {
        if (!isset($files[$key])) {
            WP_CLI::warning("{$post_type} {$key}: sync needed but no JSON file found, skipping.");
            continue;
        }

        $local_post = json_decode(file_get_contents($files[$key]), true);
        $local_post['ID'] = $post['ID']; // 0 if new, or the existing DB post ID to update.

        $result = acf_import_internal_post_type($local_post, $post_type);

        WP_CLI::success("{$post_type} synced: {$result['title']} (key: {$key}, ID: {$result['ID']})");
        $total_synced++;
    }

    acf_update_setting('json', true);
}

WP_CLI::log($total_synced ? "Done. {$total_synced} item(s) synced." : 'Done. Nothing needed syncing.');
PHPEOF
)
        write_file "$php_target" "$php_content"$'\n'
    fi

    if [[ -f "$sh_target" ]]; then
        ok "scripts/acf-sync.sh"
    else
        local sh_content
        sh_content=$(cat <<'SHEOF'
#!/usr/bin/env bash
#
# acf-sync.sh — Import ACF Local JSON field groups into the DB for one environment
#
# WHY: ACF's Local JSON does NOT make a field group's JSON file automatically
# take priority over its stored database copy on every request (see
# acf-sync.php's own header for the full explanation). A JSON-only fix can
# sit broken in the DB indefinitely after deploying the file. Run this after
# every deploy to the target environment.
#
# Usage:
#   scripts/acf-sync.sh local
#   scripts/acf-sync.sh staging
#   scripts/acf-sync.sh prod
#
# Reads target-environment values from scripts/deploy.config.sh (copy
# deploy.config.example.sh to deploy.config.sh and fill in the FIXME values
# first - deploy.config.sh is gitignored, project-specific).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV="${1:-}"

if [[ -z "$ENV" || ! "$ENV" =~ ^(local|staging|prod)$ ]]; then
    echo "Usage: $0 {local|staging|prod}"
    exit 1
fi

CONFIG="$SCRIPT_DIR/deploy.config.sh"
if [[ ! -f "$CONFIG" ]]; then
    echo "Error: $CONFIG not found."
    echo "Copy deploy.config.example.sh to deploy.config.sh and fill in the FIXME values first."
    exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG"

PHP_FILE="$SCRIPT_DIR/acf-sync.php"

case "$ENV" in
    local)
        cd "$VVV_DIR"
        vagrant ssh -- "wp --path=$VVV_WP_PATH eval-file $VVV_SHARED_DIR/scripts/acf-sync.php"
        ;;
    staging)
        REMOTE_WP_ROOT="${REMOTE_WP_CONTENT%/wp-content}"
        REMOTE_SSH_PORT="${REMOTE_SSH_PORT:-22}"
        TMP_REMOTE="/tmp/acf-sync-$(date +%s).php"
        scp -P "$REMOTE_SSH_PORT" "$PHP_FILE" "$REMOTE_USER@$REMOTE_HOST:$TMP_REMOTE"
        ssh -p "$REMOTE_SSH_PORT" "$REMOTE_USER@$REMOTE_HOST" "wp --path=$REMOTE_WP_ROOT eval-file $TMP_REMOTE; rm $TMP_REMOTE"
        ;;
    prod)
        PROD_WP_ROOT="${PROD_WP_CONTENT%/wp-content}"
        PROD_SSH_PORT="${PROD_SSH_PORT:-22}"
        TMP_REMOTE="/tmp/acf-sync-$(date +%s).php"
        scp -P "$PROD_SSH_PORT" "$PHP_FILE" "$PROD_USER@$PROD_HOST:$TMP_REMOTE"
        ssh -p "$PROD_SSH_PORT" "$PROD_USER@$PROD_HOST" "wp --path=$PROD_WP_ROOT eval-file $TMP_REMOTE; rm $TMP_REMOTE"
        ;;
esac
SHEOF
)
        write_file "$sh_target" "$sh_content"$'\n'
        chmod +x "$sh_target" 2>/dev/null || true
    fi
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
echo "── ACF sync ─"
setup_acf_sync

echo ""
echo "Done."
