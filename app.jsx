// app.jsx — DWCOA shell: auth, nav, topbar, theme, tweaks, routing.
const { useState: u, useEffect: ue, useRef: ur } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "dark": false,
  "accent": ["#0F6E45", "#0C402B", "#E7F2EB"],
  "density": "comfortable",
  "monoFigures": false
}/*EDITMODE-END*/;

const ACCENTS = {
  '#0F6E45': { name: 'Evergreen', brand: '#0F6E45', ink: '#0C402B', soft: '#E7F2EB', on: '#FFFFFF', dBrand: '#34A772', dInk: '#6FBE96', dSoft: '#16271E', dOn: '#06140D' },
  '#2A5BD7': { name: 'Indigo',    brand: '#2A5BD7', ink: '#1E3F95', soft: '#E7ECFB', on: '#FFFFFF', dBrand: '#6E92F0', dInk: '#A9BEF7', dSoft: '#15203A', dOn: '#07112B' },
  '#0E7C86': { name: 'Teal',      brand: '#0E7C86', ink: '#0A4D54', soft: '#E1F2F3', on: '#FFFFFF', dBrand: '#3CB6BF', dInk: '#79D4DA', dSoft: '#10282A', dOn: '#04181A' },
  '#7A4FD0': { name: 'Plum',      brand: '#7A4FD0', ink: '#553398', soft: '#F0EAFB', on: '#FFFFFF', dBrand: '#A484E8', dInk: '#C4ADF2', dSoft: '#221A38', dOn: '#100726' },
};

function applyTheme(t) {
  const root = document.documentElement;
  root.setAttribute('data-theme', t.dark ? 'dark' : 'light');
  root.setAttribute('data-density', t.density);
  const key = Array.isArray(t.accent) ? t.accent[0] : t.accent;
  const a = ACCENTS[key] || ACCENTS['#0F6E45'];
  if (t.dark) { root.style.setProperty('--brand', a.dBrand); root.style.setProperty('--brand-ink', a.dInk); root.style.setProperty('--brand-soft', a.dSoft); root.style.setProperty('--on-brand', a.dOn); }
  else { root.style.setProperty('--brand', a.brand); root.style.setProperty('--brand-ink', a.ink); root.style.setProperty('--brand-soft', a.soft); root.style.setProperty('--on-brand', a.on); }
  document.body.style.fontFeatureSettings = t.monoFigures ? '"tnum" 1' : '"ss01","cv01"';
}

// ---------- Toasts ----------
function useToasts() {
  const [toasts, setToasts] = u([]);
  function notify(msg, icon = 'check') {
    const id = Date.now() + Math.random();
    setToasts(t => [...t, { id, msg, icon }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 2600);
  }
  const node = (
    <div className="toast-wrap">
      {toasts.map(t => <div className="toast" key={t.id}><span className="tk">{II(t.icon, { width: 16, height: 16 })}</span>{t.msg}</div>)}
    </div>
  );
  return [notify, node];
}

// ---------- Login ----------
function Login({ onLogin }) {
  const [role, setRole] = u('admin');
  const [pw, setPw] = u('');
  const [err, setErr] = u(false);
  const [busy, setBusy] = u(false);
  function submit(e) {
    e.preventDefault();
    if (!pw) { setErr(true); return; }
    setBusy(true);
    setTimeout(() => onLogin(role), 420);
  }
  return (
    <div style={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '1.05fr .95fr', background: 'var(--bg)' }}>
      {/* brand panel */}
      <div style={{ background: 'linear-gradient(155deg, var(--green-700), var(--green-900))', color: '#fff', padding: '56px 60px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', position: 'relative', overflow: 'hidden' }} className="login-aside">
        <div style={{ position: 'absolute', inset: 0, opacity: .5, background: 'radial-gradient(600px 300px at 90% 0%, rgba(111,190,150,.35), transparent 60%)' }} />
        <div className="row gap-3" style={{ position: 'relative', zIndex: 1 }}>
          <span className="brand-mark" style={{ width: 40, height: 40 }}>{II('building', { width: 22, height: 22 })}</span>
          <div><div style={{ fontWeight: 700, fontSize: 16 }}>DWCOA Financials</div><div style={{ fontSize: 12, opacity: .7 }}>Denny Way Condo Owners Association</div></div>
        </div>
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ fontSize: 32, fontWeight: 700, letterSpacing: '-.03em', lineHeight: 1.1, maxWidth: 380 }}>Every dollar across nine homes, in one clear ledger.</div>
          <div className="row gap-5" style={{ marginTop: 32, flexWrap: 'wrap' }}>
            {[['$177k', 'Total cash'], ['9', 'Units'], ['96%', 'Dues collected']].map(([n, l], i) => (
              <div key={i}><div className="tnum" style={{ fontSize: 24, fontWeight: 700 }}>{n}</div><div style={{ fontSize: 12, opacity: .65 }}>{l}</div></div>
            ))}
          </div>
        </div>
        <div style={{ position: 'relative', zIndex: 1, fontSize: 12, opacity: .55 }}>Board-only access · Seattle, WA</div>
      </div>
      {/* form */}
      <div style={{ display: 'grid', placeItems: 'center', padding: 32 }}>
        <form onSubmit={submit} style={{ width: '100%', maxWidth: 340 }}>
          <h1 style={{ fontSize: 23, fontWeight: 700, letterSpacing: '-.02em', margin: '0 0 6px' }}>Welcome back</h1>
          <p className="muted" style={{ fontSize: 13.5, margin: '0 0 24px' }}>Sign in to the association ledger.</p>
          <div className="field" style={{ marginBottom: 14 }}>
            <label>Sign in as</label>
            <div className="seg" style={{ width: '100%' }}>
              <button type="button" className={role === 'admin' ? 'on' : ''} style={{ flex: 1 }} onClick={() => setRole('admin')}>Treasurer</button>
              <button type="button" className={role === 'viewer' ? 'on' : ''} style={{ flex: 1 }} onClick={() => setRole('viewer')}>Homeowner</button>
            </div>
          </div>
          <div className="field" style={{ marginBottom: 18 }}>
            <label>Password</label>
            <input className="input" type="password" autoFocus placeholder="••••••••" value={pw} onChange={e => { setPw(e.target.value); setErr(false); }} />
            {err && <span style={{ fontSize: 12, color: 'var(--neg)' }}>Enter any password to continue (demo).</span>}
          </div>
          <button className="btn primary" type="submit" style={{ width: '100%', height: 42 }} disabled={busy}>{busy ? 'Signing in…' : 'Log in'}{!busy && II('arrowUpRight', { width: 16, height: 16 })}</button>
          <p className="faint" style={{ fontSize: 11.5, textAlign: 'center', marginTop: 16 }}>Demo prototype · any password works</p>
        </form>
      </div>
    </div>
  );
}

// ---------- Shell ----------
const NAV = [
  { group: 'Finances', items: [
    { id: 'overview', label: 'Overview', icon: 'dashboard' },
    { id: 'transactions', label: 'Transactions', icon: 'receipt' },
    { id: 'dues', label: 'Dues by unit', icon: 'coins' },
    { id: 'budget', label: 'Budget', icon: 'pie' },
    { id: 'account', label: 'My account', icon: 'user' },
  ]},
  { group: 'Administration', adminOnly: true, items: [
    { id: 'review', label: 'Review queue', icon: 'inbox', badge: true },
    { id: 'rules', label: 'Categorization', icon: 'rules' },
    { id: 'import', label: 'Import CSV', icon: 'upload' },
  ]},
];
const TITLES = {
  overview: ['Overview', 'Association financial health at a glance'],
  transactions: ['Transactions', 'Every posted entry across all accounts'],
  dues: ['Dues by unit', 'Assessment tracking for all nine units'],
  budget: ['Budget', 'Annual plan by category'],
  account: ['My account', 'Your personal dues statement'],
  review: ['Review queue', 'Categorize imported transactions'],
  rules: ['Categorization rules', 'Teach the system to auto-categorize'],
  import: ['Import CSV', 'Bring in bank transactions'],
};

function Shell({ role, onLogout, t, setTweak }) {
  const [page, setPage] = u('overview');
  const [navOpen, setNavOpen] = u(false);
  const [notify, toastNode] = useToasts();
  const reviewCount = window.DW.REVIEW.length;
  const isAdmin = role === 'admin';
  function go(p) { setPage(p); setNavOpen(false); }

  const [title, sub] = TITLES[page] || ['', ''];
  const Page = {
    overview: <Overview go={go} role={role} />,
    transactions: <Transactions />,
    dues: <DuesPage />,
    budget: <Budget role={role} notify={notify} />,
    account: <MyAccount />,
    review: <ReviewQueue notify={notify} />,
    rules: <Rules notify={notify} />,
    import: <Import notify={notify} />,
  }[page];

  return (
    <div className="app">
      {navOpen && <div className="scrim-nav" onClick={() => setNavOpen(false)} />}
      <aside className={`sidebar ${navOpen ? 'open' : ''}`}>
        <div className="brand">
          <span className="brand-mark">{II('building', { width: 19, height: 19 })}</span>
          <div className="brand-text"><div className="brand-name">DWCOA</div><div className="brand-sub">Financials</div></div>
        </div>
        <nav className="nav">
          {NAV.map(grp => (grp.adminOnly && !isAdmin) ? null : (
            <React.Fragment key={grp.group}>
              <div className="nav-label">{grp.group}</div>
              {grp.items.map(it => (
                <button key={it.id} className={`nav-item ${page === it.id ? 'active' : ''}`} onClick={() => go(it.id)}>
                  {II(it.icon, {})}<span>{it.label}</span>
                  {it.badge && reviewCount > 0 && <span className="nav-count">{reviewCount}</span>}
                </button>
              ))}
            </React.Fragment>
          ))}
        </nav>
        <div className="sidebar-foot">
          <button className="userchip" onClick={onLogout} title="Log out">
            <span className="avatar">{isAdmin ? 'TR' : 'HO'}</span>
            <span className="uf-text"><span className="uf-name">{isAdmin ? 'Board Treasurer' : 'Homeowner'}</span><span className="uf-role">{isAdmin ? 'Full access' : 'Read-only'}</span></span>
            <span style={{ marginLeft: 'auto', color: 'var(--ink-3)', display: 'inline-flex' }}>{II('logout', { width: 16, height: 16 })}</span>
          </button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="btn icon ghost mobile-only" onClick={() => setNavOpen(true)}>{II('menu', { width: 18, height: 18 })}</button>
          <div>
            <div className="page-title">{title}</div>
            <div className="page-sub">{sub}</div>
          </div>
          <div className="topbar-actions">
            <span className="badge neutral" style={{ height: 34, padding: '0 12px' }}>{II('calendar', { width: 14, height: 14 })} As of {window.DW.fmtDate(window.DW.AS_OF)}</span>
            <div className="seg" title="Prototype: switch roles">
              <button className={isAdmin ? 'on' : ''} onClick={() => onLogout('admin')}>Treasurer</button>
              <button className={!isAdmin ? 'on' : ''} onClick={() => onLogout('viewer')}>Homeowner</button>
            </div>
            <button className="btn icon" onClick={() => setTweak('dark', !t.dark)} title="Toggle theme">{II(t.dark ? 'sun' : 'moon', { width: 17, height: 17 })}</button>
          </div>
        </header>
        <div key={page}>{Page}</div>
      </div>
      {toastNode}
    </div>
  );
}

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [auth, setAuth] = u(null); // null | role
  ue(() => applyTheme(t), [t.dark, t.accent, t.density, t.monoFigures]);

  // role switch from topbar re-auths without logout screen
  function handleAuthChange(roleOrUndef) {
    if (roleOrUndef === 'admin' || roleOrUndef === 'viewer') setAuth(roleOrUndef);
    else setAuth(null);
  }

  return (
    <>
      {auth ? <Shell role={auth} onLogout={handleAuthChange} t={t} setTweak={setTweak} />
            : <Login onLogin={(r) => setAuth(r)} />}

      <TweaksPanel>
        <TweakSection label="Appearance" />
        <TweakToggle label="Dark mode" value={t.dark} onChange={v => setTweak('dark', v)} />
        <TweakColor label="Accent" value={t.accent}
          options={[['#0F6E45','#0C402B','#E7F2EB'],['#2A5BD7','#1E3F95','#E7ECFB'],['#0E7C86','#0A4D54','#E1F2F3'],['#7A4FD0','#553398','#F0EAFB']]}
          onChange={v => setTweak('accent', v)} />
        <TweakSection label="Layout" />
        <TweakRadio label="Density" value={t.density} options={['compact','comfortable','spacious']} onChange={v => setTweak('density', v)} />
        <TweakToggle label="Mono figures" value={t.monoFigures} onChange={v => setTweak('monoFigures', v)} />
      </TweaksPanel>
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
