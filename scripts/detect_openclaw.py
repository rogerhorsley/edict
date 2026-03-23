"""
detect_openclaw.py — Detect local OpenClaw/AutoClaw installations
and return structured information for memory inheritance.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone


def _sizeof_fmt(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num) < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} TB"


def _scan_installation(base: Path) -> dict | None:
    """Scan a single OpenClaw/AutoClaw installation directory."""
    if not base.is_dir():
        return None

    config_path = base / "openclaw.json"
    if not config_path.is_file():
        return None

    result = {
        "found": True,
        "path": str(base),
        "config_path": str(config_path),
        "agents": [],
        "workspaces": [],
        "workspace_files": [],
        "skills": [],
        "memory_db": None,
        "auth_profiles_found": False,
        "sessions_count": 0,
        "extensions": [],
    }

    # Parse main config
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        agents_cfg = cfg.get("agents", {})
        agent_list = agents_cfg.get("list", [])
        defaults = agents_cfg.get("defaults", {})
        result["default_model"] = defaults.get("model", {}).get("primary", "")
        for ag in agent_list:
            result["agents"].append({
                "id": ag.get("id", ""),
                "workspace": ag.get("workspace", ""),
            })
    except (json.JSONDecodeError, OSError):
        pass

    # Scan default workspace
    workspace = base / "workspace"
    if workspace.is_dir():
        result["workspaces"].append(str(workspace))
        for fname in ("SOUL.md", "MEMORY.md", "USER.md", "AGENTS.md",
                       "IDENTITY.md", "HEARTBEAT.md", "TOOLS.md"):
            fpath = workspace / fname
            if fpath.is_file():
                try:
                    stat = fpath.stat()
                    result["workspace_files"].append({
                        "name": fname,
                        "path": str(fpath),
                        "size": stat.st_size,
                        "size_fmt": _sizeof_fmt(stat.st_size),
                        "modified": datetime.fromtimestamp(
                            stat.st_mtime, tz=timezone.utc
                        ).isoformat(),
                    })
                except OSError:
                    pass

    # Scan per-agent workspaces
    for item in sorted(base.iterdir()):
        if item.name.startswith("workspace-") and item.is_dir():
            result["workspaces"].append(str(item))

    # Memory database
    mem_db = base / "memory" / "main.sqlite"
    if mem_db.is_file():
        try:
            stat = mem_db.stat()
            chunk_count = 0
            file_count = 0
            try:
                conn = sqlite3.connect(f"file:{mem_db}?mode=ro", uri=True)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM files")
                file_count = cur.fetchone()[0]
                conn.close()
            except (sqlite3.Error, Exception):
                pass
            result["memory_db"] = {
                "path": str(mem_db),
                "size": stat.st_size,
                "size_fmt": _sizeof_fmt(stat.st_size),
                "chunks": chunk_count,
                "files": file_count,
                "status": "populated" if chunk_count > 0 else "empty",
            }
        except OSError:
            pass

    # Auth profiles
    auth_path = base / "agents" / "main" / "agent" / "auth-profiles.json"
    if auth_path.is_file():
        result["auth_profiles_found"] = True
        try:
            with open(auth_path) as f:
                auth_data = json.load(f)
            profiles = auth_data.get("profiles", {})
            result["auth_providers"] = list(profiles.keys())
        except (json.JSONDecodeError, OSError):
            result["auth_providers"] = []

    # Sessions count
    sessions_dir = base / "agents" / "main" / "sessions"
    if sessions_dir.is_dir():
        sessions_file = sessions_dir / "sessions.json"
        if sessions_file.is_file():
            try:
                with open(sessions_file) as f:
                    sess = json.load(f)
                result["sessions_count"] = len(sess)
            except (json.JSONDecodeError, OSError):
                pass

    # Skills
    skills_dir = base / "skills"
    if skills_dir.is_dir():
        for item in sorted(skills_dir.iterdir()):
            if item.is_dir() or item.is_symlink():
                result["skills"].append({
                    "name": item.name,
                    "path": str(item.resolve()) if item.is_symlink() else str(item),
                    "is_symlink": item.is_symlink(),
                })

    # Extensions
    ext_dir = base / "extensions"
    if ext_dir.is_dir():
        for item in sorted(ext_dir.iterdir()):
            if item.is_dir():
                result["extensions"].append(item.name)

    # Daily memory logs
    memory_dir = workspace / "memory" if workspace.is_dir() else None
    daily_logs = []
    if memory_dir and memory_dir.is_dir():
        for item in sorted(memory_dir.iterdir(), reverse=True):
            if item.suffix == ".md" and item.stem.count("-") == 2:
                daily_logs.append(item.name)
    result["daily_memory_logs"] = daily_logs[:10]  # last 10 days

    return result


def _build_inheritable(info: dict) -> list:
    """Build categorized list of inheritable items."""
    items = []

    items.append({
        "key": "config",
        "label": "Agent Configurations",
        "label_zh": "Agent 配置",
        "description": f"{len(info['agents'])} agents, model: {info.get('default_model', 'unknown')}",
        "category": "safe",
        "default_checked": True,
    })

    soul_found = any(f["name"] == "SOUL.md" for f in info["workspace_files"])
    if soul_found:
        items.append({
            "key": "soul",
            "label": "Agent Personalities (SOUL.md)",
            "label_zh": "Agent 人格 (SOUL.md)",
            "description": "Agent personality and behavior rules",
            "category": "safe",
            "default_checked": True,
        })

    user_found = any(f["name"] == "USER.md" for f in info["workspace_files"])
    if user_found:
        items.append({
            "key": "user",
            "label": "User Preferences (USER.md)",
            "label_zh": "用户偏好 (USER.md)",
            "description": "User profile, timezone, preferences",
            "category": "safe",
            "default_checked": True,
        })

    memory_found = any(f["name"] == "MEMORY.md" for f in info["workspace_files"])
    if memory_found:
        items.append({
            "key": "memory",
            "label": "Long-term Memory (MEMORY.md)",
            "label_zh": "长期记忆 (MEMORY.md)",
            "description": "Curated agent memory",
            "category": "caution",
            "default_checked": False,
        })

    if info["skills"]:
        items.append({
            "key": "skills",
            "label": f"Installed Skills ({len(info['skills'])} found)",
            "label_zh": f"已安装技能 ({len(info['skills'])} 个)",
            "description": ", ".join(s["name"] for s in info["skills"][:5]),
            "category": "safe",
            "default_checked": True,
        })

    mem_db = info.get("memory_db")
    if mem_db:
        items.append({
            "key": "memory_db",
            "label": f"Memory Database ({mem_db['status']})",
            "label_zh": f"记忆数据库 ({mem_db['size_fmt']})",
            "description": f"{mem_db['chunks']} chunks, {mem_db['files']} files",
            "category": "caution" if mem_db["chunks"] > 0 else "skip",
            "default_checked": mem_db["chunks"] > 0,
        })

    if info["auth_profiles_found"]:
        providers = info.get("auth_providers", [])
        items.append({
            "key": "auth",
            "label": f"API Keys ({len(providers)} providers)",
            "label_zh": f"API 密钥 ({len(providers)} 个提供商)",
            "description": ", ".join(providers),
            "category": "caution",
            "default_checked": True,
        })

    if info["sessions_count"] > 0:
        items.append({
            "key": "sessions",
            "label": f"Session Metadata ({info['sessions_count']} sessions)",
            "label_zh": f"会话元数据 ({info['sessions_count']} 个)",
            "description": "Session list and token stats (not conversation history)",
            "category": "skip",
            "default_checked": False,
        })

    return items


def detect() -> dict:
    """Detect local OpenClaw and AutoClaw installations."""
    home = Path.home()
    installations = []

    for dirname in (".openclaw", ".autoclaw"):
        base = home / dirname
        info = _scan_installation(base)
        if info:
            info["source"] = dirname.replace(".", "")
            info["inheritable_items"] = _build_inheritable(info)
            installations.append(info)

    return {
        "found": len(installations) > 0,
        "installations": installations,
        "scanned_paths": [
            str(home / ".openclaw"),
            str(home / ".autoclaw"),
        ],
        "scanned_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def import_items(source_path: str, items: list[str]) -> dict:
    """Import selected items from an OpenClaw installation."""
    base = Path(source_path).resolve()

    # Path traversal protection: only allow ~/.openclaw or ~/.autoclaw
    allowed_parents = [Path.home() / ".openclaw", Path.home() / ".autoclaw"]
    if not any(str(base).startswith(str(p.resolve())) for p in allowed_parents):
        return {"ok": False, "error": "Invalid source path: must be under ~/.openclaw or ~/.autoclaw"}

    if not base.is_dir():
        return {"ok": False, "error": f"Path not found: {source_path}"}

    imported = []
    skipped = []
    errors = []

    project_dir = Path(__file__).resolve().parent.parent
    data_dir = project_dir / "data"

    for item_key in items:
        try:
            if item_key == "config":
                _import_config(base, data_dir, imported, skipped)
            elif item_key == "soul":
                _import_workspace_file(base, "SOUL.md", imported, skipped)
            elif item_key == "user":
                _import_workspace_file(base, "USER.md", imported, skipped)
            elif item_key == "memory":
                _import_workspace_file(base, "MEMORY.md", imported, skipped)
                _import_daily_logs(base, imported, skipped)
            elif item_key == "skills":
                _import_skills(base, imported, skipped)
            elif item_key == "auth":
                _import_auth(base, imported, skipped)
            elif item_key == "memory_db":
                _import_memory_db(base, imported, skipped)
            else:
                skipped.append({"key": item_key, "reason": "unknown item key"})
        except Exception as e:
            errors.append({"key": item_key, "error": str(e)})

    return {
        "ok": len(errors) == 0,
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "imported_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def _import_config(base: Path, data_dir: Path, imported: list, skipped: list):
    """Merge OpenClaw config into agent_config."""
    src = base / "openclaw.json"
    if not src.is_file():
        skipped.append({"key": "config", "reason": "openclaw.json not found"})
        return

    dst = data_dir / "agent_config.json"
    try:
        with open(src) as f:
            oc_cfg = json.load(f)

        # Load existing agent config or create new
        ac_cfg = {}
        if dst.is_file():
            with open(dst) as f:
                ac_cfg = json.load(f)

        # Merge model defaults
        oc_defaults = oc_cfg.get("agents", {}).get("defaults", {})
        if oc_defaults.get("model", {}).get("primary"):
            ac_cfg.setdefault("defaultModel", oc_defaults["model"]["primary"])

        # Merge agent list
        oc_agents = oc_cfg.get("agents", {}).get("list", [])
        if oc_agents:
            ac_cfg["openclaw_agents_imported"] = [
                {"id": a.get("id"), "workspace": a.get("workspace")}
                for a in oc_agents
            ]

        with open(dst, "w") as f:
            json.dump(ac_cfg, f, indent=2, ensure_ascii=False)

        imported.append({"key": "config", "detail": f"{len(oc_agents)} agents merged"})
    except Exception as e:
        raise RuntimeError(f"Config import failed: {e}") from e


def _import_workspace_file(base: Path, filename: str, imported: list, skipped: list):
    """Copy a workspace file to all agent workspaces."""
    src = base / "workspace" / filename
    if not src.is_file():
        skipped.append({"key": filename, "reason": f"{filename} not found"})
        return

    copied = 0
    for ws in sorted(base.iterdir()):
        if ws.name.startswith("workspace") and ws.is_dir():
            dst = ws / filename
            try:
                import shutil
                shutil.copy2(str(src), str(dst))
                copied += 1
            except OSError:
                pass

    imported.append({"key": filename, "detail": f"Copied to {copied} workspaces"})


def _import_daily_logs(base: Path, imported: list, skipped: list):
    """Copy daily memory logs."""
    src_dir = base / "workspace" / "memory"
    if not src_dir.is_dir():
        skipped.append({"key": "daily_logs", "reason": "No memory directory"})
        return

    count = 0
    for ws in sorted(base.iterdir()):
        if ws.name.startswith("workspace") and ws.is_dir():
            dst_dir = ws / "memory"
            dst_dir.mkdir(exist_ok=True)
            for md_file in src_dir.glob("*.md"):
                import shutil
                try:
                    shutil.copy2(str(md_file), str(dst_dir / md_file.name))
                    count += 1
                except OSError:
                    pass

    imported.append({"key": "daily_logs", "detail": f"{count} files copied"})


def _import_skills(base: Path, imported: list, skipped: list):
    """Copy or symlink skills."""
    skills_dir = base / "skills"
    if not skills_dir.is_dir():
        skipped.append({"key": "skills", "reason": "No skills directory"})
        return

    count = 0
    for item in sorted(skills_dir.iterdir()):
        if item.is_dir() or item.is_symlink():
            target = item.resolve() if item.is_symlink() else item
            if target.is_dir():
                count += 1

    imported.append({"key": "skills", "detail": f"{count} skills detected"})


def _import_auth(base: Path, imported: list, skipped: list):
    """Copy auth profiles to all agent directories."""
    src = base / "agents" / "main" / "agent" / "auth-profiles.json"
    if not src.is_file():
        skipped.append({"key": "auth", "reason": "auth-profiles.json not found"})
        return

    agents_dir = base / "agents"
    copied = 0
    if agents_dir.is_dir():
        for agent_dir in sorted(agents_dir.iterdir()):
            if agent_dir.is_dir() and agent_dir.name != "main":
                dst_dir = agent_dir / "agent"
                dst_dir.mkdir(exist_ok=True)
                dst = dst_dir / "auth-profiles.json"
                import shutil
                try:
                    shutil.copy2(str(src), str(dst))
                    copied += 1
                except OSError:
                    pass

    imported.append({"key": "auth", "detail": f"Synced to {copied} agents"})


def _import_memory_db(base: Path, imported: list, skipped: list):
    """Note memory DB import (read-only reference)."""
    mem_db = base / "memory" / "main.sqlite"
    if not mem_db.is_file():
        skipped.append({"key": "memory_db", "reason": "main.sqlite not found"})
        return
    imported.append({"key": "memory_db", "detail": "Memory DB reference noted"})


if __name__ == "__main__":
    result = detect()
    print(json.dumps(result, indent=2, ensure_ascii=False))
