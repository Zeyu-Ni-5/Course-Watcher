import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, AlertCircle, ArrowDown, ArrowUpRight, BookOpen, Check, CheckCheck, CircleHelp, ExternalLink, GraduationCap, LayoutDashboard, LoaderCircle, Pause, Plus, Radar, RefreshCw, Search, X } from 'lucide-react';
import { API_DOCS, ApiError, createWatch, deleteWatch, getHealth, listWatches, setWatchActive } from './api';
import type { Watch, WatchInput } from './types';
import ConfirmDelete from './components/ConfirmDelete';
import WatchCard from './components/WatchCard';
import WatchForm from './components/WatchForm';

type Filter = 'all' | 'active' | 'paused';

export default function App() {
  const [watches, setWatches] = useState<Watch[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState<Set<number>>(new Set());
  const [deleting, setDeleting] = useState<Watch | null>(null);
  const [health, setHealth] = useState<'checking' | 'online' | 'offline'>('checking');
  const listVersion = useRef(0);
  const busyIds = useRef(new Set<number>());
  const createPending = useRef(false);
  const active = watches.filter(watch => watch.active).length;
  const filtered = watches.filter(watch => filter === 'all' || (filter === 'active' ? watch.active : !watch.active));

  const load = useCallback(async () => {
    const version = ++listVersion.current;
    setLoading(true); setLoadError('');
    try { const rows = await listWatches(); if (version === listVersion.current) setWatches(rows); }
    catch (cause) { if (version === listVersion.current) setLoadError(message(cause)); }
    finally { if (version === listVersion.current) setLoading(false); }
  }, []);
  useEffect(() => { void load(); return () => { ++listVersion.current; }; }, [load]);
  useEffect(() => {
    let current = true;
    getHealth().then(result => { if (current) setHealth(result.status === 'ok' ? 'online' : 'offline'); }).catch(() => { if (current) setHealth('offline'); });
    return () => { current = false; };
  }, []);

  function invalidateList() { ++listVersion.current; setLoading(false); }
  function message(cause: unknown) { return cause instanceof Error ? cause.message : 'Something went wrong. Please try again.'; }
  function begin(id: number) {
    if (busyIds.current.has(id)) return false;
    busyIds.current.add(id); setBusy(new Set(busyIds.current)); setActionError(''); setNotice(''); return true;
  }
  function end(id: number) { busyIds.current.delete(id); setBusy(new Set(busyIds.current)); }
  async function add(input: WatchInput) {
    if (createPending.current) return false;
    createPending.current = true; setCreating(true); setActionError(''); setNotice('');
    try {
      const result = await createWatch(input); invalidateList();
      setWatches(rows => [...rows.filter(watch => watch.id !== result.id), result]);
      setFilter('all'); setNotice('Watch created.'); return true;
    } catch (cause) { setActionError(message(cause)); return false; }
    finally { createPending.current = false; setCreating(false); }
  }
  async function toggle(watch: Watch) {
    if (!begin(watch.id)) return;
    try {
      const result = await setWatchActive(watch.id, !watch.active); invalidateList();
      setWatches(rows => rows.map(row => row.id === result.id ? result : row));
      setNotice(result.active ? 'Watch resumed.' : 'Watch paused.');
    } catch (cause) { setActionError(message(cause)); if (cause instanceof ApiError && cause.status === 404) void load(); }
    finally { end(watch.id); }
  }
  async function remove(watch: Watch) {
    if (!begin(watch.id)) return;
    try {
      await deleteWatch(watch.id); invalidateList();
      setWatches(rows => rows.filter(row => row.id !== watch.id));
      setDeleting(null); setNotice('Watch deleted.');
    } catch (cause) { setDeleting(null); setActionError(message(cause)); if (cause instanceof ApiError && cause.status === 404) void load(); }
    finally { end(watch.id); }
  }
  function newWatch() { document.getElementById('new-watch')?.scrollIntoView({ behavior: 'smooth', block: 'center' }); document.getElementById('subject')?.focus({ preventScroll: true }); }

  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to content</a>
    <aside className="sidebar">
      <a className="brand" href="#main" aria-label="Course Watcher home"><span className="brand-mark"><Radar size={24} /></span><span>course<span className="brand-light">watcher</span></span></a>
      <div className="workspace-label">YOUR WORKSPACE <span>v3</span></div>
      <nav aria-label="Main navigation"><button className="nav-item selected" onClick={() => { setFilter('all'); document.getElementById('main')?.focus(); }}><LayoutDashboard size={18} />My watchlist<span className="nav-count">{loading && !watches.length ? '—' : watches.length}</span></button><a className="nav-item" href="#how-it-works"><CircleHelp size={18} />How it works<ArrowUpRight size={15} /></a><a className="nav-item" href={API_DOCS} target="_blank" rel="noreferrer"><BookOpen size={18} />API documentation<ArrowUpRight size={15} /></a></nav>
      <div className="sidebar-bottom"><div className="campus-icon"><GraduationCap size={22} /></div><strong>Data source</strong><p>UW Open Data API</p></div>
      <div className="sidebar-footer"><span className="version-dot" />Course Watcher<span>3.0</span></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div className="breadcrumbs">Workspace <span>/</span><strong>My watchlist</strong></div><div className="topbar-right"><span className={`api-state ${health}`}><span />{health === 'online' ? 'API connected' : health === 'offline' ? 'API unavailable' : 'Connecting to API…'}</span><a className="docs-link" href={API_DOCS} target="_blank" rel="noreferrer">Docs <ExternalLink size={13} /></a><span className="avatar" aria-label="Waterloo workspace">W</span></div></header>
      <main id="main" tabIndex={-1}>
        <div className="page-heading"><div><h1>Course Watcher</h1><p>Create and manage course watches. Check section availability.</p></div><button className="button primary heading-add" onClick={newWatch}><Plus size={17} />New watch</button></div>
        <section className="summary-grid" aria-label="Watch summary">
          <div className="summary-card"><div><span>Total watches</span><strong>{loading && !watches.length ? '—' : String(watches.length).padStart(2, '0')}</strong><small>{watches.length === 1 ? '1 saved watch' : `${watches.length} saved watches`}</small></div><span className="summary-icon"><Radar size={22} strokeWidth={1.5} /></span></div>
          <div className="summary-card"><div><span>Active watches</span><strong>{loading && !watches.length ? '—' : String(active).padStart(2, '0')}<span className="stat-dot" /></strong><small>Availability checks enabled</small></div><span className="summary-icon green"><Activity size={22} strokeWidth={1.5} /></span></div>
          <div className="summary-card"><div><span>Paused watches</span><strong>{loading && !watches.length ? '—' : String(watches.length - active).padStart(2, '0')}</strong><small>Availability checks paused</small></div><span className="summary-icon"><Pause size={21} strokeWidth={1.5} /></span></div>
        </section>
        <div className="workspace-grid"><section className="watchlist" aria-labelledby="watchlist-title">
          <div className="list-heading"><div><h2 id="watchlist-title" tabIndex={-1}>Your watchlist <span>{watches.length}</span></h2><p>View, pause, resume or delete watches.</p></div><button className="button secondary refresh-button" disabled={loading || creating || busy.size > 0} onClick={() => void load()} aria-label="Refresh watches"><RefreshCw size={15} className={loading ? 'spin' : ''} /><span>Refresh</span></button></div>
          <div className="list-toolbar"><div role="tablist" aria-label="Filter watches">{(['all', 'active', 'paused'] as const).map(value => <button key={value} role="tab" aria-selected={filter === value} className={filter === value ? 'filter selected' : 'filter'} onClick={() => setFilter(value)}>{value === 'all' ? 'All watches' : value === 'active' ? 'Active' : 'Paused'}<span>{value === 'all' ? watches.length : value === 'active' ? active : watches.length - active}</span></button>)}</div><span className="sort-label">Date added <ArrowDown size={12} /></span></div>
          {notice && <div className="feedback success" role="status"><CheckCheck size={18} /><span>{notice}</span><button className="icon-button" aria-label="Dismiss success message" onClick={() => setNotice('')}><X size={15} /></button></div>}
          {actionError && <div className="feedback error" role="alert"><AlertCircle size={18} /><span>{actionError}</span><button className="icon-button" aria-label="Dismiss error message" onClick={() => setActionError('')}><X size={15} /></button></div>}
          {loadError && <div className="feedback error" role="alert"><AlertCircle size={18} /><span>{loadError}</span><button className="text-button" onClick={() => void load()}>Try again</button></div>}
          {loading ? <div className="loading-state" aria-busy="true"><div className="loading-copy"><LoaderCircle className="spin" size={18} />Loading your watches…</div><div className="watch-grid">{[1, 2, 3, 4].map(key => <div className="skeleton-card" key={key}><span /><span /><span /></div>)}</div></div> : !loadError || watches.length > 0 ? filtered.length > 0 ? <div className="watch-grid">{filtered.map(watch => <WatchCard key={watch.id} watch={watch} busy={busy.has(watch.id)} onToggle={() => void toggle(watch)} onDelete={() => setDeleting(watch)} />)}</div> : <div className="empty-state"><span className="empty-radar"><Radar size={42} strokeWidth={1} /></span><h3>{watches.length === 0 ? 'No watches yet.' : `No ${filter} watches.`}</h3><p>{watches.length === 0 ? 'Add a course to create a watch.' : 'Try another filter or add a course to your watchlist.'}</p><button className="button secondary" onClick={watches.length === 0 ? newWatch : () => setFilter('all')}>{watches.length === 0 ? <><Plus size={16} />Add your first course</> : 'View all watches'}</button></div> : null}
          <div className="watchlist-note"><Check size={14} /><span>Section data from the UW Open Data API.</span></div>
        </section><WatchForm busy={creating || loading || !!loadError} onCreate={add} /></div>
        <footer className="page-footer"><span><Radar size={15} />Availability is checked on demand.</span><span>Shared demo · Watches are visible to everyone.</span></footer>
      </main>
    </div>
    {deleting && <ConfirmDelete watch={deleting} busy={busy.has(deleting.id)} onCancel={() => setDeleting(null)} onConfirm={() => void remove(deleting)} />}
  </div>;
}

