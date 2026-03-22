import { useEffect, useState } from 'react';
import { useStore } from '../store';
import { api } from '../api';

export default function LoginButton() {
  const user = useStore((s) => s.user);
  const isAuthenticated = useStore((s) => s.isAuthenticated);
  const logout = useStore((s) => s.logout);
  const login = useStore((s) => s.login);
  const loadUser = useStore((s) => s.loadUser);
  const setActiveTab = useStore((s) => s.setActiveTab);
  const [showMenu, setShowMenu] = useState(false);

  useEffect(() => {
    // First try to restore session from stored token
    loadUser().then(() => {
      // If no stored session, try HappyCapy env auto-login
      const token = api.getToken();
      if (!token) {
        api.authEnvLogin().then((r) => {
          if (r.ok && r.token) login(r.token);
        }).catch(() => { /* not in HappyCapy env */ });
      }
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (!isAuthenticated || !user) {
    return (
      <button
        className="btn btn-g"
        style={{ fontSize: 11, padding: '2px 8px' }}
        onClick={() => setActiveTab('setup')}
      >
        Login
      </button>
    );
  }

  return (
    <div style={{ position: 'relative' }}>
      <button
        className="btn btn-g"
        style={{ fontSize: 11, padding: '2px 8px' }}
        onClick={() => setShowMenu((prev) => !prev)}
      >
        {user.name}
      </button>
      {showMenu && (
        <div className="login-menu">
          <div className="login-menu-item" style={{ fontWeight: 600, borderBottom: '1px solid var(--border)' }}>
            {user.email}
          </div>
          <div className="login-menu-item" onClick={() => { setActiveTab('setup'); setShowMenu(false); }}>
            Settings
          </div>
          <div className="login-menu-item" style={{ color: 'var(--danger)' }} onClick={() => { logout(); setShowMenu(false); }}>
            Logout
          </div>
        </div>
      )}
    </div>
  );
}
