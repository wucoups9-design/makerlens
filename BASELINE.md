# Baseline evaluation — 2026-09-23

This report publishes aggregate results only. No participant media, dataset labels, local machine paths, or prediction images are published.

## Data and scope

| Detector | Train / validation / test images | Test source videos | Test objects |
|---|---:|---:|---:|
| Goggles / unprotected eyes | 86 / 19 / 19 | 2 | 17 |
| Gloves / bare hands | 68 / 19 / 17 | 3 | 31 |

Splits are disjoint by source video file, not verified by participant or recording session. Nearby frames are correlated. Glove data consists of 104 selected AI-annotated images from 284 extracted frames; 180 were left pending, not added as negative examples. Independent human annotation acceptance has not been performed.

## Formal held-out evaluation

| Detector | Precision | Recall | mAP50 | mAP50–95 |
|---|---:|---:|---:|---:|
| Goggles | 0.7224 | 0.8500 | 0.8038 | 0.4264 |
| Gloves | 0.9765 | 0.7815 | 0.8932 | 0.6040 |

Precision/recall above are Ultralytics curve-selected values, not values at display confidence 0.4. Full class-wise summaries: [goggles](goggles_metrics.json), [gloves](gloves_metrics.json). Recorded inference timing is run-specific and does not establish real-time system performance.

## Fixed display-threshold audit

Confidence 0.4, class-aware one-to-one matching at IoU >= 0.5:

| Detector | TP | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|
| Goggles | 14 | 4 | 3 | 0.7778 | 0.8235 |
| Gloves | 24 | 3 | 7 | 0.8889 | 0.7742 |

Some wearing/removing-goggles frames have empty annotations. Apparent false positives on these frames are label-policy ambiguities, not necessarily confirmed model mistakes. This limits interpretation of both formal and fixed-threshold metrics.

## Combined-video findings

The same dual-model runner processed two complete local clips, approximately 23.1 seconds and 36.2 seconds, using stride 3. Failures were retained rather than edited out:

- In the goggles/drill scene, white sleeves were frequently detected as gloves.
- In the glove scene, exposed eyes were often missed by the goggles detector.
- Shirt graphics were sometimes detected as bare hands.
- Motion blur, fingertips at image boundaries, overlapping hands and partly hidden background people led to missed detections or poor localization.

These clips were drawn from the existing data collection, not a new independent deployment trial. The figures above must not be described as reliable performance across scenes or as safety guarantees.

## Verification and next iteration

Local image and video inference completed, output video frames and detection-log counts were checked, and the public script helper tests were run. No browser dashboard integration or live-camera safety validation is claimed.

Prioritize human label review and cross-scene training examples. Because these test errors now inform development, obtain a fresh final test set for later iterations. Object detections must not directly trigger equipment interlocks or disciplinary decisions.
