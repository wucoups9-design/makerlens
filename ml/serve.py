"""Loopback-only image inference UI; private inputs live in temporary storage."""
import argparse
import base64
import io
import hashlib
import json
import subprocess
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

HERE = Path(__file__).resolve().parent
LIMIT = 15 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000


def handler_for(goggles, gloves):
    provenance = {name: {'filename': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                  for name, path in [('goggles', goggles), ('gloves', gloves)]}
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, payload, mime='application/json'):
            data = json.dumps(payload).encode() if mime == 'application/json' else payload
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def trusted(self):
            port = self.server.server_port
            hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
            return (self.headers.get('Host') in hosts and
                    self.headers.get('Origin') in {None, *(f'http://{h}' for h in hosts)})

        def do_GET(self):
            if not self.trusted():
                return self.reply(403, {'error': '仅允许本机页面访问'})
            if self.path == '/':
                return self.reply(200, (HERE / 'web.html').read_bytes(), 'text/html; charset=utf-8')
            assets = {'/dashboard': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/styles.css': ('styles.css', 'text/css; charset=utf-8')}
            if self.path in assets:
                filename, mime = assets[self.path]
                return self.reply(200, (HERE.parent / filename).read_bytes(), mime)
            self.reply(404, {'error': '页面不存在'})

        def do_POST(self):
            if not self.trusted() or self.headers.get('X-MakerLens') != 'image':
                return self.reply(403, {'error': '请从本机检测页面提交'})
            if self.path != '/detect':
                return self.reply(404, {'error': '接口不存在'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                length = 0
            if not 0 < length <= LIMIT:
                self.close_connection = True
                return self.reply(413, {'error': '请选择不超过 15 MB 的图片'})
            self.connection.settimeout(30)
            try:
                raw = self.rfile.read(length)
                if len(raw) != length:
                    raise ValueError('图片上传不完整')
                with Image.open(io.BytesIO(raw)) as source:
                    if source.width * source.height > 20_000_000:
                        raise ValueError('图片尺寸超过 2000 万像素')
                    frame = ImageOps.exif_transpose(source).convert('RGB')
                with tempfile.TemporaryDirectory(prefix='makerlens-') as folder:
                    root = Path(folder)
                    frame.save(root / 'input.png')
                    output = root / 'result'
                    subprocess.run([sys.executable, str(HERE / 'run.py'), str(root / 'input.png'),
                                    '--goggles', str(goggles), '--gloves', str(gloves),
                                    '--output', str(output)], check=True, capture_output=True, timeout=180)
                    record = json.loads((output / 'detections.jsonl').read_text().splitlines()[0])
                    summary = json.loads((output / 'summary.json').read_text())
                    preview = base64.b64encode((output / 'preview.jpg').read_bytes()).decode()
                self.reply(200, {'image': 'data:image/jpeg;base64,' + preview,
                                 'input_sha256': hashlib.sha256(raw).hexdigest(),
                                 'models': provenance, 'confidence': {'goggles': .4, 'gloves': .4},
                                 'detections': record['detections'],
                                 'seconds': summary['elapsed_seconds']})
            except (ValueError, UnidentifiedImageError, Image.DecompressionBombError):
                self.reply(400, {'error': '无法读取图片，请使用尺寸适中的 JPG 或 PNG'})
            except subprocess.TimeoutExpired:
                self.reply(504, {'error': '检测超时，请缩小图片后重试'})
            except (OSError, subprocess.CalledProcessError):
                self.reply(500, {'error': '检测失败，请检查本机模型与运行环境'})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--goggles', type=Path, default=HERE / 'models/goggles-v1.pt')
    parser.add_argument('--gloves', type=Path, default=HERE / 'models/gloves-v3-cleanstart.pt')
    args = parser.parse_args()
    for path in (args.goggles, args.gloves):
        if not path.is_file():
            parser.error(f'Missing local weights: {path}')
    server = HTTPServer(('127.0.0.1', args.port), handler_for(args.goggles.resolve(), args.gloves.resolve()))
    print(f'MakerLens: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
