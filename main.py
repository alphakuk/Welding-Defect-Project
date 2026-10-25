"""용접 결함 판정 - 실행 진입점.

  python main.py                 담당자용 판정 프로그램(GUI) 실행
  python main.py predict 사진.jpg [...]   콘솔에서 판정
  python main.py train [--epochs N] [--resume]
  python main.py evaluate        val/test 결함별 정확도 리포트 (reports/)
"""
import argparse
import sys

from weld_defect.config import Config


def main():
    ap = argparse.ArgumentParser(description="용접 결함 판정")
    sub = ap.add_subparsers(dest="cmd")
    t = sub.add_parser("train", help="YOLO 학습")
    t.add_argument("--epochs", type=int)
    t.add_argument("--batch", type=int)
    t.add_argument("--resume", action="store_true")
    e = sub.add_parser("evaluate", help="검증/테스트 평가")
    e.add_argument("--splits", nargs="+", default=["val", "test"])
    p = sub.add_parser("predict", help="사진 판정(콘솔)")
    p.add_argument("images", nargs="+")
    p.add_argument("--save", action="store_true", help="박스 그린 결과 이미지를 outputs/에 저장")
    sub.add_parser("gui", help="판정 프로그램(GUI)")
    args = ap.parse_args()
    cfg = Config()

    if args.cmd == "train":
        from weld_defect.trainer import DefectTrainer
        if args.epochs:
            cfg.epochs = args.epochs
        if args.batch:
            cfg.batch = args.batch
        DefectTrainer(cfg).train(resume=args.resume)

    elif args.cmd == "evaluate":
        from weld_defect.evaluator import DefectEvaluator
        ev = DefectEvaluator(cfg)
        for s in args.splits:
            ev.evaluate(s)
        print(f"\n리포트 저장 위치: {cfg.report_dir}")

    elif args.cmd == "predict":
        from pathlib import Path
        from weld_defect.detector import DefectDetector
        det = DefectDetector(cfg)
        out_dir = cfg.model_dir.parent / "outputs"
        for img in args.images:
            v = det.predict(img)
            print(f"\n[{Path(img).name}]\n{v.text()}")
            if args.save:
                out_dir.mkdir(exist_ok=True)
                det.annotate(v).save(out_dir / f"{Path(img).stem}_판정.jpg", quality=95)

    else:
        from weld_defect.app import DefectApp
        DefectApp(cfg).mainloop()


if __name__ == "__main__":
    sys.exit(main())
