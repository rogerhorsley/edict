import { useEffect, useRef, useState } from 'react';
import { useStore } from '../store';
import { api, type OpenClawDetectResult, type OpenClawInstallation, type ChannelsResult, type ChannelInfo } from '../api';

// ── OpenClaw Detection Section ──

function OpenClawSection() {
  const toast = useStore((s) => s.toast);
  const [detecting, setDetecting] = useState(false);
  const [result, setResult] = useState<OpenClawDetectResult | null>(null);
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<{ imported: string[]; errors: string[] } | null>(null);

  const runDetect = async () => {
    setDetecting(true);
    setImportResult(null);
    try {
      const r = await api.openclawDetect();
      setResult(r);
      // Pre-check default items
      if (r.installations?.length) {
        const defaults: Record<string, boolean> = {};
        for (const inst of r.installations) {
          for (const item of inst.inheritable_items || []) {
            defaults[item.key] = item.default_checked;
          }
        }
        setChecked(defaults);
      }
    } catch {
      toast('OpenClaw detection failed', 'err');
    } finally {
      setDetecting(false);
    }
  };

  useEffect(() => { runDetect(); }, []);

  const handleImport = async (inst: OpenClawInstallation) => {
    const selected = Object.entries(checked).filter(([, v]) => v).map(([k]) => k);
    if (selected.length === 0) {
      toast('Please select at least one item', 'err');
      return;
    }
    setImporting(true);
    try {
      const r = await api.openclawImport(inst.path, selected);
      setImportResult({
        imported: r.imported?.map((i) => `${i.key}: ${i.detail}`) || [],
        errors: r.errors?.map((e) => `${e.key}: ${e.error}`) || [],
      });
      if (r.ok) toast('Import completed', 'ok');
      else toast('Import had errors', 'err');
    } catch {
      toast('Import failed', 'err');
    } finally {
      setImporting(false);
    }
  };

  const toggleItem = (key: string) => {
    setChecked((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="setup-section">
      <div className="sec-title">OpenClaw / AutoClaw 检测</div>

      {detecting && <div className="setup-status">Scanning...</div>}

      {result && !result.found && (
        <div className="setup-empty">
          <div>未检测到本地 OpenClaw 安装</div>
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
            已扫描: {result.scanned_paths?.join(', ')}
          </div>
          <button className="btn btn-g" onClick={runDetect} style={{ marginTop: 8 }}>重新检测</button>
        </div>
      )}

      {result?.installations?.map((inst) => (
        <div key={inst.path} className="setup-card">
          <div className="setup-card-header">
            <span className="setup-badge ok">{inst.source}</span>
            <span style={{ fontSize: 12, color: 'var(--muted)' }}>{inst.path}</span>
          </div>

          <div className="setup-stats">
            <div className="setup-stat">
              <span className="setup-stat-val">{inst.agents.length}</span>
              <span className="setup-stat-label">Agents</span>
            </div>
            <div className="setup-stat">
              <span className="setup-stat-val">{inst.skills.length}</span>
              <span className="setup-stat-label">Skills</span>
            </div>
            <div className="setup-stat">
              <span className="setup-stat-val">{inst.sessions_count}</span>
              <span className="setup-stat-label">Sessions</span>
            </div>
            <div className="setup-stat">
              <span className="setup-stat-val">{inst.memory_db?.size_fmt || '-'}</span>
              <span className="setup-stat-label">Memory DB</span>
            </div>
            {inst.default_model && (
              <div className="setup-stat">
                <span className="setup-stat-val" style={{ fontSize: 11 }}>{inst.default_model}</span>
                <span className="setup-stat-label">Default Model</span>
              </div>
            )}
          </div>

          <div style={{ marginTop: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Inheritable Items:</div>
            {inst.inheritable_items?.map((item) => (
              <label key={item.key} className={`setup-check ${item.category}`}>
                <input
                  type="checkbox"
                  checked={!!checked[item.key]}
                  onChange={() => toggleItem(item.key)}
                />
                <span className="setup-check-label">
                  <span>{item.label_zh}</span>
                  {item.category === 'caution' && <span className="setup-badge warn">sensitive</span>}
                  {item.category === 'skip' && <span className="setup-badge skip">not recommended</span>}
                </span>
                <span className="setup-check-desc">{item.description}</span>
              </label>
            ))}
          </div>

          <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
            <button
              className="btn btn-p"
              disabled={importing}
              onClick={() => handleImport(inst)}
            >
              {importing ? 'Importing...' : 'Import Selected'}
            </button>
            <button className="btn btn-g" onClick={runDetect}>Refresh</button>
          </div>

          {importResult && (
            <div className="setup-import-result" style={{ marginTop: 8 }}>
              {importResult.imported.map((msg, i) => (
                <div key={i} style={{ color: 'var(--success)', fontSize: 12 }}>OK: {msg}</div>
              ))}
              {importResult.errors.map((msg, i) => (
                <div key={i} style={{ color: 'var(--danger)', fontSize: 12 }}>ERR: {msg}</div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ── Channel Configuration Section ──

const PURPOSE_OPTIONS = [
  { key: 'dispatch', label: 'Task Dispatch' },
  { key: 'morning', label: 'Morning Brief' },
  { key: 'alerts', label: 'Alerts' },
];

function ChannelSection() {
  const toast = useStore((s) => s.toast);
  const [data, setData] = useState<ChannelsResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [formType, setFormType] = useState('feishu');
  const [formName, setFormName] = useState('');
  const [formUrl, setFormUrl] = useState('');
  const [formPurposes, setFormPurposes] = useState<string[]>(['dispatch']);
  const [editId, setEditId] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);

  const loadChannels = async () => {
    setLoading(true);
    try {
      const r = await api.channels();
      setData(r);
    } catch {
      toast('Failed to load channels', 'err');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadChannels(); }, []);

  const handleAdd = async () => {
    if (!formName.trim()) {
      toast('Name is required', 'err');
      return;
    }
    try {
      const r = await api.addChannel({
        type: formType,
        name: formName.trim(),
        webhook_url: formUrl.trim(),
        purposes: formPurposes,
      });
      if (r.ok) {
        toast('Channel added', 'ok');
        setShowForm(false);
        setFormName('');
        setFormUrl('');
        setFormPurposes(['dispatch']);
        loadChannels();
      } else {
        toast(r.error || 'Failed', 'err');
      }
    } catch {
      toast('Failed to add channel', 'err');
    }
  };

  const handleUpdate = async (ch: ChannelInfo) => {
    try {
      const r = await api.updateChannel(ch.id, {
        name: formName.trim() || ch.name,
        webhook_url: formUrl.trim(),
        purposes: formPurposes,
        enabled: ch.enabled,
      });
      if (r.ok) {
        toast('Channel updated', 'ok');
        setEditId(null);
        loadChannels();
      }
    } catch {
      toast('Failed to update', 'err');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      const r = await api.deleteChannel(id);
      if (r.ok) {
        toast('Channel deleted', 'ok');
        loadChannels();
      }
    } catch {
      toast('Failed to delete', 'err');
    }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const r = await api.testChannel(id);
      if (r.ok) toast('Test message sent', 'ok');
      else toast(r.error || 'Test failed', 'err');
    } catch {
      toast('Test failed', 'err');
    } finally {
      setTesting(null);
    }
  };

  const handleSetDefault = async (field: 'default_dispatch_channel' | 'default_morning_channel', value: string) => {
    try {
      const r = await api.setDefaultChannels({ [field]: value || null });
      if (r.ok) {
        toast('Default updated', 'ok');
        loadChannels();
      }
    } catch {
      toast('Failed', 'err');
    }
  };

  const togglePurpose = (p: string) => {
    setFormPurposes((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  };

  const typesMeta = data?.types || {};
  const channels = data?.channels || [];

  const startEdit = (ch: ChannelInfo) => {
    setEditId(ch.id);
    setFormName(ch.name);
    setFormUrl(ch.webhook_url);
    setFormPurposes(ch.purposes || []);
    setFormType(ch.type);
  };

  const maskUrl = (url: string) => {
    if (!url) return '(empty)';
    if (url.length < 20) return url;
    return url.substring(0, 30) + '...' + url.substring(url.length - 10);
  };

  return (
    <div className="setup-section">
      <div className="sec-title">渠道配置 (Channel Configuration)</div>

      {loading && <div className="setup-status">Loading...</div>}

      {/* Channel List */}
      <div className="setup-channel-list">
        {channels.map((ch) => (
          <div key={ch.id} className={`setup-card ${!ch.enabled ? 'disabled' : ''}`}>
            {editId === ch.id ? (
              /* Edit Mode */
              <div>
                <div style={{ marginBottom: 8, fontWeight: 600 }}>Edit: {ch.id}</div>
                <input className="setup-input" value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="Name" />
                <input className="setup-input" value={formUrl} onChange={(e) => setFormUrl(e.target.value)}
                  placeholder={typesMeta[ch.type]?.webhook_hint || 'Webhook URL'} style={{ marginTop: 4 }} />
                <div style={{ marginTop: 4, display: 'flex', gap: 6 }}>
                  {PURPOSE_OPTIONS.map((po) => (
                    <label key={po.key} style={{ fontSize: 12, display: 'flex', gap: 3, alignItems: 'center' }}>
                      <input type="checkbox" checked={formPurposes.includes(po.key)} onChange={() => togglePurpose(po.key)} />
                      {po.label}
                    </label>
                  ))}
                </div>
                <div style={{ marginTop: 8, display: 'flex', gap: 6 }}>
                  <button className="btn btn-p" onClick={() => handleUpdate(ch)}>Save</button>
                  <button className="btn btn-g" onClick={() => setEditId(null)}>Cancel</button>
                </div>
              </div>
            ) : (
              /* View Mode */
              <>
                <div className="setup-card-header">
                  <span>{typesMeta[ch.type]?.icon || '📡'} <b>{ch.name}</b></span>
                  <span className={`setup-badge ${ch.enabled ? 'ok' : 'skip'}`}>
                    {ch.enabled ? 'enabled' : 'disabled'}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)', margin: '4px 0' }}>
                  {typesMeta[ch.type]?.label || ch.type} | {maskUrl(ch.webhook_url)}
                </div>
                <div style={{ fontSize: 11 }}>
                  Purposes: {(ch.purposes || []).join(', ') || 'none'}
                </div>
                <div style={{ marginTop: 8, display: 'flex', gap: 6 }}>
                  <button className="btn btn-g" onClick={() => startEdit(ch)}>Edit</button>
                  <button className="btn btn-g" disabled={testing === ch.id} onClick={() => handleTest(ch.id)}>
                    {testing === ch.id ? 'Testing...' : 'Test'}
                  </button>
                  <button className="btn" style={{ color: 'var(--danger)' }} onClick={() => handleDelete(ch.id)}>Delete</button>
                </div>
              </>
            )}
          </div>
        ))}

        {channels.length === 0 && !loading && (
          <div className="setup-empty">No channels configured</div>
        )}
      </div>

      {/* Add Channel Form */}
      {showForm ? (
        <div className="setup-card" style={{ marginTop: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Add Channel</div>
          <select className="msel" value={formType} onChange={(e) => setFormType(e.target.value)} style={{ marginBottom: 4 }}>
            {Object.entries(typesMeta).map(([k, v]) => (
              <option key={k} value={k}>{v.icon} {v.label}</option>
            ))}
          </select>
          <input className="setup-input" value={formName} onChange={(e) => setFormName(e.target.value)} placeholder="Channel name" />
          <input className="setup-input" value={formUrl} onChange={(e) => setFormUrl(e.target.value)}
            placeholder={typesMeta[formType]?.webhook_hint || 'Webhook URL'} style={{ marginTop: 4 }} />
          <div style={{ marginTop: 4, display: 'flex', gap: 6 }}>
            {PURPOSE_OPTIONS.map((po) => (
              <label key={po.key} style={{ fontSize: 12, display: 'flex', gap: 3, alignItems: 'center' }}>
                <input type="checkbox" checked={formPurposes.includes(po.key)} onChange={() => togglePurpose(po.key)} />
                {po.label}
              </label>
            ))}
          </div>
          <div style={{ marginTop: 8, display: 'flex', gap: 6 }}>
            <button className="btn btn-p" onClick={handleAdd}>Add</button>
            <button className="btn btn-g" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </div>
      ) : (
        <button className="btn btn-p" style={{ marginTop: 12 }} onClick={() => {
          setShowForm(true);
          setFormName('');
          setFormUrl('');
          setFormPurposes(['dispatch']);
        }}>+ Add Channel</button>
      )}

      {/* Default Channel Selectors */}
      {channels.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Default Channels:</div>
          <div style={{ display: 'flex', gap: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 2 }}>Dispatch:</div>
              <select className="msel" style={{ maxWidth: 200 }}
                value={data?.default_dispatch_channel || ''}
                onChange={(e) => handleSetDefault('default_dispatch_channel', e.target.value)}>
                <option value="">(none)</option>
                {channels.map((ch) => <option key={ch.id} value={ch.id}>{ch.name}</option>)}
              </select>
            </div>
            <div>
              <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 2 }}>Morning Brief:</div>
              <select className="msel" style={{ maxWidth: 200 }}
                value={data?.default_morning_channel || ''}
                onChange={(e) => handleSetDefault('default_morning_channel', e.target.value)}>
                <option value="">(none)</option>
                {channels.map((ch) => <option key={ch.id} value={ch.id}>{ch.name}</option>)}
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Account/Login Section ──

function AccountSection() {
  const toast = useStore((s) => s.toast);
  const user = useStore((s) => s.user);
  const isAuthenticated = useStore((s) => s.isAuthenticated);
  const login = useStore((s) => s.login);
  const logout = useStore((s) => s.logout);

  const [loginEmail, setLoginEmail] = useState('');
  const [loginName, setLoginName] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loggingIn, setLoggingIn] = useState(false);
  const [authConfig, setAuthConfig] = useState<{ google_client_id: string; has_env_login: boolean } | null>(null);
  const [googleLoaded, setGoogleLoaded] = useState(false);
  const googleBtnRef = useRef<HTMLDivElement>(null);

  // API Key form
  const [apiProvider, setApiProvider] = useState('anthropic');
  const [apiKey, setApiKey] = useState('');
  const [modelEndpoint, setModelEndpoint] = useState('');
  const [preferredModel, setPreferredModel] = useState('');
  const [savingKey, setSavingKey] = useState(false);

  // Load auth config and attempt env auto-login
  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Load auth config
      try {
        const cfg = await api.authConfig();
        if (!cancelled && cfg.ok) setAuthConfig(cfg);
      } catch { /* ignore */ }

      // Attempt HappyCapy env auto-login if not authenticated
      if (!isAuthenticated) {
        try {
          const r = await api.authEnvLogin();
          if (!cancelled && r.ok && r.token) {
            await login(r.token);
          }
        } catch { /* not in HappyCapy env */ }
      }
    })();
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Load Google Identity Services script
  useEffect(() => {
    const gcid = authConfig?.google_client_id;
    if (!gcid || isAuthenticated) return;
    if (document.getElementById('google-gsi-script')) {
      setGoogleLoaded(true);
      return;
    }
    const script = document.createElement('script');
    script.id = 'google-gsi-script';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => setGoogleLoaded(true);
    document.body.appendChild(script);
  }, [authConfig?.google_client_id, isAuthenticated]);

  // Render Google Sign-In button
  useEffect(() => {
    const gcid = authConfig?.google_client_id;
    if (!gcid || !googleLoaded || !window.google || isAuthenticated || !googleBtnRef.current) return;

    window.google.accounts.id.initialize({
      client_id: gcid,
      callback: async (response) => {
        setLoggingIn(true);
        try {
          const r = await api.authGoogle(response.credential);
          if (r.ok && r.token) {
            await login(r.token);
            toast('Logged in with Google', 'ok');
          } else {
            toast(r.error || 'Google login failed', 'err');
          }
        } catch {
          toast('Google login failed', 'err');
        } finally {
          setLoggingIn(false);
        }
      },
    });

    window.google.accounts.id.renderButton(googleBtnRef.current, {
      type: 'standard',
      size: 'large',
      theme: 'outline',
      text: 'signin_with',
      width: 280,
    });
  }, [googleLoaded, isAuthenticated, authConfig?.google_client_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleLogin = async () => {
    if (!loginEmail.trim()) {
      toast('Email is required', 'err');
      return;
    }
    setLoggingIn(true);
    try {
      const r = await api.authLogin({
        email: loginEmail,
        name: loginName || undefined,
        password: loginPassword || undefined,
      });
      if (r.ok && r.token) {
        await login(r.token);
        toast('Login success', 'ok');
        setLoginEmail('');
        setLoginName('');
        setLoginPassword('');
      } else {
        toast(r.error || 'Login failed', 'err');
      }
    } catch {
      toast('Login failed', 'err');
    } finally {
      setLoggingIn(false);
    }
  };

  const handleLogout = async () => {
    await api.authLogout();
    logout();
    toast('Logged out', 'ok');
  };

  const handleSaveApiKey = async () => {
    setSavingKey(true);
    try {
      const r = await api.authSaveApiKey({
        provider: apiProvider,
        api_key: apiKey || undefined,
        model_endpoint: modelEndpoint || undefined,
        preferred_model: preferredModel || undefined,
      });
      if (r.ok) {
        toast('API settings saved', 'ok');
        setApiKey('');
      } else {
        toast(r.error || 'Failed', 'err');
      }
    } catch {
      toast('Save failed', 'err');
    } finally {
      setSavingKey(false);
    }
  };

  return (
    <div className="setup-section">
      <div className="sec-title">Account / Login</div>

      {isAuthenticated && user ? (
        <div className="setup-card">
          <div className="setup-card-header">
            <span><b>{user.name}</b></span>
            <span className="setup-badge ok">logged in</span>
          </div>
          <div style={{ fontSize: 12, color: 'var(--muted)', margin: '4px 0' }}>
            {user.email}
            {user.happycapy_id && ` | HappyCapy`}
            {user.google_id && ` | Google`}
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)' }}>
            Last login: {user.last_login || 'N/A'}
          </div>

          {/* API Key Settings */}
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Personal API Key:</div>
            <select className="msel" value={apiProvider} onChange={(e) => setApiProvider(e.target.value)}
              style={{ maxWidth: 200, marginBottom: 4 }}>
              <option value="anthropic">Anthropic</option>
              <option value="openai">OpenAI</option>
              <option value="google">Google</option>
            </select>
            <input className="setup-input" type="password" value={apiKey}
              onChange={(e) => setApiKey(e.target.value)} placeholder="API Key" />
            <input className="setup-input" value={modelEndpoint}
              onChange={(e) => setModelEndpoint(e.target.value)}
              placeholder="Model Endpoint (optional)" style={{ marginTop: 4 }} />
            <select className="msel" value={preferredModel} onChange={(e) => setPreferredModel(e.target.value)}
              style={{ maxWidth: 300, marginTop: 4 }}>
              <option value="">Default Model</option>
              <option value="anthropic/claude-sonnet-4-6">Claude Sonnet 4.6</option>
              <option value="anthropic/claude-opus-4-5">Claude Opus 4.5</option>
              <option value="openai/gpt-4o">GPT-4o</option>
              <option value="google/gemini-2.5-pro">Gemini 2.5 Pro</option>
            </select>
            <div style={{ marginTop: 8, display: 'flex', gap: 6 }}>
              <button className="btn btn-p" disabled={savingKey} onClick={handleSaveApiKey}>
                {savingKey ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>

          <div style={{ marginTop: 16 }}>
            <button className="btn" style={{ color: 'var(--danger)' }} onClick={handleLogout}>Logout</button>
          </div>
        </div>
      ) : (
        <div className="setup-card">
          {/* Google Sign-In */}
          {authConfig?.google_client_id && (
            <>
              <div ref={googleBtnRef} style={{ marginBottom: 12 }} />
              <div style={{ textAlign: 'center', margin: '8px 0', color: 'var(--muted)', fontSize: 12 }}>
                ──── or login with email ────
              </div>
            </>
          )}

          {/* Email login */}
          <input className="setup-input" value={loginEmail}
            onChange={(e) => setLoginEmail(e.target.value)} placeholder="Email"
            onKeyDown={(e) => e.key === 'Enter' && handleLogin()} />
          <input className="setup-input" type="password" value={loginPassword}
            onChange={(e) => setLoginPassword(e.target.value)}
            placeholder="Password (optional)" style={{ marginTop: 4 }}
            onKeyDown={(e) => e.key === 'Enter' && handleLogin()} />
          <input className="setup-input" value={loginName}
            onChange={(e) => setLoginName(e.target.value)}
            placeholder="Name (optional, for new accounts)" style={{ marginTop: 4 }} />

          <button className="btn btn-p" style={{ marginTop: 8 }} disabled={loggingIn} onClick={handleLogin}>
            {loggingIn ? 'Logging in...' : 'Login'}
          </button>

          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 8 }}>
            Login to use your personal API keys and model preferences. The dashboard works without login.
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main SetupPanel ──

export default function SetupPanel() {
  return (
    <div className="setup-panel">
      <AccountSection />
      <ChannelSection />
      <OpenClawSection />
    </div>
  );
}
