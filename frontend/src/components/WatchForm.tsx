import { useState, type FormEvent } from 'react';
import { ArrowUpRight, Info, LoaderCircle, Plus } from 'lucide-react';
import type { WatchInput } from '../types';

interface Props { onCreate: (input: WatchInput) => Promise<boolean>; busy: boolean }

export default function WatchForm({ onCreate, busy }: Props) {
  const [subject, setSubject] = useState('');
  const [catalog, setCatalog] = useState('');
  const [component, setComponent] = useState('');
  const [term, setTerm] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const success = await onCreate({ subject: subject.trim().toUpperCase(), catalog: catalog.trim().toUpperCase(), component: component || null, term_code: term.trim() || null });
    if (success) { setSubject(''); setCatalog(''); }
  }

  return <aside className="create-column" aria-label="Create a watch">
    <section className="panel create-panel" id="new-watch">
      <div className="panel-kicker"><span className="icon-square"><Plus size={19} /></span><span>CREATE WATCH</span></div>
      <h2>Add a course</h2>
      <p className="muted">Enter a subject, course number and optional filters.</p>
      <form onSubmit={submit}>
        <div className="field-pair">
          <label htmlFor="subject">Subject<input id="subject" placeholder="e.g. CS" autoComplete="off" required pattern="\s*[A-Za-z]+\s*" title="Use letters only, for example CS or ECE." maxLength={20} value={subject} onChange={e => setSubject(e.target.value)} onBlur={() => setSubject(value => value.trim().toUpperCase())} disabled={busy} /></label>
          <label htmlFor="catalog">Course number<input id="catalog" placeholder="e.g. 136" autoComplete="off" required pattern="\s*\S+\s*" title="Enter a course number without spaces." maxLength={20} value={catalog} onChange={e => setCatalog(e.target.value)} onBlur={() => setCatalog(value => value.trim().toUpperCase())} disabled={busy} /></label>
        </div>
        <label htmlFor="component">Component <span className="optional">optional</span><select id="component" value={component} onChange={e => setComponent(e.target.value)} disabled={busy}>
          <option value="">All components</option><option value="LEC">Lecture (LEC)</option><option value="LAB">Laboratory (LAB)</option><option value="TUT">Tutorial (TUT)</option><option value="SEM">Seminar (SEM)</option><option value="TST">Test (TST)</option><option value="DIS">Discussion (DIS)</option><option value="PRJ">Project (PRJ)</option><option value="FLD">Field study (FLD)</option><option value="PRA">Practicum (PRA)</option><option value="RDG">Reading (RDG)</option><option value="RES">Research (RES)</option><option value="STU">Studio (STU)</option><option value="WSP">Workshop (WSP)</option>
        </select></label>
        <label htmlFor="term">Term code <span className="optional">optional</span><input id="term" placeholder="e.g. 1269" inputMode="numeric" pattern="\s*[0-9]{4}\s*" title="Enter a four-digit UW term code, such as 1269." maxLength={12} value={term} onChange={e => setTerm(e.target.value)} onBlur={() => setTerm(value => value.trim())} aria-describedby="term-help" disabled={busy} /></label>
        <p className="field-help" id="term-help">1269 = Fall 2026. Leave blank for the current UW term.</p>
        <button className="button primary create-button" disabled={busy} type="submit">{busy ? <LoaderCircle size={17} className="spin" /> : <Plus size={17} />}{busy ? 'Creating watch…' : 'Create watch'}<ArrowUpRight size={17} className="trailing" /></button>
      </form>
    </section>
    <section className="how-panel" id="how-it-works">
      <span className="small-heading"><Info size={16} /> USAGE</span>
      <h3>How it works</h3>
      <p>Use Check availability to load current enrollment for a course.</p>
      <div className="how-row"><span>01</span> Add a course to your watchlist</div>
      <div className="how-row"><span>02</span> Check live section availability</div>
      <div className="how-row"><span>03</span> Pause or resume at any time</div>
      <p className="fine-print">Checks run on demand. No automatic alerts or course registration.</p>
    </section>
  </aside>;
}
