/**
 * API 层 — 对接 dashboard/server.py
 * 生产环境从同源 (port 7891) 请求，开发环境可通过 VITE_API_URL 指定
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

// ── Auth Token Management ──

const TOKEN_KEY = 'ac_auth_token';

function getStoredToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}

function setStoredToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* ignore */ }
}

function authHeaders(): Record<string, string> {
  const token = getStoredToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

// ── 通用请求 ──

async function fetchJ<T>(url: string): Promise<T> {
  const res = await fetch(url, { cache: 'no-store', headers: authHeaders() });
  if (!res.ok) throw new Error(String(res.status));
  return res.json();
}

async function postJ<T>(url: string, data: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  return res.json();
}

async function putJ<T>(url: string, data: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  return res.json();
}

async function deleteJ<T>(url: string): Promise<T> {
  const res = await fetch(url, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  return res.json();
}

// ── API 接口 ──

export const api = {
  // 核心数据
  liveStatus: () => fetchJ<LiveStatus>(`${API_BASE}/api/live-status`),
  agentConfig: () => fetchJ<AgentConfig>(`${API_BASE}/api/agent-config`),
  modelChangeLog: () => fetchJ<ChangeLogEntry[]>(`${API_BASE}/api/model-change-log`).catch(() => []),
  officialsStats: () => fetchJ<OfficialsData>(`${API_BASE}/api/officials-stats`),
  morningBrief: () => fetchJ<MorningBrief>(`${API_BASE}/api/morning-brief`),
  morningConfig: () => fetchJ<SubConfig>(`${API_BASE}/api/morning-config`),
  agentsStatus: () => fetchJ<AgentsStatusData>(`${API_BASE}/api/agents-status`),

  // 任务实时动态
  taskActivity: (id: string) =>
    fetchJ<TaskActivityData>(`${API_BASE}/api/task-activity/${encodeURIComponent(id)}`),
  schedulerState: (id: string) =>
    fetchJ<SchedulerStateData>(`${API_BASE}/api/scheduler-state/${encodeURIComponent(id)}`),

  // 技能内容
  skillContent: (agentId: string, skillName: string) =>
    fetchJ<SkillContentResult>(
      `${API_BASE}/api/skill-content/${encodeURIComponent(agentId)}/${encodeURIComponent(skillName)}`
    ),

  // 操作类
  setModel: (agentId: string, model: string) =>
    postJ<ActionResult>(`${API_BASE}/api/set-model`, { agentId, model }),
  setDispatchChannel: (channel: string) =>
    postJ<ActionResult>(`${API_BASE}/api/set-dispatch-channel`, { channel }),
  agentWake: (agentId: string) =>
    postJ<ActionResult>(`${API_BASE}/api/agent-wake`, { agentId }),
  taskAction: (taskId: string, action: string, reason: string) =>
    postJ<ActionResult>(`${API_BASE}/api/task-action`, { taskId, action, reason }),
  reviewAction: (taskId: string, action: string, comment: string) =>
    postJ<ActionResult>(`${API_BASE}/api/review-action`, { taskId, action, comment }),
  advanceState: (taskId: string, comment: string) =>
    postJ<ActionResult>(`${API_BASE}/api/advance-state`, { taskId, comment }),
  archiveTask: (taskId: string, archived: boolean) =>
    postJ<ActionResult>(`${API_BASE}/api/archive-task`, { taskId, archived }),
  archiveAllDone: () =>
    postJ<ActionResult & { count?: number }>(`${API_BASE}/api/archive-task`, { archiveAllDone: true }),
  schedulerScan: (thresholdSec = 180) =>
    postJ<ActionResult & { count?: number; actions?: ScanAction[]; checkedAt?: string }>(
      `${API_BASE}/api/scheduler-scan`,
      { thresholdSec }
    ),
  schedulerRetry: (taskId: string, reason: string) =>
    postJ<ActionResult>(`${API_BASE}/api/scheduler-retry`, { taskId, reason }),
  schedulerEscalate: (taskId: string, reason: string) =>
    postJ<ActionResult>(`${API_BASE}/api/scheduler-escalate`, { taskId, reason }),
  schedulerRollback: (taskId: string, reason: string) =>
    postJ<ActionResult>(`${API_BASE}/api/scheduler-rollback`, { taskId, reason }),
  refreshMorning: () =>
    postJ<ActionResult>(`${API_BASE}/api/morning-brief/refresh`, {}),
  saveMorningConfig: (config: SubConfig) =>
    postJ<ActionResult>(`${API_BASE}/api/morning-config`, config),
  addSkill: (agentId: string, skillName: string, description: string, trigger: string) =>
    postJ<ActionResult>(`${API_BASE}/api/add-skill`, { agentId, skillName, description, trigger }),

  // 远程 Skills 管理
  addRemoteSkill: (agentId: string, skillName: string, sourceUrl: string, description?: string) =>
    postJ<ActionResult & { skillName?: string; agentId?: string; source?: string; localPath?: string; size?: number; addedAt?: string }>(
      `${API_BASE}/api/add-remote-skill`, { agentId, skillName, sourceUrl, description: description || '' }
    ),
  remoteSkillsList: () =>
    fetchJ<RemoteSkillsListResult>(`${API_BASE}/api/remote-skills-list`),
  updateRemoteSkill: (agentId: string, skillName: string) =>
    postJ<ActionResult>(`${API_BASE}/api/update-remote-skill`, { agentId, skillName }),
  removeRemoteSkill: (agentId: string, skillName: string) =>
    postJ<ActionResult>(`${API_BASE}/api/remove-remote-skill`, { agentId, skillName }),

  createTask: (data: CreateTaskPayload) =>
    postJ<ActionResult & { taskId?: string }>(`${API_BASE}/api/create-task`, data),

  // ── 指令下达 ──
  pendingInsights: () =>
    fetchJ<{ ok: boolean; insights: Insight[]; total: number }>(`${API_BASE}/api/pending-insights`),
  confirmInsight: (insightId: string, editedTitle?: string) =>
    postJ<ActionResult & { taskId?: string }>(`${API_BASE}/api/confirm-insight`, { insightId, editedTitle }),
  rejectInsight: (insightId: string, reason?: string) =>
    postJ<ActionResult>(`${API_BASE}/api/reject-insight`, { insightId, reason }),
  issueCommand: (title: string, description?: string) =>
    postJ<ActionResult & { taskId?: string }>(`${API_BASE}/api/issue-command`, { title, description }),

  // ── 圆桌议事 ──
  courtDiscussStart: (topic: string, officials: string[], taskId?: string) =>
    postJ<CourtDiscussResult>(`${API_BASE}/api/court-discuss/start`, { topic, officials, taskId }),
  courtDiscussAdvance: (sessionId: string, userMessage?: string, decree?: string) =>
    postJ<CourtDiscussResult>(`${API_BASE}/api/court-discuss/advance`, { sessionId, userMessage, decree }),
  courtDiscussConclude: (sessionId: string) =>
    postJ<ActionResult & { summary?: string }>(`${API_BASE}/api/court-discuss/conclude`, { sessionId }),
  courtDiscussDestroy: (sessionId: string) =>
    postJ<ActionResult>(`${API_BASE}/api/court-discuss/destroy`, { sessionId }),
  courtDiscussFate: () =>
    fetchJ<{ ok: boolean; event: string }>(`${API_BASE}/api/court-discuss/fate`),

  // ── OpenClaw Detection ──
  openclawDetect: () =>
    fetchJ<OpenClawDetectResult>(`${API_BASE}/api/openclaw-detect`),
  openclawImport: (sourcePath: string, items: string[]) =>
    postJ<OpenClawImportResult>(`${API_BASE}/api/openclaw-import`, { sourcePath, items }),

  // ── Channel Config ──
  channels: () =>
    fetchJ<ChannelsResult>(`${API_BASE}/api/channels`),
  addChannel: (data: AddChannelPayload) =>
    postJ<ActionResult & { channel?: ChannelInfo }>(`${API_BASE}/api/channels`, data),
  updateChannel: (id: string, data: Partial<ChannelInfo>) =>
    putJ<ActionResult & { channel?: ChannelInfo }>(`${API_BASE}/api/channels/${id}`, data),
  deleteChannel: (id: string) =>
    deleteJ<ActionResult>(`${API_BASE}/api/channels/${id}`),
  testChannel: (id: string) =>
    postJ<ActionResult>(`${API_BASE}/api/channels/${id}/test`, {}),
  setDefaultChannels: (data: { default_dispatch_channel?: string; default_morning_channel?: string }) =>
    postJ<ActionResult>(`${API_BASE}/api/channels/set-default`, data),

  // ── Auth ──
  authLogin: (data: { email?: string; name?: string; password?: string }) =>
    postJ<AuthLoginResult>(`${API_BASE}/api/auth/login`, data),
  authEnvLogin: () =>
    postJ<AuthLoginResult>(`${API_BASE}/api/auth/env-login`, {}),
  authGoogle: (credential: string) =>
    postJ<AuthLoginResult>(`${API_BASE}/api/auth/google`, { credential }),
  authConfig: () =>
    fetchJ<AuthConfigResult>(`${API_BASE}/api/auth/config`),
  authLogout: () =>
    postJ<ActionResult>(`${API_BASE}/api/auth/logout`, {}),
  authMe: () =>
    fetchJ<AuthMeResult>(`${API_BASE}/api/auth/me`),
  authSaveApiKey: (data: { provider?: string; api_key?: string; model_endpoint?: string; preferred_model?: string }) =>
    postJ<ActionResult>(`${API_BASE}/api/auth/api-key`, data),
  authModels: () =>
    fetchJ<{ ok: boolean; models: { id: string; label: string; provider: string }[]; hasPersonalKey: boolean }>(`${API_BASE}/api/auth/models`),

  // Token helpers
  setToken: (token: string | null) => setStoredToken(token),
  getToken: () => getStoredToken(),
};

// ── Types ──

export interface ActionResult {
  ok: boolean;
  message?: string;
  error?: string;
}

export interface FlowEntry {
  at: string;
  from: string;
  to: string;
  remark: string;
}

export interface TodoItem {
  id: string | number;
  title: string;
  status: 'not-started' | 'in-progress' | 'completed';
  detail?: string;
}

export interface Heartbeat {
  status: 'active' | 'warn' | 'stalled' | 'unknown' | 'idle';
  label: string;
}

export interface Task {
  id: string;
  title: string;
  state: string;
  org: string;
  now: string;
  eta: string;
  block: string;
  ac: string;
  output: string;
  heartbeat: Heartbeat;
  flow_log: FlowEntry[];
  todos: TodoItem[];
  review_round: number;
  archived: boolean;
  archivedAt?: string;
  updatedAt?: string;
  sourceMeta?: Record<string, unknown>;
  activity?: ActivityEntry[];
  _prev_state?: string;
}

export interface SyncStatus {
  ok: boolean;
  [key: string]: unknown;
}

export interface LiveStatus {
  tasks: Task[];
  syncStatus: SyncStatus;
}

export interface AgentInfo {
  id: string;
  label: string;
  emoji: string;
  role: string;
  model: string;
  skills: SkillInfo[];
}

export interface SkillInfo {
  name: string;
  description: string;
  path: string;
}

export interface KnownModel {
  id: string;
  label: string;
  provider: string;
}

export interface AgentConfig {
  agents: AgentInfo[];
  knownModels?: KnownModel[];
  dispatchChannel?: string;
}

export interface ChangeLogEntry {
  at: string;
  agentId: string;
  oldModel: string;
  newModel: string;
  rolledBack?: boolean;
}

export interface OfficialInfo {
  id: string;
  label: string;
  emoji: string;
  role: string;
  rank: string;
  model: string;
  model_short: string;
  tokens_in: number;
  tokens_out: number;
  cache_read: number;
  cache_write: number;
  cost_cny: number;
  cost_usd: number;
  sessions: number;
  messages: number;
  tasks_done: number;
  tasks_active: number;
  flow_participations: number;
  merit_score: number;
  merit_rank: number;
  last_active: string;
  heartbeat: Heartbeat;
  participated_tasks: { id: string; title: string; state: string }[];
}

export interface OfficialsData {
  officials: OfficialInfo[];
  totals: { tasks_done: number; cost_cny: number };
  top_official: string;
}

export interface AgentStatusInfo {
  id: string;
  label: string;
  emoji: string;
  role: string;
  status: 'running' | 'idle' | 'offline' | 'unconfigured';
  statusLabel: string;
  lastActive?: string;
}

export interface GatewayStatus {
  alive: boolean;
  probe: boolean;
  status: string;
}

export interface AgentsStatusData {
  ok: boolean;
  gateway: GatewayStatus;
  agents: AgentStatusInfo[];
  checkedAt: string;
}

export interface MorningNewsItem {
  title: string;
  summary?: string;
  desc?: string;
  link: string;
  source: string;
  image?: string;
  pub_date?: string;
}

export interface MorningBrief {
  date?: string;
  generated_at?: string;
  categories: Record<string, MorningNewsItem[]>;
}

export interface SubCategoryConfig {
  name: string;
  enabled: boolean;
}

export interface CustomFeed {
  name: string;
  url: string;
  category: string;
}

export interface SubConfig {
  categories: SubCategoryConfig[];
  keywords: string[];
  custom_feeds: CustomFeed[];
  feishu_webhook: string;
}

export interface ActivityEntry {
  kind: string;
  at?: number | string;
  text?: string;
  thinking?: string;
  agent?: string;
  from?: string;
  to?: string;
  remark?: string;
  tools?: { name: string; input_preview?: string }[];
  tool?: string;
  output?: string;
  exitCode?: number | null;
  items?: TodoItem[];
  diff?: {
    changed?: { id: string; from: string; to: string }[];
    added?: { id: string; title: string }[];
    removed?: { id: string; title: string }[];
  };
}

export interface PhaseDuration {
  phase: string;
  durationSec: number;
  durationText: string;
  ongoing?: boolean;
}

export interface TodosSummary {
  total: number;
  completed: number;
  inProgress: number;
  notStarted: number;
  percent: number;
}

export interface ResourceSummary {
  totalTokens?: number;
  totalCost?: number;
  totalElapsedSec?: number;
}

export interface TaskActivityData {
  ok: boolean;
  message?: string;
  error?: string;
  activity?: ActivityEntry[];
  relatedAgents?: string[];
  agentLabel?: string;
  lastActive?: string;
  phaseDurations?: PhaseDuration[];
  totalDuration?: string;
  todosSummary?: TodosSummary;
  resourceSummary?: ResourceSummary;
}

export interface SchedulerInfo {
  retryCount?: number;
  escalationLevel?: number;
  lastDispatchStatus?: string;
  stallThresholdSec?: number;
  enabled?: boolean;
  lastProgressAt?: string;
  lastDispatchAt?: string;
  lastDispatchAgent?: string;
  autoRollback?: boolean;
}

export interface SchedulerStateData {
  ok: boolean;
  error?: string;
  scheduler?: SchedulerInfo;
  stalledSec?: number;
}

export interface SkillContentResult {
  ok: boolean;
  name?: string;
  agent?: string;
  content?: string;
  path?: string;
  error?: string;
}

export interface ScanAction {
  taskId: string;
  action: string;
  to?: string;
  toState?: string;
  stalledSec?: number;
}

export interface CreateTaskPayload {
  title: string;
  org: string;
  targetDept?: string;
  priority?: string;
  templateId?: string;
  params?: Record<string, string>;
}

export interface RemoteSkillItem {
  skillName: string;
  agentId: string;
  sourceUrl: string;
  description: string;
  localPath: string;
  addedAt: string;
  lastUpdated: string;
  status: 'valid' | 'not-found' | string;
}

export interface RemoteSkillsListResult {
  ok: boolean;
  remoteSkills?: RemoteSkillItem[];
  count?: number;
  listedAt?: string;
  error?: string;
}

// ── 指令下达 ──

export interface Insight {
  id: string;
  title: string;
  summary: string;
  source: string;
  suggestedAction: string;
  createdAt: string;
  status: 'pending' | 'confirmed' | 'rejected';
  confirmedAt: string | null;
  rejectedAt: string | null;
  taskId: string | null;
}

// ── 圆桌议事 ──

export interface CourtDiscussResult {
  ok: boolean;
  session_id?: string;
  topic?: string;
  round?: number;
  new_messages?: Array<{
    official_id: string;
    name: string;
    content: string;
    emotion?: string;
    action?: string;
  }>;
  scene_note?: string;
  total_messages?: number;
  error?: string;
}

// ── OpenClaw Detection ──

export interface WorkspaceFile {
  name: string;
  path: string;
  size: number;
  size_fmt: string;
  modified: string;
}

export interface InheritableItem {
  key: string;
  label: string;
  label_zh: string;
  description: string;
  category: 'safe' | 'caution' | 'skip';
  default_checked: boolean;
}

export interface OpenClawInstallation {
  found: boolean;
  path: string;
  source: string;
  config_path: string;
  agents: { id: string; workspace: string }[];
  workspaces: string[];
  workspace_files: WorkspaceFile[];
  skills: { name: string; path: string; is_symlink: boolean }[];
  memory_db: { path: string; size: number; size_fmt: string; chunks: number; files: number; status: string } | null;
  auth_profiles_found: boolean;
  auth_providers?: string[];
  sessions_count: number;
  extensions: string[];
  daily_memory_logs: string[];
  default_model?: string;
  inheritable_items: InheritableItem[];
}

export interface OpenClawDetectResult {
  ok: boolean;
  found: boolean;
  installations: OpenClawInstallation[];
  scanned_paths: string[];
  scanned_at: string;
}

export interface OpenClawImportResult {
  ok: boolean;
  imported: { key: string; detail: string }[];
  skipped: { key: string; reason: string }[];
  errors: { key: string; error: string }[];
  imported_at?: string;
}

// ── Channel Config ──

export interface ChannelInfo {
  id: string;
  type: string;
  name: string;
  webhook_url: string;
  enabled: boolean;
  purposes: string[];
  created_at: string;
  updated_at?: string;
}

export interface ChannelTypeMeta {
  label: string;
  icon: string;
  webhook_hint: string;
}

export interface ChannelsResult {
  ok: boolean;
  channels: ChannelInfo[];
  default_dispatch_channel: string | null;
  default_morning_channel: string | null;
  types: Record<string, ChannelTypeMeta>;
}

export interface AddChannelPayload {
  type: string;
  name: string;
  webhook_url: string;
  purposes: string[];
}

// ── Auth ──

export interface UserInfo {
  id: string;
  happycapy_id: string | null;
  google_id: string | null;
  email: string;
  name: string;
  model_endpoint: string | null;
  preferred_model: string | null;
  provider?: string;
  created_at: string;
  last_login?: string;
}

export interface AuthConfigResult {
  ok: boolean;
  google_client_id: string;
  has_env_login: boolean;
}

export interface AuthLoginResult {
  ok: boolean;
  token?: string;
  user?: UserInfo;
  error?: string;
}

export interface AuthMeResult {
  ok: boolean;
  user?: UserInfo;
  authenticated?: boolean;
}
