import { useEffect, useState } from 'react';
import { useStore } from '../store';

export default function LoginButton() {
  const user = useStore((s) => s.user);
  const isAuthenticated = useStore((s) => s.isAuthenticated);
  const logout = useStore((s) => s.logout);
  const loadUser = useStore((s) => s.loadUser);
  const setActiveTab = useStore((s) => s.setActiveTab);
  const [showMenu, setShowMenu] = useState(false);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

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
