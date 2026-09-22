"""Formal test metrics + fixed-threshold error audit, with visual QA output."""
import argparse
import json
from collections import Counter
from pathlib import Path
import yaml
import torch
from PIL import Image, ImageDraw
from ultralytics import YOLO

def dataset_root(config_path, data):
    root=Path(data.get('path') or '.')
    return root if root.is_absolute() else (config_path.resolve().parent/root).resolve()

def iou(a,b):
    x1,y1=max(a[0],b[0]),max(a[1],b[1])
    x2,y2=min(a[2],b[2]),min(a[3],b[3])
    inter=max(0,x2-x1)*max(0,y2-y1)
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union>0 else 0.0

def match(gt,preds,threshold=.5):
    remaining=set(range(len(gt)))
    matched=[]; unmatched=[]
    for pidx,p in sorted(enumerate(preds),key=lambda v:-v[1]['confidence']):
        candidates=[(iou(p['xyxy'],gt[g]['xyxy']),g) for g in remaining if gt[g]['class_id']==p['class_id']]
        overlap,g=max(candidates,default=(0,-1))
        if overlap>=threshold:
            matched.append({'prediction':pidx,'truth':g,'iou':overlap}); remaining.remove(g)
        else: unmatched.append(pidx)
    return matched,unmatched,sorted(remaining)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--conf',type=float,default=.4)
    p.add_argument('--device',default='mps' if torch.backends.mps.is_available() else 'cpu')
    args=p.parse_args()
    if not args.model.is_file() or not args.data.is_file(): p.error('Model and data YAML must be local files')
    if not 0<args.conf<1: p.error('Confidence must be between 0 and 1')
    args.output.mkdir(parents=True,exist_ok=False)
    data=yaml.safe_load(args.data.read_text())
    root=dataset_root(args.data, data)
    images=sorted(f for f in (root/data['test']).iterdir() if f.is_file() and f.suffix.lower() in ('.jpg','.jpeg','.png'))
    assert images, 'Empty test set'
    # Use the same absolute root for Ultralytics validation and local auditing.
    resolved_config=args.output/'resolved_data.yaml'
    resolved_config.write_text(yaml.safe_dump(dict(data, path=str(root))))
    model=YOLO(str(args.model))
    metrics=model.val(data=str(resolved_config.resolve()),split='test',device=args.device,imgsz=640,batch=8,workers=0,
                      project=str(args.output),name='formal',plots=True,save_json=True,verbose=False)
    formal={'aggregate':{k:float(v) for k,v in metrics.results_dict.items()},'per_class':metrics.summary(),
            'speed_ms':metrics.speed,'image_count':len(images), 'note':'P/R are Ultralytics curve-selected values, not fixed conf=0.4.'}
    # Ultralytics summaries include NumPy scalar counts.
    formal=json.loads(json.dumps(formal,default=lambda value:value.item()))
    (args.output/'formal_metrics.json').write_text(json.dumps(formal,indent=2))
    totals=Counter(); records=[]
    visual=args.output/'audit_images'; visual.mkdir()
    results=model.predict([str(f) for f in images],device=args.device,imgsz=640,conf=args.conf,verbose=False,stream=True)
    for image_path,result in zip(images,results):
        im=Image.open(image_path).convert('RGB'); w,h=im.size
        label=root/'labels'/'test'/(image_path.stem+'.txt')
        gt=[]
        if label.exists():
            for line in label.read_text().splitlines():
                c,x,y,bw,bh=map(float,line.split())
                gt.append({'class_id':int(c),'xyxy':[(x-bw/2)*w,(y-bh/2)*h,(x+bw/2)*w,(y+bh/2)*h]})
        preds=[{'class_id':int(c),'confidence':float(conf),'xyxy':box} for c,conf,box in
                zip(result.boxes.cls.cpu().tolist(),result.boxes.conf.cpu().tolist(),result.boxes.xyxy.cpu().tolist())]
        matched,fp,fn=match(gt,preds)
        totals.update(tp=len(matched),fp=len(fp),fn=len(fn),images=1)
        record={'image':image_path.name,'gt':gt,'predictions':preds,'matched':matched,'false_positives':fp,'missed_truth':fn}
        records.append(record)
        scale=480/max(w,h); im=im.resize((round(w*scale),round(h*scale))); draw=ImageDraw.Draw(im)
        for objs,tag,color in [(gt,'GT','#35c9ff'),(preds,'P','#ff8c26')]:
            for o in objs:
                coords=[int(v*scale) for v in o['xyxy']]
                draw.rectangle(coords,outline=color,width=2)
                y=max(0,coords[1]-12) if tag=='GT' else coords[1]+3
                text=f'{tag}:{o["class_id"]}' + (f' {o["confidence"]:.2f}' if tag=='P' else '')
                draw.text((coords[0],y),text,fill=color,stroke_width=1,stroke_fill='black')
        im.save(visual/image_path.name,quality=95)
    pval=totals['tp']/max(1,totals['tp']+totals['fp']); rval=totals['tp']/max(1,totals['tp']+totals['fn'])
    audit={'threshold':args.conf,'iou_match':.5,'totals':totals,'precision':pval,'recall':rval,'records':records,
           'error_images':[r['image'] for r in records if r['false_positives'] or r['missed_truth']],
           'legend':{'GT':'cyan ground truth','P':'orange prediction'}, 'names':model.names}
    (args.output/'fixed_threshold_audit.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps({'formal':formal,'fixed_threshold':{'totals':totals,'precision':pval,'recall':rval,'errors':audit['error_images']}},indent=2))

if __name__=='__main__': main()
