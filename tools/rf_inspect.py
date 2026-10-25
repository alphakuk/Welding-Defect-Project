"""후보 Roboflow Universe 프로젝트의 클래스/이미지 수/버전을 조회해 data/rf_candidates.json에 저장.

사용법: python tools/rf_inspect.py [workspace/project ...]
"""
import json
import sys
from pathlib import Path

from rf_common import get_api_key, project_info

CANDIDATES = [
    "trithis-workspace/welding-defects-7zoqs",
    "welddefectdetection/welddefectdetection-k1boe",
    "weldingdefects-yfhj4/weld-defects-kcocu",
    "welding-qdnjc/new-rflct",
    "welding-qdnjc/m-swo6d",
    "weld-qwzyj/welding-defects-detection",
    "workspace-028eb/weld-defect-do7dy",
    "work-rwmly/welding-defect-final0-bdnbe",
    "mehak-laif/weld_defects_annotated-4csdz",
    "oran-ai/visual-weld-inspector",
    "underwater-s7ec9/weld_defect-qp9vc",
    "deepspace-9ajsj/my-first-project-ckca5",
    "space-be2wb/final-welding-dataset-qrz4x-cw6sq",
    "weld-defect-detection-onlal/weld-surface-defect-detection-884h9",
    "byungjun/weld-data",
    "byungjun/weld-nenf5",
    "delvin-9qaxw/weld-n1hel",
    "weld-i5yt0/weld-quality-inspection-rei9l-gzxjs",
    "rongchiroi/raw_weld-pgks9",
    "wonmu-huh/-8d9fj",
    "crack-fg7d9/weld-defect-detection-compiled-xpao4",
    "sumithas-workspace/welding-defects-cgalk",
    "weldparts/welding_detect",
    "ai-vision-system/welding-defects-sxd9f",
]

OUT = Path(__file__).resolve().parent.parent / "data" / "rf_candidates.json"


def main():
    key = get_api_key()
    slugs = sys.argv[1:] or CANDIDATES
    results = {}
    if OUT.exists():
        results = json.loads(OUT.read_text(encoding="utf-8"))
    for slug in slugs:
        try:
            info = project_info(key, slug)
        except Exception as e:  # 비공개/삭제된 프로젝트 등
            print(f"[FAIL] {slug}: {e}")
            results[slug] = {"error": str(e)}
            continue
        p = info.get("project", {})
        versions = [
            {"id": v.get("id"), "images": v.get("images"), "splits": v.get("splits"),
             "exports": v.get("exports")}
            for v in info.get("versions", [])
        ]
        results[slug] = {
            "name": p.get("name"),
            "type": p.get("type"),
            "images": p.get("images"),
            "license": p.get("license"),
            "classes": p.get("classes"),
            "versions": versions,
        }
        print(f"[OK] {slug} | {p.get('type')} | imgs={p.get('images')} | "
              f"versions={[v['id'].split('/')[-1] + ':' + str(v['images']) for v in versions]}")
        print(f"     classes={p.get('classes')}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {OUT}")


if __name__ == "__main__":
    main()
