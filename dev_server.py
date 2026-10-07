"""Loopback feature preview with real portfolio storage and no model calls."""
import argparse
import hmac
import json
import secrets
import os
import threading
import io
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from pathlib import Path
from classroom_store import ClassroomStore, dispatch
from classroom_monitor import ClassroomMonitor

ROOT = Path(__file__).resolve().parent


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
ASSETS = {'/': ('index.html', 'text/html; charset=utf-8')}
ASSETS['/classroom-monitor.js'] = ('classroom-monitor.js', 'text/javascript; charset=utf-8')
ASSETS['/refined.css'] = ('refined.css', 'text/css; charset=utf-8')
for filename in ('index.html','studio.js','workshop-v2.js','classroom.js','pilot-access.js','ppe-alerts.js','ppe-live.js','auto-record-v2.js','workshop.css','lavender.css','studio.css','features.css','gyroscope-illustration.svg'):
    ext = filename.rsplit('.', 1)[1]
    ASSETS['/'+filename] = (filename, {'html':'text/html','js':'text/javascript','css':'text/css','svg':'image/svg+xml'}[ext]+'; charset=utf-8')
ASSETS['/progress.html'] = ('progress.html', 'text/html; charset=utf-8')
ASSETS['/progress.css'] = ('progress.css', 'text/css; charset=utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8770)
    parser.add_argument('--store', type=Path, default=Path.home()/'.local/share/makerlens/features.sqlite3')
    parser.add_argument('--sketch-ai', action='store_true', help='Use existing server-side sketch model configuration on explicit request')
    parser.add_argument('--ppe-models', type=Path, help='Directory containing the existing PPE weights; enable real inference')
    parser.add_argument('--gloves-model', type=Path, help='Override glove weights while retaining the goggles model')
    parser.add_argument('--bind-host', default='127.0.0.1', help='监听地址；默认仅本机，临时内网/公网部署时显式设置')
    parser.add_argument('--public-host', help='部署访问用的主机名或 IP；仅用于来源校验，不改变监听地址')
    args = parser.parse_args()
    allowed_host = args.public_host or ('127.0.0.1' if args.bind_host == '127.0.0.1' else args.bind_host)
    sketch = None
    sketch_slot = threading.BoundedSemaphore(1)
    if args.sketch_ai:
        import sketch_feedback_server as sketch
    engine = None
    inference_slot = threading.BoundedSemaphore(1)
    if args.ppe_models:
        import sys
        sys.path.insert(0, str(ROOT/'ml'))
        from ml.live_engine import LiveEngine
        engine = LiveEngine(args.ppe_models/'goggles-v1.pt', args.gloves_model or args.ppe_models/'gloves-v3-cleanstart.pt')
    store = ClassroomStore(args.store)
    monitor = ClassroomMonitor()
    teacher = secrets.token_urlsafe(32)
    settings = {'mode':'gloves','revision':1,'rules':{'gloves':'required','goggles_required':False,'sound':True}}

    class Handler(BaseHTTPRequestHandler):
        def ppe_status(self):
            return {'configured': engine is not None, 'capture':'camera-sampled' if engine else 'camera-preview', 'local_preview':args.bind_host == '127.0.0.1', **settings}

        def reply(self, status, payload, mime='application/json; charset=utf-8'):
            raw = json.dumps(payload, ensure_ascii=False).encode() if isinstance(payload, dict) else payload
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers()
            self.wfile.write(raw)

        def trusted(self):
            hosts = {f'{allowed_host}:{args.port}'}
            if args.bind_host == '127.0.0.1': hosts |= {f'127.0.0.1:{args.port}', f'localhost:{args.port}'}
            origin = self.headers.get('Origin')
            return self.headers.get('Host') in hosts and origin in {None, *(f'http://{h}' for h in hosts)}

        def teacher_trusted(self):
            return hmac.compare_digest(self.headers.get('X-MakerLens-Teacher',''), teacher)

        def do_GET(self):
            if not self.trusted(): return self.reply(403, {'error':'仅限本机功能测试'})
            if self.path == '/api/status': return self.reply(200, {'configured':bool(sketch and os.environ.get('DASHSCOPE_API_KEY')),'access_code_required':False,'local_preview':True,'provider':'阿里云百炼' if sketch else '尚未接入','model':sketch.MODEL if sketch else ''})
            if self.path == '/api/ppe/status': return self.reply(200, self.ppe_status())
            route = ASSETS.get(self.path)
            if route: return self.reply(200, (ROOT/route[0]).read_bytes(), route[1])
            return self.reply(404, {'error':'页面不存在'})

        def do_POST(self):
            if not self.trusted(): return self.reply(403, {'error':'请求来源未获准'})
            if self.path.startswith('/api/monitor/'):
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 170000: raise ValueError()
                    body = json.loads(self.rfile.read(size))
                    if not isinstance(body, dict): raise ValueError()
                    code, out = monitor.handle(self.path.rsplit('/', 1)[1], body,
                                               self.headers.get('X-MakerLens-Workspace', ''), self.teacher_trusted())
                    return self.reply(code, out)
                except (ValueError, TypeError):
                    return self.reply(400, {'error': '无效监控请求'})
            if self.path == '/api/classroom/local-teacher':
                if self.headers.get('Origin') not in (None, f'http://{allowed_host}:{args.port}', f'http://127.0.0.1:{args.port}', f'http://localhost:{args.port}'):
                    return self.reply(403, {'error':'请在本机网页开启教师预览'})
                return self.reply(200, {'teacherToken':teacher,'local_preview':True})
            if self.path == '/api/ppe/teacher/verify':
                return self.reply(200 if self.teacher_trusted() else 403, self.ppe_status() if self.teacher_trusted() else {'error':'教师管理码无效'})
            if self.path == '/api/ppe/session' and engine:
                return self.reply(200, self.ppe_status())
            if self.path == '/api/ppe/detect' and engine:
                if self.headers.get('X-MakerLens') != 'image':
                    return self.reply(403, {'error':'请从检测页面提交'})
                if not inference_slot.acquire(blocking=False):
                    return self.reply(503, {'error':'检测正在处理，请稍后重试'})
                try:
                    from PIL import Image, ImageOps, UnidentifiedImageError
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 15*1024*1024:
                        return self.reply(413, {'error':'图片为空或超过15MB'})
                    self.connection.settimeout(30)
                    raw = self.rfile.read(size)
                    if len(raw) != size: raise ValueError()
                    with Image.open(io.BytesIO(raw)) as image:
                        if image.width*image.height > 20000000: raise ValueError()
                        frame = ImageOps.exif_transpose(image).convert('RGB')
                    snapshot = {**settings, 'rules':dict(settings['rules'])}
                    result = engine(frame, snapshot['mode'])
                    return self.reply(200, {**result, 'mode':snapshot['mode'], 'rules':snapshot['rules'], 'settings_revision':snapshot['revision'], 'capture':'camera-sampled'})
                except (ValueError, OSError, Image.DecompressionBombError):
                    return self.reply(400, {'error':'图片格式或尺寸无效'})
                except Exception:
                    return self.reply(500, {'error':'模型识别失败，请检查运行环境'})
                finally:
                    inference_slot.release()
            if self.path.startswith('/api/classroom/'):
                return dispatch(self,store,self.teacher_trusted())
            if self.path == '/api/sketch-feedback' and sketch:
                if not sketch_slot.acquire(blocking=False): return self.reply(503, {'error':'AI正在分析，请稍后重试'})
                try:
                    self.school_context = store.school_context()
                    return sketch.Handler.process_sketch(self)
                finally: sketch_slot.release()
            if self.path in ('/api/sketch-feedback','/api/ppe/detect','/api/ppe/session'):
                return self.reply(503, {'error':'当前为功能预览，未启用模型。摄像头可使用仅预览模式。'})
            if self.path == '/api/ppe/settings':
                if not self.teacher_trusted(): return self.reply(403, {'error':'需要教师权限'})
                try:
                    size = int(self.headers.get('Content-Length','0'))
                    if not 0 < size < 2048: raise ValueError()
                    body = json.loads(self.rfile.read(size)); rules=body['rules']; mode=body['mode']
                    if mode not in ('both','gloves','goggles') or rules['gloves'] not in ('observe','required','forbidden') or type(rules['goggles_required']) is not bool or type(rules['sound']) is not bool: raise ValueError()
                    if mode=='gloves' and rules['goggles_required'] or mode=='goggles' and rules['gloves']!='observe': raise ValueError()
                    settings.update(mode=mode,rules=rules,revision=settings['revision']+1)
                    return self.reply(200, self.ppe_status())
                except (ValueError,KeyError,TypeError): return self.reply(400, {'error':'检测项目与规则不一致'})
            return self.reply(404, {'error':'接口不存在'})

        def log_message(self,*args): pass

        def send_json(self, status, payload): return self.reply(status,payload)

    server = ThreadingHTTPServer((args.bind_host,args.port),Handler)
    print(f'MakerLens feature preview: http://{allowed_host}:{args.port}',flush=True)
    server.serve_forever()


if __name__=='__main__': main()
