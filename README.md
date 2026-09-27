# MakerLens

[中文项目介绍与真实检测页面](README.zh-CN.md)

AI-assisted STEM workshop safety monitoring research prototype.

## What it demonstrates

- A browser-based teacher monitoring dashboard
- Local image/video inference with two fine-tuned YOLO11n detectors
- Four visual labels: `goggles_worn`, `eyes_unprotected`, `gloves_worn`, and `bare_hands`
- Annotated media plus structured, frame-level detection logs
- Video-grouped evaluation, error auditing, and documented limitations

**MakerLens is not a validated safety system.** A missing detection does not mean that a scene is safe, and detecting gloves does not determine whether gloves are appropriate for a particular operation. The prototype does not control equipment or make disciplinary decisions.

## Project status — 2026-09-27

The repository contains two related but separate parts:

1. The existing static web dashboard: `index.html`, `app.js`, and `styles.css`.
2. The local Python computer-vision pipeline in [`ml/`](ml/README.md).

The Python pipeline runs two independent detectors on the same frame. It is not a jointly trained four-class model, a person tracker, or a safety-compliance classifier. Live predictions are not yet connected to the web dashboard.

The current glove candidate, `gloves-v3-cleanstart`, was trained from generic YOLO11n weights after review of a 149-image training set. The local interview package was smoke-tested on a separate sample image and on two full videos. Those media, model weights, datasets, and prediction outputs are private and are not included here.

## Development evaluation

| Model | Train / validation / test images | Test source videos | Precision | Recall | mAP50 | mAP50–95 |
|---|---:|---:|---:|---:|---:|---:|
| Goggles v1 | 86 / 19 / 19 | 2 | 0.722 | 0.850 | 0.804 | 0.426 |
| Gloves v3 clean-start | 149 / 19 / 17 | 3 | 0.992 | 0.847 | 0.913 | 0.626 |

These small sets contain correlated video frames. Splits were separated by source video file, but participant/session independence was not established. The 17-image glove test set was retained from the earlier development cycle, so the v3 result is a regression/candidate comparison—not a fresh, final generalization test and not a deployment accuracy claim.

See the [evaluation and failure-analysis report](ml/reports/BASELINE.md).

## Local demo

For the local image-upload web interface, run `python ml/serve.py --goggles "/path/to/goggles-best.pt" --gloves "/path/to/gloves-best.pt"` and open `http://127.0.0.1:8765`. It returns real model boxes and classes. The legacy static dashboard remains separate from this new local interface.

Install the Python dependencies, keep the private weights outside Git, and run:

```sh
python ml/run.py "/path/to/image-or-video" \
  --goggles "/path/to/goggles-best.pt" \
  --gloves "/path/to/gloves-best.pt"
```

The runner never uploads the source file. It creates an annotated image/video, a JSON Lines detection log, and a summary. Default confidence is 0.4 for each detector; this is a display setting, not a validated alarm threshold. See the full [local setup and usage guide](ml/README.md).

## Observed failure cases

Full-video testing retained failures instead of selecting only successful frames. Observed issues include:

- White sleeves detected as gloves
- Shirt graphics detected as bare hands
- Exposed eyes missed in unfamiliar glove-focused scenes
- Errors around motion blur, image boundaries, overlapping hands, and small/background people
- Ambiguous goggles transitions and confusion with ordinary glasses

These findings are why the project is presented as a human-review aid and research prototype.

## Privacy and public-repository policy

No participant photos, source videos, datasets, CVAT annotations, prediction media, local paths, or model weights are published. `.gitignore` excludes common private-data and generated-output formats. Anyone reusing the project must obtain appropriate image-use permission and review dependency/model licenses.

The project uses pretrained YOLO models and AI-assisted implementation/annotation. Its contribution is the applied workflow—data review, transfer learning, evaluation, error analysis, and local prototype integration—not a new object-detection algorithm.
