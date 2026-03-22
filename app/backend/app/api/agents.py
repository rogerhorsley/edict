"""Agents API — Agent 配置和状态查询。"""

import json
import logging
from pathlib import Path

from fastapi import APIRouter

log = logging.getLogger("ac.api.agents")
router = APIRouter()

# Agent 元信息（对应 agents/ 目录下的 SOUL.md）
AGENT_META = {
    "research":   {"name": "谋部", "role": "市场调研与洞察产出", "icon": "🔭"},
    "strategy":   {"name": "策枢", "role": "战略方案制定", "icon": "🧠"},
    "review":     {"name": "衡枢", "role": "方案审核与风险把关", "icon": "⚖️"},
    "execution":  {"name": "行枢", "role": "任务拆解与派发", "icon": "🎯"},
    "hr":         {"name": "人部", "role": "组织与人才管理", "icon": "👥"},
    "finance":    {"name": "财部", "role": "财务管理与资本运营", "icon": "💰"},
    "brand":      {"name": "品部", "role": "品牌传播与市场推广", "icon": "📣"},
    "security":   {"name": "安部", "role": "信息安全与风险管理", "icon": "🛡️"},
    "compliance": {"name": "规部", "role": "合规审计与质量管控", "icon": "📋"},
    "tech":       {"name": "技部", "role": "产品开发与技术架构", "icon": "⚙️"},
}


@router.get("")
async def list_agents():
    """列出所有可用 Agent。"""
    agents = []
    for agent_id, meta in AGENT_META.items():
        agents.append({
            "id": agent_id,
            **meta,
        })
    return {"agents": agents}


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """获取 Agent 详情。"""
    meta = AGENT_META.get(agent_id)
    if not meta:
        return {"error": f"Agent '{agent_id}' not found"}, 404

    # 尝试读取 SOUL.md
    soul_path = Path(__file__).parents[4] / "agents" / agent_id / "SOUL.md"
    soul_content = ""
    if soul_path.exists():
        soul_content = soul_path.read_text(encoding="utf-8")[:2000]

    return {
        "id": agent_id,
        **meta,
        "soul_preview": soul_content,
    }


@router.get("/{agent_id}/config")
async def get_agent_config(agent_id: str):
    """获取 Agent 运行时配置。"""
    config_path = Path(__file__).parents[4] / "data" / "agent_config.json"
    if not config_path.exists():
        return {"agent_id": agent_id, "config": {}}

    try:
        configs = json.loads(config_path.read_text(encoding="utf-8"))
        agent_config = configs.get(agent_id, {})
        return {"agent_id": agent_id, "config": agent_config}
    except (json.JSONDecodeError, IOError):
        return {"agent_id": agent_id, "config": {}}
