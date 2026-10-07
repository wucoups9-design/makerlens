"""Verify a private photo API; reports never include photos or credentials.

An optional --image is sent to the explicitly selected server. Obtain the
participant's permission first. Passing tests is not an accuracy evaluation.
"""
import argparse
import base64
import getpass
import io
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from PIL import Image

EXPECTED = {
    'goggles': {'goggles_worn', 'eyes_unprotected'},
    'gloves': {'gloves_worn', 'bare_hands'},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--image', type=Path)
    parser.add_argument('--concurrency', action='store_true', help='Check two simultaneous blank uploads and recovery')
    args = parser.parse_args()
    origin = args.origin.rstrip('/')
    parsed = urlsplit(origin)
    if (parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path or not parsed.hostname or not
            (parsed.scheme == 'https' or (parsed.scheme == 'http'
             and parsed.hostname in {'127.0.0.1', 'localhost'}))):
        parser.error('Use an HTTPS origin or the private localhost tunnel')
    token = os.environ.get('MAKERLENS_ACCESS_TOKEN') or getpass.getpass('Pilot access code: ')
    if len(token) < 24:
        parser.error('Access code is too short')
    blank = io.BytesIO()
    Image.new('RGB', (640, 480), (128, 128, 128)).save(blank, format='PNG')
    records = []

    def post(name, payload, mode='both', access=token, source=origin, expected=200):
        start = time.monotonic()
        req = Request(origin + '/api/ppe/detect', data=payload, headers={
            'Origin': source, 'Authorization': 'Bearer ' + access,
            'X-MakerLens': 'image', 'X-MakerLens-Mode': mode,
            'Content-Type': 'application/octet-stream',
        }, method='POST')
        try:
            response = urlopen(req, timeout=210)
        except HTTPError as error:
            response = error
        with response:
            code = response.code
            result = json.load(response)
        entry = {'case': name, 'http': code, 'expected_http': expected,
                 'seconds': round(time.monotonic() - start, 3), 'passed': code == expected}
        if code == expected == 200:
            models = set(EXPECTED) if mode == 'both' else {mode}
            entry['models'] = sorted(result.get('models', {}))
            entry['model_sha256'] = {key: value['sha256'] for key, value in result['models'].items()}
            entry['classes'] = [item['class'] for item in result.get('detections', [])]
            entry['passed'] &= set(entry['models']) == models
            entry['passed'] &= all(item['model'] in models and
                                   item['class'] in EXPECTED[item['model']] and
                                   0 <= item['confidence'] <= 1
                                   for item in result.get('detections', []))
            preview = result.get('image', '')
            entry['passed'] &= preview.startswith('data:image/jpeg;base64,')
            Image.open(io.BytesIO(base64.b64decode(preview.split(',', 1)[1], validate=True))).verify()
        records.append(entry)
        print(json.dumps(entry, ensure_ascii=False), flush=True)

    post('invalid_access_code', blank.getvalue(), access='invalid-test-code', expected=403)
    post('invalid_origin', blank.getvalue(), source='https://untrusted.invalid', expected=403)
    post('invalid_image', b'not an image', expected=400)
    post('invalid_mode', blank.getvalue(), mode='unknown', expected=400)
    for mode in ('goggles', 'gloves', 'both'):
        post('blank_' + mode, blank.getvalue(), mode)
    if args.image:
        data = args.image.read_bytes()
        if not 0 < len(data) <= 15 * 1024 * 1024:
            parser.error('Image must be under 15 MB')
        for mode in ('goggles', 'gloves', 'both'):
            post('authorized_photo_' + mode, data, mode)
    if args.concurrency:
        barrier = threading.Barrier(2)

        def concurrent_upload(_):
            req = Request(origin + '/api/ppe/detect', data=blank.getvalue(), headers={
                'Origin': origin, 'Authorization': 'Bearer ' + token,
                'X-MakerLens': 'image', 'X-MakerLens-Mode': 'both',
                'Content-Type': 'application/octet-stream',
            }, method='POST')
            barrier.wait(timeout=10)
            try:
                response = urlopen(req, timeout=210)
            except HTTPError as error:
                response = error
            with response:
                code = response.code
                body = json.load(response)
            return {'http': code, 'has_error_message': bool(body.get('error'))}

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(concurrent_upload, range(2)))
        entry = {'case': 'two_concurrent_uploads', 'responses': outcomes,
                 'passed': sorted(item['http'] for item in outcomes) == [200, 503]
                 and all(item['has_error_message'] for item in outcomes if item['http'] == 503)}
        records.append(entry)
        print(json.dumps(entry, ensure_ascii=False), flush=True)
        post('recovery_after_busy', blank.getvalue())
    report = {'passed': all(item['passed'] for item in records), 'checks': records,
              'scope': 'API functionality only; not accuracy, safety or public availability',
              'participant_photo_used': bool(args.image)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
