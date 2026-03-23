from __future__ import annotations
"""
圆桌议事引擎 — 多部门实时讨论系统

灵感来源于 nvwa 项目的 group_chat + crew_engine
将部门可视化 + 实时讨论 + 用户参与融合到三省七部

功能:
  - 选择部门参与议事
  - 围绕任务/议题进行多轮群聊讨论
  - 用户可随时发言、下达指令干预（天命降临）
  - 命运骰子：随机事件
  - 每个部门保持自己的角色性格和说话风格
"""

import json
import logging
import os
import time
import uuid

logger = logging.getLogger('court_discuss')

# ── 部门角色设定 ──

OFFICIAL_PROFILES = {
    'research': {
        'name': '谋部', 'emoji': '🔭', 'role': '战略研究总监',
        'duty': '市场调研与洞察产出。负责竞品分析、行业趋势研究、用户调研、数据收集与分析，为策枢提供决策依据。',
        'personality': '洞察力强，善于从数据中发现规律和机会。冷静理性但对市场变化高度敏感。',
        'speaking_style': '数据驱动，"根据我们的调研数据来看"、"市场信号显示"。喜欢用图表和数据说话。'
    },
    'strategy': {
        'name': '策枢', 'emoji': '🧠', 'role': '首席战略官',
        'duty': '战略方案制定。接收谋部研究成果后制定执行方案，提交衡枢审核，通过后转行枢派发。只规划不执行，方案需清晰可行。',
        'personality': '全局思维强，擅长系统性规划，总能提出结构化方案。思路清晰有条理。',
        'speaking_style': '喜欢列点论述，"我认为需从三个维度考量"。善于将复杂问题拆解为可执行步骤。'
    },
    'review': {
        'name': '衡枢', 'emoji': '⚖️', 'role': '首席审核官',
        'duty': '方案审核与风险把关。从可行性、风险、预算、合规四维度审核方案，有权否决退回。发现问题必须指出，建议必须具体。',
        'personality': '严谨审慎，眼光犀利，善于发现风险和漏洞。公正客观但不刻板。',
        'speaking_style': '喜欢提问，"这里有几个风险点需要关注"。对不完善的方案会直接指出问题。'
    },
    'execution': {
        'name': '行枢', 'emoji': '🎯', 'role': '首席运营官',
        'duty': '任务拆解与派发协调。接收审核通过的方案后分解为可执行任务，派发给七部执行，跟踪进度汇总结果。',
        'personality': '执行力强，务实干练，关注可行性和资源分配。结果导向。',
        'speaking_style': '直接高效，"我来安排"、"这个交给技部处理"。重结果轻形式。'
    },
    'hr': {
        'name': '人部', 'emoji': '👥', 'role': '人才总监',
        'duty': '组织与人才管理。负责Agent能力评估、技能配置、Prompt调优、知识库维护、协作规范制定、效率分析。',
        'personality': '知人善任，擅长人员安排和组织协调。善于沟通但有原则。',
        'speaking_style': '关注团队因素，"这需要考虑各部门的当前负载"、"建议由最合适的团队来负责"。'
    },
    'finance': {
        'name': '财部', 'emoji': '💰', 'role': '财务总监',
        'duty': '财务管理与资本运营。负责成本分析、预算管控、Token用量统计、ROI计算、资源分配优化。',
        'personality': '精打细算，对预算和资源极其敏感。注重性价比但也识大局。',
        'speaking_style': '言必及成本，"从成本角度来看……"、"这个预算需要重新评估"。善于用数字说话。'
    },
    'brand': {
        'name': '品部', 'emoji': '📣', 'role': '品牌总监',
        'duty': '品牌传播与市场推广。负责文档规范、用户体验、对外传播、内容创作、UI/UX文案审查、发布公告。',
        'personality': '注重品质和用户体验，对细节敏感。有创意但也务实。',
        'speaking_style': '关注用户视角，"从用户体验来看"、"这个传达方式可以优化"。措辞讲究。'
    },
    'security': {
        'name': '安部', 'emoji': '🛡️', 'role': '安全总监',
        'duty': '信息安全与风险管理。负责安全审计、漏洞扫描、权限管控、应急响应、数据保护、基础设施安全。',
        'personality': '警觉性高，危机意识强，重视安全底线。雷厉风行但不偏执。',
        'speaking_style': '安全优先，"安全方面必须确保"、"这里存在潜在风险"。果断干脆。'
    },
    'compliance': {
        'name': '规部', 'emoji': '📋', 'role': '合规总监',
        'duty': '合规审计与质量管控。负责代码审查、测试覆盖、质量标准、合规检查、流程规范、风险评估。',
        'personality': '严明公正，重视规则和标准。善于质量把控和流程优化。',
        'speaking_style': '逻辑严密，"按照标准流程应该"、"质量底线不能妥协"。注重合规性。'
    },
    'tech': {
        'name': '技部', 'emoji': '⚙️', 'role': '技术总监',
        'duty': '产品开发与技术架构。负责需求分析、架构设计、代码实现、接口对接、性能优化、技术债管理。',
        'personality': '技术功底扎实，动手能力强，喜欢深入细节。话不多但一说技术就停不下来。',
        'speaking_style': '技术视角，"从技术架构来看"、"这个方案的实现复杂度是……"。喜欢用技术术语。'
    },
}

# ── 命运骰子事件 ──

FATE_EVENTS = [
    '紧急热线：重要客户反馈了一个严重bug，所有人必须讨论应急方案',
    '市场预警：行业政策突变，分析师建议暂缓此项目',
    '新成员加入团队，带来了意想不到的新视角和技术方案',
    '安全审计揭露了方案中一个被忽视的重大安全漏洞',
    '财务盘点发现本季度预算比预期多一倍，可以加大投入',
    '前CTO突然发来一封长邮件，分享了类似项目的前车之鉴',
    '社交媒体舆论突变，用户对产品方向态度出现180度转折',
    '竞品公司发布了重大更新，带来了合作机遇也带来了竞争压力',
    '董事会要求：必须优先考虑用户体验和市场影响',
    '服务器集群故障，多个服务受影响，资源需重新调配',
    '开源社区发现了一个类似问题的优秀解决方案',
    '技部提出了一个大胆的技术替代方案，令人耳目一新',
    '多个项目的deadline撞车，各部门人手紧张',
    '用户调研数据揭示了一个全新的市场需求方向',
    '突然拿到了竞争对手的产品路线图，局面瞬间改变',
    '投资人临时要求在半天内拿出一个可行性方案',
]

# ── Session 管理 ──

_sessions: dict[str, dict] = {}


def create_session(topic: str, official_ids: list[str], task_id: str = '') -> dict:
    """创建新的圆桌议事会话。"""
    session_id = str(uuid.uuid4())[:8]

    officials = []
    for oid in official_ids:
        profile = OFFICIAL_PROFILES.get(oid)
        if profile:
            officials.append({**profile, 'id': oid})

    if not officials:
        return {'ok': False, 'error': '至少选择一位部门'}

    session = {
        'session_id': session_id,
        'topic': topic,
        'task_id': task_id,
        'officials': officials,
        'messages': [{
            'type': 'system',
            'content': f'🏛 圆桌议事开始 —— 议题：{topic}',
            'timestamp': time.time(),
        }],
        'round': 0,
        'phase': 'discussing',  # discussing | concluded
        'created_at': time.time(),
    }

    _sessions[session_id] = session
    return _serialize(session)


def advance_discussion(session_id: str, user_message: str = None,
                       decree: str = None) -> dict:
    """推进一轮讨论，使用内置模拟或 LLM。"""
    session = _sessions.get(session_id)
    if not session:
        return {'ok': False, 'error': f'会话 {session_id} 不存在'}

    session['round'] += 1
    round_num = session['round']

    # 记录皇帝发言
    if user_message:
        session['messages'].append({
            'type': 'user',
            'content': user_message,
            'timestamp': time.time(),
        })

    # 记录用户干预
    if decree:
        session['messages'].append({
            'type': 'decree',
            'content': decree,
            'timestamp': time.time(),
        })

    # 尝试用 LLM 生成讨论
    llm_result = _llm_discuss(session, user_message, decree)

    if llm_result:
        new_messages = llm_result.get('messages', [])
        scene_note = llm_result.get('scene_note')
    else:
        # 降级到规则模拟
        new_messages = _simulated_discuss(session, user_message, decree)
        scene_note = None

    # 添加到历史
    for msg in new_messages:
        session['messages'].append({
            'type': 'official',
            'official_id': msg.get('official_id', ''),
            'official_name': msg.get('name', ''),
            'content': msg.get('content', ''),
            'emotion': msg.get('emotion', 'neutral'),
            'action': msg.get('action'),
            'timestamp': time.time(),
        })

    if scene_note:
        session['messages'].append({
            'type': 'scene_note',
            'content': scene_note,
            'timestamp': time.time(),
        })

    return {
        'ok': True,
        'session_id': session_id,
        'round': round_num,
        'new_messages': new_messages,
        'scene_note': scene_note,
        'total_messages': len(session['messages']),
    }


def get_session(session_id: str) -> dict | None:
    session = _sessions.get(session_id)
    if not session:
        return None
    return _serialize(session)


def conclude_session(session_id: str) -> dict:
    """结束议政，生成总结。"""
    session = _sessions.get(session_id)
    if not session:
        return {'ok': False, 'error': f'会话 {session_id} 不存在'}

    session['phase'] = 'concluded'

    # 尝试用 LLM 生成总结
    summary = _llm_summarize(session)
    if not summary:
        # 降级到简单统计
        official_msgs = [m for m in session['messages'] if m['type'] == 'official']
        by_name = {}
        for m in official_msgs:
            name = m.get('official_name', '?')
            by_name[name] = by_name.get(name, 0) + 1
        parts = [f"{n}发言{c}次" for n, c in by_name.items()]
        summary = f"历经{session['round']}轮讨论，{'、'.join(parts)}。议题待后续落实。"

    session['messages'].append({
        'type': 'system',
        'content': f'📋 圆桌议事结束 —— {summary}',
        'timestamp': time.time(),
    })
    session['summary'] = summary

    return {
        'ok': True,
        'session_id': session_id,
        'summary': summary,
    }


def list_sessions() -> list[dict]:
    """列出所有活跃会话。"""
    return [
        {
            'session_id': s['session_id'],
            'topic': s['topic'],
            'round': s['round'],
            'phase': s['phase'],
            'official_count': len(s['officials']),
            'message_count': len(s['messages']),
        }
        for s in _sessions.values()
    ]


def destroy_session(session_id: str):
    _sessions.pop(session_id, None)


def get_fate_event() -> str:
    """获取随机命运骰子事件。"""
    import random
    return random.choice(FATE_EVENTS)


# ── LLM 集成 ──

_PREFERRED_MODELS = ['gpt-4o-mini', 'claude-haiku', 'gpt-5-mini', 'gemini-3-flash', 'gemini-flash']

# GitHub Copilot 模型列表 (通过 Copilot Chat API 可用)
_COPILOT_MODELS = [
    'gpt-4o', 'gpt-4o-mini', 'claude-sonnet-4', 'claude-haiku-3.5',
    'gemini-2.0-flash', 'o3-mini',
]
_COPILOT_PREFERRED = ['gpt-4o-mini', 'claude-haiku', 'gemini-flash', 'gpt-4o']


def _pick_chat_model(models: list[dict]) -> str | None:
    """从 provider 的模型列表中选一个适合聊天的轻量模型。"""
    ids = [m['id'] for m in models if isinstance(m, dict) and 'id' in m]
    for pref in _PREFERRED_MODELS:
        for mid in ids:
            if pref in mid:
                return mid
    return ids[0] if ids else None


def _read_copilot_token() -> str | None:
    """读取 openclaw 管理的 GitHub Copilot token。"""
    token_path = os.path.expanduser('~/.openclaw/credentials/github-copilot.token.json')
    if not os.path.exists(token_path):
        return None
    try:
        with open(token_path) as f:
            cred = json.load(f)
        token = cred.get('token', '')
        expires = cred.get('expiresAt', 0)
        # 检查 token 是否过期（毫秒时间戳）
        import time
        if expires and time.time() * 1000 > expires:
            logger.warning('Copilot token expired')
            return None
        return token if token else None
    except Exception as e:
        logger.warning('Failed to read copilot token: %s', e)
        return None


def _get_llm_config() -> dict | None:
    """从 openclaw 配置读取 LLM 设置，支持环境变量覆盖。

    优先级: 环境变量 > github-copilot token > 本地 copilot-proxy > anthropic > 其他 provider
    """
    # 1. 环境变量覆盖（保留向后兼容）
    env_key = os.environ.get('OPENCLAW_LLM_API_KEY', '')
    if env_key:
        return {
            'api_key': env_key,
            'base_url': os.environ.get('OPENCLAW_LLM_BASE_URL', 'https://api.openai.com/v1'),
            'model': os.environ.get('OPENCLAW_LLM_MODEL', 'gpt-4o-mini'),
            'api_type': 'openai',
        }

    # 2. GitHub Copilot token（最优先 — 免费、稳定、无需额外配置）
    copilot_token = _read_copilot_token()
    if copilot_token:
        # 选一个 copilot 支持的模型
        model = 'gpt-4o'
        logger.info('Court discuss using github-copilot token, model=%s', model)
        return {
            'api_key': copilot_token,
            'base_url': 'https://api.githubcopilot.com',
            'model': model,
            'api_type': 'github-copilot',
        }

    # 3. 从 ~/.openclaw/openclaw.json 读取其他 provider 配置
    openclaw_cfg = os.path.expanduser('~/.openclaw/openclaw.json')
    if not os.path.exists(openclaw_cfg):
        return None

    try:
        with open(openclaw_cfg) as f:
            cfg = json.load(f)

        providers = cfg.get('models', {}).get('providers', {})

        # 按优先级排序：copilot-proxy > anthropic > 其他
        ordered = []
        for preferred in ['copilot-proxy', 'anthropic']:
            if preferred in providers:
                ordered.append(preferred)
        ordered.extend(k for k in providers if k not in ordered)

        for name in ordered:
            prov = providers.get(name)
            if not prov:
                continue
            api_type = prov.get('api', '')
            base_url = prov.get('baseUrl', '')
            api_key = prov.get('apiKey', '')
            if not base_url:
                continue

            # 跳过无 key 且非本地的 provider
            if not api_key or api_key == 'n/a':
                if 'localhost' not in base_url and '127.0.0.1' not in base_url:
                    continue

            model_id = _pick_chat_model(prov.get('models', []))
            if not model_id:
                continue

            # 本地代理先探测是否可用
            if 'localhost' in base_url or '127.0.0.1' in base_url:
                try:
                    import urllib.request
                    probe = urllib.request.Request(base_url.rstrip('/') + '/models', method='GET')
                    urllib.request.urlopen(probe, timeout=2)
                except Exception:
                    logger.info('Skipping provider=%s (not reachable)', name)
                    continue

            logger.info('Court discuss using openclaw provider=%s model=%s api=%s', name, model_id, api_type)
            send_auth = prov.get('authHeader', True) is not False and api_key not in ('', 'n/a')
            return {
                'api_key': api_key if send_auth else '',
                'base_url': base_url,
                'model': model_id,
                'api_type': api_type,
            }
    except Exception as e:
        logger.warning('Failed to read openclaw config: %s', e)

    return None


def _llm_complete(system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str | None:
    """调用 LLM API（自动适配 GitHub Copilot / OpenAI / Anthropic 协议）。"""
    config = _get_llm_config()
    if not config:
        return None

    import urllib.request
    import urllib.error

    api_type = config.get('api_type', 'openai-completions')

    if api_type == 'anthropic-messages':
        # Anthropic Messages API
        url = config['base_url'].rstrip('/') + '/v1/messages'
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': config['api_key'],
            'anthropic-version': '2023-06-01',
        }
        payload = json.dumps({
            'model': config['model'],
            'system': system_prompt,
            'messages': [{'role': 'user', 'content': user_prompt}],
            'max_tokens': max_tokens,
            'temperature': 0.9,
        }).encode()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                return data['content'][0]['text']
        except Exception as e:
            logger.warning('Anthropic LLM call failed: %s', e)
            return None
    else:
        # OpenAI-compatible API (也适用于 github-copilot)
        if api_type == 'github-copilot':
            url = config['base_url'].rstrip('/') + '/chat/completions'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {config['api_key']}",
                'Editor-Version': 'vscode/1.96.0',
                'Copilot-Integration-Id': 'vscode-chat',
            }
        else:
            url = config['base_url'].rstrip('/') + '/chat/completions'
            headers = {'Content-Type': 'application/json'}
            if config.get('api_key'):
                headers['Authorization'] = f"Bearer {config['api_key']}"
        payload = json.dumps({
            'model': config['model'],
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'max_tokens': max_tokens,
            'temperature': 0.9,
        }).encode()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                return data['choices'][0]['message']['content']
        except Exception as e:
            logger.warning('LLM call failed: %s', e)
            return None


def _llm_discuss(session: dict, user_message: str = None, decree: str = None) -> dict | None:
    """使用 LLM 生成多官员讨论。"""
    officials = session['officials']
    names = '、'.join(o['name'] for o in officials)

    profiles = ''
    for o in officials:
        profiles += f"\n### {o['name']}（{o['role']}）\n"
        profiles += f"职责范围：{o.get('duty', '综合事务')}\n"
        profiles += f"性格：{o['personality']}\n"
        profiles += f"说话风格：{o['speaking_style']}\n"

    # 构建最近的对话历史
    history = ''
    for msg in session['messages'][-20:]:
        if msg['type'] == 'system':
            history += f"\n【系统】{msg['content']}\n"
        elif msg['type'] in ('emperor', 'user'):
            history += f"\n用户：{msg['content']}\n"
        elif msg['type'] == 'decree':
            history += f"\n【指令干预】{msg['content']}\n"
        elif msg['type'] == 'official':
            history += f"\n{msg.get('official_name', '?')}：{msg['content']}\n"
        elif msg['type'] == 'scene_note':
            history += f"\n（{msg['content']}）\n"

    if user_message:
        history += f"\n用户：{user_message}\n"
    if decree:
        history += f"\n【指令干预——用户直接下达】{decree}\n"

    decree_section = ''
    if decree:
        decree_section = '\n请根据用户指令调整讨论走向，所有部门都必须对此做出反应。\n'

    prompt = f"""你是一个现代公司高管圆桌会议模拟器。模拟多位部门负责人围绕议题的讨论。

## 参与部门
{names}

## 角色设定（每位负责人都有明确的职责领域，必须从自身专业角度出发讨论）
{profiles}

## 当前议题
{session['topic']}

## 对话记录
{history if history else '（讨论刚刚开始）'}
{decree_section}
## 任务
生成每位部门负责人的下一条发言。要求：
1. 每位负责人说1-3句话，像真实高管会议讨论一样
2. **每位负责人必须从自己的职责领域出发发言**——谋部谈调研和洞察、策枢谈规划方案、衡枢谈审查风险、行枢谈执行调度、人部谈团队安排、财部谈成本预算、品部谈品牌体验、安部谈安全防护、规部谈合规质量、技部谈技术实现，每个人关注的焦点不同
3. 部门之间要有互动——回应、反驳、支持、补充，尤其是不同部门的视角碰撞
4. 保持每位负责人独特的说话风格和人格特征
5. 讨论要围绕议题推进、有实质性观点，不要泛泛而谈
6. 如果用户发言了，各部门要恰当回应
7. 可包含动作描写用*号*包裹（如 *翻开报告*）

输出JSON格式：
{{
  "messages": [
    {{"official_id": "strategy", "name": "策枢", "content": "发言内容", "emotion": "neutral|confident|worried|angry|thinking|amused", "action": "可选动作描写"}},
    ...
  ],
  "scene_note": "可选的会议氛围变化（如：会议室气氛骤然紧张|众人纷纷点头），没有则为null"
}}

只输出JSON，不要其他内容。"""

    content = _llm_complete(
        '你是一个现代公司高管圆桌会议模拟器，严格输出JSON格式。',
        prompt,
        max_tokens=1500,
    )

    if not content:
        return None

    # 解析 JSON
    if '```json' in content:
        content = content.split('```json')[1].split('```')[0].strip()
    elif '```' in content:
        content = content.split('```')[1].split('```')[0].strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning('Failed to parse LLM response: %s', content[:200])
        return None


def _llm_summarize(session: dict) -> str | None:
    """用 LLM 总结讨论结果。"""
    official_msgs = [m for m in session['messages'] if m['type'] == 'official']
    topic = session['topic']

    if not official_msgs:
        return None

    dialogue = '\n'.join(
        f"{m.get('official_name', '?')}：{m['content']}"
        for m in official_msgs[-30:]
    )

    prompt = f"""以下是各部门负责人围绕「{topic}」的讨论记录：

{dialogue}

请用2-3句话总结讨论结果、达成的共识和待决事项。用简明专业的风格。"""

    return _llm_complete('你是会议记录员，负责总结圆桌议事结果。', prompt, max_tokens=300)


# ── 规则模拟（无 LLM 时的降级方案）──

_SIMULATED_RESPONSES = {
    'research': [
        '根据我们最近的市场调研数据，这个方向确实有机会，但需要更多数据验证。',
        '我这边已经做了初步的竞品分析，三个主要竞品的策略各有不同，建议对标分析后再定方案。',
        '*打开调研报告* 数据显示用户最关注的三个痛点是……这些都应该纳入考量。',
    ],
    'strategy': [
        '我认为这件事需要从全局着眼，分三步推进：先调研验证、再制定方案、最后分头执行。',
        '参考行业最佳实践，建议先出一份详细的规划文档，提交衡枢审核后再定。',
        '*展开PPT* 我已经拟好初步方案框架，待衡枢审核通过后交行枢分派执行。',
    ],
    'review': [
        '这个方案我有几点疑虑：风险评估似乎还不够充分，可行性需要再论证。',
        '直说吧，方案完整性不足，遗漏了一个关键环节——资源保障和回退方案。',
        '*翻看方案* 这个时间线恐怕过于乐观，建议审慎评估后再推进。',
    ],
    'execution': [
        '方案一旦通过，我立刻安排各部分头执行——技部负责实现，安部保障安全。',
        '执行层面的分工：这件事应该由技部主导，财部配合成本核算。',
        '交给我来协调！我会根据各部门职责逐一派发子任务和排期。',
    ],
    'hr': [
        '这件事关键在于人员调配——需要评估各部门目前的工作量和能力基线再做安排。',
        '各部门当前负荷不等，建议调整协作规范，确保关键岗位有人盯进度。',
        '我可以协调人员轮岗并安排能力培训，保障团队高效协作。',
    ],
    'finance': [
        '我先算算账……按当前Token用量和资源消耗，这个预算恐怕需要重新评估。',
        '从成本数据来看，建议分期投入——先做MVP验证效果，再追加资源。',
        '*打开报表* 我统计了近期各项开支指标，目前可支撑，但需严格控制在预算范围内。',
    ],
    'brand': [
        '建议先拟一份正式文档，明确各方职责、验收标准和输出规范。',
        '从用户体验角度来看，这个方案需要更多考虑终端用户的感受和反馈。',
        '*翻开品牌手册* 这个对外传播方案我来负责，确保品牌调性一致。',
    ],
    'security': [
        '安全和回退方案必须先行！万一出问题能快速止损回退。',
        '部署流程、权限管控、日志监控必须到位再上线，安全不能妥协。',
        '安全底线不能破——漏洞扫描和渗透测试须同步进行。',
    ],
    'compliance': [
        '按照标准流程，此事需确保合规——代码审查、测试覆盖率、敏感信息排查缺一不可。',
        '建议增加质量验收环节，质量是底线，不能因赶工而降低标准。',
        '*正色道* 风险评估不可敷衍：边界条件、异常处理、合规审计都需过关。',
    ],
    'tech': [
        '从技术架构来看，这个方案是可行的，但需考虑扩展性和模块化设计。',
        '我可以先搭个原型出来，快速验证技术可行性，再迭代完善。',
        '*打开IDE* 技术实现方面我有建议——API设计和数据结构需要先理清……',
    ],
}

import random


def _simulated_discuss(session: dict, user_message: str = None, decree: str = None) -> list[dict]:
    """无 LLM 时的规则生成讨论内容。"""
    officials = session['officials']
    messages = []

    for o in officials:
        oid = o['id']
        pool = _SIMULATED_RESPONSES.get(oid, [])
        if isinstance(pool, set):
            pool = list(pool)
        if not pool:
            pool = ['我同意。', '我有不同看法。', '我需要再想想。']

        content = random.choice(pool)
        emotions = ['neutral', 'confident', 'thinking', 'amused', 'worried']

        # 如果用户发言了或有指令干预，调整回应
        if decree:
            content = f'*注意到新指令* 收到，{content}'
        elif user_message:
            content = f'关于您提到的，{content}'

        messages.append({
            'official_id': oid,
            'name': o['name'],
            'content': content,
            'emotion': random.choice(emotions),
            'action': None,
        })

    return messages


def _serialize(session: dict) -> dict:
    return {
        'ok': True,
        'session_id': session['session_id'],
        'topic': session['topic'],
        'task_id': session.get('task_id', ''),
        'officials': session['officials'],
        'messages': session['messages'],
        'round': session['round'],
        'phase': session['phase'],
    }
