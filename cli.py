#!/usr/bin/env python3
"""
ac — Unified CLI for Agents Company (三省七部)

Usage:
  ac dashboard [--port PORT]         Start dashboard server
  ac sync [--interval SEC]           Start background sync loop
  ac update                          Pull latest and reinstall
  ac task list [--filter F]          List tasks
  ac task create TITLE --org ORG     Create a task
  ac task state ID STATE [REMARK]    Update task state
  ac task done ID [SUMMARY]          Mark task as done
  ac skill list [AGENT]              List skills
  ac skill add AGENT -n NAME -s URL  Add remote skill
  ac skill remove AGENT NAME         Remove skill
  ac agent status [AGENT]            Show agent status
  ac agent wake AGENT [MSG]          Wake an agent
  ac channel list                    List channels
  ac channel add --type T -n N -u U  Add channel
  ac channel remove ID               Remove channel
  ac channel test ID                 Test channel webhook
  ac config get [KEY]                Get config value
  ac config set KEY VALUE            Set config value
  ac login [--email E]               Login
  ac logout                          Logout
  ac whoami                          Show current user
  ac setup detect                    Detect OpenClaw installation
  ac setup import [ITEMS...]         Import from OpenClaw
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

# ── Config & Auth Paths ──

_CONFIG_DIR = pathlib.Path.home() / '.config' / 'ac'
_CONFIG_FILE = _CONFIG_DIR / 'config.json'
_AUTH_FILE = _CONFIG_DIR / 'auth.json'


def _ensure_config_dir():
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    try:
        return json.loads(_CONFIG_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(cfg: dict):
    _ensure_config_dir()
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
    os.chmod(_CONFIG_FILE, 0o600)


def load_auth() -> dict:
    try:
        return json.loads(_AUTH_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_auth(token: str, user: dict):
    _ensure_config_dir()
    _AUTH_FILE.write_text(json.dumps({'token': token, 'user': user}, indent=2, ensure_ascii=False))
    os.chmod(_AUTH_FILE, 0o600)


def clear_auth():
    try:
        _AUTH_FILE.unlink()
    except FileNotFoundError:
        pass


# ── Repo Discovery ──

def find_repo_dir() -> pathlib.Path:
    cfg = load_config()
    if cfg.get('repo_dir'):
        p = pathlib.Path(cfg['repo_dir'])
        if p.exists():
            return p

    env = os.environ.get('AC_REPO_DIR', '')
    if env:
        p = pathlib.Path(env)
        if p.exists():
            return p

    candidates = [
        pathlib.Path.home() / 'agents_company_for_happycapy',
    ]
    for c in candidates:
        if (c / 'dashboard' / 'server.py').exists():
            return c

    # Try current directory
    cwd = pathlib.Path.cwd()
    if (cwd / 'dashboard' / 'server.py').exists():
        return cwd

    print('Error: Project directory not found. Set with: ac config set repo_dir /path/to/project')
    sys.exit(1)


# ── API Client ──

def api_base() -> str:
    cfg = load_config()
    return cfg.get('api_base', 'http://127.0.0.1:7891')


def api_call(endpoint: str, method: str = 'GET', data: dict | None = None) -> dict:
    url = f'{api_base()}{endpoint}'
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    auth = load_auth()
    if auth.get('token'):
        headers['Authorization'] = f'Bearer {auth["token"]}'

    body = json.dumps(data, ensure_ascii=False).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read())
            return err_body
        except Exception:
            return {'ok': False, 'error': f'HTTP {e.code}: {e.reason}'}
    except urllib.error.URLError as e:
        return {'ok': False, 'error': f'Connection failed: {e.reason}. Is the dashboard running?'}
    except Exception as e:
        return {'ok': False, 'error': str(e)}


def check_ok(result: dict):
    if not result.get('ok'):
        err = result.get('error', result.get('message', 'Unknown error'))
        print(f'Error: {err}')
        sys.exit(1)


# ── Commands: Dashboard / Sync / Update ──

def cmd_dashboard(args):
    repo = find_repo_dir()
    cmd = [sys.executable, str(repo / 'dashboard' / 'server.py')]
    if args.port:
        cmd += ['--port', str(args.port)]
    if args.host:
        cmd += ['--host', args.host]
    os.execv(sys.executable, cmd)


def cmd_sync(args):
    repo = find_repo_dir()
    script = repo / 'scripts' / 'run_loop.sh'
    cmd = ['bash', str(script)]
    if args.interval:
        cmd.append(str(args.interval))
    os.execvp('bash', cmd)


def cmd_update(_args):
    repo = find_repo_dir()
    os.chdir(repo)
    subprocess.run(['git', 'pull', '--ff-only', 'origin', 'main'], check=False)
    subprocess.run(['bash', 'install.sh'], check=False)


# ── Commands: Task ──

def cmd_task_list(args):
    result = api_call('/api/live-status')
    if 'error' in result and not result.get('tasks'):
        check_ok(result)
    tasks = result.get('tasks', [])

    f = getattr(args, 'filter', 'all')
    if f == 'active':
        tasks = [t for t in tasks if not t.get('archived') and t.get('state') not in ('Done', 'Cancelled')]
    elif f == 'archived':
        tasks = [t for t in tasks if t.get('archived') or t.get('state') in ('Done', 'Cancelled')]

    if not tasks:
        print('No tasks found.')
        return

    print(f'{"ID":<24} {"State":<12} {"Org":<6} {"Title"}')
    print('-' * 70)
    for t in tasks:
        title = (t.get('title') or '')[:40]
        print(f'{t.get("id", "?"):<24} {t.get("state", "?"):<12} {t.get("org", "?"):<6} {title}')
    print(f'\nTotal: {len(tasks)} tasks')


def cmd_task_create(args):
    result = api_call('/api/create-task', 'POST', {
        'title': args.title,
        'org': args.org,
        'priority': args.priority or 'normal',
    })
    check_ok(result)
    tid = result.get('taskId', '?')
    print(f'Task created: {tid}')


def cmd_task_state(args):
    result = api_call('/api/advance-state', 'POST', {
        'taskId': args.task_id,
        'comment': args.remark or '',
    })
    check_ok(result)
    print(f'Task {args.task_id} state updated.')


def cmd_task_done(args):
    result = api_call('/api/task-action', 'POST', {
        'taskId': args.task_id,
        'action': 'done',
        'reason': args.summary or '',
    })
    check_ok(result)
    print(f'Task {args.task_id} marked as done.')


# ── Commands: Skill ──

def cmd_skill_list(args):
    result = api_call('/api/remote-skills-list')
    check_ok(result)
    skills = result.get('remoteSkills', [])
    if args.agent:
        skills = [s for s in skills if s.get('agentId') == args.agent]

    if not skills:
        print('No remote skills found.')
        return

    print(f'{"Agent":<14} {"Skill":<24} {"Status":<10} {"Source URL"}')
    print('-' * 80)
    for s in skills:
        url = (s.get('sourceUrl') or '')[:30]
        print(f'{s.get("agentId", "?"):<14} {s.get("skillName", "?"):<24} {s.get("status", "?"):<10} {url}')
    print(f'\nTotal: {len(skills)} skills')


def cmd_skill_add(args):
    result = api_call('/api/add-remote-skill', 'POST', {
        'agentId': args.agent,
        'skillName': args.name,
        'sourceUrl': args.source,
        'description': args.description or '',
    })
    check_ok(result)
    print(f'Skill {args.name} added to {args.agent}.')


def cmd_skill_remove(args):
    result = api_call('/api/remove-remote-skill', 'POST', {
        'agentId': args.agent,
        'skillName': args.name,
    })
    check_ok(result)
    print(f'Skill {args.name} removed from {args.agent}.')


# ── Commands: Agent ──

def cmd_agent_status(args):
    result = api_call('/api/agents-status')
    check_ok(result)
    agents = result.get('agents', [])
    if args.agent:
        agents = [a for a in agents if a.get('id') == args.agent]

    if not agents:
        print('No agents found.')
        return

    gw = result.get('gateway', {})
    if gw:
        status = 'online' if gw.get('alive') else 'offline'
        print(f'Gateway: {status}')
        print()

    print(f'{"ID":<14} {"Name":<16} {"Status":<12} {"Role"}')
    print('-' * 60)
    for a in agents:
        print(f'{a.get("id", "?"):<14} {a.get("label", "?"):<16} {a.get("statusLabel", "?"):<12} {a.get("role", "")}')


def cmd_agent_wake(args):
    result = api_call('/api/agent-wake', 'POST', {
        'agentId': args.agent,
        'message': args.message or '',
    })
    check_ok(result)
    print(f'Agent {args.agent} wake signal sent.')


# ── Commands: Channel ──

def cmd_channel_list(_args):
    result = api_call('/api/channels')
    check_ok(result)
    channels = result.get('channels', [])

    if not channels:
        print('No channels configured.')
        return

    dd = result.get('default_dispatch_channel', '')
    dm = result.get('default_morning_channel', '')

    print(f'{"ID":<20} {"Type":<10} {"Name":<20} {"Enabled":<8} {"Default"}')
    print('-' * 70)
    for ch in channels:
        defaults = []
        if ch['id'] == dd:
            defaults.append('dispatch')
        if ch['id'] == dm:
            defaults.append('morning')
        dflt = ', '.join(defaults) if defaults else ''
        enabled = 'yes' if ch.get('enabled') else 'no'
        print(f'{ch["id"]:<20} {ch.get("type", "?"):<10} {ch.get("name", "?"):<20} {enabled:<8} {dflt}')


def cmd_channel_add(args):
    result = api_call('/api/channels', 'POST', {
        'type': args.type,
        'name': args.name,
        'webhook_url': args.url,
        'purposes': args.purposes.split(',') if args.purposes else [],
    })
    check_ok(result)
    ch = result.get('channel', {})
    print(f'Channel created: {ch.get("id", "?")} ({ch.get("name", "")})')


def cmd_channel_remove(args):
    result = api_call(f'/api/channels/{args.id}', 'DELETE')
    check_ok(result)
    print(f'Channel {args.id} removed.')


def cmd_channel_test(args):
    result = api_call(f'/api/channels/{args.id}/test', 'POST', {})
    check_ok(result)
    print(f'Test message sent to channel {args.id}.')


# ── Commands: Config ──

def cmd_config_get(args):
    cfg = load_config()
    if args.key:
        val = cfg.get(args.key)
        if val is None:
            print(f'{args.key}: (not set)')
        else:
            print(f'{args.key}: {val}')
    else:
        if not cfg:
            print('No configuration set. Defaults:')
            print(f'  api_base: {api_base()}')
            print(f'  repo_dir: {find_repo_dir()}')
        else:
            for k, v in cfg.items():
                print(f'{k}: {v}')


def cmd_config_set(args):
    cfg = load_config()
    cfg[args.key] = args.value
    save_config(cfg)
    print(f'{args.key} = {args.value}')


# ── Commands: Auth ──

def cmd_login(args):
    if args.email:
        import getpass
        password = ''
        try:
            password = getpass.getpass('Password (optional, press Enter to skip): ')
        except (EOFError, KeyboardInterrupt):
            print()

        result = api_call('/api/auth/login', 'POST', {
            'email': args.email,
            'name': args.name or args.email.split('@')[0],
            'password': password or '',
        })
        if result.get('ok') and result.get('token'):
            save_auth(result['token'], result.get('user', {}))
            name = result.get('user', {}).get('name', args.email)
            print(f'Logged in as {name}')
        else:
            print(f'Login failed: {result.get("error", "unknown")}')
            sys.exit(1)
        return

    # Try env auto-login
    result = api_call('/api/auth/env-login', 'POST', {})
    if result.get('ok') and result.get('token'):
        save_auth(result['token'], result.get('user', {}))
        name = result.get('user', {}).get('name', '?')
        print(f'Auto-logged in as {name} (HappyCapy environment)')
        return

    # Fallback: prompt for email
    print('No HappyCapy environment detected.')
    print('Use: ac login --email your@email.com')
    print('Or start the dashboard and login via browser: ac dashboard')


def cmd_logout(_args):
    auth = load_auth()
    if auth.get('token'):
        api_call('/api/auth/logout', 'POST', {})
    clear_auth()
    print('Logged out.')


def cmd_whoami(_args):
    auth = load_auth()
    if not auth.get('token'):
        print('Not logged in. Run: ac login')
        sys.exit(1)

    result = api_call('/api/auth/me')
    if result.get('ok') and result.get('user'):
        u = result['user']
        print(f'Name:  {u.get("name", "?")}')
        print(f'Email: {u.get("email", "?")}')
        if u.get('happycapy_id'):
            print(f'HappyCapy ID: {u["happycapy_id"]}')
        if u.get('google_id'):
            print(f'Google: connected')
        print(f'Last login: {u.get("last_login", "N/A")}')
    else:
        print('Session expired or invalid. Run: ac login')
        clear_auth()
        sys.exit(1)


# ── Commands: Setup ──

def cmd_setup_detect(_args):
    result = api_call('/api/openclaw-detect')
    check_ok(result)

    installations = result.get('installations', [])
    if not installations:
        print('No OpenClaw installation found.')
        print(f'Scanned: {", ".join(result.get("scanned_paths", []))}')
        return

    for inst in installations:
        print(f'Found: {inst.get("source", "?")} at {inst.get("path", "?")}')
        agents = inst.get('agents', [])
        print(f'  Agents: {len(agents)}')
        skills = inst.get('skills', [])
        print(f'  Skills: {len(skills)}')
        mem = inst.get('memory_db')
        if mem:
            print(f'  Memory DB: {mem.get("size_fmt", "?")} ({mem.get("status", "?")})')
        print(f'  Auth profiles: {"yes" if inst.get("auth_profiles_found") else "no"}')
        print(f'  Sessions: {inst.get("sessions_count", 0)}')
        print()
        print('  Importable items:')
        for item in inst.get('inheritable_items', []):
            check = 'x' if item.get('default_checked') else ' '
            cat = item.get('category', '')
            warn = ' (caution)' if cat == 'caution' else ' (skip)' if cat == 'skip' else ''
            print(f'    [{check}] {item.get("key", "?")}: {item.get("label", "?")}{warn}')


def cmd_setup_import(args):
    # First detect to find the path
    detect = api_call('/api/openclaw-detect')
    check_ok(detect)

    installations = detect.get('installations', [])
    if not installations:
        print('No OpenClaw installation found. Run: ac setup detect')
        sys.exit(1)

    source_path = installations[0].get('path', '')
    items = args.items if args.items else ['config', 'soul', 'user', 'skills']

    result = api_call('/api/openclaw-import', 'POST', {
        'sourcePath': source_path,
        'items': items,
    })
    check_ok(result)

    imported = result.get('imported', [])
    skipped = result.get('skipped', [])
    errors = result.get('errors', [])

    if imported:
        print('Imported:')
        for item in imported:
            print(f'  + {item.get("key", "?")}: {item.get("detail", "")}')
    if skipped:
        print('Skipped:')
        for item in skipped:
            print(f'  - {item.get("key", "?")}: {item.get("reason", "")}')
    if errors:
        print('Errors:')
        for item in errors:
            print(f'  ! {item.get("key", "?")}: {item.get("error", "")}')


# ── Argument Parser ──

def build_parser():
    parser = argparse.ArgumentParser(
        prog='ac',
        description='Agents Company CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest='command', help='Available commands')

    # dashboard
    p = sub.add_parser('dashboard', help='Start dashboard server')
    p.add_argument('--port', type=int, default=None)
    p.add_argument('--host', default=None)

    # sync
    p = sub.add_parser('sync', help='Start background sync loop')
    p.add_argument('--interval', type=int, default=None)

    # update
    sub.add_parser('update', help='Pull latest and reinstall')

    # task
    task_p = sub.add_parser('task', help='Task management')
    task_sub = task_p.add_subparsers(dest='task_cmd')

    p = task_sub.add_parser('list', help='List tasks')
    p.add_argument('--filter', '-f', choices=['active', 'archived', 'all'], default='all')

    p = task_sub.add_parser('create', help='Create a task')
    p.add_argument('title')
    p.add_argument('--org', required=True)
    p.add_argument('--priority', default='normal')

    p = task_sub.add_parser('state', help='Update task state')
    p.add_argument('task_id')
    p.add_argument('state')
    p.add_argument('remark', nargs='?', default='')

    p = task_sub.add_parser('done', help='Mark task as done')
    p.add_argument('task_id')
    p.add_argument('summary', nargs='?', default='')

    # skill
    skill_p = sub.add_parser('skill', help='Skill management')
    skill_sub = skill_p.add_subparsers(dest='skill_cmd')

    p = skill_sub.add_parser('list', help='List remote skills')
    p.add_argument('agent', nargs='?', default=None)

    p = skill_sub.add_parser('add', help='Add remote skill')
    p.add_argument('agent')
    p.add_argument('--name', '-n', required=True)
    p.add_argument('--source', '-s', required=True)
    p.add_argument('--description', '-d', default='')

    p = skill_sub.add_parser('remove', help='Remove remote skill')
    p.add_argument('agent')
    p.add_argument('name')

    # agent
    agent_p = sub.add_parser('agent', help='Agent management')
    agent_sub = agent_p.add_subparsers(dest='agent_cmd')

    p = agent_sub.add_parser('status', help='Show agent status')
    p.add_argument('agent', nargs='?', default=None)

    p = agent_sub.add_parser('wake', help='Wake an agent')
    p.add_argument('agent')
    p.add_argument('message', nargs='?', default='')

    # channel
    ch_p = sub.add_parser('channel', help='Channel management')
    ch_sub = ch_p.add_subparsers(dest='channel_cmd')

    ch_sub.add_parser('list', help='List channels')

    p = ch_sub.add_parser('add', help='Add a channel')
    p.add_argument('--type', '-t', required=True)
    p.add_argument('--name', '-n', required=True)
    p.add_argument('--url', '-u', required=True)
    p.add_argument('--purposes', '-p', default='')

    p = ch_sub.add_parser('remove', help='Remove a channel')
    p.add_argument('id')

    p = ch_sub.add_parser('test', help='Test channel webhook')
    p.add_argument('id')

    # config
    cfg_p = sub.add_parser('config', help='Configuration')
    cfg_sub = cfg_p.add_subparsers(dest='config_cmd')

    p = cfg_sub.add_parser('get', help='Get config value')
    p.add_argument('key', nargs='?', default=None)

    p = cfg_sub.add_parser('set', help='Set config value')
    p.add_argument('key')
    p.add_argument('value')

    # login
    p = sub.add_parser('login', help='Login to dashboard')
    p.add_argument('--email', '-e', default=None)
    p.add_argument('--name', '-n', default=None)

    # logout
    sub.add_parser('logout', help='Logout')

    # whoami
    sub.add_parser('whoami', help='Show current user')

    # setup
    setup_p = sub.add_parser('setup', help='System setup')
    setup_sub = setup_p.add_subparsers(dest='setup_cmd')

    setup_sub.add_parser('detect', help='Detect OpenClaw installation')

    p = setup_sub.add_parser('import', help='Import from OpenClaw')
    p.add_argument('items', nargs='*', default=[])

    return parser


# ── Main Dispatch ──

_TASK_DISPATCH = {
    'list': cmd_task_list,
    'create': cmd_task_create,
    'state': cmd_task_state,
    'done': cmd_task_done,
}

_SKILL_DISPATCH = {
    'list': cmd_skill_list,
    'add': cmd_skill_add,
    'remove': cmd_skill_remove,
}

_AGENT_DISPATCH = {
    'status': cmd_agent_status,
    'wake': cmd_agent_wake,
}

_CHANNEL_DISPATCH = {
    'list': cmd_channel_list,
    'add': cmd_channel_add,
    'remove': cmd_channel_remove,
    'test': cmd_channel_test,
}

_CONFIG_DISPATCH = {
    'get': cmd_config_get,
    'set': cmd_config_set,
}

_SETUP_DISPATCH = {
    'detect': cmd_setup_detect,
    'import': cmd_setup_import,
}


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    cmd = args.command

    if cmd == 'dashboard':
        cmd_dashboard(args)
    elif cmd == 'sync':
        cmd_sync(args)
    elif cmd == 'update':
        cmd_update(args)
    elif cmd == 'login':
        cmd_login(args)
    elif cmd == 'logout':
        cmd_logout(args)
    elif cmd == 'whoami':
        cmd_whoami(args)
    elif cmd == 'task':
        fn = _TASK_DISPATCH.get(args.task_cmd)
        if fn:
            fn(args)
        else:
            parser.parse_args(['task', '--help'])
    elif cmd == 'skill':
        fn = _SKILL_DISPATCH.get(args.skill_cmd)
        if fn:
            fn(args)
        else:
            parser.parse_args(['skill', '--help'])
    elif cmd == 'agent':
        fn = _AGENT_DISPATCH.get(args.agent_cmd)
        if fn:
            fn(args)
        else:
            parser.parse_args(['agent', '--help'])
    elif cmd == 'channel':
        fn = _CHANNEL_DISPATCH.get(args.channel_cmd)
        if fn:
            fn(args)
        else:
            parser.parse_args(['channel', '--help'])
    elif cmd == 'config':
        fn = _CONFIG_DISPATCH.get(args.config_cmd)
        if fn:
            fn(args)
        else:
            parser.parse_args(['config', '--help'])
    elif cmd == 'setup':
        fn = _SETUP_DISPATCH.get(args.setup_cmd)
        if fn:
            fn(args)
        else:
            parser.parse_args(['setup', '--help'])
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
