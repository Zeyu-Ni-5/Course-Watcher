import { useEffect, useState } from 'react';
import { AlertCircle, ArrowUpRight, LoaderCircle, RefreshCw } from 'lucide-react';
import { getWatchStatus } from '../api';
import { dateLabel } from '../format';
import type { WatchStatus } from '../types';

export default function StatusDetails({ id }: { id: number }) {
  const [data, setData] = useState<WatchStatus | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setLoading(true); setError(''); setData(null);
    getWatchStatus(id, controller.signal)
      .then(result => { if (current) setData(result); })
      .catch(cause => { if (current) setError(cause instanceof Error ? cause.message : 'Could not check this course.'); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; controller.abort(); };
  }, [id, revision]);

  return <section className="status-details" aria-label="Live section availability" aria-busy={loading}>
    {loading && <p className="checking"><LoaderCircle size={16} className="spin" />Checking live enrollment…</p>}
    {error && <div className="inline-error" role="alert"><AlertCircle size={17} /><div><p>{error}</p><button className="text-button" onClick={() => setRevision(v => v + 1)}>Retry availability</button></div></div>}
    {data && <>
      <div className="section-heading"><span>SECTION AVAILABILITY</span><button className="icon-button" aria-label="Refresh availability" onClick={() => setRevision(v => v + 1)}><RefreshCw size={14} /></button></div>
      {data.sections.length === 0 && <p className="muted">No section results returned.</p>}
      {data.sections.map(section => <div className="section-row" key={section.section}>
        <div><strong>{section.section}</strong><span className="enrollment">{section.enrolled_total} / {section.capacity}</span></div>
        <span className={`seat-status ${section.status.toLowerCase()}`}>{section.status === 'OPEN' ? <><ArrowUpRight size={14} />{Math.max(0, section.capacity - section.enrolled_total)} seats available</> : 'Full'}</span>
        <div className="capacity-track"><span style={{ width: `${section.capacity > 0 ? Math.min(100, section.enrolled_total / section.capacity * 100) : 100}%` }} /></div>
      </div>)}
      <p className="checked-time">Checked {dateLabel(data.checked_at)} · Availability can change.</p>
    </>}
  </section>;
}
