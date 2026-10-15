"""Verify real HTTP behavior; never delete a pre-existing watch."""

import argparse
import json
import uuid

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--origin')
    parser.add_argument('--enrollment', action='store_true')
    parser.add_argument('--subject', default='CS')
    parser.add_argument('--catalog')
    parser.add_argument('--component', default='LEC')
    parser.add_argument('--term', default='1269')
    args = parser.parse_args()
    if args.enrollment and not args.catalog:
        parser.error('--enrollment requires --catalog for a real offered course')

    watch_id = None
    results = {}
    headers = {'Origin': args.origin} if args.origin else {}
    with httpx.Client(base_url=args.base_url.rstrip('/'), timeout=30, headers=headers) as client:
        health = client.get('/health')
        health.raise_for_status()
        assert health.json() == {'status': 'ok'}
        results['health'] = 'ok'
        if args.origin:
            preflight = client.options('/watches/1', headers={
                'Origin': args.origin,
                'Access-Control-Request-Method': 'PATCH',
                'Access-Control-Request-Headers': 'content-type',
            })
            assert preflight.status_code == 200, preflight.text
            assert preflight.headers.get('access-control-allow-origin') == args.origin
            results['cors'] = 'ok'
        try:
            created = client.post('/watches', json={
                'subject': args.subject,
                'catalog': args.catalog or f'VERIFY{uuid.uuid4().hex[:10].upper()}',
                'component': args.component,
                'term_code': args.term,
            })
            created.raise_for_status()
            assert created.status_code == 201
            watch_id = created.json()['id']
            results['create'] = 'ok'
            listing = client.get('/watches')
            listing.raise_for_status()
            assert any(row['id'] == watch_id for row in listing.json())
            retrieved = client.get(f'/watches/{watch_id}')
            retrieved.raise_for_status()
            assert retrieved.json()['id'] == watch_id
            results['list_and_get'] = 'ok'
            for active in (False, True):
                updated = client.patch(f'/watches/{watch_id}', json={'active': active})
                updated.raise_for_status()
                assert updated.json()['active'] is active
            results['pause_and_resume'] = 'ok'
            if args.enrollment:
                status = client.get(f'/watches/{watch_id}/status')
                status.raise_for_status()
                data = status.json()
                assert data['watch_id'] == watch_id
                assert data['sections'], 'No sections returned'
                results['live_enrollment'] = data
        finally:
            if watch_id is not None:
                deleted = client.delete(f'/watches/{watch_id}')
                deleted.raise_for_status()
                assert deleted.status_code == 204 and not deleted.content
                assert client.get(f'/watches/{watch_id}').status_code == 404
                results['delete_and_cleanup'] = 'ok'
            print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
