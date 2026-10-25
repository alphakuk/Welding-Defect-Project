"""제출 자료(.pptx) 생성: 제출자료/용접결함판정AI_김인국.pptx

사용법: .venv/Scripts/python tools/make_presentation.py
이미지는 제출자료/assets/ , 모델 결과는 reports/ · runs/weld_yolo11s/ 에서 읽는다.
"""
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData, XyChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "제출자료"
ASSET = OUT_DIR / "assets"
OUT = OUT_DIR / "용접결함판정AI_김인국.pptx"

AUTHOR = "김인국"
PERIOD = "2026.10.12 ~ 2026.11.04"
FONT = "맑은 고딕"
CODE_FONT = "Consolas"

DARK, WHITE, LIGHT = "17212B", "FFFFFF", "EEF1F4"
ORANGE, ORANGE_T, BLUE = "E2702B", "A94A12", "2B5C8A"
BODY, MUTED, LINE, SOFT = "3B4550", "5E6873", "D9DDE1", "C9D1D9"
CODE_BG, CODE_FG, CODE_CM = "0F171F", "E6E9EC", "8FB3A0"


def rgb(h):
    return RGBColor.from_string(h)


# ---------------------------------------------------------------- 기본 도구
def set_font(run, size, bold=False, color=BODY, name=FONT, italic=False):
    f = run.font
    f.size, f.bold, f.italic = Pt(size), bold, italic
    f.color.rgb = rgb(color)
    f.name = name
    rpr = run._r.get_or_add_rPr()
    rpr.set("lang", "ko-KR")      # 한국어로 지정해야 단어 단위 줄바꿈이 적용됨
    rpr.set("altLang", "en-US")
    for tag in ("a:ea", "a:cs"):  # 한글(동아시아) 글꼴도 지정
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set("typeface", name)


def keep_words(para):
    """한글 단어가 중간에서 끊기지 않게 (PowerPoint 기본값은 글자 단위 줄바꿈)."""
    para._p.get_or_add_pPr().set("eaLnBrk", "0")


def text(slide, x, y, w, h, paras, size=16, color=BODY, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=1.15, after=0, font=FONT, name=None):
    """paras: str | [str | [(text, {opts}) ...] ...] 한 원소 = 한 문단."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    if isinstance(paras, str):
        paras = [paras]
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        keep_words(para)
        para.line_spacing = spacing
        para.space_after = Pt(after)
        runs = p if isinstance(p, list) else [(p, {})]
        for t, o in runs:
            r = para.add_run()
            r.text = t
            set_font(r, o.get("size", size), o.get("bold", bold), o.get("color", color),
                     o.get("font", font), o.get("italic", False))
    return tb


def box(slide, x, y, w, h, fill=LIGHT, line=None, radius=0.06, shape=MSO_SHAPE.ROUNDED_RECTANGLE, name=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        s.name = name
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = Pt(1)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    s.text_frame.text = ""
    return s


def circle_num(slide, x, y, d, label, fill=ORANGE, color=WHITE, size=16):
    c = box(slide, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    tf = c.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    set_font(r, size, True, color)
    return c


def table(slide, x, y, w, rows, col_w, size=14, row_h=0.42, header_fill=DARK, zebra=True, highlight=()):
    gf = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w),
                                Inches(row_h * len(rows)))
    tbl = gf.table
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(w * cw)
    for ri, row in enumerate(rows):
        tbl.rows[ri].height = Inches(row_h)
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.margin_left = cell.margin_right = Inches(0.12)
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if ri == 0:
                cell.fill.fore_color.rgb = rgb(header_fill)
            elif ri in highlight:
                cell.fill.fore_color.rgb = rgb("FBE9DD")
            else:
                cell.fill.fore_color.rgb = rgb(LIGHT if zebra and ri % 2 == 0 else WHITE)
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            keep_words(p)
            r = p.add_run()
            r.text = str(val)
            set_font(r, size, ri == 0 or ci == 0, WHITE if ri == 0 else (DARK if ci == 0 else BODY))
    return gf


def code(slide, x, y, w, h, src, size=12, title=None):
    box(slide, x, y, w, h, fill=CODE_BG, radius=0.03)
    top = y + 0.2
    if title:
        text(slide, x + 0.25, y + 0.15, w - 0.5, 0.3, title, size=11, color="9AA8B5", font=CODE_FONT)
        top = y + 0.55
    tb = slide.shapes.add_textbox(Inches(x + 0.25), Inches(top), Inches(w - 0.5), Inches(h - (top - y) - 0.15))
    tf = tb.text_frame
    tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(src.strip("\n").split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.1
        idx = line.find("#")
        body, cm = (line, "") if idx < 0 else (line[:idx], line[idx:])
        for t, col in ((body, CODE_FG), (cm, CODE_CM)):
            if t:
                r = p.add_run()
                r.text = t
                set_font(r, size, False, col, CODE_FONT)


def picture(slide, path, x, y, w=None, h=None, fit=True, name=None):
    """fit=True: (w,h) 상자 안에 비율 유지로 넣고 가운데 정렬."""
    from PIL import Image
    with Image.open(path) as im:
        iw, ih = im.size
    if fit and w and h:
        s = min(w / iw, h / ih)
        pw, ph = iw * s, ih * s
        x, y, w, h = x + (w - pw) / 2, y + (h - ph) / 2, pw, ph
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w) if w else None,
                                   Inches(h) if h else None)
    if name:
        pic.name = name
    return pic


def style_chart(chart, size=12):
    chart.font.size = Pt(size)
    chart.font.name = FONT
    chart.font.color.rgb = rgb(BODY)


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(13.333), Inches(7.5)
        self.prs.core_properties.author = AUTHOR
        self.prs.core_properties.title = "용접 결함 판정 AI"
        self.n = 0

    def slide(self, eyebrow=None, title=None, bg=WHITE, notes=None, footer=True):
        s = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.n += 1
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = rgb(bg)
        dark = bg == DARK
        if eyebrow:
            text(s, 0.6, 0.38, 12, 0.3, eyebrow, size=12, bold=True, color=ORANGE if dark else ORANGE_T)
        if title:
            text(s, 0.6, 0.66, 12.1, 0.7, title, size=28, bold=True, color=WHITE if dark else DARK, name="Title")
        if footer:
            text(s, 0.6, 7.05, 6, 0.25, f"용접 결함 판정 AI · {AUTHOR}", size=10, color=SOFT if dark else MUTED)
            text(s, 11.7, 7.05, 1.03, 0.25, str(self.n), size=10, color=SOFT if dark else MUTED,
                 align=PP_ALIGN.RIGHT)
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        return s

    def save(self):
        OUT_DIR.mkdir(exist_ok=True)
        self.prs.save(OUT)
        print("저장:", OUT)


# ---------------------------------------------------------------- 데이터
CLS_KO = ["용입부족", "균열", "언더컷", "언더필", "아크스트라이크", "기공", "블로홀", "스패터", "오버랩"]
TEST_ACC = [50.0, 90.2, 80.4, 96.6, 89.3, 66.1, 77.8, 83.4, 0.0]      # 판정 정확도 (reports/test_metrics)
TEST_MAP = [36.5, 77.7, 75.7, 99.5, 79.2, 39.7, 80.8, 57.8, 1.2]      # mAP50
V1_IMAGES = [61, 1508, 1402, 292, 293, 1307, 96, 1975, 78]            # 1차 데이터셋 결함별 사진 수


def read_curve():
    import csv
    with open(ROOT / "runs/weld_yolo11s/results.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    key = lambda r, k: next(v for kk, v in r.items() if kk.strip() == k)
    return [(int(float(key(r, "epoch"))), float(key(r, "metrics/mAP50(B)")) * 100,
             float(key(r, "metrics/mAP50-95(B)")) * 100) for r in rows]


# ---------------------------------------------------------------- 슬라이드
def build():
    d = Deck()

    # 1 표지 ------------------------------------------------------------
    s = d.slide(bg=DARK, footer=False, notes=(
        "용접부 사진을 넣으면 어떤 결함이 어디에 있는지 AI가 박스로 표시해 주는 '용접 결함 판정 AI' 프로젝트 결과 보고서입니다."))
    text(s, 0.8, 1.7, 7, 0.4, "BOOTCAMP PROJECT", size=14, bold=True, color=ORANGE)
    text(s, 0.8, 2.15, 7, 1.0, "용접 결함 판정 AI", size=48, bold=True, color=WHITE)
    text(s, 0.8, 3.35, 6.6, 1.0, "사진 한 장으로 9가지 용접 결함의 종류와 위치를 찾아내는 YOLO 객체탐지 프로그램",
         size=20, color=SOFT, spacing=1.3)
    text(s, 0.8, 5.25, 7, 0.4, [[("작성자  ", {"bold": True, "color": WHITE}), (AUTHOR, {})]], size=16, color=SOFT)
    text(s, 0.8, 5.7, 7, 0.4, [[("기간  ", {"bold": True, "color": WHITE}), (PERIOD, {})]], size=16, color=SOFT)
    picture(s, ASSET / "gui.png", 7.75, 1.4, 4.95, 4.7, name="표지 이미지")

    # 2 목차 ------------------------------------------------------------
    s = d.slide("CONTENTS", "목차", notes="일곱 부분으로 구성했습니다. 특히 다섯 번째 프로젝트 결과를 자세히 설명했습니다.")
    items = [("01", "프로젝트 개요", "내용 요약 · 기간 · 참여자"), ("02", "개발 동기", "기획 배경 · 목표 · 결함 9종"),
             ("03", "프로젝트 내용", "개발 환경 · 기능 · 핵심 코드"), ("04", "주요 일정", "10.12 ~ 11.04 개발 일정"),
             ("05", "프로젝트 결과", "정확도 · 그래프 · 시연 · 한계"), ("06", "기대효과", "현장 활용 효과"),
             ("07", "프로젝트 요약", "요약 · 어려움과 해결 · 느낀 점")]
    for i, (no, t, sub) in enumerate(items):
        col, row = i % 4, i // 4
        x, y = 0.6 + col * 3.07, 1.75 + row * 2.55
        hot = no == "05"
        box(s, x, y, 2.85, 2.25, fill=DARK if hot else LIGHT)
        text(s, x + 0.3, y + 0.3, 2.3, 0.6, no, size=30, bold=True, color=ORANGE if hot else ORANGE_T)
        text(s, x + 0.3, y + 1.0, 2.3, 0.45, t, size=18, bold=True, color=WHITE if hot else DARK)
        text(s, x + 0.3, y + 1.5, 2.4, 0.6, sub, size=12, color=SOFT if hot else MUTED)

    # 3 개요 ------------------------------------------------------------
    s = d.slide("01 · 프로젝트 개요", "용접 사진을 넣으면 AI가 결함을 찾아 표시합니다",
                notes="공개 데이터로 결함 9종 데이터셋을 만들고, YOLO 모델을 학습시켜, 담당자가 바로 쓰는 판정 프로그램까지 완성한 프로젝트입니다.")
    box(s, 0.6, 1.65, 5.9, 5.1, fill=DARK)
    text(s, 0.95, 1.95, 5.2, 0.45, "프로젝트 내용 요약", size=18, bold=True, color=ORANGE)
    text(s, 0.95, 2.6, 5.2, 4.0, [
        [("공개된 용접 결함 사진 데이터를 모아 ", {}), ("9가지 결함", {"bold": True, "color": WHITE}),
         ("으로 정리했습니다.", {})],
        [("사진 속 물체의 종류와 위치를 함께 찾는 ", {}), ("YOLO 객체탐지 AI", {"bold": True, "color": WHITE}),
         ("를 학습시켰습니다.", {})],
        [("담당자가 사진을 넣으면 ", {}), ("결함 종류 · 위치 · 신뢰도", {"bold": True, "color": WHITE}),
         ("를 박스로 표시하는 판정 프로그램을 완성했습니다.", {})]],
        size=16, color=SOFT, spacing=1.45, after=14)
    table(s, 6.85, 1.65, 5.88, [["항목", "내용"], ["프로젝트명", "용접 결함 판정 AI"], ["기간", PERIOD],
                                 ["참여자", AUTHOR], ["판정 대상", "용접 결함 9종"], ["핵심 기술", "YOLO11 객체탐지"],
                                 ["데이터", "Roboflow 공개 데이터 15종 통합"], ["결과물", "판정 프로그램 + 학습 코드"]],
          [0.3, 0.7], size=14, row_h=0.6)

    # 4 배경 · 목표 -----------------------------------------------------
    s = d.slide("02 · 프로젝트 개발 동기", "눈으로 하는 외관 검사를 AI가 도울 수 없을까?",
                notes="외관 검사는 사람의 경험에 크게 의존하고, 결함 종류가 많아 헷갈리며, 기록을 남기기 어렵습니다. 그래서 데이터셋, AI 모델, 판정 프로그램 세 가지를 목표로 잡았습니다.")
    text(s, 0.6, 1.65, 6, 0.4, "기획 배경", size=18, bold=True, color=DARK)
    bg = [("사람마다 판정이 다릅니다", "외관 검사는 검사자의 경험과 숙련도에 크게 의존합니다."),
          ("결함 종류가 많고 비슷합니다", "기공과 블로홀, 언더컷과 언더필처럼 헷갈리는 결함이 많습니다."),
          ("기록이 남기 어렵습니다", "어디에 어떤 결함이 있었는지 사진으로 남기고 비교하기 번거롭습니다.")]
    for i, (t, sub) in enumerate(bg):
        y = 2.2 + i * 1.5
        box(s, 0.6, y, 5.9, 1.3, fill=LIGHT)
        text(s, 0.9, y + 0.2, 5.4, 0.4, t, size=16, bold=True, color=DARK)
        text(s, 0.9, y + 0.65, 5.4, 0.6, sub, size=13, color=BODY)
    text(s, 6.85, 1.65, 6, 0.4, "목표", size=18, bold=True, color=DARK)
    goals = [("결함 9종 데이터셋", "공개 데이터를 모아 직접 구축"),
             ("결함 판정 AI", "종류와 위치를 함께 찾도록 학습 · 검증 · 테스트"),
             ("판정 프로그램", "담당자가 사진만 넣으면 바로 판정")]
    for i, (t, sub) in enumerate(goals):
        y = 2.2 + i * 1.5
        box(s, 6.85, y, 5.88, 1.3, fill=DARK)
        circle_num(s, 7.15, y + 0.3, 0.7, str(i + 1), size=20)
        text(s, 8.1, y + 0.2, 4.4, 0.4, t, size=16, bold=True, color=WHITE)
        text(s, 8.1, y + 0.65, 4.4, 0.6, sub, size=13, color=SOFT)

    # 5 결함 9종 --------------------------------------------------------
    s = d.slide("02 · 프로젝트 개발 동기", "판정 대상: 용접 결함 9종",
                notes="왼쪽은 프로젝트 기준으로 삼은 결함 분류표이고, 오른쪽은 일반인도 알기 쉽게 한 줄로 풀어 쓴 설명입니다.")
    box(s, 0.6, 1.6, 5.6, 5.2, fill=WHITE, line=LINE, radius=0.03)
    picture(s, ASSET / "wD.png", 0.75, 1.7, 5.3, 5.0, name="결함 분류표")
    table(s, 6.5, 1.6, 6.23, [["결함", "쉽게 말하면"], ["용입부족", "용접이 충분히 깊이 녹아들지 않음"],
                               ["균열", "용접부에 금이 감"], ["언더컷", "용접선 옆 모재가 움푹 패임"],
                               ["언더필", "용접이 덜 채워짐"], ["아크스트라이크", "용접봉이 닿아 모재 표면이 패임"],
                               ["기공", "내부에 생긴 가스 기포"], ["블로홀", "표면으로 빠져나온 작은 구멍"],
                               ["스패터", "튀어나와 붙은 금속 알갱이"], ["오버랩", "모재 위로 넘쳐 덮인 용접"]],
          [0.32, 0.68], size=14, row_h=0.52)

    # 6 개발 환경 -------------------------------------------------------
    s = d.slide("03 · 프로젝트 내용", "개발 환경",
                notes="학습은 GPU 메모리가 큰 Colab T4에서 했고, PC의 GTX 1650은 판정 프로그램 실행과 테스트에 사용했습니다. 처음 PC에서 학습을 시도했지만 한 epoch에 13분 이상 걸려 Colab으로 옮겼습니다.")
    envs = [("언어 · 라이브러리", ORANGE, ["Python", "PyTorch (CUDA)", "Ultralytics YOLO11", "Pillow · Matplotlib",
                                         "tkinter (화면 프로그램)"]),
            ("하드웨어", BLUE, ["Windows 10 PC", "Intel i7-9700 · RAM 16GB", "GTX 1650 4GB (판정 · 테스트)",
                              "Google Colab T4 GPU (학습)"]),
            ("도구 · 데이터", DARK, ["VS Code + Colab 확장", "Google Drive (결과 저장)", "Roboflow Universe (공개 데이터)",
                                   "Claude Code (개발 보조)"])]
    for i, (t, col, lines) in enumerate(envs):
        x = 0.6 + i * 4.1
        box(s, x, 1.7, 3.85, 4.9, fill=LIGHT)
        circle_num(s, x + 0.35, 2.0, 0.75, str(i + 1), fill=col, size=20)
        text(s, x + 0.35, 2.95, 3.2, 0.45, t, size=18, bold=True, color=DARK)
        text(s, x + 0.35, 3.6, 3.3, 2.8, lines, size=14, color=BODY, spacing=1.2, after=8)

    # 7 전체 흐름 -------------------------------------------------------
    s = d.slide("03 · 프로젝트 내용", "전체 흐름: 데이터에서 판정 프로그램까지",
                notes="다섯 단계를 왼쪽부터 순서대로 설명합니다. 아래 상자는 YOLO가 무엇인지 일반인에게 설명하는 부분입니다.")
    steps = [("데이터 수집", "Roboflow 공개 데이터 24개 조사, 15개 선정"),
             ("정리 · 통합", "제각각인 결함 이름을 9종으로 통일, 중복 제거"),
             ("AI 학습", "YOLO11이 결함 사진과 위치를 반복 학습"),
             ("검증 · 테스트", "처음 보는 사진으로 결함별 정확도 측정"),
             ("판정 프로그램", "사진을 넣으면 결함 위치를 박스로 표시")]
    for i, (t, sub) in enumerate(steps):
        x = 0.6 + i * 2.5
        last = i == len(steps) - 1
        box(s, x, 1.8, 2.15, 2.9, fill=ORANGE if last else DARK)
        text(s, x + 0.25, 2.0, 1.7, 0.6, str(i + 1), size=28, bold=True, color=DARK if last else ORANGE)
        text(s, x + 0.25, 2.7, 1.75, 0.45, t, size=16, bold=True, color=DARK if last else WHITE)
        text(s, x + 0.25, 3.25, 1.75, 1.4, sub, size=12, color=DARK if last else SOFT, spacing=1.3)
        if not last:
            a = box(s, x + 2.18, 3.08, 0.28, 0.34, fill=ORANGE, shape=MSO_SHAPE.CHEVRON)
    box(s, 0.6, 5.1, 12.13, 1.6, fill=LIGHT)
    text(s, 0.95, 5.35, 11.5, 1.2, [
        [("객체탐지(YOLO)란?  ", {"bold": True, "color": DARK, "size": 16})],
        [("사진 한 장에서 “무엇이” “어디에” 있는지를 한 번에 찾는 AI입니다. "
          "그래서 결함 종류뿐 아니라 위치까지 박스로 알려 줍니다.", {})]], size=15, spacing=1.35)

    # 8 코드 구성 -------------------------------------------------------
    s = d.slide("03 · 프로젝트 내용", "주요 기능과 코드 구성 (모듈 · 클래스)",
                notes="코드를 역할별 모듈과 클래스로 나눴습니다. 다음 네 장에서 핵심 코드를 하나씩 설명합니다.")
    table(s, 0.6, 1.65, 12.13, [["파일 (모듈)", "클래스", "하는 일"],
                                 ["main.py", "-", "실행 시작점: 화면 · 학습 · 평가 · 판정 명령"],
                                 ["weld_defect/config.py", "Config", "결함 9종 정의, 경로, 학습 · 증강 설정"],
                                 ["weld_defect/trainer.py", "DefectTrainer", "YOLO 모델 학습, 최종 모델 저장"],
                                 ["weld_defect/evaluator.py", "DefectEvaluator", "검증 · 테스트, 결함별 정확도 표 · 그래프"],
                                 ["weld_defect/detector.py", "DefectDetector", "사진 판정, 번호 · 색 박스 그리기"],
                                 ["weld_defect/app.py", "DefectApp", "담당자용 판정 프로그램 화면"],
                                 ["tools/build_dataset.py", "-", "데이터 다운로드 · 9종 통일 · 분할"],
                                 ["colab_train.ipynb", "-", "Colab GPU 학습 노트북"]],
          [0.3, 0.2, 0.5], size=14, row_h=0.5)
    pills = ["판정프로그램.bat 더블클릭 실행", "사진 · 폴더 단위 판정", "결과 이미지 저장", "신뢰도 기준 조절"]
    x = 0.6
    for p in pills:
        w = 0.25 + len(p) * 0.2
        b = box(s, x, 6.35, w, 0.45, fill=LIGHT, radius=0.5)
        text(s, x, 6.35, w, 0.45, p, size=12, bold=True, color=DARK, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        x += w + 0.2

    # 9 데이터셋 --------------------------------------------------------
    s = d.slide("03 · 프로젝트 내용", "데이터셋 구축: 흩어진 공개 데이터를 하나로",
                notes="공개 데이터마다 결함 이름과 기준이 달라 통일하는 작업이 가장 중요했습니다. 그래프는 1차 데이터셋의 결함별 사진 수로, 스패터와 균열은 많고 블로홀, 오버랩, 용입부족은 매우 적습니다.")
    box(s, 0.6, 1.6, 12.13, 1.25, fill=DARK)
    stats = [("15개", "통합한 공개 데이터셋"), ("9종", "통일한 결함 이름"), ("약 6,200장", "1차 데이터셋 사진"),
             ("70 : 15 : 15", "학습 : 검증 : 테스트")]
    for i, (big, small) in enumerate(stats):
        x = 0.6 + i * 3.03
        text(s, x, 1.68, 3.03, 0.65, big, size=30, bold=True, color=ORANGE, align=PP_ALIGN.CENTER)
        text(s, x, 2.35, 3.03, 0.35, small, size=13, color=SOFT, align=PP_ALIGN.CENTER)
    cd = CategoryChartData()
    cd.categories = CLS_KO
    cd.add_series("사진 수", V1_IMAGES)
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(3.05), Inches(7.6),
                            Inches(3.8), cd)
    ch = gf.chart
    style_chart(ch, 11)
    ch.has_title = True
    ch.chart_title.text_frame.text = "결함별 사진 수 (1차 데이터셋 · 주황 = 100장 미만)"
    set_font(ch.chart_title.text_frame.paragraphs[0].runs[0], 14, True, DARK)
    ch.has_legend = False
    pl = ch.plots[0]
    pl.gap_width = 60
    pl.has_data_labels = True
    pl.data_labels.font.size = Pt(11)
    pl.data_labels.number_format = '#,##0'
    pl.data_labels.number_format_is_linked = False
    pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    ser = pl.series[0]
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = rgb(BLUE)
    for idx in (0, 6, 8):  # 매우 적은 결함 강조
        pt = ser.points[idx]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(ORANGE)
    ch.value_axis.has_major_gridlines = True
    ch.value_axis.major_gridlines.format.line.color.rgb = rgb("E1E4E8")
    ch.value_axis.format.line.fill.background()
    feats = [("이름 통일", "“Spatters”, “Splatter”, 중국어 “咬边(언더컷)”처럼 제각각인 이름을 9종으로 맞춤"),
             ("공정한 시험", "같은 사진 · 영상의 연속 장면은 한 묶음으로 처리해 학습용과 시험용에 섞이지 않게 분리"),
             ("사진 검수", "결함별로 잘라 눈으로 확인, 용입부족은 외관 사진이 없어 X-ray로 보완")]
    for i, (t, sub) in enumerate(feats):
        y = 3.05 + i * 1.3
        box(s, 8.45, y, 4.28, 1.15, fill=LIGHT)
        text(s, 8.7, y + 0.13, 3.8, 0.35, t, size=14, bold=True, color=DARK)
        text(s, 8.7, y + 0.48, 3.85, 0.65, sub, size=11, color=BODY, spacing=1.2)

    # 10~13 핵심 코드 ----------------------------------------------------
    def code_slide(no, title, src, src_title, points, notes):
        s = d.slide(f"03 · 프로젝트 내용 · 핵심 코드 {no}", title, notes=notes)
        code(s, 0.6, 1.6, 7.4, 5.2, src, size=12, title=src_title)
        for i, (t, sub) in enumerate(points):
            y = 1.6 + i * 1.32
            circle_num(s, 8.3, y + 0.05, 0.5, str(i + 1), size=14)
            text(s, 8.95, y, 3.8, 0.4, t, size=15, bold=True, color=DARK)
            text(s, 8.95, y + 0.42, 3.8, 0.85, sub, size=12, color=BODY, spacing=1.25)
        return s

    code_slide("①", "데이터 정리: 제각각인 결함 이름을 9종으로", '''
# data/sources.yaml (발췌)
sources:
  - slug: oran-ai/visual-weld-inspector
    version: 12
    class_map:              # 원본 이름 -> 9종 결함
      Underfill: underfill
      Arc Strike: arc_strike
      Pin Hole: blowhole    # 표면의 작은 가스 구멍
      Spatter: spatter
      Lack Of Fusion: null  # 9종이 아님 -> 제외

# tools/build_dataset.py (발췌)
def group_key(stem):
    """Roboflow 증강 사본을 원본 단위로 묶는다."""
    base = stem.split(".rf.")[0]
    return re.sub(r"_(jpg|jpeg|png|bmp|webp)$", "", base)
''', "sources.yaml · build_dataset.py", [
        ("어떤 데이터를 쓸지", "Roboflow 공개 데이터 15개를 목록으로 관리합니다."),
        ("이름 바꾸기 표", "데이터마다 다른 결함 이름을 우리 기준 9종으로 바꿉니다."),
        ("9종이 아니면 제외", "null로 표시한 결함은 학습에서 뺍니다."),
        ("같은 사진 묶기", "변형된 사본을 원본과 한 묶음으로 처리해 시험 누수를 막습니다.")],
        "데이터 정리 규칙을 코드가 아닌 설정 파일로 관리해서, 데이터를 추가하거나 빼기 쉽게 만들었습니다.")

    code_slide("②", "AI 학습: YOLO11 모델 학습시키기", '''
# weld_defect/trainer.py (발췌)
class DefectTrainer:
    def train(self, resume=False):
        c = self.cfg
        model = YOLO(c.base_model)      # yolo11s.pt (사전학습)
        model.train(
            data=str(c.data_yaml),      # 9종 데이터셋
            epochs=c.epochs,            # 최대 반복 횟수
            patience=c.patience,        # 개선 없으면 조기 종료
            imgsz=c.imgsz,              # 640px 로 맞춰 학습
            batch=c.batch,
            cos_lr=True,
            **c.augment,                # 회전 · 색감 · 크기 변형
        )
        best = c.runs_dir / c.run_name / "weights" / "best.pt"
        shutil.copy2(best, c.best_model)  # 최종 모델 저장
''', "weld_defect/trainer.py", [
        ("사전학습 모델에서 출발", "이미 일반 사물을 배운 YOLO11s에 용접 결함을 추가로 가르칩니다."),
        ("반복 학습 + 조기 종료", "정해진 횟수만큼 반복하되, 좋아지지 않으면 스스로 멈춥니다."),
        ("사진 변형(증강)", "돌리고 색을 바꾼 사진도 보여 줘 다양한 환경에 대비합니다."),
        ("가장 좋은 모델 저장", "검증 점수가 가장 높았던 모델을 판정 프로그램에 씁니다.")],
        "사전학습 모델을 출발점으로 쓰면 적은 데이터로도 빠르게 학습할 수 있습니다.")

    code_slide("③", "평가: 결함별 판정 정확도 계산", '''
# weld_defect/evaluator.py (발췌)
for r in results:                        # 테스트 사진 한 장씩
    gt = {정답 결함 번호들}               # 라벨 파일에서 읽기
    pred = {int(x) for x in r.boxes.cls.tolist()}
    for cid in stats:                    # 결함 9종마다
        if cid in gt and cid in pred:
            stats[cid]["tp"] += 1        # 찾음
        elif cid in gt:
            stats[cid]["fn"] += 1        # 놓침
        elif cid in pred:
            stats[cid]["fp"] += 1        # 헛경보

recall = tp / (tp + fn)       # 판정 정확도
precision = tp / (tp + fp)    # 판정 정밀도
''', "weld_defect/evaluator.py", [
        ("처음 보는 사진으로 시험", "학습에 쓰지 않은 테스트 사진만 사용합니다."),
        ("사진마다 채점", "정답 결함과 AI가 찾은 결함을 비교합니다."),
        ("찾음 · 놓침 · 헛경보", "결함 9종마다 세 가지 경우를 셉니다."),
        ("두 가지 점수", "놓치지 않는 능력(정확도)과 헛경보가 적은 능력(정밀도)")],
        "정답 라벨과 AI 판정을 사진 단위로 비교해 결함별 점수를 계산합니다. gt 줄은 이해를 돕기 위해 간단히 줄여 썼습니다.")

    code_slide("④", "판정: 사진 한 장에서 결함 찾기", '''
# weld_defect/detector.py (발췌)
def predict(self, image_path):
    img = self._load(image_path)
    r = self.model.predict(img, conf=self.cfg.conf,
                           iou=self.cfg.iou)[0]
    dets = []
    for cls, conf, xyxy in zip(r.boxes.cls.tolist(),
                               r.boxes.conf.tolist(),
                               r.boxes.xyxy.tolist()):
        c = CLASSES[int(cls)]           # 결함 번호 -> 한글 이름
        dets.append(Detection(c.id, c.name, c.ko,
                              conf, tuple(xyxy)))
    dets.sort(key=lambda d: -d.conf)    # 신뢰도 높은 순
    return Verdict(image_path, dets)    # 대표 결함 + 위치
''', "weld_defect/detector.py", [
        ("사진을 AI에 넣기", "학습된 모델이 결함 후보와 위치를 찾습니다."),
        ("신뢰도 기준 적용", "기본 25% 이상 확신하는 결함만 남깁니다."),
        ("한글 결함명으로 변환", "번호를 '언더컷'처럼 사람이 읽는 이름으로 바꿉니다."),
        ("결과 정리", "신뢰도 순으로 번호를 매겨 화면과 이미지에 표시합니다.")],
        "판정 프로그램은 이 predict 함수를 사진마다 호출하고, 결과를 번호 박스로 그려 보여 줍니다.")

    # 14 일정 (간트) -----------------------------------------------------
    s = d.slide("04 · 주요 일정", "개발 일정 (2026.10.12 ~ 11.04)",
                notes="기간 전체의 개발 일정입니다. 10월 25일 현재 v2 재학습을 Colab에서 진행 중이며, 11월 초 평가와 최종 제출을 준비합니다.")
    import datetime as dt
    start, end = dt.date(2026, 10, 12), dt.date(2026, 11, 4)
    days = (end - start).days + 1
    X0, W = 4.1, 8.63
    per = W / days
    phases = [("기획 · 결함 기준 조사", dt.date(2026, 10, 12), dt.date(2026, 10, 16), BLUE, "완료"),
              ("데이터셋 구축 · 코드 작성", dt.date(2026, 10, 17), dt.date(2026, 10, 17), BLUE, "완료"),
              ("1차 학습(v1) · 평가", dt.date(2026, 10, 17), dt.date(2026, 10, 17), BLUE, "완료"),
              ("결과 분석 · 개선(v2)", dt.date(2026, 10, 18), dt.date(2026, 10, 18), BLUE, "완료"),
              ("보고서 작성 · 학습 시간 단축 검토", dt.date(2026, 10, 19), dt.date(2026, 10, 24), BLUE, "완료"),
              ("v2 재학습 (Colab)", dt.date(2026, 10, 25), dt.date(2026, 10, 31), ORANGE, "진행 중"),
              ("v2 평가 · 최종 제출 준비", dt.date(2026, 11, 1), dt.date(2026, 11, 4), "9AA3AD", "예정")]
    for wk in range(0, days, 7):
        x = X0 + wk * per
        dd = start + dt.timedelta(days=wk)
        text(s, x, 1.62, 1.2, 0.3, f"{dd.month}.{dd.day}", size=11, color=MUTED)
        ln = s.shapes.add_connector(1, Inches(x), Inches(1.95), Inches(x), Inches(6.45))
        ln.line.color.rgb = rgb("E1E4E8")
    text(s, X0 + W - 0.6, 1.62, 0.6, 0.3, "11.4", size=11, color=MUTED, align=PP_ALIGN.RIGHT)
    for i, (t, a, b, col, st) in enumerate(phases):
        y = 2.05 + i * 0.62
        text(s, 0.6, y + 0.05, 3.4, 0.4, t, size=13, bold=True, color=DARK)
        bx = X0 + (a - start).days * per
        bw = max(((b - a).days + 1) * per, 0.36)
        box(s, bx, y, bw, 0.42, fill=col, radius=0.25)
        text(s, bx + bw + 0.1, y + 0.07, 1.4, 0.3, st, size=11, bold=True,
             color=ORANGE_T if st == "진행 중" else MUTED)
    text(s, 0.6, 6.55, 12, 0.3, "10.17 ~ 10.18은 하루 단위 작업(데이터 · 코드 · 학습 · 개선)이 몰려 막대가 짧게 표시됩니다.",
         size=11, color=MUTED)

    # 15 점수 읽는 법 ----------------------------------------------------
    s = d.slide("05 · 프로젝트 결과", "결과를 보기 전에: 점수 읽는 법", bg=LIGHT,
                notes="판정 정확도는 놓치지 않는 능력, 정밀도는 헛경보를 내지 않는 능력입니다. mAP50은 위치 박스까지 맞혔는지 보는 점수입니다.")
    text(s, 0.6, 1.55, 12, 0.45, [[("AI가 ", {}), ("학습할 때 한 번도 보지 않은 사진(테스트용 약 900장)", {"bold": True, "color": DARK}),
                                  ("으로 시험을 봤습니다.", {})]], size=16)
    cards = [("판정 정확도", "그 결함이 있는 사진 중 AI가 그 결함을 찾아낸 비율", "예) 90% = 균열 사진 10장 중 9장을 찾음", ORANGE_T),
             ("판정 정밀도", "AI가 “균열”이라고 한 것 중 진짜 균열인 비율", "높을수록 헛경보가 적음", BLUE),
             ("mAP50 (위치 점수)", "결함의 위치 박스까지 맞혔는지 보는 종합 점수", "정답 박스와 절반 이상 겹치면 맞힌 것으로 계산", DARK),
             ("신뢰도", "AI가 스스로 얼마나 확신하는지(0~100%)", "판정 프로그램은 기본 25% 이상만 표시", MUTED)]
    for i, (t, a, b, col) in enumerate(cards):
        x, y = 0.6 + (i % 2) * 6.15, 2.25 + (i // 2) * 2.3
        box(s, x, y, 5.98, 2.05, fill=WHITE)
        circle_num(s, x + 0.3, y + 0.3, 0.55, str(i + 1), fill=col, size=14)
        text(s, x + 1.05, y + 0.32, 4.7, 0.45, t, size=18, bold=True, color=DARK)
        text(s, x + 1.05, y + 0.9, 4.7, 0.5, a, size=14, color=BODY, spacing=1.25)
        text(s, x + 1.05, y + 1.45, 4.7, 0.45, b, size=13, bold=True, color=col)

    # 16 결함별 정확도 차트 ----------------------------------------------
    s = d.slide("05 · 프로젝트 결과", "결함별 판정 정확도와 위치 점수 (테스트 사진)",
                notes="9종 중 6종은 78% 이상 찾아냈습니다. 정밀도는 대부분 90% 이상이라 AI가 결함이라고 하면 거의 맞습니다. 반면 기공, 용입부족, 오버랩은 놓치는 경우가 많습니다.")
    cd = CategoryChartData()
    cd.categories = CLS_KO
    cd.add_series("판정 정확도 (사진 단위)", TEST_ACC)
    cd.add_series("mAP50 (위치 점수)", TEST_MAP)
    ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.55), Inches(8.6),
                            Inches(5.3), cd).chart
    style_chart(ch, 12)
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.TOP
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(12)
    pl = ch.plots[0]
    pl.gap_width, pl.overlap = 70, -10
    pl.has_data_labels = True
    pl.data_labels.font.size = Pt(10)
    pl.data_labels.number_format = '0'
    pl.data_labels.number_format_is_linked = False
    pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    for ser, col in zip(pl.series, (BLUE, ORANGE)):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(col)
    va = ch.value_axis
    va.maximum_scale, va.minimum_scale, va.major_unit = 110, 0, 20
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("E1E4E8")
    va.tick_labels.font.size = Pt(11)
    ch.category_axis.tick_labels.font.size = Pt(12)
    box(s, 9.45, 1.55, 3.28, 2.3, fill=DARK)
    text(s, 9.7, 1.75, 2.9, 0.35, "전체 위치 점수 (mAP50)", size=13, color=SOFT)
    text(s, 9.7, 2.15, 2.9, 0.9, "60.9%", size=44, bold=True, color=ORANGE)
    text(s, 9.7, 3.15, 2.9, 0.55, "9종 평균, 박스 위치까지 맞힌 정도", size=12, color=SOFT)
    box(s, 9.45, 4.05, 3.28, 2.8, fill=LIGHT)
    text(s, 9.7, 4.25, 2.85, 2.5, [
        [("잘 찾음 (80% 이상)", {"bold": True, "color": BLUE})],
        "언더필 97 · 균열 90 · 아크스트라이크 89 · 스패터 83 · 언더컷 80",
        [("개선 필요", {"bold": True, "color": ORANGE_T})],
        "기공 66 · 용입부족 50 · 오버랩 0"], size=12, spacing=1.25, after=6)

    # 17 학습 곡선 -------------------------------------------------------
    curve = read_curve()
    s = d.slide("05 · 프로젝트 결과", "학습 과정: 반복할수록 똑똑해진 AI",
                notes="Colab T4 GPU에서 YOLO11s 모델로 학습한 실제 기록입니다. 50회쯤 위치 점수 58%에 도달한 뒤 더 오르지 않아 71회에서 조기 종료했습니다.")
    xy = XyChartData()
    s1 = xy.add_series("mAP50 (위치 점수)")
    s2 = xy.add_series("mAP50-95 (엄격한 위치 점수)")
    for ep, m50, m95 in curve:
        s1.add_data_point(ep, m50)
        s2.add_data_point(ep, m95)
    ch = s.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER_LINES_NO_MARKERS, Inches(0.6), Inches(1.55),
                            Inches(8.3), Inches(5.3), xy).chart
    style_chart(ch, 12)
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.TOP
    ch.legend.include_in_layout = False
    for ser, col in zip(ch.plots[0].series, (BLUE, ORANGE)):
        ser.format.line.color.rgb = rgb(col)
        ser.format.line.width = Pt(2.5)
        ser.smooth = False
    va, ca = ch.value_axis, ch.category_axis
    va.maximum_scale, va.minimum_scale, va.major_unit = 70, 0, 10
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("E1E4E8")
    va.has_title = True
    va.axis_title.text_frame.text = "검증 점수 (%)"
    ca.minimum_scale, ca.maximum_scale, ca.major_unit = 0, 75, 10
    ca.has_major_gridlines = False
    ca.has_title = True
    ca.axis_title.text_frame.text = "학습 반복 횟수 (epoch)"
    for ax in (va, ca):
        set_font(ax.axis_title.text_frame.paragraphs[0].runs[0], 12, False, MUTED)
    best = max(curve, key=lambda r: r[1])
    text(s, 9.15, 1.6, 3.6, 5.2, [
        [("시작 ", {}), (f"{curve[0][1]:.0f}%", {"bold": True, "color": DARK})],
        "처음엔 결함을 거의 못 찾았습니다.",
        [("최고 ", {}), (f"{best[1]:.1f}% ({best[0]}회)", {"bold": True, "color": ORANGE_T})],
        "사진을 반복해 볼수록 점수가 올라 50회쯤 58% 근처에 도달했습니다.",
        [("자동 종료 ", {}), (f"{curve[-1][0]}회", {"bold": True, "color": DARK})],
        "그 뒤로 더 좋아지지 않아 스스로 학습을 멈췄습니다(조기 종료).",
        [("엄격한 점수(주황)", {"bold": True, "color": DARK})],
        "박스 테두리까지 정확한지 보는 점수로, 약 30%입니다."], size=14, spacing=1.3, after=6)

    # 18 결과 해석 -------------------------------------------------------
    s = d.slide("05 · 프로젝트 결과", "결과 해석: 무엇이 점수를 갈랐나",
                notes="잘 맞히는 결함은 모양이 뚜렷하고 데이터가 많습니다. 못 맞히는 결함은 데이터가 적거나(오버랩), 다른 종류의 사진으로 대체했거나(용입부족), 너무 작습니다(기공).")
    box(s, 0.6, 1.6, 5.95, 3.7, fill=LIGHT)
    text(s, 0.95, 1.85, 5.3, 0.45, "잘 찾는 결함 (80~97%)", size=18, bold=True, color=BLUE)
    text(s, 0.95, 2.4, 5.3, 0.4, "언더필 · 균열 · 아크스트라이크", size=15, bold=True, color=DARK)
    text(s, 0.95, 2.95, 5.35, 2.3, ["• 모양이 뚜렷함: 금(균열), 둥글게 패인 자국(아크스트라이크)",
                                    "• 학습 사진이 충분함: 균열은 1,000장 이상",
                                    "• 결함이 커서 사진을 줄여도 형태가 남음"], size=14, spacing=1.3, after=8)
    box(s, 6.78, 1.6, 5.95, 3.7, fill=LIGHT)
    text(s, 7.13, 1.85, 5.3, 0.45, "어려운 결함 (0~66%)", size=18, bold=True, color=ORANGE_T)
    text(s, 7.13, 2.45, 5.35, 2.8, [[("• 오버랩 0%: ", {"bold": True, "color": DARK}), ("학습 사진이 약 50장뿐", {})],
                                    [("• 용입부족 50%: ", {"bold": True, "color": DARK}),
                                     ("외관 사진 공개 데이터가 없어 X-ray 사진으로 대체", {})],
                                    [("• 기공 66%: ", {"bold": True, "color": DARK}),
                                     ("구멍이 매우 작아 사진을 줄이면 몇 픽셀로 뭉개짐", {})]], size=14, spacing=1.3, after=8)
    box(s, 0.6, 5.55, 12.13, 1.25, fill=DARK)
    text(s, 0.95, 5.55, 11.5, 1.25, [[("결론: 성능을 좌우한 것은 AI 모델보다 ", {}),
                                      ("데이터의 양과 질", {"bold": True, "color": ORANGE}), ("이었습니다.", {})]],
         size=20, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)

    # 19 혼동행렬 --------------------------------------------------------
    s = d.slide("05 · 프로젝트 결과", "혼동행렬: AI는 무엇을 무엇으로 헷갈렸나",
                notes="가로가 정답, 세로가 AI 판정입니다. 대각선이 진할수록 잘 맞힌 것입니다. 박스 단위로 엄격하게 센 표라 앞의 사진 단위 정확도와 숫자가 다를 수 있습니다.")
    box(s, 0.6, 1.55, 7.3, 5.3, fill=WHITE, line=LINE, radius=0.02)
    picture(s, ROOT / "reports/test_confusion_matrix.png", 0.7, 1.6, 7.1, 5.2, name="혼동행렬")
    text(s, 8.2, 1.6, 4.55, 5.2, [
        [("읽는 법", {"bold": True, "color": DARK, "size": 16})],
        "가로 = 정답 결함, 세로 = AI 판정. 대각선(왼쪽 위 → 오른쪽 아래)이 진할수록 정확합니다.",
        [("잘 맞힘", {"bold": True, "color": BLUE, "size": 16})],
        "균열 94% · 용입부족 93% · 스패터 88% · 언더컷 80%",
        [("헷갈림", {"bold": True, "color": ORANGE_T, "size": 16})],
        "오버랩은 15%만 맞히고 38%는 배경으로 놓침. 언더필 일부(25%)는 기공으로 판정",
        [("영어 이름", {"bold": True, "color": DARK, "size": 16})],
        "incomplete_penetration 용입부족 · crack 균열 · undercut 언더컷 · underfill 언더필 · arc_strike 아크스트라이크 · "
        "porosity 기공 · blowhole 블로홀 · spatter 스패터 · overlap 오버랩 · background 배경(결함 없음)"],
         size=13, spacing=1.3, after=6)

    # 20 정답 vs AI ------------------------------------------------------
    s = d.slide("05 · 프로젝트 결과", "정답과 AI 판정 비교 (검증 사진 16장)",
                notes="왼쪽은 사람이 표시한 정답, 오른쪽은 같은 사진에 대한 AI 판정입니다. 박스 옆 숫자는 신뢰도입니다. 대부분 같은 위치를 찾았고, 일부 작은 결함은 놓쳤습니다.")
    for i, (fn, label) in enumerate((("val_batch0_labels.jpg", "정답 (사람이 표시)"),
                                     ("val_batch0_pred.jpg", "AI 판정 (숫자 = 신뢰도)"))):
        x = 0.6 + i * 6.15
        box(s, x, 1.55, 5.98, 0.45, fill=DARK if i else BLUE, radius=0.15)
        text(s, x, 1.55, 5.98, 0.45, label, size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)
        picture(s, ROOT / "runs/weld_yolo11s" / fn, x, 2.1, 5.98, 4.75, name=label)

    # 21 판정 프로그램 화면 ----------------------------------------------
    s = d.slide("05 · 프로젝트 결과 · 시연", "판정 프로그램 실행 화면", bg=LIGHT,
                notes="판정프로그램.bat을 더블클릭하면 이 화면이 열립니다. 예시 사진에서는 모재 표면의 아크스트라이크 3곳을 찾아 신뢰도 80%, 58%, 41%로 표시했습니다.")
    picture(s, ASSET / "gui.png", 0.6, 1.55, 8.2, 5.3, name="판정 프로그램 화면")
    steps = [("사진 열기", "판정할 사진(여러 장 가능)이나 폴더 선택"), ("판정 목록", "사진마다 대표 결함과 신뢰도"),
             ("결함 위치 박스", "번호 · 결함명 · 신뢰도를 사진 위에 표시"), ("결과 설명", "결함 종류별 개수와 위치 좌표"),
             ("결과 이미지 저장", "박스가 그려진 사진을 기록으로 보관")]
    for i, (t, sub) in enumerate(steps):
        y = 1.6 + i * 1.04
        circle_num(s, 9.1, y, 0.5, str(i + 1), size=14)
        text(s, 9.75, y - 0.02, 3.0, 0.35, t, size=15, bold=True, color=DARK)
        text(s, 9.75, y + 0.36, 3.0, 0.6, sub, size=12, color=BODY, spacing=1.2)

    # 22 결함별 판정 예시 ------------------------------------------------
    s = d.slide("05 · 프로젝트 결과 · 시연", "결함별 판정 예시", bg=DARK,
                notes="판정 프로그램으로 결함별 사진을 판정한 결과입니다. 결함마다 박스 색이 정해져 있어 여러 결함이 함께 있어도 구분됩니다. 사진은 공개 데이터셋에서 고른 예시입니다.")
    text(s, 0.6, 1.4, 12, 0.3, "박스 색 = 결함 종류 · #번호 = 신뢰도 높은 순 · % = AI가 확신하는 정도", size=13, color=SOFT)
    demos = [("demo_crack.jpg", "균열 63%", "금이 간 선 전체를 감쌈"), ("demo_undercut.jpg", "언더컷 73%", "비드 옆 패인 홈"),
             ("demo_underfill.jpg", "언더필 64%", "덜 채워진 비드"), ("demo_arc_strike.jpg", "아크스트라이크 80%", "3곳 모두 찾음"),
             ("demo_porosity.jpg", "기공 68%", "구멍이 모인 구간"), ("demo_spatter.jpg", "스패터 61%", "알갱이 4개 각각 표시")]
    for i, (fn, t, sub) in enumerate(demos):
        x, y = 0.6 + (i % 3) * 4.1, 1.85 + (i // 3) * 2.6
        box(s, x, y, 3.93, 2.05, fill="0F171F", radius=0.04)
        picture(s, ASSET / fn, x + 0.05, y + 0.05, 3.83, 1.95, name=t)
        text(s, x, y + 2.1, 3.93, 0.35, [[(t, {"bold": True, "color": WHITE}), (f"  {sub}", {})]], size=12, color=SOFT)

    # 23 출처별 재검증 ---------------------------------------------------
    s = d.slide("05 · 프로젝트 결과 · 한계 분석", "다른 사진에도 통할까? 출처별로 다시 검증",
                notes="공개 데이터 원본을 출처별로 40장씩 뽑아 다시 판정했습니다. 원본에는 학습에 쓴 사진이 일부 섞여 있어 출처 A~I의 비율은 처음 보는 사진의 성능보다 높게 나온 값입니다. 반대로 주황 3곳은 학습한 출처인데도 못 맞혔다는 뜻이라, 촬영 환경이 달라지면 약하다는 결론이 더 분명해집니다. 출처 이름은 부록에 정리했습니다.")
    text(s, 0.6, 1.42, 12.1, 0.3, "※ 출처별 원본 40장씩 다시 판정 · 학습에 쓴 사진이 일부 포함됨 · 결함 표시가 있는 표본 11~40장 · 출처 이름은 부록 참고",
         size=11, color=MUTED)
    src = [("출처 A", 100), ("출처 B", 92), ("출처 C", 88), ("출처 D", 82), ("출처 E", 77), ("출처 F", 77),
           ("출처 G", 72), ("출처 H", 71), ("출처 I", 50), ("변형 심한 사진", 24), ("낯선 스타일", 13),
           ("휴대폰 현장 사진", 0)]
    cd = CategoryChartData()
    cd.categories = [n for n, _ in reversed(src)]
    cd.add_series("정답 결함을 찾은 비율", [v for _, v in reversed(src)])
    ch = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(1.85), Inches(7.4), Inches(5.0),
                            cd).chart
    style_chart(ch, 12)
    ch.has_legend = False
    ch.has_title = True
    ch.chart_title.text_frame.text = "출처별 정답 결함을 찾은 비율 (%)"
    set_font(ch.chart_title.text_frame.paragraphs[0].runs[0], 14, True, DARK)
    pl = ch.plots[0]
    pl.gap_width = 50
    pl.has_data_labels = True
    pl.data_labels.font.size = Pt(11)
    pl.data_labels.number_format = '0'
    pl.data_labels.number_format_is_linked = False
    pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    ser = pl.series[0]
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = rgb(BLUE)
    for idx in range(3):
        pt = ser.points[idx]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = rgb(ORANGE)
    va = ch.value_axis
    va.maximum_scale, va.minimum_scale, va.major_unit = 110, 0, 20
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = rgb("E1E4E8")
    text(s, 8.3, 1.9, 4.45, 3.0, [
        [("출처 A~I: 50~100%", {"bold": True, "color": BLUE})],
        "학습에 쓴 사진이 섞여 있어 실제보다 높게 나온 값",
        [("주황 3곳: 0~24%", {"bold": True, "color": ORANGE_T})],
        "학습한 출처인데도 못 맞힘: 과도한 확대 · 회전, 처음 보는 스타일, 결함 표시가 어긋난 고해상도 현장 사진"],
         size=14, spacing=1.3, after=6)
    box(s, 8.3, 4.95, 4.43, 1.9, fill=DARK)
    text(s, 8.55, 4.95, 4.0, 1.9, [[("테스트 점수가 좋아도 ", {}), ("처음 보는 촬영 환경", {"bold": True, "color": ORANGE}),
                                    ("에서는 약합니다. 현장에 쓰려면 ", {}),
                                    ("현장 사진으로 추가 학습", {"bold": True, "color": ORANGE}), ("이 필요합니다.", {})]],
         size=14, color=WHITE, spacing=1.35, anchor=MSO_ANCHOR.MIDDLE)

    # 24 개선판 v2 -------------------------------------------------------
    s = d.slide("05 · 프로젝트 결과 · 개선", "발견한 문제를 고친 개선판(v2)",
                notes="결함 표시가 잘못된 출처 2곳을 빼고, 적은 결함은 같은 사진을 여러 번 보여 주는 반복 학습으로 늘렸습니다. 시험용 사진은 원본 그대로 두어 공정하게 비교합니다. 현재 Colab에서 재학습 중입니다.")
    cd = CategoryChartData()
    cd.categories = ["오버랩", "아크스트라이크", "언더필", "블로홀", "용입부족"]
    cd.add_series("1차 (v1)", [54, 191, 232, 79, 44])
    cd.add_series("개선 (v2)", [846, 783, 639, 372, 264])
    ch = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.55), Inches(6.9), Inches(5.3),
                            cd).chart
    style_chart(ch, 12)
    ch.has_title = True
    ch.chart_title.text_frame.text = "적은 결함의 학습 사진 수 (장)"
    set_font(ch.chart_title.text_frame.paragraphs[0].runs[0], 14, True, DARK)
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.TOP
    ch.legend.include_in_layout = False
    pl = ch.plots[0]
    pl.gap_width, pl.overlap = 60, -10
    pl.has_data_labels = True
    pl.data_labels.font.size = Pt(11)
    pl.data_labels.number_format = '#,##0'
    pl.data_labels.number_format_is_linked = False
    pl.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
    for ser, col in zip(pl.series, ("9AA3AD", ORANGE)):
        ser.format.fill.solid()
        ser.format.fill.fore_color.rgb = rgb(col)
    ch.value_axis.has_major_gridlines = True
    ch.value_axis.major_gridlines.format.line.color.rgb = rgb("E1E4E8")
    table(s, 7.75, 1.55, 4.98, [["개선 항목", "1차 (v1)", "개선 (v2)"],
                                 ["표시 불량 출처", "포함", "2곳 제외"],
                                 ["학습용 사진", "4,403장", "16,332장"],
                                 ["적은 결함", "그대로", "반복 학습 (최대 6배)"],
                                 ["판정 화면", "결함명 박스", "번호 · 색 · 위치 좌표"]],
          [0.34, 0.26, 0.4], size=12, row_h=0.55)
    box(s, 7.75, 4.55, 4.98, 2.3, fill=LIGHT)
    text(s, 8.0, 4.75, 4.5, 2.0, [[("현재 상태", {"bold": True, "color": ORANGE_T, "size": 16})],
                                  "데이터와 코드 준비 완료. Colab에서 v2 재학습 진행 중이며, 끝나면 v1과 같은 방법으로 비교합니다.",
                                  [("학습용 사진에는 변형 사본과 반복 사진이 포함됩니다.", {"color": MUTED, "size": 11})]],
         size=13, spacing=1.35, after=8)

    # 25 기대효과 --------------------------------------------------------
    s = d.slide("06 · 기대효과", "현장에서 기대할 수 있는 효과", bg=LIGHT,
                notes="AI가 사람을 대신하기보다, 1차 선별과 기록을 맡아 검사자를 돕는 도구로 쓰는 것이 현실적입니다.")
    eff = [("판정 기준 통일", "검사자가 달라도 같은 기준으로 1차 판정, 숙련도 차이를 줄임", BLUE),
           ("빠른 1차 선별", "폴더째 넣어 결함 의심 사진을 먼저 골라내고, 사람은 그 사진에 집중", ORANGE),
           ("기록과 추적", "결함 위치가 표시된 이미지를 저장해 보고서 · 이력 관리에 활용", DARK),
           ("교육 · 확장", "초보 검사자의 결함 학습 보조, 현장 사진을 더해 정확도 향상", BLUE)]
    for i, (t, sub, col) in enumerate(eff):
        x, y = 0.6 + (i % 2) * 6.15, 1.65 + (i // 2) * 2.6
        box(s, x, y, 5.98, 2.35, fill=WHITE)
        circle_num(s, x + 0.35, y + 0.4, 0.75, str(i + 1), fill=col, size=20)
        text(s, x + 1.4, y + 0.42, 4.3, 0.45, t, size=20, bold=True, color=DARK)
        text(s, x + 1.4, y + 1.0, 4.3, 1.1, sub, size=14, color=BODY, spacing=1.35)

    # 26 요약 · 느낀 점 ---------------------------------------------------
    s = d.slide("07 · 프로젝트 요약", "한 장 요약",
                notes="프로젝트 전체를 다섯 줄로 요약했습니다. 오른쪽은 이 프로젝트를 한 문장으로 줄인 소감입니다.")
    rows = [("무엇을", "용접 사진 속 결함 9종의 종류와 위치를 찾는 AI 판정 프로그램"),
            ("어떻게", "공개 데이터 15개를 9종으로 통일 → YOLO11s를 Colab GPU로 학습"),
            ("결과", "위치 점수 60.9%, 6종은 판정 정확도 78~97%, 판정 프로그램 완성"),
            ("한계", "오버랩 · 용입부족 · 기공은 데이터 부족, 처음 보는 촬영 환경에 약함"),
            ("다음", "v2 재학습, 실제 현장 사진 수집 · 라벨링 후 추가 학습")]
    for i, (k, v) in enumerate(rows):
        y = 1.65 + i * 1.03
        ln = s.shapes.add_connector(1, Inches(0.6), Inches(y), Inches(7.5), Inches(y))
        ln.line.color.rgb = rgb(DARK if i == 0 else LINE)
        ln.line.width = Pt(1.5 if i == 0 else 0.75)
        text(s, 0.6, y + 0.22, 1.3, 0.45, k, size=16, bold=True, color=ORANGE_T)
        text(s, 1.95, y + 0.2, 5.55, 0.8, v, size=14, color=BODY, spacing=1.25)
    ln = s.shapes.add_connector(1, Inches(0.6), Inches(6.8), Inches(7.5), Inches(6.8))
    ln.line.color.rgb = rgb(DARK)
    ln.line.width = Pt(1.5)
    box(s, 7.85, 1.65, 4.88, 5.15, fill=DARK)
    text(s, 8.2, 1.9, 4.2, 0.45, "한 줄 소감", size=18, bold=True, color=ORANGE)
    text(s, 8.2, 2.6, 4.25, 2.6, [
        [("“테스트 점수 90%에 기뻐했던 날, ", {}), ("현장 사진 앞에서 0%", {"color": ORANGE}),
         ("를 보고 데이터의 무게를 배웠습니다.”", {})]],
         size=20, bold=True, color=WHITE, spacing=1.45)
    text(s, 8.2, 5.6, 4.25, 0.9, "어떤 어려움이 있었고 어떻게 풀었는지, 그리고 그 과정에서 느낀 점을 다음 장에 담았습니다.",
         size=12, color=SOFT, spacing=1.35)

    # 27~28 힘들었던 점과 해결 -------------------------------------------
    def struggle_slide(no, title, pairs, notes):
        s = d.slide(f"07 · 프로젝트 요약 · 어려움과 해결 {no}", title, notes=notes)
        text(s, 0.6, 1.5, 5.6, 0.35, "힘들었던 점", size=14, bold=True, color=ORANGE_T)
        text(s, 6.95, 1.5, 5.8, 0.35, "이렇게 해결했습니다", size=14, bold=True, color=BLUE)
        for i, (pt, pd, st, sd) in enumerate(pairs):
            y = 1.95 + i * 1.65
            box(s, 0.6, y, 5.75, 1.45, fill="FBE9DD")
            text(s, 0.85, y + 0.17, 5.3, 0.4, pt, size=15, bold=True, color=DARK)
            text(s, 0.85, y + 0.6, 5.3, 0.8, pd, size=12, color=BODY, spacing=1.3)
            box(s, 6.45, y + 0.53, 0.35, 0.4, fill=ORANGE, shape=MSO_SHAPE.CHEVRON)
            box(s, 6.95, y, 5.78, 1.45, fill="E3ECF4")
            text(s, 7.2, y + 0.17, 5.35, 0.4, st, size=15, bold=True, color=DARK)
            text(s, 7.2, y + 0.6, 5.35, 0.8, sd, size=12, color=BODY, spacing=1.3)

    struggle_slide("①", "데이터와의 씨름", [
        ("공개 데이터마다 결함 이름이 달랐다",
         "24개 데이터셋을 열어 보니 같은 스패터도 Spatters · Splatter, 언더컷은 중국어 ‘咬边’으로 적혀 있었습니다.",
         "이름 바꾸기 표 + 눈으로 검수",
         "데이터별로 원래 이름을 9종에 연결하는 표를 만들고, 결함 부위를 잘라 한 장씩 확인했습니다."),
        ("용입부족 외관 사진이 어디에도 없었다",
         "9종 중 하나인데 겉에서 찍은 공개 사진을 끝내 찾지 못했습니다.",
         "대안 4가지를 비교해 X-ray로 대체",
         "용접 중 영상, X-ray, 비슷한 결함 대체, 비워 두기를 비교해 X-ray를 쓰고, 한계는 결과에 그대로 밝혔습니다."),
        ("테스트 90%인데 현장 사진은 0%",
         "점수만 보고 끝났다고 생각했는데, 휴대폰으로 찍은 현장 사진에서는 결함을 하나도 찾지 못했습니다.",
         "출처별 재검증으로 원인 추적",
         "결함 표시가 엉뚱한 곳에 그려진 데이터를 찾아 2곳을 빼고, 적은 결함은 반복 학습시키는 v2를 만들었습니다.")],
        "가장 시간이 많이 든 부분은 모델이 아니라 데이터였습니다. 특히 테스트 점수와 실제 사진의 차이를 발견한 순간이 프로젝트의 방향을 바꿨습니다.")

    struggle_slide("②", "학습 환경과의 씨름", [
        ("내 PC로는 학습에 13시간",
         "GPU 메모리 4GB인 GTX 1650으로는 학습 한 번에 13분, 전체 13시간이 걸리는 속도였습니다.",
         "가벼운 모델 시험 후 Colab GPU로 전환",
         "더 가벼운 모델로 속도를 확인한 뒤, 학습은 Colab T4 GPU에서 하고 PC는 판정 프로그램 실행에 썼습니다."),
        ("데이터 업로드 실패, 평가 중 메모리 초과",
         "Colab에 데이터를 올리지 못했고, 평가 단계에서는 GPU 메모리 11GB를 한꺼번에 요구하는 오류가 났습니다.",
         "노트북 구조를 바꾸고 나눠서 처리",
         "노트북이 Roboflow에서 직접 데이터를 만들도록 바꾸고, 평가는 사진을 16장씩 나눠 처리하게 고쳤습니다."),
        ("입력창 하나를 놓쳐 5시간, 그리고 GPU 소진",
         "키 입력창을 못 보고 5시간을 기다렸고, 그사이 무료 GPU 사용량이 바닥나 학습이 멈췄습니다.",
         "끊겨도 이어지는 학습 구조",
         "키 입력을 맨 앞으로 옮기고, 학습 기록을 매번 Drive에 저장해 끊겨도 그 지점부터 이어서 학습하게 했습니다.")],
        "작은 실수와 환경의 제약이 반복됐지만, 그때마다 같은 문제가 다시 생기지 않도록 구조를 바꿨습니다.")

    # 29 느낀 점 ---------------------------------------------------------
    s = d.slide("07 · 프로젝트 요약 · 느낀 점", "느낀 점", bg=DARK,
                notes="이 프로젝트를 하며 가장 크게 느낀 네 가지입니다.")
    text(s, 0.6, 1.5, 12.1, 0.8, [[("“숫자가 좋을 때보다, ", {}), ("숫자를 의심했을 때", {"color": ORANGE}),
                                   (" 더 많이 배웠습니다.”", {})]], size=26, bold=True, color=WHITE)
    feel = [("기뻤던 날, 무너졌던 날",
             "균열 90%, 언더필 97%라는 숫자를 처음 봤을 때 정말 뿌듯했습니다. 그런데 휴대폰으로 찍은 현장 사진을 넣자 "
             "화면에는 ‘결함 미검출’만 떴습니다. 그 허탈함이 이 프로젝트에서 가장 크게 배운 순간이었습니다."),
            ("AI는 보여 준 만큼만 배운다",
             "모델을 탓하고 싶었지만 사진을 한 장씩 다시 열어 보니, 결함 표시가 엉뚱한 곳에 그려진 데이터가 있었습니다. "
             "좋은 AI는 좋은 코드보다 정직한 데이터에서 나온다는 것을 몸으로 이해했습니다."),
            ("멈춰도 다시 이어 가는 법",
             "입력창 하나를 놓쳐 5시간을 기다리고, GPU가 바닥나 학습이 멈춘 날은 정말 속상했습니다. "
             "하지만 그 덕분에 끊겨도 이어지는 구조를 만들었고, 실수가 시스템을 단단하게 만든다는 것을 배웠습니다."),
            ("현장의 눈에 대한 존경",
             "9가지 결함을 하나하나 구분하며, 매일 눈으로 이 결함을 가려내는 검사자들의 경험이 얼마나 대단한지 새삼 느꼈습니다. "
             "이 프로그램이 그분들을 대신하기보다, 지친 눈을 한 번 더 받쳐 주는 도구가 되길 바랍니다.")]
    for i, (t, body) in enumerate(feel):
        x, y = 0.6 + (i % 2) * 6.15, 2.5 + (i // 2) * 2.2
        box(s, x, y, 5.98, 2.0, fill="22303D")
        text(s, x + 0.3, y + 0.2, 5.4, 0.4, t, size=15, bold=True, color=ORANGE)
        text(s, x + 0.3, y + 0.65, 5.45, 1.3, body, size=12, color=SOFT, spacing=1.35)

    # 27 마무리 ----------------------------------------------------------
    s = d.slide(bg=DARK, footer=False, notes=(
        "마무리: 사진 한 장으로 시작한 이 AI가 현장 검사자의 든든한 두 번째 눈이 될 수 있도록, "
        "v2 재학습과 실제 현장 사진 학습으로 계속 발전시키겠습니다."))
    text(s, 0.8, 1.6, 11.5, 0.4, "CLOSING", size=14, bold=True, color=ORANGE)
    text(s, 0.8, 2.1, 11.7, 2.0, [[("사진 한 장으로 시작한 AI가", {})],
                                  [("현장 검사자의 ", {}), ("든든한 두 번째 눈", {"color": ORANGE}), ("이 되도록", {})]],
         size=36, bold=True, color=WHITE, spacing=1.25)
    text(s, 0.8, 4.2, 11.5, 0.9, "v2 재학습과 실제 현장 사진 학습으로 정확도를 높여, 검사 현장에서 바로 쓰이는 도구로 계속 발전시키겠습니다.",
         size=20, color=SOFT, spacing=1.35)
    text(s, 0.8, 5.6, 11.5, 0.5, "감사합니다", size=26, bold=True, color=WHITE)
    text(s, 0.8, 6.5, 11.5, 0.35, f"용접 결함 판정 AI · {AUTHOR} · {PERIOD}", size=12, color=SOFT)

    # 부록: 재검증 출처 ---------------------------------------------------
    s = d.slide("부록", "출처별 재검증에 사용한 데이터셋 (Roboflow Universe)",
                notes="23번 슬라이드의 출처 A~I와 주황 3곳의 실제 데이터셋 이름입니다. 각 출처의 원본 사진 40장씩을 1차 모델로 다시 판정했습니다.")
    table(s, 0.6, 1.55, 12.13, [["보고서 표시", "데이터셋 (작성자 / 프로젝트)", "찾은 비율", "결함 표시 있는 표본"],
                                 ["출처 A", "oran-ai / visual-weld-inspector", "100%", "11장"],
                                 ["출처 B", "weld-qwzyj / welding-defects-detection", "92%", "39장"],
                                 ["출처 C", "weld-defect-detection-onlal / weld-surface-defect-detection", "88%", "17장"],
                                 ["출처 D", "space-be2wb / final-welding-dataset", "82%", "28장"],
                                 ["출처 E", "ai-vision-system / welding-defects", "77%", "13장"],
                                 ["출처 F", "delvin-9qaxw / weld", "77%", "39장"],
                                 ["출처 G", "trithis-workspace / welding-defects", "72%", "40장"],
                                 ["출처 H", "welddefectdetection / welddefectdetection", "71%", "34장"],
                                 ["출처 I", "welding-qdnjc / m", "50%", "40장"],
                                 ["변형 심한 사진", "mubessirul-ummah / afteraugmentasiwelddefect", "24%", "34장"],
                                 ["낯선 스타일", "weldparts / welding_detect", "13%", "15장"],
                                 ["휴대폰 현장 사진", "weld-tk71z / weld51", "0%", "40장"]],
          [0.17, 0.53, 0.12, 0.18], size=12, row_h=0.38, highlight=(10, 11, 12))
    text(s, 0.6, 6.6, 12.1, 0.2,
         "※ 원본 사진에는 학습에 쓴 사진이 일부 포함됨 · X-ray 사진 소스 3곳은 결함 표시 있는 표본이 0~2장이라 제외 · 출처: universe.roboflow.com",
         size=10, color=MUTED)

    d.save()


if __name__ == "__main__":
    build()
