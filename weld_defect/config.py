"""경로, 결함 클래스 정의, 학습 하이퍼파라미터."""
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class DefectClass:
    id: int
    name: str      # 데이터셋 라벨명
    ko: str        # 한글 결함명
    desc: str      # H:/Welding_Defects/wD.png 의 설명


CLASSES = [
    DefectClass(0, "incomplete_penetration", "용입부족", "용융금속의 두께가 모재두께보다 적게 용입이 된 상태"),
    DefectClass(1, "crack", "균열", "용접부에 금이 가는 현상"),
    DefectClass(2, "undercut", "언더컷", "용접부 부근의 모재가 용접열에 의해 움푹 패인 형상"),
    DefectClass(3, "underfill", "언더필", "용접이 덜 채워진 현상"),
    DefectClass(4, "arc_strike", "아크스트라이크", "용접봉을 모재에 대고 Arc를 발생시킴으로 인해 모재표면이 움푹 패인 현상"),
    DefectClass(5, "porosity", "기공", "가스가 외부로 빠져나오지 못하고 내부에서 기포를 형성한 상태"),
    DefectClass(6, "blowhole", "블로홀", "가스가 용접비드 표면으로 빠져나오면서 발생한 작은 구멍"),
    DefectClass(7, "spatter", "스패터", "용접 시 조그마한 금속 알갱이가 튀겨나와 모재에 묻어있는 형상"),
    DefectClass(8, "overlap", "오버랩", "용접개선 절단면을 지나 모재 상부까지 용접된 형상"),
]
CLASS_BY_NAME = {c.name: c for c in CLASSES}


@dataclass
class Config:
    data_yaml: Path = ROOT / "datasets" / "weld_det" / "data.yaml"
    dataset_dir: Path = ROOT / "datasets" / "weld_det"
    runs_dir: Path = ROOT / "runs"
    model_dir: Path = ROOT / "models"
    report_dir: Path = ROOT / "reports"
    font_path: str = "C:/Windows/Fonts/malgunbd.ttf"

    # 학습 (기본값은 Colab 기준. 로컬 GTX 1650 에서는 batch 8 이하)
    base_model: str = "yolo11s.pt"
    run_name: str = "weld_yolo11s_v2"
    epochs: int = 80
    patience: int = 20
    time_hours: float = 0     # >0 이면 epochs 대신 이 시간(시간 단위) 안에 학습을 마치도록 일정 조정
    imgsz: int = 640
    batch: int = 8
    workers: int = 2
    seed: int = 42

    # 증강 (다양한 촬영 환경에 대한 일반화 목적, Ultralytics 기본값보다 강하게)
    augment: dict = field(default_factory=lambda: dict(
        fliplr=0.5, flipud=0.5, degrees=15, translate=0.15, scale=0.7, shear=2.0,
        hsv_h=0.02, hsv_s=0.6, hsv_v=0.5, mosaic=1.0, mixup=0.15, close_mosaic=10,
    ))

    # 추론
    conf: float = 0.25
    iou: float = 0.5

    @property
    def best_model(self) -> Path:
        return self.model_dir / "weld_best.pt"

    def ensure_dirs(self):
        for d in (self.runs_dir, self.model_dir, self.report_dir):
            d.mkdir(parents=True, exist_ok=True)

