#!/usr/bin/env python3
"""
scheduled_research.py — 谋部定时研究任务调度器

功能：
  - 按配置的时间间隔触发谋部 Agent 执行研究任务
  - 将研究成果写入 data/pending_insights.json
  - 支持多种研究类型：竞品扫描、行业趋势、技术监控等

用法：
  python3 scripts/scheduled_research.py              # 一次性检查并执行到期任务
  python3 scripts/scheduled_research.py --daemon      # 守护模式，持续运行
  python3 scripts/scheduled_research.py --list        # 列出所有定时任务及状态
  python3 scripts/scheduled_research.py --trigger ID  # 手动触发指定任务

配置文件：data/research_schedule.json
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [research] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger('scheduled_research')

# ── 路径 ──

REPO_DIR = Path(os.environ.get('REPO_DIR', Path(__file__).resolve().parent.parent))
DATA_DIR = REPO_DIR / 'data'
INSIGHTS_FILE = DATA_DIR / 'pending_insights.json'
SCHEDULE_FILE = DATA_DIR / 'research_schedule.json'
LAST_RUN_FILE = DATA_DIR / 'research_last_run.json'

# ── 默认定时任务 ──

DEFAULT_SCHEDULE = [
    {
        'id': 'weekly_competitive_scan',
        'name': '竞品动态周扫描',
        'description': '扫描主要竞品（CrewAI, AutoGen, LangGraph等）的最新更新、发布日志和社区动态',
        'interval_hours': 168,  # 每周
        'prompt': '请对以下AI Agent框架进行最新动态扫描：CrewAI, AutoGen, LangGraph, OpenAI Swarm。'
                  '关注：版本更新、新功能、社区讨论热点、Star增长趋势。输出结构化分析报告。',
        'enabled': True,
    },
    {
        'id': 'daily_tech_trend',
        'name': '技术趋势日报',
        'description': '监控AI/LLM领域的重要技术动态和论文',
        'interval_hours': 24,  # 每天
        'prompt': '请扫描过去24小时内AI/LLM领域的重要动态：新模型发布、重要论文、'
                  '开源项目更新、行业新闻。筛选出最值得关注的3-5条，并给出简要分析。',
        'enabled': True,
    },
    {
        'id': 'weekly_market_report',
        'name': '市场分析周报',
        'description': '分析目标市场的需求变化、用户反馈和竞争格局',
        'interval_hours': 168,  # 每周
        'prompt': '请分析AI Agent工具市场的最新变化：用户需求趋势、定价策略变化、'
                  '新进入者分析、用户反馈汇总。输出结构化市场分析报告。',
        'enabled': False,  # 默认关闭，用户可开启
    },
]


def _load_json(path: Path, default=None):
    if not path.exists():
        return default if default is not None else []
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return default if default is not None else []


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def load_schedule() -> list[dict]:
    """加载研究任务计划。如果不存在则创建默认配置。"""
    if not SCHEDULE_FILE.exists():
        _save_json(SCHEDULE_FILE, DEFAULT_SCHEDULE)
        logger.info('已创建默认研究计划: %s', SCHEDULE_FILE)
        return DEFAULT_SCHEDULE
    return _load_json(SCHEDULE_FILE, DEFAULT_SCHEDULE)


def load_last_runs() -> dict[str, str]:
    """加载各任务的最后执行时间。"""
    return _load_json(LAST_RUN_FILE, {})


def save_last_run(task_id: str):
    """记录任务的执行时间。"""
    runs = load_last_runs()
    runs[task_id] = datetime.now(timezone.utc).isoformat()
    _save_json(LAST_RUN_FILE, runs)


def is_due(task: dict, last_runs: dict) -> bool:
    """检查任务是否到期需要执行。"""
    if not task.get('enabled', True):
        return False
    task_id = task['id']
    last_run_str = last_runs.get(task_id)
    if not last_run_str:
        return True  # 从未执行过
    try:
        last_run = datetime.fromisoformat(last_run_str)
        interval_sec = task.get('interval_hours', 24) * 3600
        return (datetime.now(timezone.utc) - last_run).total_seconds() >= interval_sec
    except (ValueError, TypeError):
        return True


def submit_insight(title: str, summary: str, source: str, suggested_action: str = ''):
    """将研究成果写入 pending_insights.json。"""
    insights = _load_json(INSIGHTS_FILE, [])

    # 生成 ID
    today = datetime.now(timezone.utc).strftime('%Y%m%d')
    today_count = sum(1 for i in insights if i.get('id', '').startswith(f'INS-{today}'))
    insight_id = f'INS-{today}-{today_count + 1:03d}'

    insight = {
        'id': insight_id,
        'title': title,
        'summary': summary,
        'source': source,
        'suggestedAction': suggested_action,
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'status': 'pending',
        'confirmedAt': None,
        'rejectedAt': None,
        'taskId': None,
    }

    insights.append(insight)
    _save_json(INSIGHTS_FILE, insights)
    logger.info('已提交洞察: %s - %s', insight_id, title)
    return insight_id


def execute_research(task: dict) -> bool:
    """执行研究任务。尝试调用 openclaw agent，失败则生成占位洞察。"""
    task_id = task['id']
    prompt = task.get('prompt', '')

    logger.info('执行研究任务: %s (%s)', task['name'], task_id)

    # 尝试调用 openclaw agent
    try:
        import subprocess
        result = subprocess.run(
            ['openclaw', 'agent', '--agent', 'research', '-m', prompt],
            capture_output=True, text=True, timeout=300,
            cwd=str(REPO_DIR),
        )
        if result.returncode == 0 and result.stdout.strip():
            output = result.stdout.strip()
            # 解析 agent 输出，提取标题和摘要
            lines = output.split('\n')
            title = lines[0][:100] if lines else task['name']
            summary = '\n'.join(lines[1:5]) if len(lines) > 1 else output[:500]
            submit_insight(
                title=title,
                summary=summary,
                source=f'scheduled:{task_id}',
                suggested_action=task.get('suggested_action', ''),
            )
            save_last_run(task_id)
            return True
    except FileNotFoundError:
        logger.info('openclaw CLI 未安装，使用占位模式')
    except subprocess.TimeoutExpired:
        logger.warning('研究任务超时: %s', task_id)
    except Exception as e:
        logger.warning('执行研究任务失败: %s - %s', task_id, e)

    # 降级：生成占位洞察（标记来源为 placeholder）
    submit_insight(
        title=f'[待研究] {task["name"]}',
        summary=f'定时研究任务 "{task["name"]}" 已触发，但 Agent 未就绪。'
                f'任务描述：{task.get("description", "")}',
        source=f'scheduled:{task_id}:placeholder',
        suggested_action='配置 openclaw CLI 后重新触发',
    )
    save_last_run(task_id)
    return False


def check_and_run():
    """检查所有到期任务并执行。"""
    schedule = load_schedule()
    last_runs = load_last_runs()

    due_tasks = [t for t in schedule if is_due(t, last_runs)]
    if not due_tasks:
        logger.info('无到期研究任务')
        return 0

    logger.info('发现 %d 个到期研究任务', len(due_tasks))
    executed = 0
    for task in due_tasks:
        if execute_research(task):
            executed += 1
    return executed


def list_schedule():
    """列出所有定时任务及状态。"""
    schedule = load_schedule()
    last_runs = load_last_runs()

    print(f'\n{"ID":<30} {"名称":<20} {"间隔":<10} {"状态":<8} {"上次执行":<25}')
    print('-' * 95)
    for t in schedule:
        tid = t['id']
        interval = f"{t.get('interval_hours', 24)}h"
        status = '启用' if t.get('enabled', True) else '禁用'
        last = last_runs.get(tid, '从未')
        due = '(到期)' if is_due(t, last_runs) else ''
        print(f'{tid:<30} {t["name"]:<20} {interval:<10} {status:<8} {last:<25} {due}')
    print()


def main():
    args = sys.argv[1:]

    if '--list' in args:
        list_schedule()
        return

    if '--trigger' in args:
        idx = args.index('--trigger')
        if idx + 1 >= len(args):
            print('用法: --trigger TASK_ID')
            sys.exit(1)
        target_id = args[idx + 1]
        schedule = load_schedule()
        task = next((t for t in schedule if t['id'] == target_id), None)
        if not task:
            print(f'未找到任务: {target_id}')
            sys.exit(1)
        execute_research(task)
        return

    if '--daemon' in args:
        logger.info('守护模式启动，每 60 秒检查一次')
        while True:
            try:
                check_and_run()
            except Exception as e:
                logger.error('检查循环异常: %s', e)
            time.sleep(60)
    else:
        check_and_run()


if __name__ == '__main__':
    main()
