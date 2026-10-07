"""Private, same-origin photo inference backend for a reverse-proxied pilot.

Never expose this port directly to the internet. Terminate HTTPS, rate-limit,
and proxy /api/ppe/detect to /detect on 127.0.0.1 at the web server.
"""
import argparse
import hmac
import os
import threading
import sys
import time
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from serve import handler_for
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sketch_feedback_server as sketch
from classroom_store import ClassroomStore, dispatch as classroom_dispatch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--origin', required=True, help='Exact HTTPS site origin, e.g. https://www.example.cn')
    parser.add_argument('--goggles', type=Path)
    parser.add_argument('--gloves', type=Path)
    parser.add_argument('--features-only', action='store_true', help='Serve classroom features without loading PPE models')
    args = parser.parse_args()
    secret = os.environ.get('MAKERLENS_ACCESS_TOKEN', '')
    if len(secret) < 24:
        parser.error('Set a random MAKERLENS_ACCESS_TOKEN of at least 24 characters')
    origin = urlsplit(args.origin)
    if (origin.username or origin.password or origin.path or origin.query or origin.fragment
            or not origin.hostname or not (origin.scheme == 'https' or
            (origin.scheme == 'http' and origin.hostname in ('localhost', '127.0.0.1')))):
        parser.error('--origin must be an HTTPS origin, or HTTP localhost for an SSH tunnel')
    if args.features_only:
        class ModelFreeHandler(BaseHTTPRequestHandler):
            def reply(self, status, payload, mime='application/json'):
                raw = json.dumps(payload, ensure_ascii=False).encode() if mime == 'application/json' else payload
                self.send_response(status)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(raw)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                self.wfile.write(raw)
        parent = ModelFreeHandler
    else:
        from live_engine import LiveEngine
        for path in (args.goggles, args.gloves):
            if path is None or not path.is_file():
                parser.error(f'Missing model: {path}')
        parent = handler_for(args.goggles.resolve(), args.gloves.resolve(),
                             LiveEngine(args.goggles.resolve(), args.gloves.resolve()))
    teacher_secret = os.environ.get('MAKERLENS_TEACHER_TOKEN', '')
    settings_path = Path(os.environ.get('MAKERLENS_PPE_SETTINGS', '/var/lib/makerlens/ppe-settings.json'))
    settings_lock = threading.Lock()
    classroom_store = ClassroomStore(os.environ.get('MAKERLENS_CLASSROOM_DB', '/var/lib/makerlens/classroom.sqlite3'))
    settings = {'mode': 'gloves', 'revision': 1,
                'rules': {'gloves': 'required', 'goggles_required': False, 'sound': True}}
    if settings_path.exists():
        saved = json.loads(settings_path.read_text())
        if saved.get('mode') not in ('both', 'goggles', 'gloves'):
            raise ValueError('Invalid saved PPE mode')
        settings.update(saved)
    inference_slot = threading.BoundedSemaphore(1)
    sketch_slot = threading.BoundedSemaphore(1)
    sketch_calls = []
    static_root = Path(__file__).resolve().parents[1]
    assets = {'/': ('index.html', 'text/html; charset=utf-8'),
              '/index.html': ('index.html', 'text/html; charset=utf-8')}
    for name in ('workshop', 'workshop-v2', 'classroom', 'studio', 'auto-record', 'auto-record-v2', 'pilot-access', 'ppe-live', 'ppe-alerts'):
        assets['/' + name + '.js'] = (name + '.js', 'text/javascript; charset=utf-8')
    for name in ('workshop', 'lavender', 'studio', 'features'):
        assets['/' + name + '.css'] = (name + '.css', 'text/css; charset=utf-8')
    assets['/steam-hero.png'] = ('steam-hero.png', 'image/png')
    assets['/gyroscope-illustration.svg'] = ('gyroscope-illustration.svg', 'image/svg+xml')

    class PilotHandler(parent):
        def teacher_trusted(self):
            supplied = self.headers.get('X-MakerLens-Teacher', '')
            return (len(teacher_secret) >= 24 and teacher_secret != secret and
                    hmac.compare_digest(supplied.encode(), teacher_secret.encode()))

        def ppe_status(self):
            with settings_lock:
                return {'configured': not args.features_only, 'capture': 'camera-preview' if args.features_only else 'camera-sampled', **settings,
                    'access_code_required': True, 'teacher_configured': len(teacher_secret) >= 24,
                    'settings_scope': '当前试点课堂', 'minimum_interval_ms': 1000}

        def trusted(self):
            supplied = self.headers.get('Authorization', '')
            return (self.headers.get('Origin') == args.origin
                    and hmac.compare_digest(supplied.encode(), ('Bearer ' + secret).encode()))

        def do_GET(self):
            if self.path == '/health' and self.client_address[0] in ('127.0.0.1', '::1'):
                return self.reply(200, {'status': 'ready'})
            if self.path == '/api/ppe/status':
                return self.reply(200, self.ppe_status())
            if self.path == '/api/status':
                return self.reply(200, {'configured': bool(os.environ.get('DASHSCOPE_API_KEY')),
                    'provider': '阿里云百炼 Qwen', 'model': sketch.MODEL,
                    'access_code_required': True})
            if self.path in assets:
                name, mime = assets[self.path]
                path = static_root / name
                if path.is_file():
                    return self.reply(200, path.read_bytes(), mime)
            return self.reply(404, {'error': '接口不存在'})

        def do_POST(self):
            if not self.trusted():
                return self.reply(403, {'error': '访问码不正确，或当前网页来源未获准'})
            if self.path.startswith('/api/classroom/'):
                return classroom_dispatch(self, classroom_store, self.teacher_trusted())
            if self.path == '/api/ppe/session':
                return self.reply(200, self.ppe_status())
            if self.path in ('/api/ppe/teacher/verify', '/api/ppe/settings'):
                if not self.teacher_trusted():
                    return self.reply(403, {'error': '需要独立的教师管理码；学生访问码不能修改检测项目'})
                if self.path.endswith('/verify'):
                    return self.reply(200, self.ppe_status())
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 1024: raise ValueError()
                    body = json.loads(self.rfile.read(size))
                    if body.get('mode') not in ('both', 'goggles', 'gloves'): raise ValueError()
                    with settings_lock:
                        rules = body.get('rules', settings['rules'])
                        if (not isinstance(rules, dict) or rules.get('gloves') not in ('observe', 'required', 'forbidden')
                                or type(rules.get('goggles_required')) is not bool
                                or type(rules.get('sound')) is not bool): raise ValueError()
                        if body['mode'] == 'gloves' and rules['goggles_required']: raise ValueError()
                        if body['mode'] == 'goggles' and rules['gloves'] != 'observe': raise ValueError()
                        updated = {'mode': body['mode'], 'revision': settings['revision'] + 1, 'rules': rules}
                        temporary = settings_path.with_suffix('.tmp')
                        temporary.write_text(json.dumps(updated))
                        temporary.chmod(0o600)
                        temporary.replace(settings_path)
                        settings.update(updated)
                except (ValueError, AttributeError, TypeError):
                    return self.reply(400, {'error': '规则无效，或所需护具模型未启用；请同时检查检测项目与佩戴规则'})
                except OSError:
                    return self.reply(503, {'error': '配置保存失败，原设置保持不变'})
                return self.reply(200, self.ppe_status())
            if self.path == '/api/sketch-feedback':
                if not sketch_slot.acquire(blocking=False):
                    return self.reply(503, {'error': '草图服务正在分析，请稍后重试'})
                try:
                    now = time.monotonic()
                    sketch_calls[:] = [t for t in sketch_calls if now - t < 86400]
                    if len(sketch_calls) >= 120 or sum(now - t < 60 for t in sketch_calls) >= 6:
                        return self.reply(429, {'error': '已达到试点分析次数限制，请稍后再试或联系教师'})
                    sketch_calls.append(now)
                    self.school_context = classroom_store.school_context()
                    return sketch.Handler.process_sketch(self)
                finally:
                    sketch_slot.release()
            if self.path not in ('/detect', '/api/ppe/detect'):
                return self.reply(404, {'error': '接口不存在'})
            if args.features_only:
                return self.reply(503, {'error': '护具模型暂未启用，请使用摄像头仅预览'})
            # Never trust a client-supplied mode, including direct calls to /detect.
            with settings_lock:
                self.ppe_configuration = dict(settings)
            if 'X-MakerLens-Mode' in self.headers:
                del self.headers['X-MakerLens-Mode']
            self.headers['X-MakerLens-Mode'] = self.ppe_configuration['mode']
            if not inference_slot.acquire(blocking=False):
                return self.reply(503, {'error': '服务正在处理另一张照片，请稍后重试'})
            self.path = '/detect'
            try:
                super().do_POST()
            finally:
                inference_slot.release()

        def send_json(self, code, payload):
            return self.reply(code, payload)

        def reply(self, status, payload, mime='application/json'):
            if status == 200 and isinstance(payload, dict) and 'detections' in payload:
                payload = {**payload, 'settings_revision': self.ppe_configuration['revision'],
                           'capture': 'camera-sampled', 'rules': self.ppe_configuration['rules']}
            return super().reply(status, payload, mime)

        def setup(self):
            super().setup()
            self.connection.settimeout(30)

        def log_message(self, format, *values):
            # Avoid writing participant requests or query strings to a log.
            pass

    server = ThreadingHTTPServer(('127.0.0.1', args.port), PilotHandler)
    print(f'MakerLens pilot API listening on 127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
