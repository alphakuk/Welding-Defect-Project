"""Roboflow API 공통 유틸 (roboflow 패키지 없이 REST로 직접 호출)."""
import os
import time

import requests

API = "https://api.roboflow.com"


def get_api_key():
    key = os.environ.get("ROBOFLOW_API_KEY")
    if not key and os.name == "nt":
        # 사용자 환경변수로 설정했지만 현재 프로세스에 반영되지 않은 경우
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                key, _ = winreg.QueryValueEx(k, "ROBOFLOW_API_KEY")
        except OSError:
            key = None
    if not key:
        raise SystemExit("ROBOFLOW_API_KEY 환경변수가 설정되어 있지 않습니다.")
    return key.strip()


def project_info(key, slug):
    """slug = 'workspace/project' -> 프로젝트 메타데이터(JSON)."""
    r = requests.get(f"{API}/{slug}", params={"api_key": key}, timeout=60)
    r.raise_for_status()
    return r.json()


def export_link(key, version_id, fmt="yolov8", max_wait=600):
    """version_id = 'workspace/project/3' -> 다운로드 zip 링크.
    export가 아직 생성되지 않았으면 생성될 때까지 폴링."""
    url = f"{API}/{version_id}/{fmt}"
    start = time.time()
    while True:
        r = requests.get(url, params={"api_key": key}, timeout=120)
        r.raise_for_status()
        data = r.json()
        link = (data.get("export") or {}).get("link")
        if link:
            return link
        if time.time() - start > max_wait:
            raise TimeoutError(f"export 생성 대기 시간 초과: {version_id}")
        time.sleep(5)


def download(url, dest):
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
