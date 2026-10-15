import { useEffect, useRef } from 'react';
import { LoaderCircle, Trash2 } from 'lucide-react';
import type { Watch } from '../types';

export default function ConfirmDelete({ watch, busy, onCancel, onConfirm }: { watch: Watch; busy: boolean; onCancel: () => void; onConfirm: () => void }) {
  const panel = useRef<HTMLDivElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previousFocus = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden'; cancel.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      if (previousFocus?.isConnected) previousFocus.focus();
      else document.getElementById('watchlist-title')?.focus();
    };
  }, []);
  return <div className="modal-backdrop" onClick={event => { if (event.target === event.currentTarget && !busy) onCancel(); }}>
    <div className="delete-dialog" role="dialog" aria-modal="true" aria-labelledby="delete-title" aria-describedby="delete-description" ref={panel} onKeyDown={event => {
      if (event.key === 'Escape' && !busy) onCancel();
      if (event.key === 'Tab') {
        const buttons = panel.current?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)');
        if (!buttons?.length) { event.preventDefault(); return; }
        const first = buttons[0], last = buttons[buttons.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    }}>
      <span className="delete-symbol"><Trash2 size={24} /></span>
      <h2 id="delete-title">Remove {watch.subject} {watch.catalog}?</h2>
      <p id="delete-description">This deletes the watch and its saved enrollment snapshots. You can add the course again later.</p>
      <div className="dialog-actions"><button className="button secondary" ref={cancel} disabled={busy} onClick={onCancel}>Cancel</button><button className="button danger" disabled={busy} onClick={onConfirm}>{busy && <LoaderCircle className="spin" size={16} />}{busy ? 'Deleting…' : 'Delete watch'}</button></div>
    </div>
  </div>;
}
