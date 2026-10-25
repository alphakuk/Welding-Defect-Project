"""data/raw 원본 사진에서 소스별로 모델 판정을 원본 라벨(9종 매핑)과 비교.

사용법: .venv/Scripts/python tools/check_raw.py [소스당 표본 수]
"""
import random
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from build_dataset import RAW, SOURCES, parse_label, source_dir  # noqa: E402
from weld_defect.config import CLASS_BY_NAME, CLASSES, Config  # noqa: E402
from weld_defect.detector import DefectDetector  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
cfg = Config()
det = DefectDetector(cfg)
srcs = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))["sources"]
random.seed(0)

print(f"{'source':<45}{'표본':>5}{'라벨있음':>8}{'결함검출':>8}{'정답포함':>8}{'대표판정정답':>10}   주요 판정")
for src in srcs:
    sdir = source_dir(src["slug"], src["version"])
    names = yaml.safe_load((sdir / "data.yaml").read_text(encoding="utf-8"))["names"]
    imgs = sorted(p for p in sdir.rglob("images/*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
    sample = random.sample(imgs, min(N, len(imgs)))
    n_lab = n_any = n_hit = n_top = 0
    top = Counter()
    for p in sample:
        lbl = p.parent.parent / "labels" / f"{p.stem}.txt"
        gt = set()
        if lbl.exists():
            for line in lbl.read_text(encoding="utf-8").splitlines():
                b = parse_label(line)
                if b and src["class_map"].get(names[b[0]]):
                    gt.add(CLASS_BY_NAME[src["class_map"][names[b[0]]]].id)
        v = det.predict(p)
        pred = {d.class_id for d in v.detections}
        top[v.main.ko if v.main else "없음"] += 1
        if gt:
            n_lab += 1
            n_any += bool(pred)
            n_hit += bool(gt & pred)
            n_top += bool(v.main and v.main.class_id in gt)
    f = lambda a: f"{a / n_lab:.0%}" if n_lab else "-"
    print(f"{src['slug'][:44]:<45}{len(sample):>5}{n_lab:>8}{f(n_any):>8}{f(n_hit):>8}{f(n_top):>10}   "
          + ", ".join(f"{k}{c}" for k, c in top.most_common(3)))
