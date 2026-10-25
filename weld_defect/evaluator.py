"""검증/테스트 평가: 결함별 탐지 성능 + 이미지 단위 판정 정확도."""
import csv
import shutil
from pathlib import Path
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from ultralytics import YOLO

from .config import CLASSES, Config

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class DefectEvaluator:
    """
    지표 정의
      - 탐지 Precision / Recall / mAP50 / mAP50-95 : 박스 단위 (Ultralytics val)
      - 판정 정확도 : 해당 결함이 있는 사진 중, 모델이 그 결함을 찾아낸 사진의 비율 (이미지 단위 재현율)
      - 판정 정밀도 : 모델이 그 결함이라고 판정한 사진 중 실제로 그 결함이 있는 비율
    """

    def __init__(self, cfg: Config, weights: Path = None):
        self.cfg = cfg
        cfg.ensure_dirs()
        self.weights = Path(weights or cfg.best_model)
        self.model = YOLO(str(self.weights))

    def evaluate(self, split: str) -> List[Dict]:
        box = self._box_metrics(split)
        img = self._image_metrics(split)
        rows = []
        for c in CLASSES:
            b, m = box.get(c.id, {}), img[c.id]
            rows.append({
                "id": c.id, "class": c.name, "결함": c.ko,
                "이미지수": m["n_pos"],
                "판정정확도": m["recall"], "판정정밀도": m["precision"],
                "탐지P": b.get("p"), "탐지R": b.get("r"),
                "mAP50": b.get("map50"), "mAP50-95": b.get("map"),
            })
        self._save(split, rows, box.get("all", {}))
        return rows

    # ---- 박스 단위 (Ultralytics) ----
    def _box_metrics(self, split):
        c = self.cfg
        name = f"eval_{split}"
        m = self.model.val(data=str(c.data_yaml), split=split, imgsz=c.imgsz, batch=c.batch,
                           conf=0.001, iou=0.6, project=str(c.runs_dir), name=name,
                           exist_ok=True, plots=True, verbose=False)
        out = {}
        for i, cid in enumerate(m.box.ap_class_index):
            p, r, ap50, ap = m.box.class_result(i)
            out[int(cid)] = {"p": p, "r": r, "map50": ap50, "map": ap}
        out["all"] = {"p": m.box.mp, "r": m.box.mr, "map50": m.box.map50, "map": m.box.map}
        cm = c.runs_dir / name / "confusion_matrix_normalized.png"
        if cm.exists():
            shutil.copy2(cm, c.report_dir / f"{split}_confusion_matrix.png")
        return out

    # ---- 이미지 단위 판정 ----
    def _image_metrics(self, split):
        c = self.cfg
        img_dir = c.dataset_dir / split / "images"
        lbl_dir = c.dataset_dir / split / "labels"
        images = sorted(p for p in img_dir.iterdir() if p.suffix.lower() in IMG_EXT)
        stats = {cl.id: {"tp": 0, "fp": 0, "fn": 0} for cl in CLASSES}
        # 리스트를 통째로 넘기면 한 배치로 처리되어 GPU 메모리 초과 -> 나눠서 추론
        chunk = 16
        results = (r for i in range(0, len(images), chunk)
                   for r in self.model.predict([str(p) for p in images[i:i + chunk]], conf=c.conf,
                                               iou=c.iou, imgsz=c.imgsz, verbose=False))
        for r in results:
            stem = Path(r.path).stem
            lbl = lbl_dir / f"{stem}.txt"
            gt = {int(l.split()[0]) for l in lbl.read_text().splitlines() if l.strip()} if lbl.exists() else set()
            pred = {int(x) for x in r.boxes.cls.tolist()}
            for cid in stats:
                if cid in gt and cid in pred:
                    stats[cid]["tp"] += 1
                elif cid in gt:
                    stats[cid]["fn"] += 1
                elif cid in pred:
                    stats[cid]["fp"] += 1
        out = {}
        for cid, s in stats.items():
            n_pos = s["tp"] + s["fn"]
            out[cid] = {
                "n_pos": n_pos,
                "recall": s["tp"] / n_pos if n_pos else None,
                "precision": s["tp"] / (s["tp"] + s["fp"]) if s["tp"] + s["fp"] else None,
            }
        return out

    # ---- 저장 ----
    def _save(self, split, rows, overall):
        rd = self.cfg.report_dir
        with open(rd / f"{split}_metrics.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})

        md = [f"## {split} 결과 (모델: {self.weights.name})", "",
              "| 결함 | 이미지 수 | 판정 정확도 | 판정 정밀도 | 탐지 P | 탐지 R | mAP50 | mAP50-95 |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for r in rows:
            md.append(f"| {r['결함']} | {r['이미지수']} | {pct(r['판정정확도'])} | {pct(r['판정정밀도'])} | "
                      f"{pct(r['탐지P'])} | {pct(r['탐지R'])} | {pct(r['mAP50'])} | {pct(r['mAP50-95'])} |")
        md.append(f"| **전체** | | | | {pct(overall.get('p'))} | {pct(overall.get('r'))} | "
                  f"**{pct(overall.get('map50'))}** | {pct(overall.get('map'))} |")
        (rd / f"{split}_metrics.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        self._plot(split, rows)
        print("\n".join(md))

    def _plot(self, split, rows):
        try:
            font_manager.fontManager.addfont(self.cfg.font_path)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=self.cfg.font_path).get_name()
        except (OSError, RuntimeError):
            pass
        labels = [r["결함"] for r in rows]
        acc = [(r["판정정확도"] or 0) * 100 for r in rows]
        m50 = [(r["mAP50"] or 0) * 100 for r in rows]
        x = range(len(rows))
        fig, ax = plt.subplots(figsize=(11, 5))
        b1 = ax.bar([i - 0.2 for i in x], acc, 0.4, label="판정 정확도(이미지)", color="#4363d8")
        b2 = ax.bar([i + 0.2 for i in x], m50, 0.4, label="mAP50(박스)", color="#f58231")
        ax.bar_label(b1, fmt="%.0f", fontsize=8)
        ax.bar_label(b2, fmt="%.0f", fontsize=8)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels)
        ax.set_ylim(0, 105)
        ax.set_ylabel("%")
        ax.set_title(f"결함별 성능 ({split})")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(self.cfg.report_dir / f"{split}_per_class.png", dpi=120)
        plt.close(fig)


def pct(v):
    return "-" if v is None else f"{v * 100:.1f}%"
