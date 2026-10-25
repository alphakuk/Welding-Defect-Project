"""YOLO 학습."""
import shutil
from pathlib import Path

from ultralytics import YOLO

from .config import Config


class DefectTrainer:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        cfg.ensure_dirs()

    def train(self, resume: bool = False) -> Path:
        c = self.cfg
        last = c.runs_dir / c.run_name / "weights" / "last.pt"
        if resume and last.exists():
            model = YOLO(str(last))
            model.train(resume=True)
        else:
            model = YOLO(str(c.model_dir / c.base_model)) if (c.model_dir / c.base_model).exists() \
                else YOLO(c.base_model)
            model.train(
                data=str(c.data_yaml),
                epochs=c.epochs,
                patience=c.patience,
                imgsz=c.imgsz,
                batch=c.batch,
                workers=c.workers,
                seed=c.seed,
                project=str(c.runs_dir),
                name=c.run_name,
                exist_ok=True,
                cos_lr=True,
                plots=True,
                **({"time": c.time_hours} if c.time_hours else {}),
                **c.augment,
            )
        best = c.runs_dir / c.run_name / "weights" / "best.pt"
        shutil.copy2(best, c.best_model)
        print(f"최종 모델 저장: {c.best_model}")
        return c.best_model
