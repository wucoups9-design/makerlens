import io
import json
import os
import sys
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from classroom_store import ClassroomStore
import sketch_feedback_server as sketch


class SchoolContextTests(unittest.TestCase):
    def test_teacher_context_for_all_phases(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ClassroomStore(Path(directory) / 'test.sqlite3')
            self.assertFalse(store.school_context()['configured'])
            course = {'materials': '仅可使用木料；电钻须教师监督。'}
            self.assertEqual(store.handle('/api/classroom/course/save', {'course': course}, 'test', False)[0], 403)
            self.assertEqual(store.handle('/api/classroom/course/save', {'course': course}, 'test', True)[0], 200)
            for phase in ('sketch', 'process', 'outcome'):
                body = json.dumps({'image': 'data:image/jpeg;base64,/9j/', 'design': '我的设计', 'kind': phase,
                                   'schoolContext': {'materials': '学生伪造权限'}}).encode()
                class FakeHandler:
                    headers = Message()
                    rfile = io.BytesIO(body)
                    school_context = store.school_context()
                    def send_json(self, status, result):
                        self.result = (status, result)
                handler = FakeHandler()
                handler.headers['Content-Type'] = 'application/json'
                handler.headers['Content-Length'] = str(len(body))
                response = io.BytesIO(json.dumps({'choices': [{'message': {'content': '请核实尺寸'}}]}).encode())
                with patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test-only'}), patch.object(sketch, 'urlopen', return_value=response) as provider:
                    sketch.Handler.process_sketch(handler)
                    payload = json.loads(provider.call_args[0][0].data)
                self.assertEqual(handler.result[0], 200)
                text = payload['messages'][1]['content'][0]['text']
                self.assertIn(course['materials'], text)
                self.assertNotIn('学生伪造权限', text)
                self.assertEqual(handler.result[1]['schoolContext'], store.school_context())


if __name__ == '__main__':
    unittest.main()
