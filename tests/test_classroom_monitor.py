import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from classroom_monitor import ClassroomMonitor


class MonitorTests(unittest.TestCase):
    def test_task_permissions_and_ephemeral_frames(self):
        m = ClassroomMonitor()
        key = 'a'*48
        self.assertEqual(m.handle('start', {}, key, False)[0], 403)
        task = m.handle('start', {}, key, True)[1]['task']
        with patch('classroom_monitor.time.time', return_value=100):
            self.assertEqual(m.handle('heartbeat', {'taskId':task['id'], 'camera':True,
                                                    'image':'data:image/jpeg;base64,/9j/'}, key, False)[0], 200)
            self.assertEqual(m.handle('list', {}, key, False)[0], 403)
            self.assertTrue(m.handle('list', {}, key, True)[1]['clients'][0]['image'])
        with patch('classroom_monitor.time.time', return_value=116):
            client = m.handle('list', {}, key, True)[1]['clients'][0]
            self.assertFalse(client['online'])
            self.assertEqual(client['image'], '')
        m.handle('stop', {}, key, True)
        self.assertFalse(m.clients)
        self.assertEqual(m.handle('heartbeat', {'taskId':task['id']}, key, False)[0], 409)

if __name__ == '__main__': unittest.main()
