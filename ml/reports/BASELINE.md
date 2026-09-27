# Development evaluation and failure analysis — 2026-09-27

This report publishes aggregate results only. It excludes participant media, annotations, datasets, local machine paths, model weights, and prediction outputs.

## Data and scope

| Detector | Train / validation / test images | Test source videos | Test objects |
|---|---:|---:|---:|
| Goggles v1 | 86 / 19 / 19 | 2 | 17 |
| Gloves v3 clean-start | 149 / 19 / 17 | 3 | 31 |

The splits are disjoint by source video file, not verified by participant or recording session. Nearby frames remain correlated. The 149-image glove training set was reviewed before the clean-start run; structural checks passed, but no independent second-annotator agreement study was performed.

The glove validation and test images were retained from the previous development cycle. Because earlier test errors informed later data work, this test is a regression/candidate comparison, not a fresh final holdout.

## Formal evaluation

| Detector | Precision | Recall | mAP50 | mAP50–95 |
|---|---:|---:|---:|---:|
| Goggles v1 | 0.7224 | 0.8500 | 0.8038 | 0.4264 |
| Gloves v1 (historical) | 0.9765 | 0.7815 | 0.8932 | 0.6040 |
| Gloves v3 clean-start | 0.9920 | 0.8470 | 0.9130 | 0.6260 |

Precision and recall are Ultralytics curve-selected values, not measurements at the demo confidence setting of 0.4. Minor rounding is used for the v3 aggregate. These figures do not establish deployment accuracy or real-time performance.

Historical class-wise summaries remain available for [goggles v1](goggles_metrics.json) and [gloves v1](gloves_v1_metrics.json). The current v3 row is the verified aggregate recorded by the local experiment manifest.

## Full-video findings

The same dual-model runner processed complete local clips rather than a hand-picked success reel. Retained failures included:

- White sleeves frequently detected as gloves in a drill scene
- Shirt graphics detected as bare hands
- Exposed eyes missed in a glove-focused scene
- Poor localization or missed detections around motion blur, fingertips at image boundaries, overlapping hands, and partly hidden background people
- Ambiguous wearing/removing-goggles frames and possible confusion with ordinary glasses

These videos came from the existing collection, not a fresh deployment trial. Detection counts across frames are not people or incident counts.

## Interpretation

The v3 glove candidate improved the retained development-set aggregate, but the small correlated test cannot support a general safety claim. Cross-scene errors show that object-level benchmark metrics alone do not capture the intended classroom setting.

MakerLens should remain a research/demo and human-review aid. It must not directly trigger equipment interlocks, disciplinary actions, or claims that a student is safe. The next valid milestone is evaluation on new participants, recording sessions, backgrounds, clothing, and operations that were not used to choose the model or training data.
