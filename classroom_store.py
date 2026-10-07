"""One-classroom portfolio storage. Teacher writes are checked by the hosting handler."""
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

LIMIT = 25 * 1024 * 1024
IMAGE = re.compile(r'data:image/(jpeg|png|webp);base64,[A-Za-z0-9+/=]+\Z')


class ClassroomStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, owner TEXT NOT NULL, revision INTEGER NOT NULL, document TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS course (id INTEGER PRIMARY KEY, document TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS observations (id INTEGER PRIMARY KEY AUTOINCREMENT, document TEXT NOT NULL)')
        self.path.chmod(0o600)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def owner(self, key):
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9-]{48,160}', key):
            raise ValueError('换设备凭证无效，请从原设备导出')
        return hashlib.sha256(key.encode()).hexdigest()

    def validate(self, value):
        if not isinstance(value, dict) or not re.fullmatch(r'[A-Za-z0-9-]{16,80}', str(value.get('id', ''))):
            raise ValueError('作品编号无效')
        for key in ('name', 'student', 'goal', 'materials', 'reflection', 'members', 'deadline', 'status'):
            if key in value and (not isinstance(value[key], str) or len(value[key]) > 12000):
                raise ValueError('作品文字字段无效')
        for key in ('sketches', 'records', 'tests'):
            records = value.get(key)
            if not isinstance(records, list) or len(records) > 500:
                raise ValueError('记录格式无效或超过500条')
            seen = set()
            for record in records:
                if not isinstance(record, dict) or not isinstance(record.get('note'), str) or not isinstance(record.get('time'), str):
                    raise ValueError('记录说明或时间无效')
                rid = record.get('id', '')
                if not isinstance(rid, str) or not re.fullmatch(r'[A-Za-z0-9-]{16,80}', rid) or rid in seen:
                    raise ValueError('记录编号重复或无效')
                seen.add(rid)
                if record.get('image') and (not isinstance(record['image'], str) or not IMAGE.fullmatch(record['image'])):
                    raise ValueError('照片格式无效')
        if value.get('outcomeImage') and (not isinstance(value['outcomeImage'], str) or not IMAGE.fullmatch(value['outcomeImage'])):
            raise ValueError('成品图片格式无效')
        links = value.get('links', {})
        if not isinstance(links, dict) or any(not isinstance(u, str) or not u.startswith('https://') for u in links.values() if u):
            raise ValueError('交互场景请使用 HTTPS')
        if not isinstance(value.get('done', []), list) or any(type(n) is not int or n not in range(6) for n in value.get('done', [])):
            raise ValueError('工序自查格式无效')
        for record in value['tests']:
            measurements = record.get('measurements', [])
            if not isinstance(measurements, list) or len(measurements) > 50 or any(type(n) not in (int, float) or not 0 < n < 1e7 for n in measurements):
                raise ValueError('测试测量格式无效')
            record['average'] = sum(measurements) / len(measurements) if measurements else None

    def school_context(self):
        with self.connect() as db:
            row = db.execute('SELECT document FROM course WHERE id=1').fetchone()
        course = json.loads(row[0]) if row else {}
        materials = course.get('materials', '').strip()
        return {'configured': bool(materials), 'materials': materials}

    def handle(self, path, body, key, teacher=False):
        if path == '/api/classroom/ppe-report':
            owner = self.owner(key)
            code = str(body.get('station', '未填小组代号'))[:80]
            reason = body.get('reason', 'gloves_missing')
            if reason not in ('gloves_missing', 'hands_not_visible'):
                return 400, {'error': '无效监测提醒类型'}
            note = ('监测端报告：连续十分钟未检测到裸手或戴手套的手，请检查工位画面及监测状态。'
                    if reason == 'hands_not_visible' else '监测端报告：未戴手套提醒持续两分钟未改善，请教师处理。')
            event = {'note':note, 'reason':reason, 'stage':code,
                     'source':'AI监测端提示（非教师确认）', 'time':datetime.now(timezone.utc).isoformat(), 'resolved':False, 'owner':owner}
            with self.connect() as db:
                rows = db.execute('SELECT id,document FROM observations ORDER BY id DESC LIMIT 200').fetchall()
                for row in rows:
                    previous = json.loads(row[1])
                    if previous.get('owner') == owner and previous.get('reason', 'gloves_missing') == reason and not previous.get('resolved'):
                        return 200, {'reported':True, 'id':row[0]}
                cursor = db.execute('INSERT INTO observations(document) VALUES (?)',(json.dumps(event,ensure_ascii=False),))
                return 200, {'reported':True, 'id':cursor.lastrowid}
        if path.startswith('/api/classroom/observation'):
            if not teacher: return 403, {'error': '仅教师可操作课堂观察日志'}
            if path == '/api/classroom/observations':
                with self.connect() as db:
                    rows = db.execute('SELECT id, document FROM observations ORDER BY id DESC LIMIT 200').fetchall()
                return 200, {'observations': [{'id':row[0],**json.loads(row[1])} for row in rows]}
            if path == '/api/classroom/observation':
                if not isinstance(body.get('note'), str) or not 0 < len(body['note'].strip()) <= 4000: raise ValueError('请填写观察说明')
                event = {'note':body['note'].strip(),'stage':str(body.get('stage',''))[:80], 'source':'教师现场观察','time':datetime.now(timezone.utc).isoformat(),'resolved':False}
                with self.connect() as db:
                    cursor = db.execute('INSERT INTO observations(document) VALUES (?)', (json.dumps(event, ensure_ascii=False),))
                    event['id'] = cursor.lastrowid
                return 200, {'observation':event}
            if path == '/api/classroom/observation/resolve':
                if not isinstance(body.get('response'), str) or not 0 < len(body['response'].strip()) <= 4000: raise ValueError('请填写处理说明')
                with self.connect() as db:
                    db.execute('BEGIN IMMEDIATE')
                    row=db.execute('SELECT document FROM observations WHERE id=?',(body.get('id'),)).fetchone()
                    if not row: return 404, {'error':'日志不存在'}
                    event=json.loads(row[0]);event.update(resolved=True,response=body['response'].strip(),resolvedAt=datetime.now(timezone.utc).isoformat())
                    db.execute('UPDATE observations SET document=? WHERE id=?',(json.dumps(event,ensure_ascii=False),body['id']))
                return 200, {'observation':event}
            return 404, {'error':'日志接口不存在'}
        if path == '/api/classroom/course':
            with self.connect() as db:
                row = db.execute('SELECT document FROM course WHERE id=1').fetchone()
            return 200, {'course': json.loads(row[0]) if row else None}
        if path == '/api/classroom/course/save':
            if not teacher: return 403, {'error': '仅教师可修改课堂任务'}
            c = body.get('course')
            if not isinstance(c, dict): raise ValueError('课堂任务格式无效')
            for field in ('instructions', 'materials', 'deadline', 'name'):
                if not isinstance(c.get(field, ''), str) or len(c.get(field, '')) > 12000:
                    raise ValueError('课堂任务字段无效')
            cube_link = c.get('cubeLink', '')
            if not isinstance(cube_link, str) or len(cube_link) > 2000 or (cube_link and not cube_link.startswith('https://')):
                raise ValueError('Cube 分享链接必须为 HTTPS')
            links = c.get('links', {})
            if not isinstance(links, dict) or any(not isinstance(u, str) or not u.startswith('https://') for u in links.values() if u):
                raise ValueError('教学场景必须为 HTTPS')
            with self.connect() as db:
                db.execute('INSERT OR REPLACE INTO course VALUES (1,?)', (json.dumps(c, ensure_ascii=False),))
            return 200, {'course': c}
        if path == '/api/classroom/list':
            if not teacher: return 403, {'error': '仅教师可查看全班档案'}
            with self.connect() as db:
                rows = db.execute('SELECT document FROM projects').fetchall()
            result = []
            for row in rows:
                d = json.loads(row[0])
                result.append({k: d.get(k) for k in ('id', 'name', 'student', 'status', 'updatedAt', 'revision') } | {
                    'sketches': len(d['sketches']), 'records': len(d['records']), 'tests': len(d['tests']),
                    'pending': sum(bool(x.get('feedback')) and not x.get('review') for k in ('sketches','records','tests') for x in d[k])})
            return 200, {'projects': result}
        if path == '/api/classroom/project':
            with self.connect() as db:
                row = db.execute('SELECT owner, document FROM projects WHERE id=?', (body.get('id', ''),)).fetchone()
            if not row or (not teacher and row[0] != self.owner(key)):
                return 404, {'error': '找不到你的作品'}
            return 200, {'project': json.loads(row[1])}
        if path == '/api/classroom/mine':
            owner = self.owner(key)
            with self.connect() as db:
                rows = db.execute('SELECT document FROM projects WHERE owner=?', (owner,)).fetchall()
            return 200, {'projects': [json.loads(row[0]) for row in rows]}
        if path == '/api/classroom/sync':
            owner = self.owner(key)
            d = body.get('project')
            self.validate(d)
            # Never accept teacher judgments, workspace credentials or drafts from a student write.
            d = json.loads(json.dumps(d))
            d.pop('drafts', None)
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT owner, revision, document FROM projects WHERE id=?', (d['id'],)).fetchone()
                if row and row[0] != owner: return 404, {'error': '找不到你的作品'}
                if row and body.get('baseRevision') != row[1]:
                    return 409, {'error': '课堂版本已更新。请先取回教师评价再同步；新设备可先恢复课堂作品。', 'project': json.loads(row[2])}
                previous = json.loads(row[2]) if row else {}
                d['teacher'] = previous.get('teacher', '')
                for kind in ('sketches', 'records', 'tests'):
                    reviews = {r['id']: r.get('review') for r in previous.get(kind, [])}
                    for r in d[kind]:
                        r.pop('review', None)
                        if reviews.get(r['id']): r['review'] = reviews[r['id']]
                student_content = {k:v for k,v in d.items() if k not in ('teacher','revision','updatedAt','syncedAt','syncedDigest','_studentDigest')}
                for kind in ('sketches','records','tests'):
                    student_content[kind] = [{k:v for k,v in r.items() if k != 'review'} for r in d[kind]]
                d['_studentDigest'] = hashlib.sha256(json.dumps(student_content, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                d['revision'] = (row[1] if row else 0) + 1
                d['syncedAt'] = datetime.now(timezone.utc).isoformat()
                db.execute('INSERT OR REPLACE INTO projects VALUES (?,?,?,?)', (d['id'], owner, d['revision'], json.dumps(d, ensure_ascii=False)))
            return 200, {'project': d}
        if path == '/api/classroom/review':
            if not teacher: return 403, {'error': '仅教师可写评价'}
            if not isinstance(body.get('note'), str) or len(body['note']) > 12000: raise ValueError('评价文字无效')
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                row = db.execute('SELECT owner, revision, document FROM projects WHERE id=?', (body.get('id', ''),)).fetchone()
                if not row: return 404, {'error': '作品不存在'}
                if body.get('baseRevision') != row[1]: return 409, {'error': '作品已更新，请重新打开后评价'}
                d = json.loads(row[2])
                if body.get('recordId'):
                    record = next((r for k in ('sketches','records','tests') for r in d[k] if r['id'] == body['recordId']), None)
                    if record is None: return 404, {'error': '记录不存在'}
                    if body.get('status') not in ('待修改', '已复核', '需现场确认'): raise ValueError('复核状态无效')
                    record['review'] = {'note': body['note'], 'status': body['status'], 'time': datetime.now(timezone.utc).isoformat()}
                else: d['teacher'] = body['note']
                d['revision'] = row[1] + 1
                db.execute('UPDATE projects SET revision=?, document=? WHERE id=?', (d['revision'], json.dumps(d, ensure_ascii=False), d['id']))
            return 200, {'project': d}
        return 404, {'error': '课堂接口不存在'}


def dispatch(handler, store, teacher):
    try:
        size = int(handler.headers.get('Content-Length', '0'))
        if not 0 < size <= LIMIT:
            handler.close_connection = True
            return handler.reply(413, {'error': '档案超过25MB，请导出备份并减少照片后再同步'})
        body = json.loads(handler.rfile.read(size))
        if not isinstance(body, dict): raise ValueError('请求格式无效')
        status, result = store.handle(handler.path, body, handler.headers.get('X-MakerLens-Workspace', ''), teacher)
        return handler.reply(status, result)
    except (ValueError, TypeError, AttributeError, KeyError):
        return handler.reply(400, {'error': '档案或请求字段格式无效，请检查后重试'})
    except (OSError, sqlite3.Error):
        return handler.reply(503, {'error': '课堂保存暂不可用，本地档案仍可继续使用'})
