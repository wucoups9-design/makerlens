// Three consecutive fresh samples, per camera. No identity or safety classification.
class PPEAlerts {
  constructor(){this.reset()}
  reset(){this.counts={};this.revision=null;this.last=0;this.lastSound=-Infinity;this.gloveSince=null;this.reported=false;this.noHandsSince=null;this.noHandsReported=false}
  update(result, now=Date.now()){
    if(result.settings_revision!==this.revision||now-this.last>5000){this.counts={};this.lastSound=-Infinity;this.gloveSince=null;this.reported=false;this.noHandsSince=null;this.noHandsReported=false;}
    this.revision=result.settings_revision;this.last=now;
    const r=result.rules||{gloves:'observe',goggles_required:false,sound:false};
    const names=new Set(result.detections.filter(d=>d.confidence>=.4).map(d=>d.class));
    const checks=[];
    if(r.gloves!=='observe'&&result.mode!=='goggles')checks.push({key:'gloves',
      seen:names.has('bare_hands')||names.has('gloves_worn'),
      bad:names.has(r.gloves==='required'?'bare_hands':'gloves_worn'),
      message:r.gloves==='required'?'检测到裸手，请戴好手套！':'当前工序禁止戴手套，请先停止操作并脱下手套！'});
    if(r.goggles_required&&result.mode!=='gloves')checks.push({key:'goggles',
      seen:names.has('goggles_worn')||names.has('eyes_unprotected'),bad:names.has('eyes_unprotected'),
      message:'请戴好护目镜！'});
    const alerts=[],unknown=[],pending=[];
    for(const c of checks){this.counts[c.key]=c.bad?(this.counts[c.key]||0)+1:0;
      if(!c.seen)unknown.push(c.key==='gloves'?'手部无法判断':'眼部无法判断');
      else if(this.counts[c.key]>=3)alerts.push(c.message);
      else if(c.bad)pending.push('疑似异常，等待连续3帧确认');
    }
    const badGloves=result.mode!=='goggles'&&r.gloves==='required'&&names.has('bare_hands')&&!names.has('gloves_worn');
    if(!badGloves){this.gloveSince=null;this.reported=false;}else if(this.gloveSince===null)this.gloveSince=now;
    const escalate=badGloves&&!this.reported&&now-this.gloveSince>=120000&&this.counts.gloves>=3;
    const noHands=result.mode!=='goggles'&&!names.has('bare_hands')&&!names.has('gloves_worn');
    if(!noHands){this.noHandsSince=null;this.noHandsReported=false;}else if(this.noHandsSince===null)this.noHandsSince=now;
    const missingEscalate=noHands&&!this.noHandsReported&&now-this.noHandsSince>=600000;
    const beep=!!(alerts.length&&r.sound&&now-this.lastSound>=10000);
    if(beep)this.lastSound=now;
    return {alerts,unknown,pending,beep,escalate,missingEscalate,observing:!checks.length};
  }
}
if(typeof module!=='undefined')module.exports=PPEAlerts;
