"""원본 소스에서 특정 클래스 bbox crop 몇 장을 한 장의 격자 이미지로 저장 (매핑 검수용).

사용법: python tools/preview_class.py <raw 폴더명> <클래스명> <출력.jpg> [개수]
"""
import sys
from pathlib import Path

import yaml
from PIL import Image

from build_dataset import RAW, parse_label

src, cls_name, out = sys.argv[1], sys.argv[2], sys.argv[3]
n = int(sys.argv[4]) if len(sys.argv) > 4 else 12
sdir = RAW / src
names = yaml.safe_load((sdir / "data.yaml").read_text(encoding="utf-8"))["names"]
cid = names.index(cls_name)

tiles = []
for lbl in sorted(sdir.rglob("labels/*.txt")):
    for line in lbl.read_text(encoding="utf-8").splitlines():
        b = parse_label(line)
        if not b or b[0] != cid:
            continue
        imgs = [p for p in lbl.parent.parent.glob("images/" + lbl.stem + ".*")]
        if not imgs:
            continue
        with Image.open(imgs[0]) as im:
            im = im.convert("RGB")
            W, H = im.size
            _, cx, cy, w, h = b
            pw, ph = max(w * W * 2, 64), max(h * H * 2, 64)
            box = (max(0, cx * W - pw / 2), max(0, cy * H - ph / 2),
                   min(W, cx * W + pw / 2), min(H, cy * H + ph / 2))
            tiles.append(im.crop(tuple(int(v) for v in box)).resize((200, 200)))
        break
    if len(tiles) >= n:
        break

cols = 4
grid = Image.new("RGB", (cols * 200, ((len(tiles) + cols - 1) // cols) * 200), "white")
for i, t in enumerate(tiles):
    grid.paste(t, ((i % cols) * 200, (i // cols) * 200))
grid.save(out, quality=90)
print(f"{len(tiles)} tiles -> {out}")
