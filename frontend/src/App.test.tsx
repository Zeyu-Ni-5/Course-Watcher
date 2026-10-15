import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import App from './App';

const watch = { id: 7, subject: 'CS', catalog: '136', component: 'LEC', term_code: '1269', active: true, created_at: '2026-10-14T12:00:00Z' };

function serve(initial = [watch]) {
  let watches = structuredClone(initial);
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = String(url);
    if (path.endsWith('/health')) return Response.json({ status: 'ok' });
    if (path.endsWith('/status')) return Response.json({ watch_id: 7, term_code: '1269', checked_at: '2026-10-14T13:00:00Z', sections: [{ section: 'LEC 001', component: 'LEC', enrolled_total: 90, capacity: 100, status: 'OPEN' }, { section: 'LEC 002', component: 'LEC', enrolled_total: 100, capacity: 100, status: 'FULL' }] });
    if (options.method === 'POST') {
      const payload = JSON.parse(options.body);
      watches = [...watches, { ...watch, ...payload, id: 8 }];
      return Response.json(watches.at(-1), { status: 201 });
    }
    if (options.method === 'PATCH') {
      watches = watches.map(w => ({ ...w, ...JSON.parse(options.body) }));
      return Response.json(watches[0]);
    }
    if (options.method === 'DELETE') { watches = []; return new Response(null, { status: 204 }); }
    return Response.json(watches);
  }));
}

describe('watch dashboard', () => {
  it('shows loading while the list request is pending', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    render(<App />);
    expect(screen.getByText('Loading your watches…')).toBeInTheDocument();
  });
  it('offers a useful empty state and creates a watch through the form', async () => {
    serve([]);
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByText('No watches yet.')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Subject'), 'ECE');
    await user.type(screen.getByLabelText('Course number'), '240');
    await user.type(screen.getByLabelText(/Term code/), '1269');
    await user.click(screen.getByRole('button', { name: 'Create watch' }));
    expect(await screen.findByRole('heading', { name: 'ECE 240' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Watch created');
  });
  it('pauses and resumes a watch with confirmed server data', async () => {
    serve();
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole('button', { name: 'Pause CS 136' }));
    expect(await screen.findByRole('button', { name: 'Resume CS 136' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Resume CS 136' }));
    expect(await screen.findByRole('button', { name: 'Pause CS 136' })).toBeInTheDocument();
  });
  it('accepts pasted fields with surrounding whitespace using backend normalization', async () => {
    serve([]);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('No watches yet.');
    await user.type(screen.getByLabelText('Subject'), ' cs ');
    await user.type(screen.getByLabelText('Course number'), ' 136 ');
    await user.type(screen.getByLabelText(/Term code/), ' 1269 ');
    await user.click(screen.getByRole('button', { name: 'Create watch' }));
    expect(await screen.findByRole('heading', { name: 'CS 136' })).toBeInTheDocument();
  });
  it('moves keyboard focus to the watchlist after the deleted control disappears', async () => {
    serve();
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole('button', { name: 'Delete CS 136' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete watch' }));
    await screen.findByText('No watches yet.');
    expect(screen.getByRole('heading', { name: /Your watchlist/ })).toHaveFocus();
  });
  it('does not delete until confirmed and then handles an empty 204', async () => {
    serve();
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole('button', { name: 'Delete CS 136' }));
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByRole('heading', { name: 'CS 136' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Delete CS 136' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete watch' }));
    expect(await screen.findByText('No watches yet.')).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Watch deleted');
  });
  it('explains an empty filter without hiding the overall watch count', async () => {
    serve();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole('heading', { name: 'CS 136' });
    await user.click(screen.getByRole('tab', { name: /Paused/ }));
    expect(screen.getByText('No paused watches.')).toBeInTheDocument();
    expect(screen.getByText('1 saved watch')).toBeInTheDocument();
  });
  it('shows real section results on demand', async () => {
    serve();
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole('button', { name: 'Check availability for CS 136' }));
    expect(await screen.findByText('LEC 001')).toBeInTheDocument();
    expect(screen.getByText('90 / 100')).toBeInTheDocument();
    expect(screen.getByText('10 seats available')).toBeInTheDocument();
    expect(screen.getByText('Full')).toBeInTheDocument();
  });
  it('reports list errors and supports retry', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ detail: 'Service unavailable' }, { status: 503 })));
    const user = userEvent.setup();
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable');
    serve();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('heading', { name: 'CS 136' })).toBeInTheDocument();
  });
  it('shows duplicate errors without adding a fake watch', async () => {
    serve([]);
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText('No watches yet.');
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ detail: 'This watch already exists.' }, { status: 409 })));
    await user.type(screen.getByLabelText('Subject'), 'CS');
    await user.type(screen.getByLabelText('Course number'), '136');
    await user.click(screen.getByRole('button', { name: 'Create watch' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('This watch already exists.');
    expect(screen.getByText('No watches yet.')).toBeInTheDocument();
  });
  it('keeps a confirmed mutation successful even if a subsequent list request would fail', async () => {
    serve();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole('heading', { name: 'CS 136' });
    vi.stubGlobal('fetch', vi.fn(async (_url, options) => options?.method === 'PATCH' ? Response.json({ ...watch, active: false }) : Response.json({ detail: 'Refresh failed' }, { status: 503 })));
    await user.click(screen.getByRole('button', { name: 'Pause CS 136' }));
    expect(await screen.findByRole('button', { name: 'Resume CS 136' })).toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Watch paused');
  });
  it('clears pending details when a watch is deleted and ignores a late result', async () => {
    serve();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole('heading', { name: 'CS 136' });
    let resolveStatus!: (response: Response) => void;
    vi.stubGlobal('fetch', vi.fn(async (url, options) => {
      if (String(url).endsWith('/status')) return new Promise<Response>(resolve => { resolveStatus = resolve; });
      if (options?.method === 'DELETE') return new Response(null, { status: 204 });
      return Response.json([watch]);
    }));
    await user.click(screen.getByRole('button', { name: 'Check availability for CS 136' }));
    expect(await screen.findByText('Checking live enrollment…')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Delete CS 136' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Delete watch' }));
    await screen.findByText('No watches yet.');
    await act(async () => { resolveStatus(Response.json({ watch_id: 7, term_code: '1269', checked_at: '2026-10-14T13:00:00Z', sections: [{ section: 'LEC 099', component: 'LEC', enrolled_total: 1, capacity: 10, status: 'OPEN' }] })); });
    expect(screen.queryByText('LEC 099')).not.toBeInTheDocument();
  });
  it('shows UW failures separately and permits another status attempt', async () => {
    serve();
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole('heading', { name: 'CS 136' });
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ detail: 'UW_API_KEY is not set.' }, { status: 502 })));
    await user.click(screen.getByRole('button', { name: 'Check availability for CS 136' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('UW_API_KEY is not set.');
    serve();
    await user.click(screen.getByRole('button', { name: 'Retry availability' }));
    expect(await screen.findByText('LEC 001')).toBeInTheDocument();
  });
});
