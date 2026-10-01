"""Scheduled-job health for the Ops tab: crontab entries vs. their log files."""
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

OPS_TREE = Path('/home/bain/ops/bain-studio')
GRACE = timedelta(minutes=10)
LOOKBACK_DAYS = 8
SKIP_RE = re.compile(r'claude -p "ok"')


def _field(spec, lo, hi):
    out = set()
    for part in spec.split(','):
        step = 1
        if '/' in part:
            part, s = part.split('/')
            step = int(s)
        if part == '*':
            a, b = lo, hi
        elif '-' in part:
            a, b = map(int, part.split('-'))
        else:
            a = int(part)
            b = hi if step != 1 else a
        out.update(range(a, b + 1, step))
    return out


def _matches(fields, t):
    mins, hrs, dom, mon, dow = fields
    return (t.minute in mins and t.hour in hrs and t.month in mon
            and t.day in dom and ((t.weekday() + 1) % 7) in dow)


def last_fire(schedule, now):
    """Most recent datetime <= now at which a 5-field cron schedule fires."""
    m, h, d, mo, w = schedule.split()
    fields = (_field(m, 0, 59), _field(h, 0, 23), _field(d, 1, 31),
              _field(mo, 1, 12), {x % 7 for x in _field(w, 0, 7)})
    t = now.replace(second=0, microsecond=0)
    for _ in range(LOOKBACK_DAYS * 24 * 60):
        if _matches(fields, t):
            return t
        t -= timedelta(minutes=1)
    return None


def _name(cmd):
    m = re.search(r'([\w.-]+)\.(?:py|sh)\b', cmd)
    if not m:
        return cmd.split()[0]
    if 'upwork-proposals' in cmd:
        return 'upwork/' + m.group(1)
    return m.group(1)


def _log_path(cmd):
    m = re.search(r'>>\s*(\S+)', cmd)
    if not m:
        return None
    p = os.path.expandvars(m.group(1))
    if os.path.isabs(p):
        return Path(p)
    cd = re.search(r'cd\s+(\S+)', cmd)
    return Path(os.path.expandvars(cd.group(1))) / p if cd else None


def _last_line(path):
    try:
        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 600))
            lines = f.read().decode('utf-8', 'replace').strip().splitlines()
        return lines[-1][:200] if lines else ''
    except OSError:
        return ''


def jobs(now=None):
    now = now or datetime.now()
    raw = subprocess.run(['crontab', '-l'], capture_output=True, text=True).stdout
    result = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or re.match(r'^[A-Z_]+=', line):
            continue
        parts = line.split(None, 5)
        if len(parts) < 6 or SKIP_RE.search(parts[5]):
            continue
        schedule, cmd = ' '.join(parts[:5]), parts[5]
        log = _log_path(cmd)
        expected = last_fire(schedule, now)
        ran = None
        if log and log.exists():
            ran = datetime.fromtimestamp(log.stat().st_mtime)
        if expected is None:
            status = 'unknown'
        elif ran is None:
            status = 'no-log'
        elif ran >= expected - GRACE:
            status = 'ok'
        else:
            status = 'missed'
        result.append({
            'name': _name(cmd),
            'schedule': schedule,
            'expected': expected.isoformat(timespec='minutes') if expected else None,
            'last_activity': ran.isoformat(timespec='minutes') if ran else None,
            'status': status,
            'last_line': _last_line(log) if log else '',
            'log': str(log) if log else None,
        })
    order = {'missed': 0, 'no-log': 1, 'unknown': 2, 'ok': 3}
    result.sort(key=lambda j: (order[j['status']], j['name']))
    return result


def _git(*args):
    r = subprocess.run(['git', '-C', str(OPS_TREE), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def summary():
    now = datetime.now()
    up = subprocess.run(['uptime', '-s'], capture_output=True, text=True).stdout.strip()
    cron = subprocess.run(['systemctl', 'is-active', 'cron'], capture_output=True, text=True).stdout.strip()
    return {
        'now': now.isoformat(timespec='minutes'),
        'booted': up[:16].replace(' ', 'T'),
        'cron': cron,
        'ops_tag': _git('describe', '--tags', '--exact-match'),
        'ops_head': _git('rev-parse', '--short', 'HEAD'),
        'jobs': jobs(now),
    }
