"""Colab 학습용 업로드 파일 생성: colab/bc_weld_colab.zip (코드 + YOLO 데이터셋).

사용법: python tools/pack_for_colab.py
생성된 zip을 Google Drive '내 드라이브/BC_Project/' 폴더에 업로드한 뒤 colab_train.ipynb 실행.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "colab" / "bc_weld_colab.zip"
INCLUDE = ["main.py", "weld_defect", "datasets/weld_det"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    OUT.parent.mkdir(exist_ok=True)
    n = 0
    with zipfile.ZipFile(OUT, "w") as z:
        for item in INCLUDE:
            p = ROOT / item
            files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file())
            for f in files:
                if "__pycache__" in f.parts or f.suffix == ".cache":
                    continue
                # 이미지는 이미 압축된 포맷이라 무압축 저장(빠름)
                comp = zipfile.ZIP_STORED if f.suffix.lower() in IMG_EXT else zipfile.ZIP_DEFLATED
                z.write(f, f.relative_to(ROOT).as_posix(), compress_type=comp)
                n += 1
    print(f"{n}개 파일 -> {OUT} ({OUT.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
