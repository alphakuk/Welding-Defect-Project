"""학습된 모델로 사진 한 장의 결함을 판정."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps
from ultralytics import YOLO

from .config import CLASSES, Config

# 결함별 고정 색 (id 순서: 용입부족 균열 언더컷 언더필 아크스트라이크 기공 블로홀 스패터 오버랩)
COLORS = ["#e6194b", "#ff7f00", "#ffe119", "#3cb44b", "#00bcd4",
          "#4363d8", "#911eb4", "#f032e6", "#8b4513"]
TEXT_COLORS = ["white", "black", "black", "black", "black", "white", "white", "black", "white"]


@dataclass
class Detection:
    class_id: int
    name: str
    ko: str
    conf: float
    box: tuple  # x1, y1, x2, y2 (px)


@dataclass
class Verdict:
    image: Path
    detections: List[Detection] = field(default_factory=list)

    @property
    def is_defect(self) -> bool:
        return bool(self.detections)

    @property
    def main(self) -> Optional[Detection]:
        """가장 신뢰도가 높은 결함 = 대표 판정."""
        return max(self.detections, key=lambda d: d.conf) if self.detections else None

    def summary(self) -> dict:
        """결함 종류별 (개수, 최고 신뢰도), 신뢰도 높은 순."""
        out = {}
        for d in self.detections:
            n, best = out.get(d.ko, (0, 0.0))
            out[d.ko] = (n + 1, max(best, d.conf))
        return dict(sorted(out.items(), key=lambda kv: -kv[1][1]))

    def text(self) -> str:
        if not self.is_defect:
            return "판정: 검출된 결함 없음"
        lines = [f"판정: {self.main.ko} (신뢰도 {self.main.conf:.0%})",
                 "결함 종류: " + ", ".join(f"{ko} {n}곳" for ko, (n, _) in self.summary().items()),
                 "결함 위치 (사진의 번호 박스):"]
        for i, d in enumerate(self.detections, 1):
            x1, y1, x2, y2 = (int(v) for v in d.box)
            lines.append(f"  #{i} {d.ko} {d.conf:.0%}  위치 ({x1},{y1})~({x2},{y2}) px")
        return "\n".join(lines)


class DefectDetector:
    def __init__(self, cfg: Config, weights: Optional[Path] = None):
        self.cfg = cfg
        weights = Path(weights or cfg.best_model)
        if not weights.exists():
            raise FileNotFoundError(f"모델 파일이 없습니다: {weights} (먼저 python main.py train)")
        self.model = YOLO(str(weights))
        self.font_path = cfg.font_path

    def predict(self, image_path) -> Verdict:
        image_path = Path(image_path)
        img = self._load(image_path)
        r = self.model.predict(img, conf=self.cfg.conf, iou=self.cfg.iou, verbose=False)[0]
        dets = []
        for cls, conf, xyxy in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist(), r.boxes.xyxy.tolist()):
            c = CLASSES[int(cls)]
            dets.append(Detection(c.id, c.name, c.ko, conf, tuple(xyxy)))
        dets.sort(key=lambda d: -d.conf)
        return Verdict(image_path, dets)

    def annotate(self, verdict: Verdict, min_side: int = 960) -> Image.Image:
        """결함 위치에 번호/결함명/신뢰도 박스를 그린 이미지. 작은 사진은 키워서 그린다."""
        img = self._load(verdict.image)
        scale = max(1.0, min_side / min(img.size))
        if scale > 1:
            img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(self.font_path, max(16, img.width // 55))
        except OSError:
            font = ImageFont.load_default()
        width = max(3, img.width // 300)
        if not verdict.detections:
            msg = "결함 미검출"
            tb = draw.textbbox((12, 12), msg, font=font)
            draw.rectangle((tb[0] - 6, tb[1] - 6, tb[2] + 6, tb[3] + 6), fill="#2e7d32")
            draw.text((12, 12), msg, fill="white", font=font)
            return img

        boxes = []
        min_box = 8 * width  # 아주 작은 결함(기공 등)도 보이도록 최소 크기 확보
        for d in verdict.detections:
            x1, y1, x2, y2 = (v * scale for v in d.box)
            if x2 - x1 < min_box:
                cx = (x1 + x2) / 2
                x1, x2 = cx - min_box / 2, cx + min_box / 2
            if y2 - y1 < min_box:
                cy = (y1 + y2) / 2
                y1, y2 = cy - min_box / 2, cy + min_box / 2
            boxes.append((x1, y1, x2, y2))
        # 1) 박스: 검은 테두리 + 결함 색 (밝은/어두운 배경 모두에서 보이게)
        for d, b in zip(verdict.detections, boxes):
            draw.rectangle(b, outline="black", width=width + 2)
            draw.rectangle(b, outline=COLORS[d.class_id], width=width)
        # 2) 라벨: 박스 위, 공간이 없으면 박스 아래. 다른 라벨과 겹치면 비켜 놓는다
        placed = []
        for i, (d, b) in enumerate(zip(verdict.detections, boxes), 1):
            label = f"#{i} {d.ko} {d.conf:.0%}"
            l, t, r, btm = draw.textbbox((0, 0), label, font=font)
            tw, th = r - l, btm - t
            x = min(max(0, b[0]), img.width - tw - 6)
            y = b[1] - th - 10 if b[1] - th - 10 >= 0 else min(b[3] + 4, img.height - th - 8)
            step = -(th + 12) if y < b[1] else th + 12
            for _ in range(20):
                rect = (x - 3, y - 2, x + tw + 3, y + th + 8)
                if not any(rect[0] < p[2] and p[0] < rect[2] and rect[1] < p[3] and p[1] < rect[3]
                           for p in placed):
                    break
                y += step
                if y < 0 or y > img.height - th - 8:
                    step, y = -step, min(max(0, y), img.height - th - 8)
            placed.append(rect)
            draw.rectangle(rect, fill=COLORS[d.class_id], outline="black")
            draw.text((x, y - t), label, fill=TEXT_COLORS[d.class_id], font=font)
        return img

    @staticmethod
    def _load(path) -> Image.Image:
        with Image.open(path) as im:
            return ImageOps.exif_transpose(im).convert("RGB")
