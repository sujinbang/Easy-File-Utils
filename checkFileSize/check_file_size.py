import os
import re
import csv
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


# ─────────────────────────────────────────────
#  핵심 로직
# ─────────────────────────────────────────────
def scan_dir(path):
    """파일 수 + 용량 동시 계산 (반복 스택)."""
    total_size = 0
    total_files = 0
    stack = [path]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        if entry.is_file(follow_symlinks=False):
                            total_size += entry.stat(follow_symlinks=False).st_size
                            total_files += 1
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except OSError:
                        pass
        except PermissionError:
            pass
    return total_size, total_files


def format_size(size):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


# ─────────────────────────────────────────────
#  GUI 애플리케이션
# ─────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📁 폴더 용량 비교 도구")
        self.resizable(True, True)
        self.minsize(820, 560)

        # 색상 팔레트
        BG     = "#1e1e2e"
        PANEL  = "#2a2a3e"
        ACCENT = "#7c6af7"
        FG     = "#cdd6f4"
        MUTED  = "#6c7086"
        GREEN  = "#a6e3a1"
        RED    = "#f38ba8"
        ENTRY  = "#313244"

        self.configure(bg=BG)

        style = ttk.Style(self)
        style.theme_use("clam")

        # Treeview
        style.configure("Treeview",
                        background=PANEL, foreground=FG,
                        fieldbackground=PANEL, rowheight=26,
                        font=("Malgun Gothic", 10))
        style.configure("Treeview.Heading",
                        background=ACCENT, foreground="white",
                        font=("Malgun Gothic", 10, "bold"))
        style.map("Treeview", background=[("selected", "#45475a")])

        # Progressbar
        style.configure("TProgressbar",
                        troughcolor=PANEL, background=ACCENT,
                        thickness=6)

        # ── 색 변수를 인스턴스에 저장 (콜백에서 사용)
        self._colors = dict(BG=BG, PANEL=PANEL, ACCENT=ACCENT,
                            FG=FG, MUTED=MUTED, GREEN=GREEN, RED=RED, ENTRY=ENTRY)

        self._build_ui(BG, PANEL, ACCENT, FG, MUTED, GREEN, RED, ENTRY)

        # 행 데이터 저장용
        self._rows: list[dict] = []           # {"src","dest","src_s","src_c","dest_s","dest_c"}

    # ── UI 구성 ──────────────────────────────
    def _build_ui(self, BG, PANEL, ACCENT, FG, MUTED, GREEN, RED, ENTRY):
        pad = dict(padx=12, pady=6)

        # ── 제목 ─────────────────────────────
        tk.Label(self, text="📁  폴더 용량 비교 도구",
                 bg=BG, fg=ACCENT,
                 font=("Malgun Gothic", 15, "bold")).pack(pady=(14, 2))
        tk.Label(self, text="엑셀 파일을 불러오거나 경로를 직접 입력해 비교하세요.",
                 bg=BG, fg=MUTED,
                 font=("Malgun Gothic", 9)).pack(pady=(0, 10))

        # ── 엑셀 불러오기 ────────────────────
        frame_excel = tk.Frame(self, bg=PANEL, bd=0, relief="flat")
        frame_excel.pack(fill="x", padx=14, pady=(0, 6))

        tk.Label(frame_excel, text="엑셀 파일 (src / dest 열 포함)",
                 bg=PANEL, fg=MUTED,
                 font=("Malgun Gothic", 9)).pack(anchor="w", padx=10, pady=(8, 2))

        row_xl = tk.Frame(frame_excel, bg=PANEL)
        row_xl.pack(fill="x", padx=10, pady=(0, 8))

        self._excel_var = tk.StringVar()
        tk.Entry(row_xl, textvariable=self._excel_var,
                 bg=ENTRY, fg=FG, insertbackground=FG,
                 relief="flat", font=("Malgun Gothic", 10),
                 state="readonly").pack(side="left", fill="x", expand=True, ipady=5)

        tk.Button(row_xl, text="📂 찾아보기",
                  bg=ACCENT, fg="white", relief="flat",
                  font=("Malgun Gothic", 9, "bold"), cursor="hand2",
                  command=self._browse_excel,
                  activebackground="#6a59d1", activeforeground="white",
                  padx=10).pack(side="left", padx=(6, 0))

        tk.Button(row_xl, text="불러오기",
                  bg="#45475a", fg=FG, relief="flat",
                  font=("Malgun Gothic", 9), cursor="hand2",
                  command=self._load_excel,
                  activebackground="#585b70", activeforeground=FG,
                  padx=10).pack(side="left", padx=(4, 0))

        # ── 직접 입력 ────────────────────────
        frame_manual = tk.Frame(self, bg=PANEL, bd=0, relief="flat")
        frame_manual.pack(fill="x", padx=14, pady=(0, 8))

        tk.Label(frame_manual, text="직접 입력",
                 bg=PANEL, fg=MUTED,
                 font=("Malgun Gothic", 9)).grid(
                     row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 2))

        lbl_kw = dict(bg=PANEL, fg=FG, font=("Malgun Gothic", 9))
        ent_kw = dict(bg=ENTRY, fg=FG, insertbackground=FG,
                      relief="flat", font=("Malgun Gothic", 10))

        tk.Label(frame_manual, text="원본(src):", **lbl_kw).grid(
            row=1, column=0, padx=(10, 4), pady=4, sticky="e")
        self._src_var = tk.StringVar()
        tk.Entry(frame_manual, textvariable=self._src_var, width=46, **ent_kw).grid(
            row=1, column=1, ipady=4, sticky="ew")
        tk.Button(frame_manual, text="폴더",
                  bg="#45475a", fg=FG, relief="flat", cursor="hand2",
                  font=("Malgun Gothic", 8),
                  command=lambda: self._pick_folder(self._src_var),
                  activebackground="#585b70", activeforeground=FG,
                  padx=6).grid(row=1, column=2, padx=4)

        tk.Label(frame_manual, text="복사(dest):", **lbl_kw).grid(
            row=2, column=0, padx=(10, 4), pady=4, sticky="e")
        self._dest_var = tk.StringVar()
        tk.Entry(frame_manual, textvariable=self._dest_var, width=46, **ent_kw).grid(
            row=2, column=1, ipady=4, sticky="ew")
        tk.Button(frame_manual, text="폴더",
                  bg="#45475a", fg=FG, relief="flat", cursor="hand2",
                  font=("Malgun Gothic", 8),
                  command=lambda: self._pick_folder(self._dest_var),
                  activebackground="#585b70", activeforeground=FG,
                  padx=6).grid(row=2, column=2, padx=4)
        tk.Button(frame_manual, text="➕ 행 추가",
                  bg="#45475a", fg=FG, relief="flat", cursor="hand2",
                  font=("Malgun Gothic", 9),
                  command=self._add_manual_row,
                  activebackground="#585b70", activeforeground=FG,
                  padx=8).grid(row=2, column=3, padx=(4, 10))

        frame_manual.columnconfigure(1, weight=1)

        # ── 실행 버튼 행 ─────────────────────
        frame_btn = tk.Frame(self, bg=BG)
        frame_btn.pack(fill="x", padx=14, pady=(2, 6))

        self._btn_run = tk.Button(
            frame_btn, text="▶  비교 시작",
            bg=ACCENT, fg="white", relief="flat",
            font=("Malgun Gothic", 11, "bold"), cursor="hand2",
            command=self._run,
            activebackground="#6a59d1", activeforeground="white",
            padx=18, pady=6)
        self._btn_run.pack(side="left")

        tk.Button(frame_btn, text="🗑 목록 초기화",
                  bg="#45475a", fg=FG, relief="flat",
                  font=("Malgun Gothic", 9), cursor="hand2",
                  command=self._clear,
                  activebackground="#585b70", activeforeground=FG,
                  padx=10, pady=6).pack(side="left", padx=(6, 0))

        self._btn_csv = tk.Button(
            frame_btn, text="💾 CSV 저장",
            bg="#45475a", fg=FG, relief="flat",
            font=("Malgun Gothic", 9), cursor="hand2",
            command=self._save_csv, state="disabled",
            activebackground="#585b70", activeforeground=FG,
            padx=10, pady=6)
        self._btn_csv.pack(side="left", padx=(6, 0))

        # ── 진행바 ───────────────────────────
        self._pb = ttk.Progressbar(self, mode="indeterminate")
        self._pb.pack(fill="x", padx=14, pady=(0, 6))

        # ── 결과 테이블 ──────────────────────
        frame_tree = tk.Frame(self, bg=BG)
        frame_tree.pack(fill="both", expand=True, padx=14, pady=(0, 8))

        cols = ("번호", "원본 경로", "복사 경로",
                "원본 파일수", "복사 파일수", "파일수",
                "원본 용량", "복사 용량", "용량")
        self._tree = ttk.Treeview(frame_tree, columns=cols, show="headings")

        widths = [40, 220, 220, 90, 90, 70, 110, 110, 70]
        for col, w in zip(cols, widths):
            self._tree.heading(col, text=col)
            self._tree.column(col, width=w, minwidth=40,
                              anchor="center" if w <= 110 else "w")

        self._tree.tag_configure("ok",   background="#1e3a2f", foreground=GREEN)
        self._tree.tag_configure("fail", background="#3b1f27", foreground=RED)
        self._tree.tag_configure("row0", background=PANEL)
        self._tree.tag_configure("row1", background="#252535")

        sb_y = ttk.Scrollbar(frame_tree, orient="vertical",   command=self._tree.yview)
        sb_x = ttk.Scrollbar(frame_tree, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        sb_y.pack(side="right",  fill="y")
        sb_x.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        # ── 상태바 ───────────────────────────
        self._status = tk.StringVar(value="대기 중…")
        tk.Label(self, textvariable=self._status,
                 bg=BG, fg=MUTED,
                 font=("Malgun Gothic", 9),
                 anchor="w").pack(fill="x", padx=14, pady=(0, 8))

    # ── 이벤트 핸들러 ────────────────────────
    def _browse_excel(self):
        path = filedialog.askopenfilename(
            title="엑셀 파일 선택",
            filetypes=[("Excel 파일", "*.xlsx *.xls"), ("모든 파일", "*.*")])
        if path:
            self._excel_var.set(path)

    def _pick_folder(self, var: tk.StringVar):
        path = filedialog.askdirectory(title="폴더 선택")
        if path:
            var.set(path)

    def _load_excel(self):
        if not HAS_PANDAS:
            messagebox.showerror("오류", "pandas 라이브러리가 설치되어 있지 않습니다.\npip install pandas openpyxl")
            return
        path = self._excel_var.get().strip()
        if not path:
            messagebox.showwarning("경고", "엑셀 파일 경로를 먼저 선택하세요.")
            return
        try:
            df = pd.read_excel(path)
            loaded = 0
            for _, row in df.iterrows():
                src  = re.sub(r'[\u200e\u200f\u202a-\u202e]', '', str(row.get("src",  "")).strip().replace('"', ''))
                dest = re.sub(r'[\u200e\u200f\u202a-\u202e]', '', str(row.get("dest", "")).strip().replace('"', ''))
                if src and dest and src != "nan" and dest != "nan":
                    self._rows.append({"src": src, "dest": dest,
                                       "src_s": None, "src_c": None,
                                       "dest_s": None, "dest_c": None})
                    loaded += 1
            self._status.set(f"엑셀에서 {loaded}행 불러옴. ▶ 비교 시작을 눌러 계산하세요.")
            self._refresh_tree_pending()
        except Exception as e:
            messagebox.showerror("오류", f"엑셀 읽기 실패:\n{e}")

    def _add_manual_row(self):
        src  = re.sub(r'[\u200e\u200f\u202a-\u202e]', '', self._src_var.get().strip())
        dest = re.sub(r'[\u200e\u200f\u202a-\u202e]', '', self._dest_var.get().strip())
        if not src or not dest:
            messagebox.showwarning("경고", "원본·복사 경로를 모두 입력하세요.")
            return
        self._rows.append({"src": src, "dest": dest,
                           "src_s": None, "src_c": None,
                           "dest_s": None, "dest_c": None})
        self._src_var.set("")
        self._dest_var.set("")
        self._refresh_tree_pending()
        self._status.set(f"행 추가됨 (총 {len(self._rows)}행). ▶ 비교 시작을 눌러 계산하세요.")

    def _clear(self):
        self._rows.clear()
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._btn_csv.config(state="disabled")
        self._status.set("목록 초기화됨.")

    def _refresh_tree_pending(self):
        """결과 없이 경로만 표시."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        for i, r in enumerate(self._rows):
            tag = "row0" if i % 2 == 0 else "row1"
            self._tree.insert("", "end", iid=str(i),
                              values=(i + 1, r["src"], r["dest"],
                                      "-", "-", "-", "-", "-", "-"),
                              tags=(tag,))

    def _run(self):
        if not self._rows:
            messagebox.showwarning("경고", "비교할 경로가 없습니다. 엑셀을 불러오거나 직접 입력하세요.")
            return
        self._btn_run.config(state="disabled")
        self._btn_csv.config(state="disabled")
        self._pb.start(12)
        self._status.set("비교 중…")
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        GREEN = self._colors["GREEN"]
        RED   = self._colors["RED"]

        total = len(self._rows)
        for i, r in enumerate(self._rows):
            self.after(0, lambda i=i: self._status.set(
                f"처리 중  {i+1} / {total}  ─  {self._rows[i]['src']}"))
            try:
                with ThreadPoolExecutor(max_workers=2) as ex:
                    fs = ex.submit(scan_dir, r["src"])
                    fd = ex.submit(scan_dir, r["dest"])
                    r["src_s"],  r["src_c"]  = fs.result()
                    r["dest_s"], r["dest_c"] = fd.result()
            except Exception as e:
                r["src_s"] = r["src_c"] = r["dest_s"] = r["dest_c"] = -1
                self.after(0, lambda e=e: self._status.set(f"오류: {e}"))

        self.after(0, self._finish)

    def _finish(self):
        self._pb.stop()
        self._btn_run.config(state="normal")

        for item in self._tree.get_children():
            self._tree.delete(item)

        ok_cnt = fail_cnt = 0
        for i, r in enumerate(self._rows):
            ss, sc = r["src_s"],  r["src_c"]
            ds, dc = r["dest_s"], r["dest_c"]

            if ss is None or ss == -1:
                size_ok = count_ok = False
                vals = (i+1, r["src"], r["dest"], "오류", "오류", "❌", "오류", "오류", "❌")
                tag = "fail"
            else:
                size_ok  = (ss == ds)
                count_ok = (sc == dc)
                s_sym  = "✅" if size_ok  else "❌"
                c_sym  = "✅" if count_ok else "❌"
                vals = (i+1,
                        r["src"], r["dest"],
                        f"{sc:,}", f"{dc:,}", c_sym,
                        format_size(ss), format_size(ds), s_sym)
                tag = "ok" if (size_ok and count_ok) else "fail"

            if tag == "ok":
                ok_cnt += 1
            else:
                fail_cnt += 1

            self._tree.insert("", "end", iid=str(i), values=vals, tags=(tag,))

        total = len(self._rows)
        self._status.set(
            f"완료  ─  총 {total}행 / ✅ 일치 {ok_cnt}행 / ❌ 불일치 {fail_cnt}행")

        if any(r["src_s"] is not None for r in self._rows):
            self._btn_csv.config(state="normal")

    def _save_csv(self):
        now = datetime.now()
        init_name = f"비교결과_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        path = filedialog.asksaveasfilename(
            title="CSV 저장 위치",
            defaultextension=".csv",
            initialfile=init_name,
            filetypes=[("CSV 파일", "*.csv"), ("모든 파일", "*.*")])
        if not path:
            return

        header = ["번호", "원본 경로", "복사 경로",
                  "원본 파일수", "복사 파일수", "파일수 일치",
                  "원본 용량(Bytes)", "복사 용량(Bytes)",
                  "원본 용량", "복사 용량", "용량 일치", "실행일시"]
        ts = now.strftime("%Y-%m-%d %H:%M:%S")

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(header)
                for i, r in enumerate(self._rows):
                    ss, sc = r["src_s"], r["src_c"]
                    ds, dc = r["dest_s"], r["dest_c"]
                    if ss is None or ss == -1:
                        w.writerow([i+1, r["src"], r["dest"],
                                    "오류","오류","❌","오류","오류","오류","오류","❌", ts])
                    else:
                        w.writerow([i+1, r["src"], r["dest"],
                                    sc, dc,
                                    "일치" if sc == dc else "불일치",
                                    ss, ds,
                                    format_size(ss), format_size(ds),
                                    "일치" if ss == ds else "불일치",
                                    ts])
            messagebox.showinfo("저장 완료", f"CSV 파일이 저장되었습니다.\n{path}")
        except Exception as e:
            messagebox.showerror("저장 오류", str(e))


# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()