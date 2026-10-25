"""Roboflow 소스들을 내려받아 9개 결함 클래스로 통일한 데이터셋을 만든다.

출력
  datasets/weld_det/{train,val,test}/{images,labels}  YOLO 객체탐지
  datasets/weld_det/data.yaml, manifest.csv, stats.txt
  datasets/weld_cls/{train,val,test}/<class>/*.jpg     bbox crop 이미지 분류

사용법
  python tools/build_dataset.py            # 다운로드(캐시 사용) + 빌드
  python tools/build_dataset.py --no-download
"""
import argparse
import csv
import hashlib
import math
import random
import re
import shutil
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageOps

from rf_common import download, export_link, get_api_key

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SOURCES = ROOT / "data" / "sources.yaml"
DET = ROOT / "datasets" / "weld_det"
CLS = ROOT / "datasets" / "weld_cls"

# H:/Welding_Defects/wD.png 의 결함 9종
CLASSES = [
    ("incomplete_penetration", "용입부족"),
    ("crack", "균열"),
    ("undercut", "언더컷"),
    ("underfill", "언더필"),
    ("arc_strike", "아크스트라이크"),
    ("porosity", "기공"),
    ("blowhole", "블로홀"),
    ("spatter", "스패터"),
    ("overlap", "오버랩"),
]
CLASS_ID = {name: i for i, (name, _) in enumerate(CLASSES)}
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SPLIT_RATIO = {"train": 0.7, "val": 0.15, "test": 0.15}


def source_dir(slug, version):
    return RAW / f"{slug.replace('/', '__')}__v{version}"


def fetch(key, src):
    out = source_dir(src["slug"], src["version"])
    done = out / ".done"
    if done.exists():
        return out
    RAW.mkdir(parents=True, exist_ok=True)
    zpath = out.with_suffix(".zip")
    if not zpath.exists():
        link = export_link(key, f"{src['slug']}/{src['version']}", "yolov8")
        print(f"  download {src['slug']} v{src['version']}", flush=True)
        download(link, zpath)
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    with zipfile.ZipFile(zpath) as z:
        for m in z.infolist():
            if m.is_dir():
                continue
            target = (out / shorten(m.filename)).resolve()
            # zip slip 방지
            if not str(target).startswith(str(out.resolve())):
                raise ValueError(f"잘못된 zip 경로: {m.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(m) as fsrc, open(target, "wb") as fdst:
                shutil.copyfileobj(fsrc, fdst)
    done.write_text("ok")
    return out


def shorten(member, limit=60):
    """Windows 경로 길이 제한 회피: 긴 파일명의 원본 부분을 해시로 줄인다.
    이미지와 라벨이 같은 이름으로 줄어들도록 확장자를 뺀 stem 기준으로 처리."""
    parts = member.split("/")
    name = parts[-1]
    stem, dot, ext = name.rpartition(".")
    if not dot or len(stem) <= limit:
        return member
    base, rf, rest = stem.partition(".rf.")
    short = base[:30] + "_" + hashlib.md5(base.encode()).hexdigest()[:10]
    parts[-1] = f"{short}{rf}{rest}.{ext}"
    return "/".join(parts)


def group_key(stem):
    """Roboflow 증강 사본(xxx_jpg.rf.<hash>)을 원본 단위로 묶는다."""
    base = stem.split(".rf.")[0]
    return re.sub(r"_(jpg|jpeg|png|bmp|webp)$", "", base, flags=re.I)


def parse_label(line):
    """YOLO bbox 또는 polygon(seg) 한 줄 -> (cls, cx, cy, w, h)."""
    vals = line.split()
    if len(vals) < 5:
        return None
    c = int(float(vals[0]))
    nums = [float(v) for v in vals[1:]]
    if len(nums) == 4:
        cx, cy, w, h = nums
    else:
        xs, ys = nums[0::2], nums[1::2]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return None
    return c, cx, cy, w, h


def collect(src, sdir, seen_md5, img_count, cap):
    """img_count: 클래스별 누적 원본(그룹) 수. 그룹의 모든 클래스가 cap에 도달했으면 그룹째 건너뛴다.
    증강 사본은 모두 수집하고 copy_idx로 구분 (train만 전체 사용, val/test는 copy_idx 0만)."""
    meta = yaml.safe_load((sdir / "data.yaml").read_text(encoding="utf-8"))
    names = meta["names"]
    license_ = (meta.get("roboflow") or {}).get("license", "")
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names)]
    cmap = src["class_map"]
    unknown = [n for n in names if n not in cmap]
    if unknown:
        raise SystemExit(f"{src['slug']}: class_map에 없는 클래스 {unknown} (null로 제외 지정 필요)")

    keep_aug = src.get("keep_aug", True)
    items, copies, skipped = [], Counter(), set()
    dropped = Counter()
    for img in sorted(p for p in sdir.rglob("*") if p.suffix.lower() in IMG_EXT):
        g = f"{src['slug']}::{group_key(img.stem)}"
        if g in skipped or (copies[g] and not keep_aug):
            continue
        lbl = img.parent.parent / "labels" / (img.stem + ".txt")
        if not lbl.exists():
            continue
        boxes = []
        for line in lbl.read_text(encoding="utf-8").splitlines():
            b = parse_label(line)
            if b is None:
                continue
            target = cmap[names[b[0]]]
            if target is None:
                dropped[names[b[0]]] += 1
                continue
            boxes.append((CLASS_ID[target],) + b[1:])
        if not boxes:
            continue
        present = {b[0] for b in boxes}
        if not copies[g] and cap and all(img_count[c] >= cap for c in present):
            skipped.add(g)
            continue
        md5 = hashlib.md5(img.read_bytes()).hexdigest()
        if md5 in seen_md5:
            continue
        seen_md5.add(md5)
        if not copies[g]:
            for c in present:
                img_count[c] += 1
        items.append({"img": img, "boxes": boxes, "group": g, "md5": md5, "copy_idx": copies[g],
                      "source": src["slug"], "license": license_})
        copies[g] += 1
    return items, dropped


def dhash(path):
    with Image.open(path) as im:
        im.draft("L", (64, 64))  # JPEG는 축소 디코딩 -> 큰 사진도 빠르게
        g = im.convert("L").resize((9, 8))
    px = list(g.getdata())
    return sum(1 << i for i in range(64) if px[(i // 8) * 9 + i % 8] > px[(i // 8) * 9 + i % 8 + 1])


def merge_near_duplicates(items, max_dist):
    """같은 소스 안에서 dHash 해밍거리 max_dist 이하인 원본 이미지(영상 연속 프레임 등)를
    한 그룹으로 묶어 train/val/test 사이 누수를 막는다.
    증강 사본은 이미 원본과 같은 그룹이므로 원본(copy_idx 0)끼리만 비교한다."""
    parent = {}

    def find(g):
        while parent.setdefault(g, g) != g:
            parent[g] = parent[parent[g]]
            g = parent[g]
        return g

    t = time.time()
    by_src = defaultdict(list)
    for it in items:
        if it["copy_idx"] == 0:
            by_src[it["source"]].append(it)
    merged = 0
    for its in by_src.values():
        h = np.array([dhash(it["img"]) for it in its], dtype=np.uint64)
        for i in range(len(h) - 1):
            x = (h[i + 1:] ^ h[i]).view(np.uint8).reshape(-1, 8)
            close = np.nonzero(np.unpackbits(x, axis=1).sum(axis=1) <= max_dist)[0]
            for j in close + i + 1:
                a, b = find(its[i]["group"]), find(its[j]["group"])
                if a != b:
                    parent[b] = a
                    merged += 1
    for it in items:
        it["group"] = find(it["group"])
    print(f"유사 이미지 그룹 병합: {merged}건, 최종 그룹 {len({it['group'] for it in items})}개 "
          f"({time.time() - t:.0f}초)", flush=True)


def oversample(items, target, max_factor):
    """train에서 이미지 수가 target 미만인 희소 클래스가 포함된 사진을 반복 추가."""
    if not target or max_factor <= 1:
        return []
    train = [it for it in items if it["split"] == "train"]
    cnt = Counter(c for it in train for c in {b[0] for b in it["boxes"]})
    factor = {c: min(max_factor, math.ceil(target / n)) for c, n in cnt.items() if n < target}
    extra = []
    for it in train:
        f = max((factor.get(b[0], 1) for b in it["boxes"]), default=1)
        extra += [dict(it, dup=k) for k in range(1, f)]
    print("오버샘플링: " + ", ".join(f"{CLASSES[c][1]} x{f}" for c, f in sorted(factor.items()))
          + f" -> {len(extra)}장 추가")
    return extra


def split_items(items, seed):
    """그룹 단위로, 각 그룹의 '가장 희소한 클래스' 기준 층화 분할."""
    freq = Counter(b[0] for it in items for b in it["boxes"])
    groups = defaultdict(list)
    for it in items:
        groups[it["group"]].append(it)
    strata = defaultdict(list)
    for g, its in groups.items():
        rare = min({b[0] for it in its for b in it["boxes"]}, key=lambda c: freq[c])
        strata[rare].append(g)
    rng = random.Random(seed)
    assign = {}
    for c, gs in sorted(strata.items()):
        rng.shuffle(gs)
        n = len(gs)
        n_val = max(1, round(n * SPLIT_RATIO["val"])) if n >= 3 else 0
        n_test = max(1, round(n * SPLIT_RATIO["test"])) if n >= 3 else 0
        for i, g in enumerate(gs):
            assign[g] = "val" if i < n_val else "test" if i < n_val + n_test else "train"
    for it in items:
        it["split"] = assign[it["group"]]


def write_crops(it, out_dir, stem, crop_pad, min_crop):
    """bbox 영역(여백 crop_pad)을 잘라 out_dir/<class>/ 에 저장. 클래스별 저장 수 반환."""
    saved = Counter()
    with Image.open(it["img"]) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        W, H = im.size
        for k, (c, cx, cy, w, h) in enumerate(it["boxes"]):
            pw, ph = w * W * (1 + crop_pad), h * H * (1 + crop_pad)
            x0, y0 = max(0, cx * W - pw / 2), max(0, cy * H - ph / 2)
            x1, y1 = min(W, cx * W + pw / 2), min(H, cy * H + ph / 2)
            if x1 - x0 < min_crop or y1 - y0 < min_crop:
                continue
            name = CLASSES[c][0]
            im.crop((int(x0), int(y0), int(x1), int(y1))).save(out_dir / name / f"{stem}_{k}.jpg", quality=95)
            saved[name] += 1
    return saved


def write_outputs(items, crop_pad, min_crop, skip_cls=False):
    shutil.rmtree(DET, ignore_errors=True)
    shutil.rmtree(CLS, ignore_errors=True)
    for s in SPLIT_RATIO:
        (DET / s / "images").mkdir(parents=True)
        (DET / s / "labels").mkdir(parents=True)
        for name, _ in CLASSES:
            if not skip_cls:
                (CLS / s / name).mkdir(parents=True)

    box_cnt = defaultdict(Counter)
    img_cnt = defaultdict(Counter)
    crop_cnt = defaultdict(Counter)
    rows = []
    for it in items:
        s = it["split"]
        short = it["source"].split("/")[1][:20]
        stem = f"{short}_{it['md5'][:12]}" + (f"_dup{it['dup']}" if it.get("dup") else "")
        dst = DET / s / "images" / (stem + it["img"].suffix.lower())
        shutil.copy2(it["img"], dst)
        (DET / s / "labels" / (stem + ".txt")).write_text(
            "".join(f"{c} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n" for c, cx, cy, w, h in it["boxes"]),
            encoding="utf-8")

        if not skip_cls:
            crop_cnt[s].update(write_crops(it, CLS / s, stem, crop_pad, min_crop))

        cls_names = sorted({CLASSES[b[0]][0] for b in it["boxes"]})
        for c in {b[0] for b in it["boxes"]}:
            img_cnt[s][CLASSES[c][0]] += 1
        for b in it["boxes"]:
            box_cnt[s][CLASSES[b[0]][0]] += 1
        rows.append([f"{s}/images/{dst.name}", s, ";".join(cls_names), len(it["boxes"]),
                     it["source"], it["license"], it["img"].name])

    with open(DET / "manifest.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["file", "split", "classes", "n_boxes", "source", "license", "original_name"])
        w.writerows(rows)

    (DET / "data.yaml").write_text(
        "# 용접 결함 9종 (H:/Welding_Defects/wD.png 기준)\n"
        f"path: {DET.as_posix()}\ntrain: train/images\nval: val/images\ntest: test/images\n"
        f"nc: {len(CLASSES)}\nnames:\n"
        + "".join(f"  {i}: {n}  # {ko}\n" for i, (n, ko) in enumerate(CLASSES)),
        encoding="utf-8")

    lines = []
    for title, cnt in [("이미지 수(해당 클래스 포함)", img_cnt), ("bbox 수", box_cnt), ("분류 crop 수", crop_cnt)]:
        lines.append(f"\n[{title}]")
        lines.append(f"{'class':<24}{'train':>8}{'val':>8}{'test':>8}{'total':>8}")
        for name, ko in CLASSES:
            v = [cnt[s][name] for s in SPLIT_RATIO]
            lines.append(f"{name + '(' + ko + ')':<24}" + "".join(f"{x:>8}" for x in v) + f"{sum(v):>8}")
    n_img = Counter(it["split"] for it in items)
    lines.insert(0, "총 이미지: " + ", ".join(f"{s}={n_img[s]}" for s in SPLIT_RATIO) + f", total={len(items)}")
    stats = "\n".join(lines)
    (DET / "stats.txt").write_text(stats + "\n", encoding="utf-8")
    print(stats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-download", action="store_true")
    ap.add_argument("--download-only", action="store_true")
    ap.add_argument("--near-dup", type=int, default=6, help="유사 이미지로 볼 dHash 해밍거리")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--crop-pad", type=float, default=0.2, help="crop 시 bbox 여백 비율")
    ap.add_argument("--min-crop", type=int, default=24, help="이보다 작은 crop은 제외(px)")
    ap.add_argument("--skip-cls", action="store_true", help="분류용 crop(weld_cls) 생성 생략")
    args = ap.parse_args()
    t0 = time.time()

    cfg = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))
    key = None if args.no_download else get_api_key()
    RAW.mkdir(parents=True, exist_ok=True)

    if args.download_only:
        for src in cfg["sources"]:
            print(f"{src['slug']} v{src['version']} -> {fetch(key, src)}", flush=True)
        return

    items, seen, img_count = [], set(), Counter()
    cap = cfg.get("max_images_per_class")
    for src in cfg["sources"]:
        sdir = source_dir(src["slug"], src["version"]) if args.no_download else fetch(key, src)
        its, dropped = collect(src, sdir, seen, img_count, cap)
        print(f"{src['slug']} v{src['version']}: {len(its)}장 사용"
              + (f" (제외 라벨 {dict(dropped)})" if dropped else "")
              + f"  [{time.time() - t0:.0f}초]", flush=True)
        items += its

    merge_near_duplicates(items, args.near_dup)
    split_items(items, args.seed)
    # val/test 는 그룹(원본)당 1장만 -> 증강 사본으로 점수가 부풀려지지 않게
    items = [it for it in items if it["split"] == "train" or it["copy_idx"] == 0]
    n_aug = sum(it["copy_idx"] > 0 for it in items)
    print(f"train 증강 사본 포함: {n_aug}장")
    items += oversample(items, cfg.get("oversample_min_images", 0), cfg.get("oversample_max_factor", 1))
    write_outputs(items, args.crop_pad, args.min_crop, args.skip_cls)
    (DET / ".build_hash").write_text(build_hash(), encoding="utf-8")
    print(f"완료 ({(time.time() - t0) / 60:.1f}분)")


def build_hash():
    """빌드 규칙(sources.yaml + 이 스크립트)이 바뀌었는지 판별용."""
    h = hashlib.md5()
    for p in (SOURCES, Path(__file__)):
        h.update(p.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode("utf-8"))
    return h.hexdigest()


if __name__ == "__main__":
    main()
