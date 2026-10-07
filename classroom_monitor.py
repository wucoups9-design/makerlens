"""Ephemeral classroom camera thumbnails. Never persisted to disk."""
import base64
import re
import threading
import time
import secrets


class ClassroomMonitor:
    def __init__(self):
        self.lock = threading.Lock()
        self.task = None
        self.clients = {}

    def handle(self, path, body, key, teacher):
        with self.lock:
            now = time.time()
            if path in ('start', 'stop', 'list') and not teacher:
                return 403, {'error': '仅教师可管理课堂监控'}
            if path == 'start':
                self.task = {'id': secrets.token_hex(12), 'name': str(body.get('name', '制作任务'))[:80]}
                self.clients.clear()
            elif path == 'stop':
                self.task = None
                self.clients.clear()
            elif path == 'heartbeat':
                if not self.task or body.get('taskId') != self.task['id']:
                    return 409, {'error': '课堂任务未开始或已切换'}
                if not re.fullmatch(r'[A-Za-z0-9-]{48,160}', key):
                    return 400, {'error': '无效设备凭证'}
                if key not in self.clients and len(self.clients) >= 100:
                    return 429, {'error': '试点最多100个设备'}
                camera = body.get('camera') is True
                image = body.get('image', '') if camera else ''
                if image:
                    if not isinstance(image, str) or len(image) > 160000 or not re.fullmatch(r'data:image/jpeg;base64,[A-Za-z0-9+/=]+', image):
                        return 400, {'error': '画面格式无效'}
                    try:
                        raw = base64.b64decode(image.split(',', 1)[1], validate=True)
                        if not raw.startswith(b'\xff\xd8\xff'): raise ValueError()
                    except ValueError:
                        return 400, {'error': '画面格式无效'}
                self.clients[key] = {'id': secrets.token_hex(6) if key not in self.clients else self.clients[key]['id'],
                                     'station': str(body.get('station', '未填代号'))[:80],
                                     'camera': camera, 'image': image, 'updatedAt': now}
            elif path not in ('status', 'list'):
                return 404, {'error': '接口不存在'}
            # Purge stale images even before a teacher reads the list.
            for client in self.clients.values():
                if now - client['updatedAt'] > 15:
                    client['image'] = ''
            result = {'task': self.task}
            if path == 'list':
                result['clients'] = [{**c, 'online': now-c['updatedAt'] <= 15} for c in self.clients.values()]
            return 200, result
