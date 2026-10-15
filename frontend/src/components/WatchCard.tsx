import { useEffect, useState } from 'react';
import { ArrowUpRight, BookOpen, CalendarDays, ChevronUp, LoaderCircle, Pause, Play, Trash2 } from 'lucide-react';
import { dateLabel, termLabel } from '../format';
import type { Watch } from '../types';
import StatusDetails from './StatusDetails';

interface Props { watch: Watch; busy: boolean; onToggle: () => void; onDelete: () => void }

export default function WatchCard({ watch, busy, onToggle, onDelete }: Props) {
  const [expanded, setExpanded] = useState(false);
  const title = `${watch.subject} ${watch.catalog}`;
  useEffect(() => { if (!watch.active) setExpanded(false); }, [watch.active]);
  return <article className={`watch-card ${watch.active ? '' : 'paused-card'}`} aria-label={`${title} watch`}>
    <div className="watch-top"><span className="course-icon"><BookOpen size={21} strokeWidth={1.6} /></span><span className={`badge ${watch.active ? 'active' : 'paused'}`}><span />{watch.active ? 'Active' : 'Paused'}</span></div>
    <h3>{title}</h3>
    <div className="watch-meta"><span>{watch.component || 'All components'}</span><i /><span><CalendarDays size={13} />{termLabel(watch.term_code)}</span></div>
    <p className="watch-date">Added {dateLabel(watch.created_at)}</p>
    <div className="card-actions">
      <button className="check-button" disabled={!watch.active || busy} aria-label={`Check availability for ${title}`} aria-expanded={expanded} onClick={() => setExpanded(v => !v)}>{expanded ? 'Hide availability' : 'Check availability'}{expanded ? <ChevronUp size={15} /> : <ArrowUpRight size={15} />}</button>
      <div className="compact-actions"><button className="icon-button" aria-label={`${watch.active ? 'Pause' : 'Resume'} ${title}`} title={watch.active ? 'Pause watch' : 'Resume watch'} disabled={busy} onClick={onToggle}>{busy ? <LoaderCircle size={16} className="spin" /> : watch.active ? <Pause size={16} /> : <Play size={16} />}</button><button className="icon-button delete-button" aria-label={`Delete ${title}`} title="Delete watch" disabled={busy} onClick={onDelete}><Trash2 size={16} /></button></div>
    </div>
    {watch.active && expanded && <StatusDetails id={watch.id} />}
  </article>;
}
