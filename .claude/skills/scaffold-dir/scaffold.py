#!/usr/bin/env python3
"""Scaffold a new project directory with git repo and optionally WordPress structure."""

import os
import sys
import argparse
import json
import re
import subprocess
from pathlib import Path


def scaffold_project(path, name=None, is_wordpress=False, is_ddev=False,
                     plugin_names=None, theme_names=None, mu_plugin_names=None,
                     php_version='8.2', database='mariadb:11.8', wp_version=None):
    """
    Create a new project directory with git repo and optional WordPress structure.

    Args:
        path: Absolute path for the new project directory
        name: Project name (defaults to path basename)
        is_wordpress: Create WordPress-aware structure
        is_ddev: Set up DDEV configuration
        plugin_names: List of custom plugin names to allowlist
        theme_names: List of custom theme names to allowlist
        mu_plugin_names: List of custom mu-plugin names to allowlist
        php_version: PHP version for the DDEV config
        database: Database as TYPE:VERSION for the DDEV config
        wp_version: WordPress core version to pin, or 'latest'. None downloads nothing.

    Returns:
        dict with status and messages
    """
    plugin_names = plugin_names or []
    theme_names = theme_names or []
    mu_plugin_names = mu_plugin_names or []

    path = Path(path)
    name = name or path.name

    # A client's host dictates the stack. DDEV does not validate these at config
    # time - it writes whatever it is given and the container fails later - so
    # check the shape here, while the error is still cheap.
    if not re.fullmatch(r'[a-z]+:[0-9][0-9.]*', database):
        return {
            'status': 'error',
            'message': f"--db must be TYPE:VERSION, e.g. mysql:8.0 or mariadb:10.4 (got '{database}')."
        }
    if not re.fullmatch(r'[0-9]+\.[0-9]+', php_version):
        return {
            'status': 'error',
            'message': f"--php must be MAJOR.MINOR, e.g. 8.2 (got '{php_version}')."
        }
    if wp_version and not re.fullmatch(r'latest|[0-9]+\.[0-9]+(\.[0-9]+)?', wp_version):
        return {
            'status': 'error',
            'message': f"--wp-version must be latest or X.Y[.Z], e.g. 6.4.3 (got '{wp_version}')."
        }

    report = []

    # 1. Validate
    if path.exists() and any(path.iterdir()):
        return {
            'status': 'error',
            'message': f"Directory {path} already exists and is non-empty — aborting to avoid overwriting."
        }

    if not path.parent.exists():
        return {
            'status': 'error',
            'message': f"Parent directory {path.parent} does not exist. Create it first."
        }

    # 2. Create directory
    path.mkdir(parents=True, exist_ok=True)
    report.append("✓ directory created")

    # 3. Git init. git 2.25 has no `init -b`, so HEAD is repointed directly -
    # this works on every version and avoids ever creating `master`.
    subprocess.run(['git', 'init'], cwd=path, check=True, capture_output=True)
    subprocess.run(['git', 'symbolic-ref', 'HEAD', 'refs/heads/main'],
                   cwd=path, check=True, capture_output=True)
    report.append("✓ git init (on main)")

    # 4. Create standard directory structure.
    #
    # Every directory gets a .gitkeep. Without one, git tracks nothing empty and
    # a clone arrives with none of the layout - which is the whole point of this
    # script. The working folders are ignored by content (`bin/*`) rather than
    # wholesale (`bin/`), so the .gitkeep inside them survives.
    (path / '.claude').mkdir(exist_ok=True)
    (path / 'qa').mkdir(exist_ok=True)
    created = ['qa']

    if is_wordpress:
        created += ['bin', 'export', 'import', 'scripts', 'context', 'docs',
                    'backups', 'public_html']
    elif is_ddev:
        # A DDEV config points docroot at public_html, so the directory has to
        # exist or `ddev start` fails against a missing docroot.
        created += ['public_html']

    for dir_name in created:
        (path / dir_name).mkdir(exist_ok=True)
        (path / dir_name / '.gitkeep').touch()

    report.append(f"✓ directories created ({len(created)}, each with .gitkeep)")

    # 5. Write .gitignore
    if is_wordpress:
        gitignore_content = _create_wp_gitignore(plugin_names, theme_names, mu_plugin_names)
    else:
        gitignore_content = _create_generic_gitignore()

    (path / '.gitignore').write_text(gitignore_content)
    report.append("✓ .gitignore written" + (" (WordPress-aware)" if is_wordpress else ""))

    # 5b. wp-cli.yml and README - WordPress projects only.
    if is_wordpress:
        # Without this, a bare `wp` command runs against the repo root rather
        # than the install.
        (path / 'wp-cli.yml').write_text("path: public_html\n")
        (path / 'README.md').write_text(f"# {name}\n")

        # The .gitignore deliberately excludes plugins/ and themes/, which loses
        # the record of what is installed. wp-project-layout.md requires a
        # committed manifest instead; seed it so it is never simply forgotten.
        (path / 'docs' / 'installed-versions.md').write_text(
            f"# {name} — installed versions\n\n"
            "Regenerate after any install, update or removal. The .gitignore excludes\n"
            "`plugins/` and `themes/`, so this file is the only record of what runs here.\n\n"
            "```bash\n"
            "ddev wp core version\n"
            "ddev wp plugin list --fields=name,status,version,update_version\n"
            "ddev wp theme list  --fields=name,status,version,update_version\n"
            "```\n\n"
            "## Target stack\n\n"
            f"- PHP: {php_version}\n"
            f"- Database: {database}\n"
            "- WordPress: " + (wp_version or "_record the client's version here_") + "\n\n"
            "## WordPress core\n\n_not yet installed_\n\n"
            "## Plugins\n\n_not yet installed_\n\n"
            "## Themes\n\n_not yet installed_\n"
        )
        report.append("✓ wp-cli.yml + README.md + docs/installed-versions.md written")

        # wp-content skeleton. Core is downloaded with --skip-content so the
        # bundled themes and plugins do not arrive, which means these have to be
        # created here. The named custom dirs are allowlisted in .gitignore, so a
        # .gitkeep in them is tracked and the clone carries the full tree.
        wp_content = path / 'public_html' / 'wp-content'
        for sub in ('plugins', 'themes', 'mu-plugins'):
            (wp_content / sub).mkdir(parents=True, exist_ok=True)
        for sub, names in (('plugins', plugin_names), ('themes', theme_names)):
            for n in names:
                (wp_content / sub / n).mkdir(parents=True, exist_ok=True)
                (wp_content / sub / n / '.gitkeep').touch()
        report.append("✓ wp-content skeleton created")

    # 5c. WordPress core, pinned. Only on request - most client projects import
    # the client's own files rather than a clean core.
    if wp_version:
        have_wp = subprocess.run(['which', 'wp'], capture_output=True).returncode == 0
        if not have_wp:
            report.append(f"⊘ wp-cli not found — WordPress {wp_version} NOT downloaded")
        else:
            cmd = ['wp', 'core', 'download', '--path=public_html', '--skip-content']
            if wp_version != 'latest':
                cmd.append(f'--version={wp_version}')
            done = subprocess.run(cmd, cwd=path, capture_output=True, text=True)
            if done.returncode == 0:
                report.append(f"✓ WordPress {wp_version} downloaded (--skip-content)")
            else:
                err = (done.stderr or done.stdout).strip().splitlines()
                report.append(f"⚠ WordPress {wp_version} download failed: "
                              f"{err[-1] if err else 'unknown error'}")

        # A global or system gitignore can silently swallow a file we just
        # wrote - wp-cli.yml is a VVV-era entry in many setups. Say so rather
        # than force-adding, which would override a deliberate user setting.
        for fname in ('wp-cli.yml', 'README.md'):
            ignored = subprocess.run(['git', 'check-ignore', '-q', fname],
                                     cwd=path, capture_output=True).returncode == 0
            if ignored:
                src = subprocess.run(['git', 'check-ignore', '-v', fname],
                                     cwd=path, capture_output=True, text=True).stdout.strip()
                report.append(f"⚠ {fname} is gitignored and will NOT be tracked — {src}")

    # 6. DDEV configuration
    ddev_report = None
    if is_wordpress or is_ddev or (path / '.ddev').exists():
        ddev_report = _setup_ddev_config(path, name, php_version, is_wordpress, database)
        report.append(f"✓ {ddev_report}")

    # 7. Initial commit
    subprocess.run(['git', 'add', '.'], cwd=path, check=True, capture_output=True)
    commit_msg = f"init: scaffold {name}" + (" (WordPress)" if is_wordpress else "")
    subprocess.run(['git', 'commit', '-m', commit_msg], cwd=path, check=True, capture_output=True)
    report.append("✓ initial commit")

    # 7b. Git flow layout: main is released code, develop is where work happens.
    # Studio convention, so the scaffold should not leave it to be done by hand.
    subprocess.run(['git', 'checkout', '-b', 'develop'], cwd=path, check=True, capture_output=True)
    report.append("✓ develop branched from main (git flow)")

    # 8. Shutter profile
    shutter_available = subprocess.run(['which', 'shutter-profile'],
                                     capture_output=True).returncode == 0
    if shutter_available:
        try:
            subprocess.run(['shutter-profile', 'create', name, str(path / 'qa' / 'qa-inbox')],
                         check=True, capture_output=True)
            report.append(f"✓ shutter profile '{name}' created")
        except subprocess.CalledProcessError:
            report.append("⚠ shutter profile creation failed (continuing)")
    else:
        report.append("⊘ shutter-profile not found (skipped)")

    return {
        'status': 'success',
        'path': str(path),
        'report': report
    }


def _create_wp_gitignore(plugin_names, theme_names, mu_plugin_names):
    """Create a WordPress-aware .gitignore with three-tier pattern."""
    lines = [
        "# Environment and credentials",
        ".env",
        ".env.local",
        "wp-config.php",
        "wp-config-ddev.php",
        "",
        "# Database, archives, logs",
        "*.sql",
        "*.zip",
        "*.wpress",
        "*.log",
        "",
        "# IDE and OS",
        ".DS_Store",
        ".vscode/",
        "*.swp",
        "__pycache__/",
        "*.pyc",
        "",
        "# Node (if used for builds)",
        "node_modules/",
        "npm-debug.log",
        "",
        "# Ignore everything in the \"public_html\" directory except the \"wp-content\"",
        "# directory.",
        "public_html/*",
        "!public_html/.gitkeep",
        "!public_html/wp-content/",
        "",
        "# Ignore everything in the \"wp-content\" directory, except the \"plugins\",",
        "# \"themes\" and \"mu-plugins\" directories.",
        "public_html/wp-content/*",
        "!public_html/wp-content/plugins/",
        "!public_html/wp-content/themes/",
        "!public_html/wp-content/mu-plugins/",
        "",
        "# Ignore everything in the \"plugins\" directory, except the plugins we maintain.",
        "public_html/wp-content/plugins/*",
    ]

    # Add plugin allowlists
    if plugin_names:
        for plugin in plugin_names:
            lines.append(f"!public_html/wp-content/plugins/{plugin}/")
    else:
        lines.append("# !public_html/wp-content/plugins/<client>-custom/")

    lines.extend([
        "",
        "# Ignore everything in the \"mu-plugins\" directory, except the mu-plugins we",
        "# maintain.",
        "public_html/wp-content/mu-plugins/*",
    ])

    # Add mu-plugin allowlists
    if mu_plugin_names:
        for mu_plugin in mu_plugin_names:
            lines.append(f"!public_html/wp-content/mu-plugins/{mu_plugin}")
    else:
        lines.append("# !public_html/wp-content/mu-plugins/<client>-fixes.php")

    lines.extend([
        "",
        "# Ignore everything in the \"themes\" directory, except the themes we maintain.",
        "public_html/wp-content/themes/*",
    ])

    # Add theme allowlists
    if theme_names:
        for theme in theme_names:
            lines.append(f"!public_html/wp-content/themes/{theme}/")
    else:
        lines.append("# !public_html/wp-content/themes/<client>-theme/")

    lines.extend([
        "",
        "# Asana and project-internal",
        "asana-mirror.md",
        "asana-ids.json",
        "",
        "# Working folders - contents ignored, the directory itself is kept so",
        "# a clone arrives with the full layout.",
        "bin/*",
        "!bin/.gitkeep",
        "export/*",
        "!export/.gitkeep",
        "import/*",
        "!import/.gitkeep",
        "backups/*",
        "!backups/.gitkeep",
        "qa/*",
        "!qa/.gitkeep",
    ])

    return "\n".join(lines) + "\n"


def _create_generic_gitignore():
    """Create a minimal generic .gitignore."""
    return """.env
.env.local
node_modules/
__pycache__/
*.pyc
.DS_Store
"""


def _setup_ddev_config(path, name, php_version='8.2', is_wordpress=False,
                       database='mariadb:11.8'):
    """Set up DDEV configuration with docroot pointing to public_html."""
    config_path = path / '.ddev' / 'config.yaml'

    if config_path.exists():
        content = config_path.read_text()
        if 'docroot:' in content:
            if 'docroot: public_html' in content:
                return "DDEV config: docroot already set to public_html"
            else:
                return "DDEV config: existing docroot found (manual review recommended)"
        else:
            # Append docroot line
            content = content.rstrip() + "\ndocroot: public_html\n"
            config_path.write_text(content)
            return "DDEV config: docroot set to public_html (added to existing config)"
    else:
        # Create minimal config
        config_path.parent.mkdir(parents=True, exist_ok=True)
        # Spelled out rather than left to DDEV's defaults - unstated values are
        # how configuration drifts between projects.
        db_type, db_version = database.split(':', 1)
        lines = [
            "# .ddev config - generated by scaffold-dir",
            'ddev_version: ">=1.23.0"',
            f"name: {name}",
            "docroot: public_html",
            f'php_version: "{php_version}"',
            "webserver_type: nginx-fpm",
            "database:",
            f"  type: {db_type}",
            f'  version: "{db_version}"',
        ]
        if is_wordpress:
            lines.insert(3, "type: wordpress")
        config_path.write_text("\n".join(lines) + "\n")
        kind = "wordpress, " if is_wordpress else ""
        return (f"DDEV config: created ({kind}php {php_version}, {database}, "
                "docroot public_html)")


def main():
    parser = argparse.ArgumentParser(description='Scaffold a new project directory with git repo.')
    parser.add_argument('path', help='Absolute path for the new project directory')
    parser.add_argument('name', nargs='?', help='Project name (defaults to directory basename)')
    parser.add_argument('--wordpress', action='store_true', help='Create WordPress-aware structure')
    parser.add_argument('--ddev', action='store_true', help='Set up DDEV configuration')
    parser.add_argument('--php', default='8.2',
                        help='PHP version for DDEV config (default: 8.2). Match the client host.')
    parser.add_argument('--wp-version', dest='wp_version', default=None,
                        help="Pin WordPress core: X.Y[.Z] or 'latest'. Downloads core into "
                             "public_html (needs wp-cli). Omit to download nothing.")
    parser.add_argument('--db', default='mariadb:11.8', dest='database',
                        help='Database as TYPE:VERSION (default: mariadb:11.8). '
                             'Match the client host, e.g. mysql:8.0, mysql:5.7, mariadb:10.4.')
    parser.add_argument('--plugin', action='append', dest='plugins', help='Custom plugin name (can be repeated)')
    parser.add_argument('--theme', action='append', dest='themes', help='Custom theme name (can be repeated)')
    parser.add_argument('--mu-plugin', action='append', dest='mu_plugins', help='Custom mu-plugin name (can be repeated)')

    args = parser.parse_args()

    result = scaffold_project(
        path=args.path,
        name=args.name,
        is_wordpress=args.wordpress,
        is_ddev=args.ddev,
        plugin_names=args.plugins or [],
        theme_names=args.themes or [],
        mu_plugin_names=args.mu_plugins or [],
        php_version=args.php,
        database=args.database,
        wp_version=args.wp_version
    )

    if result['status'] == 'error':
        print(f"Error: {result['message']}", file=sys.stderr)
        sys.exit(1)

    print(f"scaffold-dir: {result['path']}")
    for line in result['report']:
        print(f"  {line}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
