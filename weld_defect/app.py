"""담당자용 판정 프로그램 (tkinter GUI)."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from .config import CLASSES, Config
from .detector import DefectDetector, Verdict

FILETYPES = [("이미지", "*.jpg *.jpeg *.png *.bmp *.webp"), ("모든 파일", "*.*")]


class DefectApp:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.root = tk.Tk()
        self.root.title("용접 결함 판정 프로그램")
        self.root.geometry("1200x780")
        self.detector = None
        self.results = []      # [(Verdict, PIL.Image)]
        self._photo = None
        self._build()
        self.root.after(100, self._load_model)

    # ---------- UI ----------
    def _build(self):
        bar = ttk.Frame(self.root, padding=6)
        bar.pack(fill="x")
        ttk.Button(bar, text="사진 열기", command=self.open_images).pack(side="left")
        ttk.Button(bar, text="폴더 열기", command=self.open_folder).pack(side="left", padx=4)
        ttk.Button(bar, text="결과 이미지 저장", command=self.save_current).pack(side="left")
        ttk.Label(bar, text="신뢰도 기준").pack(side="left", padx=(20, 4))
        self.conf_var = tk.DoubleVar(value=self.cfg.conf)
        ttk.Spinbox(bar, from_=0.05, to=0.95, increment=0.05, width=5,
                    textvariable=self.conf_var).pack(side="left")
        self.status = ttk.Label(bar, text="모델 불러오는 중...")
        self.status.pack(side="right")

        body = ttk.PanedWindow(self.root, orient="horizontal")
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, padding=4)
        ttk.Label(left, text="판정 목록").pack(anchor="w")
        self.listbox = tk.Listbox(left, width=42, font=("맑은 고딕", 10))
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self._show_selected())
        body.add(left, weight=1)

        right = ttk.Frame(body, padding=4)
        # 결과 칸을 먼저 아래에 고정해야 큰 사진이 결과 글을 화면 밖으로 밀어내지 않음
        self.result_text = tk.Text(right, height=10, font=("맑은 고딕", 11))
        self.result_text.pack(side="bottom", fill="x", pady=(6, 0))
        self.canvas = tk.Label(right, bg="#222")
        self.canvas.pack(fill="both", expand=True)
        body.add(right, weight=4)

        legend = ttk.Frame(self.root, padding=4)
        legend.pack(fill="x")
        ttk.Label(legend, text="판정 결함: " + " · ".join(c.ko for c in CLASSES),
                  foreground="#555").pack(anchor="w")
        self.canvas.bind("<Configure>", lambda e: self._show_selected())

    def _load_model(self):
        try:
            self.detector = DefectDetector(self.cfg)
            self.status.config(text=f"모델: {self.cfg.best_model.name}")
        except Exception as e:
            self.status.config(text="모델 없음")
            messagebox.showerror("모델 오류", str(e))

    # ---------- 동작 ----------
    def open_images(self):
        paths = filedialog.askopenfilenames(title="판정할 사진 선택", filetypes=FILETYPES)
        self.run(paths)

    def open_folder(self):
        d = filedialog.askdirectory(title="사진 폴더 선택")
        if d:
            exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
            self.run(sorted(str(p) for p in Path(d).iterdir() if p.suffix.lower() in exts))

    def run(self, paths):
        if not paths or self.detector is None:
            return
        self.cfg.conf = float(self.conf_var.get())
        for i, p in enumerate(paths, 1):
            self.status.config(text=f"판정 중 {i}/{len(paths)}")
            self.root.update_idletasks()
            try:
                v = self.detector.predict(p)
            except Exception as e:
                messagebox.showerror("판정 오류", f"{p}\n{e}")
                continue
            self.results.append((v, self.detector.annotate(v)))
            head = v.main.ko + f" {v.main.conf:.0%}" if v.is_defect else "결함 없음"
            self.listbox.insert("end", f"{Path(p).name}  →  {head}")
        self.status.config(text=f"완료 ({len(self.results)}장)")
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set("end")
        self.listbox.see("end")
        self._show_selected()

    def _current(self):
        sel = self.listbox.curselection()
        return self.results[sel[0]] if sel else None

    def _show_selected(self):
        cur = self._current()
        if not cur:
            return
        v, img = cur
        w, h = max(self.canvas.winfo_width(), 100), max(self.canvas.winfo_height(), 100)
        view = img.copy()
        view.thumbnail((w, h))
        self._photo = ImageTk.PhotoImage(view)
        self.canvas.config(image=self._photo)
        self.result_text.delete("1.0", "end")
        self.result_text.insert("end", f"{v.image.name}\n{v.text()}")

    def save_current(self):
        cur = self._current()
        if not cur:
            return
        v, img = cur
        out = filedialog.asksaveasfilename(initialfile=f"{v.image.stem}_판정.jpg",
                                           defaultextension=".jpg", filetypes=[("JPEG", "*.jpg")])
        if out:
            img.save(out, quality=95)

    def mainloop(self):
        self.root.mainloop()
