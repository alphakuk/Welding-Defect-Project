"""colab_train.ipynb 생성 스크립트 (노트북 내용을 코드로 관리)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "colab_train.ipynb"
# 노트북에 내장할 프로젝트 파일 (업로드 없이 Colab에서 재구성)
EMBED = ["main.py", "weld_defect/__init__.py", "weld_defect/config.py", "weld_defect/trainer.py",
         "weld_defect/evaluator.py", "weld_defect/detector.py", "weld_defect/app.py",
         "tools/rf_common.py", "tools/build_dataset.py", "data/sources.yaml"]
FILES = {p: (ROOT / p).read_text(encoding="utf-8-sig") for p in EMBED}


def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src.strip("\n")}


def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": src.strip("\n")}


cells = [
    md("""
# 용접 결함 YOLO 학습 (Colab)

런타임 유형을 **GPU** 로 설정 후 **모두 실행** → 바로 뜨는 **화면 맨 위 입력창에 Roboflow 키 입력** (이후 자동 진행, T4 기준 약 4~5시간)

- 데이터: **Roboflow에서 직접 받아 데이터셋 생성** (빌드 규칙이 바뀌면 자동 재생성)
- 학습: 최대 80 epoch, 20 epoch 동안 개선 없으면 조기 종료. 시간 제한이 필요하면 3번 셀의 `cfg.time_hours` 설정
- 결과(`weld_best.pt`, `reports/`)는 Drive **내 드라이브/BC_Project/results.zip** → PC의 `H:\\BC_Project` 에 압축 해제
- 체크포인트가 Drive에 저장되므로 런타임이 끊기면 **다시 모두 실행**하면 이어서 학습
"""),
    md("## 0. Roboflow 키 입력 (실행 직후 화면 맨 위 입력창에 붙여넣고 Enter)"),
    code("""
import os, getpass
if not os.environ.get('ROBOFLOW_API_KEY'):
    print('▲ 화면 맨 위 입력창에 Roboflow Private API Key 를 붙여넣고 Enter 를 누르세요')
    os.environ['ROBOFLOW_API_KEY'] = getpass.getpass('Roboflow Private API Key: ').strip()
print('키 입력 완료' if os.environ['ROBOFLOW_API_KEY'] else '키가 비어 있습니다! 이 셀을 다시 실행하세요')
"""),
    code("""
!nvidia-smi --query-gpu=name,memory.total --format=csv
"""),
    md("## 1. Drive 연결 및 프로젝트 코드 생성"),
    code("""
import os
from pathlib import Path

DRIVE = Path('/content/drive/MyDrive/BC_Project')   # 결과/체크포인트 저장 위치
WORK = Path('/content/BC_Project')                   # 학습은 빠른 로컬 디스크에서

from google.colab import drive
drive.mount('/content/drive')
DRIVE.mkdir(parents=True, exist_ok=True)

FILES = """ + repr(FILES) + """
for rel, text in FILES.items():
    p = WORK / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
print('코드 파일', len(FILES), '개 생성 ->', WORK)
"""),
    code("""
!pip -q install ultralytics
!apt-get -qq install -y fonts-nanum > /dev/null
"""),
    md("## 2. 데이터셋 준비 (Roboflow 직접 다운로드)"),
    code("""
import sys, shutil, getpass
sys.path.insert(0, str(WORK / 'tools'))
from build_dataset import build_hash
det = WORK / 'datasets/weld_det'
marker = det / '.build_hash'
if marker.exists() and marker.read_text().strip() == build_hash():
    print('데이터셋 이미 준비됨 (최신 빌드 규칙)')
else:
    shutil.rmtree(WORK / 'datasets', ignore_errors=True)
    print('Roboflow에서 받아 데이터셋을 생성합니다 (15~20분).')
    assert os.environ.get('ROBOFLOW_API_KEY'), '맨 위 0번 셀에서 Roboflow 키를 먼저 입력하세요'
    !cd {WORK} && python tools/build_dataset.py --skip-cls

# data.yaml 의 Windows 경로(H:/...)를 Colab 경로로 교체
yml = WORK / 'datasets/weld_det/data.yaml'
lines = [f'path: {WORK}/datasets/weld_det' if l.startswith('path:') else l
         for l in yml.read_text(encoding='utf-8').splitlines()]
yml.write_text('\\n'.join(lines) + '\\n', encoding='utf-8')
print(yml.read_text(encoding='utf-8'))
for s in ['train', 'val', 'test']:
    print(s, len(os.listdir(WORK / f'datasets/weld_det/{s}/images')), '장')
"""),
    md("## 3. 설정"),
    code("""
import sys
os.chdir(WORK)
sys.path.insert(0, str(WORK))
from weld_defect.config import Config

cfg = Config()                     # 모델/epoch/증강은 weld_defect/config.py 기본값 사용
cfg.time_hours = 0                 # 0 = epochs(80)만큼 끝까지 학습. 시간 제한이 필요하면 예: 2.0 (시간)
cfg.batch = 32                     # T4(16GB) 기준. 메모리 부족 시 16
cfg.workers = 4
cfg.runs_dir = DRIVE / 'runs'      # 체크포인트를 Drive에 저장 -> 끊겨도 이어서 학습
cfg.model_dir = DRIVE / 'models'
cfg.report_dir = DRIVE / 'reports'
cfg.font_path = '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf'
cfg.ensure_dirs()
print(cfg)
"""),
    md("## 4. 학습 (이어서 학습 자동 처리)"),
    code("""
import shutil
from weld_defect.trainer import DefectTrainer

weights = cfg.runs_dir / cfg.run_name / 'weights'
try:
    DefectTrainer(cfg).train(resume=(weights / 'last.pt').exists())
except AssertionError as e:          # 이미 학습이 끝난 경우: 'nothing to resume'
    print(e)
    shutil.copy2(weights / 'best.pt', cfg.best_model)
print('최종 모델:', cfg.best_model)
"""),
    md("## 5. 검증 / 테스트 - 결함별 정확도"),
    code("""
from IPython.display import Markdown, Image, display
from weld_defect.evaluator import DefectEvaluator

ev = DefectEvaluator(cfg)
for split in ['val', 'test']:
    ev.evaluate(split)
    display(Markdown((cfg.report_dir / f'{split}_metrics.md').read_text(encoding='utf-8')))
"""),
    code("""
for split in ['val', 'test']:
    display(Markdown(f'### {split}'))
    display(Image(str(cfg.report_dir / f'{split}_per_class.png')))
    display(Image(str(cfg.report_dir / f'{split}_confusion_matrix.png'), width=700))
"""),
    md("## 6. 결과 묶기 → Drive `BC_Project/results.zip`"),
    code("""
import zipfile
run = cfg.runs_dir / cfg.run_name
out = DRIVE / 'results.zip'
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(cfg.best_model, 'models/weld_best.pt')
    for f in cfg.report_dir.iterdir():
        z.write(f, f'reports/{f.name}')
    for f in run.glob('*.*'):        # results.csv, 학습 곡선 등
        if f.is_file():
            z.write(f, f'runs/{cfg.run_name}/{f.name}')
print(out, f'{out.stat().st_size / 1e6:.1f} MB')
"""),
]

nb = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"provenance": [], "gpuType": "T4"},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 0,
}

for c in cells:  # nbformat: source 는 줄 단위 리스트
    lines = c["source"].split("\n")
    c["source"] = [l + "\n" for l in lines[:-1]] + [lines[-1]]

OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(OUT)

