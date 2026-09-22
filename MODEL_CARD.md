# Private local model weights

Weights are not included in the public repository. Copy your locally trained files here, or provide their locations with `--goggles` and `--gloves`.

| Filename | Ordered class names | SHA-256 of the evaluated local baseline |
|---|---|---|
| `goggles-v1.pt` | `goggles_worn`, `eyes_unprotected` | `0a91496657a9e13e7b57ec215aa57d549988b22b046c001cd68e947e589624b8` |
| `gloves-v1.pt` | `gloves_worn`, `bare_hands` | `1508a3d6ca3dbba8e7f3c9bbca294a7f5dedc6a31ee5583782cd0a4fa12ab5bc` |

Only load trusted checkpoints. Both models are pretrained YOLO11n fine-tunes, not models trained from scratch. The runner checks class order before inference. Dataset/image-use permissions and dependency licensing need separate review before sharing models publicly.
