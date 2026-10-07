"""Run as root on the CVM after installing dependencies. Private pilot only."""
import io
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import subprocess
import time
import urllib.request
import urllib.error

root = Path('/opt/makerlens')
assert os.geteuid() == 0 and (root / 'models/goggles-v1.pt').is_file()
try:
    pwd.getpwnam('makerlens')
except KeyError:
    subprocess.run(['useradd', '--system', '--home-dir', '/var/lib/makerlens',
                    '--shell', '/sbin/nologin', 'makerlens'], check=True)
env = Path('/etc/makerlens-pilot.env')
if not env.exists():
    fd = os.open(env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write('MAKERLENS_ACCESS_TOKEN=' + secrets.token_urlsafe(32) + '\n'
                'MAKERLENS_ORIGIN=http://127.0.0.1:8766\n')
os.chmod(env, 0o600)
subprocess.run(['chown', '-R', 'root:makerlens', str(root)], check=True)
subprocess.run(['chmod', '-R', 'o-rwx', str(root)], check=True)
subprocess.run(['chmod', '-R', 'g+rX', str(root)], check=True)
shutil.copyfile(root / 'ml/makerlens-pilot.service',
                '/etc/systemd/system/makerlens-pilot.service')
subprocess.run(['systemctl', 'daemon-reload'], check=True)
subprocess.run(['systemctl', 'enable', '--now', 'makerlens-pilot'], check=True)
base = 'http://127.0.0.1:8766'
for _ in range(20):
    try:
        urllib.request.urlopen(base + '/health', timeout=2).close()
        break
    except OSError:
        time.sleep(1)
config = dict(line.split('=', 1) for line in env.read_text().splitlines())
headers = {'Origin': config['MAKERLENS_ORIGIN'], 'X-MakerLens': 'image',
           'Authorization': 'Bearer ' + config['MAKERLENS_ACCESS_TOKEN']}

def request(path, data=None, extra=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(base + path, data=data,
                headers=extra or {}), timeout=195) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()

report = {}
for path in ('/', '/health', '/api/ppe/status', '/workshop.js', '/models/goggles-v1.pt'):
    code, _ = request(path)
    report[path] = code
    assert code == (404 if path.startswith('/models/') else 200), (path, code)
report['unauthorized'], _ = request('/api/ppe/detect', b'invalid')
assert report['unauthorized'] == 403
report['invalid_image'], _ = request('/api/ppe/detect', b'invalid', headers)
assert report['invalid_image'] == 400
from PIL import Image
image = io.BytesIO()
Image.new('RGB', (640, 480), (160, 160, 160)).save(image, 'JPEG')
started = time.monotonic()
status, body = request('/api/ppe/detect', image.getvalue(), headers)
report['inference_http'] = status
report['request_seconds'] = round(time.monotonic() - started, 3)
assert status == 200, body.decode()[:200]
result = json.loads(body)
report['inference_seconds'] = result['seconds']
report['model_names'] = list(result['models'])
report['note'] = 'Synthetic blank image smoke test, not an accuracy evaluation.'
report['service'] = subprocess.check_output(['systemctl', 'is-active', 'makerlens-pilot'], text=True).strip()
report['memory'] = subprocess.check_output(['systemctl', 'show', 'makerlens-pilot', '-p', 'MemoryCurrent', '-p', 'MemoryPeak'], text=True).strip()
Path('/var/lib/makerlens/deployment-smoke.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
