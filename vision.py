"""Local two-model PPE visual demo. No compliance/safety decisions are made."""
import argparse
import json
import math
import shutil
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageOps
from ultralytics import YOLO

HERE = Path(__file__).resolve().parent
EXPECTED = {'goggles': ['goggles_worn', 'eyes_unprotected'],
            'gloves': ['gloves_worn', 'bare_hands']}
COLORS = {'goggles_worn': (230,180,40), 'eyes_unprotected': (40,130,245),
          'gloves_worn': (210,80,200), 'bare_hands': (80,205,245)}

def resize_frame(frame, long_side):
    h,w = frame.shape[:2]
    scale = min(1.0, long_side/max(h,w))
    # H.264 yuv420p requires even dimensions.
    size = (max(2, round(w*scale)//2*2), max(2, round(h*scale)//2*2))
    return cv2.resize(frame, size) if size != (w,h) else frame

def extract_boxes(result, model_name):
    if result.boxes is None:
        return []
    answer=[]
    for xyxy, cls, confidence in zip(result.boxes.xyxy.cpu().tolist(),
                                    result.boxes.cls.cpu().tolist(), result.boxes.conf.cpu().tolist()):
        name=result.names[int(cls)]
        if name not in EXPECTED[model_name]:
            raise ValueError(f'Unexpected class {name} in {model_name}')
        answer.append({'model':model_name, 'class':name, 'confidence':round(confidence,5),
                       'xyxy':[round(v,2) for v in xyxy]})
    return answer

def draw_frame(frame, detections, stamp):
    out = frame.copy()
    for det in detections:
        x1,y1,x2,y2 = (round(v) for v in det['xyxy'])
        color = COLORS[det['class']]
        cv2.rectangle(out,(x1,y1),(x2,y2),color,2)
        text=f"{det['class']} {det['confidence']:.2f}"
        (tw,th),base = cv2.getTextSize(text,cv2.FONT_HERSHEY_SIMPLEX,.42,1)
        tx=min(max(0,x1),max(0,out.shape[1]-tw-5))
        ty=max(th+5,y1-5)
        cv2.rectangle(out,(tx,ty-th-3),(tx+tw+4,ty+base), (20,20,20), -1)
        cv2.putText(out,text,(tx+2,ty),cv2.FONT_HERSHEY_SIMPLEX,.42,color,1,cv2.LINE_AA)
    cv2.rectangle(out,(0,0),(out.shape[1],43),(23,23,23),-1)
    cv2.putText(out, 'MakerLens | Research demo | '+stamp,(8,17),cv2.FONT_HERSHEY_SIMPLEX,.42,(240,240,240),1,cv2.LINE_AA)
    cv2.putText(out,'Detections only - NOT a safety decision',(8,34),cv2.FONT_HERSHEY_SIMPLEX,.39,(70,190,255),1,cv2.LINE_AA)
    return out

class VideoWriter:
    def __init__(self,path,size,fps):
        self.process=None
        ffmpeg=shutil.which('ffmpeg')
        if not ffmpeg and Path('/opt/homebrew/bin/ffmpeg').exists():
            ffmpeg='/opt/homebrew/bin/ffmpeg'
        if ffmpeg:
            self.process=subprocess.Popen([ffmpeg,'-hide_banner','-loglevel','error','-n',
                '-f','rawvideo','-pix_fmt','bgr24','-s',f'{size[0]}x{size[1]}','-r',str(fps),
                '-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','24',
                '-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)
        else:
            self.writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*'mp4v'),fps,size)
            if not self.writer.isOpened():
                raise RuntimeError('Cannot create video writer')
    def write(self,frame):
        if self.process:
            self.process.stdin.write(np.ascontiguousarray(frame).tobytes())
        else:
            self.writer.write(frame)
    def close(self):
        if self.process:
            self.process.stdin.close()
            if self.process.wait()!=0:
                raise RuntimeError('Video encoding failed')
        else:
            self.writer.release()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path,help='Local image or video; never uploaded')
    parser.add_argument('--output',type=Path,help='New directory; an existing directory is refused')
    parser.add_argument('--goggles',type=Path,default=HERE/'models/goggles-v1.pt')
    parser.add_argument('--gloves',type=Path,default=HERE/'models/gloves-v1.pt')
    parser.add_argument('--device',default='mps' if torch.backends.mps.is_available() else 'cpu')
    parser.add_argument('--goggles-conf',type=float,default=.4)
    parser.add_argument('--gloves-conf',type=float,default=.4)
    parser.add_argument('--imgsz',type=int,default=640)
    parser.add_argument('--long-side',type=int,default=960)
    parser.add_argument('--stride',type=int,default=3,help='For video: process every Nth frame, retaining playback duration')
    parser.add_argument('--seconds',type=float,default=0,help='0=whole video, otherwise first N seconds')
    args=parser.parse_args()
    if not args.source.is_file(): parser.error('Source file does not exist')
    if args.stride<1 or args.long_side<64 or args.imgsz<32 or args.seconds<0: parser.error('Invalid size/stride/seconds')
    if not all(0<c<1 for c in (args.goggles_conf,args.gloves_conf)): parser.error('Confidence must be between 0 and 1')
    models=[]
    for name,path,conf in [('goggles',args.goggles,args.goggles_conf),('gloves',args.gloves,args.gloves_conf)]:
        if not path.is_file(): parser.error(f'Missing model: {path}')
        model=YOLO(str(path))
        if [model.names[i] for i in range(len(model.names))]!=EXPECTED[name]:
            parser.error(f'Wrong classes in {path}: {model.names}')
        models.append((name,model,conf))
    output=args.output or HERE/'results'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    output.mkdir(parents=True,exist_ok=False)
    def detect(frame):
        objects=[]
        for name,model,conf in models:
            result=model.predict(frame,device=args.device,imgsz=args.imgsz,conf=conf,verbose=False)[0]
            objects.extend(extract_boxes(result,name))
        return objects
    count=Counter(); processed=0; started=time.perf_counter()
    if args.source.suffix.lower() in {'.jpg','.jpeg','.png','.bmp','.webp'}:
        rgb=np.array(ImageOps.exif_transpose(Image.open(args.source)).convert('RGB'))
        frame=resize_frame(cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR),args.long_side)
        detections=detect(frame)
        if not cv2.imwrite(str(output/'preview.jpg'),draw_frame(frame,detections,'Image')):
            raise RuntimeError('Image write failed')
        (output/'detections.jsonl').write_text(json.dumps({'frame_index':0,'time_seconds':0,'detections':detections})+'\n')
        count.update(d['class'] for d in detections); processed=1
        media={'type':'image','width':frame.shape[1],'height':frame.shape[0]}
    else:
        cap=cv2.VideoCapture(str(args.source))
        if not cap.isOpened(): raise RuntimeError('Cannot decode source video')
        cap.set(cv2.CAP_PROP_ORIENTATION_AUTO,1)
        fps=cap.get(cv2.CAP_PROP_FPS)
        if not math.isfinite(fps) or fps<=0:
            cap.release(); raise RuntimeError('Invalid source FPS; cannot preserve timestamps')
        writer=None; n=0; output_size=None
        try:
            with (output/'detections.jsonl').open('w') as log:
                while True:
                    ok,frame=cap.read()
                    if not ok or (args.seconds and n/fps>=args.seconds): break
                    frame_id=n; n+=1
                    if frame_id%args.stride: continue
                    frame=resize_frame(frame,args.long_side)
                    detections=detect(frame)
                    visual=draw_frame(frame,detections,f'{frame_id/fps:.1f}s')
                    if writer is None:
                        output_size=(frame.shape[1],frame.shape[0])
                        writer=VideoWriter(output/'annotated.mp4',output_size,fps/args.stride)
                        if not cv2.imwrite(str(output/'preview.jpg'),visual): raise RuntimeError('Preview write failed')
                    writer.write(visual)
                    log.write(json.dumps({'frame_index':frame_id,'time_seconds':round(frame_id/fps,4),'detections':detections})+'\n')
                    count.update(d['class'] for d in detections); processed+=1
                    if processed%60==0: print(f'Processed {processed} frames, source {frame_id/fps:.1f}s',flush=True)
        finally:
            cap.release()
            if writer: writer.close()
        if not processed: raise RuntimeError('No frames decoded')
        media={'type':'video','source_fps':fps,'output_fps':fps/args.stride,'source_frames_read':n,
               'width':output_size[0],'height':output_size[1],'audio':'omitted','stride':args.stride}
    summary={'source':str(args.source.resolve()),'output':str(output.resolve()),'models':{name:str(path.resolve()) for name,path in [('goggles',args.goggles),('gloves',args.gloves)]},
             'device':args.device,'confidence':{'goggles':args.goggles_conf,'gloves':args.gloves_conf},
             'imgsz':args.imgsz,'processed_frames':processed,'media':media,'elapsed_seconds':round(time.perf_counter()-started,3),
             'detections_over_frames':dict(count),'limitations':['Counts are frame detections, NOT unique people or incidents.',
                'No detection does not mean safe. Occlusion and incorrect predictions remain possible.',
                'Two independent detectors; no person association, machine-state recognition, or compliance decision.']}
    (output/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
