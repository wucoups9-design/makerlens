# MakerLens

AI-assisted STEM workshop safety monitoring prototype.

## Features

- Safety-goggle and glove monitoring interface
- Rule-based workshop safety alerts
- Teacher monitoring dashboard
- Camera-based prototype workflow
- Local image/video detection using two fine-tuned YOLO11n models
- Video-grouped evaluation, error auditing, and documented limitations

## Project Status — 2026-09-23

The first local computer-vision baseline has been trained and evaluated. Two independent detectors process the same image/video and export annotated media and structured detections.

**This is a research prototype, not a validated safety system.** False positives and missed detections remain substantial across scenes. A missing detection does not imply safety, and detecting gloves does not determine whether gloves are appropriate for a particular operation.

The existing web dashboard (`index.html`, `app.js`, `styles.css`) is preserved. The Python pipeline in [`vision.py`](VISION_GUIDE.md) runs separately: this update does **not** connect live model predictions to the web dashboard or deploy a new inference service.

## Demo

The web interface has been tested through Tencent Cloud EdgeOne. Local video inference is now available through [`vision.py`](vision.py); see the [setup and usage guide](VISION_GUIDE.md).

No participant photos, source videos, datasets, prediction videos, or model weights are included in this public repository. Running inference requires the two locally trained weights described in [`MODEL_CARD.md`](MODEL_CARD.md).

## Baseline results

| Model | Test images / source videos | mAP50 | mAP50–95 |
|---|---:|---:|---:|
| Goggles / unprotected eyes | 19 / 2 | 80.4% | 42.6% |
| Gloves / bare hands | 17 / 3 | 89.3% | 60.4% |

These are small, correlated video-frame test sets, **not deployment accuracy claims**. Only source-video-file separation was verified, not participant or recording-session independence. Glove annotations are AI-generated and have not received independent human acceptance.

See the [evaluation report and failure analysis](BASELINE.md) and [next steps](VISION_GUIDE.md#next-steps).

## Privacy and scope

Inference accepts local files and does not send input images/videos to a remote inference service. Results can contain identifiable images and local paths: keep them private unless separately reviewed and authorized for sharing. The repository ignore rules exclude datasets, media, weights, and generated runs.

The project uses pretrained YOLO models and AI-assisted implementation/annotation. It is an application and evaluation baseline, not a new detection algorithm. Review dependency licenses and obtain appropriate image-use permission before redistribution or deployment.
