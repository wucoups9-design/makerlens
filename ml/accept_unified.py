"""Run on the private server. Synthetic-only integration acceptance, no secrets printed."""
import base64, io, json, os, time, urllib.request, urllib.error
from PIL import Image, ImageDraw

base = os.environ.get('MAKERLENS_ORIGIN', 'http://127.0.0.1:8766')
headers = {'Origin': base, 'Authorization': 'Bearer '+os.environ['MAKERLENS_ACCESS_TOKEN'], 'Content-Type':'application/json'}
report = {'tests': {}, 'note':'Synthetic image only; connectivity, not accuracy or safety certification.'}
def request(path, body=None, extra=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(base+path, data=body, headers=extra or {}), timeout=195) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:return e.code,e.read()
def check(name, condition):
    report['tests'][name] = bool(condition)
    if not condition: raise AssertionError(name)
for path in ['/','/auto-record.js','/pilot-access.js','/lavender.css','/steam-hero.png']:
    code,_=request(path);check('asset '+path,code==200)
for path in ['/sketch_feedback_server.py','/ml/cloud_serve.py','/bailian.json','/models/goggles-v1.pt']:
    code,_=request(path);check('private '+path,code==404)
for path in ['/api/status','/api/ppe/status']:
    code,raw=request(path); data=json.loads(raw)
    check('configured '+path,code==200 and data['configured'] and data['access_code_required'])
for path in ['/api/sketch-feedback','/api/ppe/detect']:
    code,_=request(path,b'{}',{'Origin':base});check('unauthorized '+path,code==403)
    code,_=request(path,b'{}',{**headers,'Origin':'https://untrusted.invalid'});check('bad origin '+path,code==403)
code,_=request('/api/sketch-feedback',b'{}',headers);check('invalid sketch',code==400)
image=Image.new('RGB',(640,480),'white');d=ImageDraw.Draw(image)
d.ellipse((170,140,470,270),outline='black',width=3);d.line((320,70,320,350),fill='black',width=4)
d.line((170,205,320,350,470,205),fill='black',width=3);d.text((20,20),'Student concept: spinning top. Dimensions and joint not specified.',fill='black')
b=io.BytesIO();image.save(b,'JPEG');jpeg=b.getvalue()
started=time.monotonic()
code,raw=request('/api/sketch-feedback',json.dumps({'image':'data:image/jpeg;base64,'+base64.b64encode(jpeg).decode(),'design':''}).encode(),headers)
result=json.loads(raw);check('real sketch AI without written description',code==200 and len(result.get('feedback',''))>30)
report['sketch_seconds']=round(time.monotonic()-started,2);report['sketch_model']=result.get('model');report['feedback_characters']=len(result.get('feedback',''))
for mode in ['goggles','gloves','both']:
    code,raw=request('/api/ppe/detect',jpeg,{**headers,'Content-Type':'application/octet-stream','X-MakerLens':'image','X-MakerLens-Mode':mode})
    result=json.loads(raw);check('PPE '+mode,code==200 and isinstance(result.get('detections'),list) and bool(result.get('models')))
report['passed']=all(report['tests'].values())
print(json.dumps(report,ensure_ascii=False,indent=2))
