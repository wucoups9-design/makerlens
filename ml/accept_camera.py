"""Authorized server-side camera protocol/role tests using synthetic frames only."""
import io,json,os,time,urllib.request,urllib.error
from PIL import Image
base=os.environ['MAKERLENS_ORIGIN']
student={'Origin':base,'Authorization':'Bearer '+os.environ['MAKERLENS_ACCESS_TOKEN']}
teacher={**student,'X-MakerLens-Teacher':os.environ['MAKERLENS_TEACHER_TOKEN']}
report={'checks':{},'seconds':[],'scope':'Synthetic-frame protocol and performance; not camera hardware or accuracy.'}
def request(path,body=None,headers=None):
    try:
        with urllib.request.urlopen(urllib.request.Request(base+path,data=body,headers=headers or {}),timeout=30) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
def check(name,value):
    report['checks'][name]=bool(value)
    assert value,name
def set_mode(mode,headers):
    return request('/api/ppe/settings',json.dumps({'mode':mode}).encode(),{**headers,'Content-Type':'application/json'})
code,initial=request('/api/ppe/status');check('camera endpoint ready',code==200 and initial['capture']=='camera-sampled' and initial['teacher_configured'])
code,_=set_mode('gloves',student);check('student cannot change mode',code==403)
code,_=set_mode('gloves',{**student,'X-MakerLens-Teacher':os.environ['MAKERLENS_ACCESS_TOKEN']});check('student code is not teacher code',code==403)
code,_=set_mode('gloves',{**teacher,'Origin':'https://invalid.example'});check('teacher wrong origin denied',code==403)
code,_=request('/api/ppe/teacher/verify',b'{}',teacher);check('teacher login',code==200)
buffer=io.BytesIO();Image.new('RGB',(640,480),'gray').save(buffer,'JPEG');frame=buffer.getvalue()
try:
    for mode in ['goggles','gloves','both']:
        code,settings=set_mode(mode,teacher);check('teacher config '+mode,code==200 and settings['mode']==mode)
        for route in ['/api/ppe/detect','/detect']:
            started=time.perf_counter()
            code,result=request(route,frame,{**student,'Content-Type':'application/octet-stream','X-MakerLens':'image','X-MakerLens-Mode':'gloves' if mode!='gloves' else 'goggles'})
            report['seconds'].append(round(time.perf_counter()-started,3))
            expected={'goggles','gloves'} if mode=='both' else {mode}
            check('server ignores student mode '+route+' '+mode,code==200 and result['mode']==mode and set(result['models'])==expected and result['settings_revision']==settings['revision'])
    for n in range(3):
        started=time.perf_counter();code,result=request('/api/ppe/detect',frame,{**student,'X-MakerLens':'image'})
        report['seconds'].append(round(time.perf_counter()-started,3));check('successive frame '+str(n),code==200)
finally:
    code,out=set_mode(initial['mode'],teacher);check('original teacher setting restored',code==200 and out['mode']==initial['mode'])
report['passed']=all(report['checks'].values());print(json.dumps(report,indent=2))
