# MakerLens — local vision baseline

Two separate YOLO11n detectors run on the same frame. This is not a jointly trained four-class model, a person tracker, or a safety-compliance classifier. The web dashboard is not connected to this pipeline yet.

## Labels

| Detector | Class 0 | Class 1 |
|---|---|---|
| Goggles | `goggles_worn` | `eyes_unprotected` |
| Hands | `gloves_worn` | `bare_hands` |

Each visible hand is annotated separately. Unworn equipment is not classified as worn. Glasses, transitions, occlusion and motion blur need careful review.

## Setup

The recorded baseline ran on macOS ARM64, Python 3.9.6, PyTorch 2.8.0 and Apple MPS. Other platforms or Python versions require compatibility checks. From the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Place your local trained weights at `models/goggles-v1.pt` and `models/gloves-v1.pt`, or pass their paths explicitly. They are deliberately not published. See [weight details](MODEL_CARD.md). Optional FFmpeg produces browser-friendly H.264 video; without it, the script falls back to OpenCV MP4V, which may not play in every browser.

## Run on a local file

```sh
python vision.py "/path/to/video.mp4" \
  --goggles "/path/to/goggles-best.pt" \
  --gloves "/path/to/gloves-best.pt" \
  --output "/path/to/new-output-directory"
```

The same command accepts JPG/PNG images. Output directories must be new; existing directories are refused. Without `--output`, a timestamped directory is created under `results/`.

- `annotated.mp4` for video, `preview.jpg` for images/video preview.
- `detections.jsonl`: class, confidence, box and frame timestamp, in resized output-image coordinates.
- `summary.json`: settings and frame-level detection counts, **not people or incident counts**.

The default confidence is 0.4 for each detector, and video stride is 3. Playback FPS is divided by the same stride to retain approximately the original duration. Audio is omitted. Use `--stride 1` for every frame, `--seconds 10` for a short trial, or `--device cpu` to avoid MPS. The default device is MPS when available, otherwise CPU.

Do not treat the colored labels as safe/unsafe decisions. No detections does not mean no risk.

## Training and evaluation

Each model started from `yolo11n.pt` pretrained weights and was fine-tuned for 50 epochs, 640 input size, batch 8, MPS, workers 0, seed 0. Best weights were selected using validation, not test metrics.

```sh
yolo detect train model=yolo11n.pt data="/path/to/data.yaml" \
  epochs=50 imgsz=640 batch=8 device=mps workers=0 seed=0 \
  project="/path/to/training-runs" name=baseline

python evaluate.py --model "/path/to/best.pt" \
  --data "/path/to/data.yaml" --output "/path/to/new-audit" --conf 0.4

python -m unittest test_vision -v
```

The evaluator expects a local YOLO detection dataset with `images/test` and matching `labels/test`, and a YAML containing `test: images/test` and `names`. `path` may be absolute, relative to the YAML file, or omitted. Only JPG/JPEG/PNG test images in that directory are audited. Formal metrics are produced by Ultralytics; fixed-threshold auditing separately matches predictions by class and IoU >= 0.5, one-to-one, in descending confidence order. Missing/empty labels are treated as background: review them before evaluating.

Datasets and exact per-image annotations are private and are not included, so cloning this repository alone does not reproduce training or the reported metrics. See [baseline results](BASELINE.md).

## Next steps

1. Independently review the 104 AI-annotated glove images; 180 extracted images remain unannotated.
2. Resolve eye-label policies for wearing/removing goggles, regular glasses, and occlusion.
3. Add fully annotated training examples of white sleeves, shirt prints, background people, small hands, and each detector's unfamiliar scenes.
4. Evaluate on new participants and recording sessions; do not repeatedly tune on the current test set and present it as untouched.
5. Only after validation, connect inference to the dashboard. Keep operational rules separate from object detection and retain human supervision.
