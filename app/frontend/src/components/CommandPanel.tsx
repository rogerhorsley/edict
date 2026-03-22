import { useState, useEffect } from 'react';
import { useStore, timeAgo } from '../store';
import { api, type Insight } from '../api';

export default function CommandPanel() {
  const pendingInsights = useStore((s) => s.pendingInsights);
  const loadInsights = useStore((s) => s.loadInsights);
  const loadAll = useStore((s) => s.loadAll);
  const toast = useStore((s) => s.toast);

  const [cmdTitle, setCmdTitle] = useState('');
  const [cmdDesc, setCmdDesc] = useState('');
  const [sending, setSending] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');

  useEffect(() => {
    loadInsights();
  }, [loadInsights]);

  // ── Issue Command ──
  const handleIssueCommand = async () => {
    if (!cmdTitle.trim()) return;
    setSending(true);
    try {
      const r = await api.issueCommand(cmdTitle.trim(), cmdDesc.trim());
      if (r.ok) {
        toast(`${r.taskId} 指令已下达`);
        setCmdTitle('');
        setCmdDesc('');
        loadAll();
      } else {
        toast(r.error || '下达失败', 'err');
      }
    } catch {
      toast('服务器连接失败', 'err');
    }
    setSending(false);
  };

  // ── Confirm Insight ──
  const handleConfirm = async (insight: Insight) => {
    try {
      const title = editingId === insight.id ? editTitle.trim() : undefined;
      const r = await api.confirmInsight(insight.id, title);
      if (r.ok) {
        toast(`${r.taskId} 任务已创建`);
        setEditingId(null);
        setEditTitle('');
        loadInsights();
        loadAll();
      } else {
        toast(r.error || '确认失败', 'err');
      }
    } catch {
      toast('服务器连接失败', 'err');
    }
  };

  // ── Reject Insight ──
  const handleReject = async (insightId: string) => {
    try {
      const r = await api.rejectInsight(insightId, rejectReason.trim());
      if (r.ok) {
        toast('洞察已驳回');
        setRejectingId(null);
        setRejectReason('');
        loadInsights();
      } else {
        toast(r.error || '驳回失败', 'err');
      }
    } catch {
      toast('服务器连接失败', 'err');
    }
  };

  return (
    <div style={{ padding: '0 8px' }}>
      {/* Section 1: Pending Insights */}
      <div className="cmd-section">
        <div className="cmd-section-title">
          <span>🔭 谋部洞察</span>
          <span style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 400, marginLeft: 8 }}>
            {pendingInsights.length} 条待审
          </span>
          <button
            className="btn-refresh"
            onClick={() => loadInsights()}
            style={{ marginLeft: 'auto', fontSize: 11, padding: '2px 8px' }}
          >
            刷新
          </button>
        </div>

        {pendingInsights.length === 0 ? (
          <div className="cmd-empty">
            暂无待审洞察
            <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
              谋部定时任务产出的洞察将在此显示，确认后自动创建任务
            </div>
          </div>
        ) : (
          <div className="cmd-insight-list">
            {pendingInsights.map((ins) => (
              <div className="cmd-insight-card" key={ins.id}>
                <div className="cmd-insight-header">
                  <span className="cmd-insight-id">{ins.id}</span>
                  <span className="cmd-insight-time">{timeAgo(ins.createdAt)}</span>
                </div>
                <div className="cmd-insight-title">{ins.title}</div>
                {ins.summary && (
                  <div className="cmd-insight-summary">{ins.summary}</div>
                )}
                <div className="cmd-insight-meta">
                  {ins.source && <span className="cmd-tag">来源: {ins.source}</span>}
                  {ins.suggestedAction && <span className="cmd-tag">建议: {ins.suggestedAction}</span>}
                </div>

                {/* Edit mode */}
                {editingId === ins.id && (
                  <div style={{ marginTop: 8 }}>
                    <input
                      className="cmd-input"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      placeholder="编辑后的任务标题..."
                      style={{ width: '100%', marginBottom: 6 }}
                    />
                  </div>
                )}

                {/* Reject reason */}
                {rejectingId === ins.id && (
                  <div style={{ marginTop: 8 }}>
                    <input
                      className="cmd-input"
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      placeholder="驳回原因（可选）..."
                      style={{ width: '100%', marginBottom: 6 }}
                    />
                    <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                      <button className="btn btn-g" onClick={() => setRejectingId(null)} style={{ fontSize: 11, padding: '4px 10px' }}>
                        取消
                      </button>
                      <button
                        className="btn"
                        onClick={() => handleReject(ins.id)}
                        style={{ fontSize: 11, padding: '4px 10px', background: 'var(--warn)', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
                      >
                        确认驳回
                      </button>
                    </div>
                  </div>
                )}

                {/* Actions */}
                {rejectingId !== ins.id && (
                  <div className="cmd-insight-actions">
                    <button
                      className="cmd-btn cmd-btn-primary"
                      onClick={() => handleConfirm(ins)}
                    >
                      {editingId === ins.id ? '确认（编辑后）' : '确认下发'}
                    </button>
                    {editingId !== ins.id ? (
                      <button
                        className="cmd-btn cmd-btn-edit"
                        onClick={() => { setEditingId(ins.id); setEditTitle(ins.title); }}
                      >
                        编辑后下发
                      </button>
                    ) : (
                      <button
                        className="cmd-btn cmd-btn-edit"
                        onClick={() => { setEditingId(null); setEditTitle(''); }}
                      >
                        取消编辑
                      </button>
                    )}
                    <button
                      className="cmd-btn cmd-btn-reject"
                      onClick={() => { setRejectingId(ins.id); setRejectReason(''); }}
                    >
                      驳回
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section 2: Direct Command Input */}
      <div className="cmd-section" style={{ marginTop: 24 }}>
        <div className="cmd-section-title">
          <span>📡 直接下达指令</span>
        </div>
        <div className="cmd-form">
          <input
            className="cmd-input cmd-input-main"
            value={cmdTitle}
            onChange={(e) => setCmdTitle(e.target.value)}
            placeholder="输入指令标题（如：分析竞品最新动态）..."
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleIssueCommand(); } }}
          />
          <textarea
            className="cmd-input cmd-input-desc"
            value={cmdDesc}
            onChange={(e) => setCmdDesc(e.target.value)}
            placeholder="补充说明（可选）..."
            rows={2}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            <button
              className="cmd-btn cmd-btn-primary cmd-btn-lg"
              onClick={handleIssueCommand}
              disabled={sending || !cmdTitle.trim()}
            >
              {sending ? '下达中...' : '📡 下达指令'}
            </button>
          </div>
        </div>
        <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 8 }}>
          指令将直接发送给谋部进行研究分析，研究完成后进入策枢 → 衡枢 → 行枢流程
        </div>
      </div>

      <style>{`
        .cmd-section {
          margin-bottom: 16px;
        }
        .cmd-section-title {
          display: flex;
          align-items: center;
          font-size: 14px;
          font-weight: 700;
          margin-bottom: 12px;
          padding-bottom: 8px;
          border-bottom: 1px solid var(--line);
        }
        .cmd-empty {
          text-align: center;
          padding: 32px 0;
          color: var(--muted);
          font-size: 13px;
        }
        .cmd-insight-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .cmd-insight-card {
          background: var(--panel2);
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 12px 14px;
        }
        .cmd-insight-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 6px;
        }
        .cmd-insight-id {
          font-size: 10px;
          color: var(--acc);
          font-family: monospace;
        }
        .cmd-insight-time {
          font-size: 10px;
          color: var(--muted);
        }
        .cmd-insight-title {
          font-size: 13px;
          font-weight: 600;
          margin-bottom: 4px;
        }
        .cmd-insight-summary {
          font-size: 12px;
          color: var(--muted);
          line-height: 1.5;
          margin-bottom: 6px;
        }
        .cmd-insight-meta {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin-bottom: 8px;
        }
        .cmd-tag {
          font-size: 10px;
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: 4px;
          padding: 2px 6px;
          color: var(--muted);
        }
        .cmd-insight-actions {
          display: flex;
          gap: 6px;
          margin-top: 6px;
        }
        .cmd-btn {
          font-size: 11px;
          padding: 4px 12px;
          border-radius: 4px;
          border: 1px solid var(--line);
          background: var(--panel);
          color: var(--text);
          cursor: pointer;
          transition: all 0.15s;
        }
        .cmd-btn:hover { opacity: 0.85; }
        .cmd-btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .cmd-btn-primary {
          background: var(--acc);
          color: #fff;
          border-color: var(--acc);
          font-weight: 600;
        }
        .cmd-btn-edit {
          color: var(--acc);
        }
        .cmd-btn-reject {
          color: var(--warn);
          border-color: var(--warn);
        }
        .cmd-btn-lg {
          font-size: 13px;
          padding: 8px 20px;
        }
        .cmd-form {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .cmd-input {
          background: var(--panel2);
          border: 1px solid var(--line);
          border-radius: 6px;
          padding: 8px 12px;
          font-size: 12px;
          color: var(--text);
          outline: none;
          font-family: inherit;
        }
        .cmd-input:focus {
          border-color: var(--acc);
        }
        .cmd-input-main {
          font-size: 14px;
          padding: 10px 14px;
        }
        .cmd-input-desc {
          resize: vertical;
          min-height: 40px;
        }
      `}</style>
    </div>
  );
}
