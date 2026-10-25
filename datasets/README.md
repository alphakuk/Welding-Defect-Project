# 용접 결함 데이터셋

결함 9종 기준: `H:/Welding_Defects/wD.png`. 출처: Roboflow Universe 공개 데이터셋 15개 (`data/sources.yaml`).
재생성: `python tools/build_dataset.py --no-download` (다운로드 포함 시 옵션 없이, `ROBOFLOW_API_KEY` 필요)

| id | class | 결함 | 이미지 수 (train/val/test) |
|---|---|---|---|
| 0 | incomplete_penetration | 용입부족 | 44 / 9 / 8 ⚠ X-ray 사진 |
| 1 | crack | 균열 | 1070 / 227 / 211 |
| 2 | undercut | 언더컷 | 972 / 200 / 230 |
| 3 | underfill | 언더필 | 232 / 31 / 29 |
| 4 | arc_strike | 아크스트라이크 | 191 / 54 / 48 |
| 5 | porosity | 기공 | 939 / 191 / 177 |
| 6 | blowhole | 블로홀 | 79 / 9 / 8 (원본 클래스 Pin Hole) |
| 7 | spatter | 스패터 | 1396 / 303 / 276 |
| 8 | overlap | 오버랩 | 54 / 13 / 11 |

총 6,215장 (train 4,403 / val 919 / test 893). 상세 수치: `weld_det/stats.txt`, 파일별 출처·라이선스: `weld_det/manifest.csv`.

## 구성
- `weld_det/` — YOLO 객체탐지 (`data.yaml`로 바로 학습 가능)
- `weld_cls/` — bbox 영역 crop(여백 20%) 이미지 분류, `split/class/*.jpg`

## 빌드 규칙
- 9종에 해당하지 않는 원본 클래스(Lack of Fusion, Burn Through, Slag 등)는 라벨에서 제외. 해당 결함이 사진에 있어도 라벨이 없으므로 탐지 학습 시 배경으로 취급됨.
- md5 중복 제거, Roboflow 증강 사본은 원본 1장만 사용 (학습 시 증강 별도 적용 권장).
- 영상 연속 프레임 등 유사 이미지(dHash 거리 ≤ 6)는 같은 split에 배치해 누수 방지.
- 클래스별 이미지 상한 1500장 (스패터·기공 과다 방지), 희소 클래스 기준 층화 분할 70/15/15.

## 주의
- 용입부족은 외관 사진 공개 데이터가 없어 X-ray 투과 사진으로 채움. 모델이 "X-ray 사진 = 용입부족"으로 학습할 수 있으므로 외관 사진 판정 성능은 기대하기 어려움 → 직접 촬영 데이터로 교체 필요.
- 블로홀·오버랩·용입부족은 100장 미만으로 적음. val/test 수치 변동이 큼.
