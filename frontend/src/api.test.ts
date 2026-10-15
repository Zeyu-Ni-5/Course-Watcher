import { describe, expect, it, vi } from 'vitest';
import { createWatch, deleteWatch, listWatches } from './api';

describe('API boundary', () => {
  it('accepts a successful deletion without trying to decode an empty body', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 204 })));
    await expect(deleteWatch(7)).resolves.toBeUndefined();
  });
  it('submits watch fields as JSON to the real endpoint contract', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url, options) => {
      expect(String(url)).toBe('/api/watches');
      expect(options.method).toBe('POST');
      expect(JSON.parse(options.body)).toEqual({ subject: 'CS', catalog: '136', component: 'LEC', term_code: '1269' });
      return Response.json({ id: 7, subject: 'CS', catalog: '136', component: 'LEC', term_code: '1269', active: true, created_at: '2026-10-14T12:00:00Z' }, { status: 201 });
    }));
    expect((await createWatch({ subject: 'CS', catalog: '136', component: 'LEC', term_code: '1269' })).id).toBe(7);
  });
  it('explains a duplicate watch using the backend message', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ detail: 'This watch already exists.' }, { status: 409 })));
    await expect(listWatches()).rejects.toThrow('This watch already exists.');
  });
  it('turns FastAPI validation arrays into readable messages', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Response.json({ detail: [{ loc: ['body', 'subject'], msg: 'Subject must contain letters only.' }] }, { status: 422 })));
    await expect(listWatches()).rejects.toThrow('subject: Subject must contain letters only.');
  });
  it('explains a connection failure', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch'); }));
    await expect(listWatches()).rejects.toThrow('Could not connect');
  });
});
