# MakerLens local vision pipeline

Two independent YOLO11n detectors process the same local image or video. This is not a four-class joint model, person tracker, machine-state detector, or safety-compliance system. The web dashboard is not connected to this pipeline yet.

## Labels

| Detector | Class 0 | Class 1 |
|---|---|---|
| Goggles | `goggles_worn` | `eyes_unprotected` |
| Hands | `gloves_worn` | `bare_hands` |

Each visible hand is annotated separately. Unworn equipment should not be classified as worn. Ordinary glasses, wearing/removing transitions, occlusion, image boundaries, and motion blur require careful review.

## Setup

The recorded local baseline used macOS ARM64, Python 3.9.6, PyTorch 2.8.0, and Apple MPS. Other platforms require compatibility checks.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r ml/requirements.txt
```

Keep private weights at `ml/models/goggles-v1.pt` and `ml/models/gloves-v3-cleanstart.pt`, or pass their paths explicitly. Weights are deliberately excluded from Git. Optional FFmpeg produces browser-friendly H.264; otherwise the script falls back to OpenCV MP4V.

## Run on a local file

For the image-upload webpage, start `python ml/serve.py --goggles /path/to/goggles.pt --gloves /path/to/gloves.pt` and open `http://127.0.0.1:8765`. Images are processed locally with temporary files cleared after inference. See the [Chinese walkthrough](../README.zh-CN.md).

```sh
python ml/run.py "/path/to/video.mp4" \
  --goggles "/path/to/goggles-best.pt" \
  --gloves "/path/to/gloves-best.pt" \
  --output "/path/to/new-output-directory"
```

JPG, PNG, and common video files are accepted. Existing output directories are refused. Without `--output`, a timestamped directory is created under `ml/results/`.

Outputs:

- `annotated.mp4` for video or `preview.jpg` for images
- `detections.jsonl` with class, confidence, bounding box, frame index, and timestamp
- `summary.json` with settings and frame-level detection counts

Counts are not unique people, incidents, or safety violations. Audio is omitted. Defaults are confidence 0.4, image size 640, and video stride 3. Use `--stride 1` to process every frame, `--seconds 10` for a short trial, or `--device cpu` when MPS is unavailable.

## Training and evaluation

The current glove candidate used 149 reviewed training images, 19 validation images, and the retained 17-image development test. Both detectors started from generic `yolo11n.pt` pretrained weights and were fine-tuned at 640 input size, batch 8, Apple MPS, workers 0, and seed 0.

```sh
yolo detect train model=yolo11n.pt data="/path/to/data.yaml" \
  epochs=50 imgsz=640 batch=8 device=mps workers=0 seed=0

python ml/evaluate.py --model "/path/to/best.pt" \
  --data "/path/to/data.yaml" --output "/path/to/new-audit" --conf 0.4

python -m unittest discover -s ml/tests -v
```

The evaluator expects `images/test`, matching `labels/test`, and a YOLO YAML with `test` and `names`. Formal Ultralytics metrics and fixed-threshold one-to-one matching at class-aware IoU >= 0.5 are reported separately.

Datasets and per-image annotations are private, so cloning this repository alone cannot reproduce training or the reported metrics. See the [evaluation report](reports/BASELINE.md).

## Interview/demo workflow

For a live presentation, use a previously verified fallback result first, then run one reviewed local sample image. A fresh video can demonstrate generalization, but its output should be described as exploratory. Do not install dependencies, retrain, or tune thresholds during the interview.

## Next steps

1. Collect a fresh participant/session-separated final test set.
2. Add reviewed cross-scene examples: white sleeves, printed clothing, ordinary glasses, occlusion, small hands, and unfamiliar eye angles.
3. Define consistent annotation policy for goggles transitions and partially visible hands/eyes.
4. Evaluate both detectors on the same new scenes and retain failures.
5. Only after broader validation, consider dashboard integration while preserving human supervision.
