# Private local model weights

Weights are not included in the public repository. Copy your locally trained files here, or provide their locations with `--goggles` and `--gloves`.

| Filename | Ordered class names | SHA-256 of the evaluated local candidate |
|---|---|---|
| `goggles-v1.pt` | `goggles_worn`, `eyes_unprotected` | `0a91496657a9e13e7b57ec215aa57d549988b22b046c001cd68e947e589624b8` |
| `gloves-v3-cleanstart.pt` | `gloves_worn`, `bare_hands` | `a3e0efb63158963c177a019f51d8a7e82df223ff4443cafe96ce076ac2456089` |

Only load trusted checkpoints. Both models are YOLO11n fine-tunes initialized from generic pretrained weights, not models trained from random initialization. The runner checks class order before inference. Dataset/image-use permissions and dependency licensing need separate review before sharing models publicly.
