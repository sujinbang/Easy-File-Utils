import pandas as pd
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import traceback


def list_folder_recursive(path):
    """
    주어진 경로를 재귀 탐색하여 모든 .xlsx 파일의 전체 경로 리스트를 반환합니다.
    만약 path가 파일이고 .xlsx로 끝난다면 해당 파일만 반환합니다.
    """
    xlsx_file_list = []

    if os.path.isfile(path):
        if path.lower().endswith('.xlsx'):
            xlsx_file_list.append(os.path.abspath(path))
        return [], xlsx_file_list

    for root, dirs, files in os.walk(path):
        for f in files:
            if f.lower().endswith('.xlsx'):
                xlsx_file_list.append(os.path.join(root, f))

    return None, xlsx_file_list


def convert_xlsx_to_csv(input_path, output_dir, sheet_name=0, encoding='utf-8', log_callback=None):
    """
    input_path가 단일 파일일 수도 있고, 폴더일 수도 있습니다.
    발견된 모든 .xlsx 파일을 읽어 output_dir에 같은 이름의 .csv로 저장합니다.

    log_callback: 선택적 함수로, 진행 로그를 받을 수 있습니다. (문자열 매개)
    """

    def log(msg):
        if log_callback:
            try:
                log_callback(msg)
            except Exception:
                # avoid logging exceptions interfering with conversion
                print('log callback error', traceback.format_exc())
        else:
            print(msg)

    if not os.path.exists(input_path):
        log(f"오류: 입력 경로 '{input_path}'이(가) 존재하지 않습니다.")
        return

    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
            log(f"출력 폴더를 생성했습니다: {output_dir}")
        except Exception as e:
            log(f"출력 폴더 생성 실패: {e}")
            return

    _, xlsx_files = list_folder_recursive(input_path)

    if len(xlsx_files) == 0:
        log("변환할 .xlsx 파일을 찾지 못했습니다.")
        return

    log(f"--- 파일 변환 시작 ({len(xlsx_files)}개 파일) ---")
    log(f"입력 경로: {input_path}")
    log(f"출력 폴더: {output_dir}")

    for path in xlsx_files:
        try:
            if not os.path.exists(path):
                log(f"오류: 입력 파일 '{path}'이(가) 존재하지 않습니다. 건너뜁니다.")
                continue

            df = pd.read_excel(path, sheet_name=sheet_name)
            log(f"'{path}' 파일의 시트 '{sheet_name}'을(를) 읽었습니다. (총 {len(df)} 행)")

            base_name = os.path.splitext(os.path.basename(path))[0]
            out_path = os.path.join(output_dir, base_name + '.csv')
            df.to_csv(out_path, index=False, encoding=encoding)
            log(f"저장: {out_path}")

        except Exception as e:
            log(f"변환 중 오류 ({path}): {e}\n" + traceback.format_exc())

    log("--- 파일 변환 완료 ---")


class XlsxToCsvGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('XLSX → CSV 변환기')
        self.geometry('700x420')

        # Input selection
        frame_top = tk.Frame(self)
        frame_top.pack(fill='x', padx=10, pady=8)

        tk.Label(frame_top, text='입력 경로 (폴더 또는 단일 .xlsx 파일):').grid(row=0, column=0, sticky='w')
        self.input_var = tk.StringVar()
        tk.Entry(frame_top, textvariable=self.input_var, width=60).grid(row=1, column=0, padx=(0,8))
        tk.Button(frame_top, text='찾기', command=self.browse_input).grid(row=1, column=1)

        tk.Label(frame_top, text='출력 폴더:').grid(row=2, column=0, sticky='w', pady=(8,0))
        self.output_var = tk.StringVar()
        tk.Entry(frame_top, textvariable=self.output_var, width=60).grid(row=3, column=0, padx=(0,8))
        tk.Button(frame_top, text='찾기', command=self.browse_output).grid(row=3, column=1)

        # Options
        frame_opts = tk.Frame(self)
        frame_opts.pack(fill='x', padx=10)
        tk.Label(frame_opts, text='시트(이름 또는 인덱스):').grid(row=0, column=0, sticky='w')
        self.sheet_var = tk.StringVar(value='0')
        tk.Entry(frame_opts, textvariable=self.sheet_var, width=12).grid(row=0, column=1, sticky='w')

        tk.Label(frame_opts, text='인코딩:').grid(row=0, column=2, sticky='w', padx=(10,0))
        self.encoding_var = tk.StringVar(value='utf-8')
        tk.Entry(frame_opts, textvariable=self.encoding_var, width=12).grid(row=0, column=3, sticky='w')

        # Buttons
        frame_btns = tk.Frame(self)
        frame_btns.pack(fill='x', padx=10, pady=(6,0))
        tk.Button(frame_btns, text='변환 시작', command=self.start_convert, bg='#4CAF50', fg='white').pack(side='left')
        tk.Button(frame_btns, text='종료', command=self.quit).pack(side='right')

        # Log area
        tk.Label(self, text='로그:').pack(anchor='w', padx=10, pady=(8,0))
        self.log_area = ScrolledText(self, height=12)
        self.log_area.pack(fill='both', expand=True, padx=10, pady=(0,10))
        self.log_area.configure(state='disabled')

        self.protocol('WM_DELETE_WINDOW', self.quit)

    def browse_input(self):
        # 먼저 사용자에게 파일 선택 또는 폴더 선택을 묻는 작은 모달 창을 띄웁니다.
        def ask_choice():
            dlg = tk.Toplevel(self)
            dlg.title('선택')
            dlg.transient(self)
            dlg.resizable(False, False)

            tk.Label(dlg, text='파일을 선택하시겠습니까, 아니면 폴더를 선택하시겠습니까?').pack(padx=16, pady=12)

            result = {'choice': None}

            def choose_file():
                result['choice'] = 'file'
                dlg.destroy()

            def choose_dir():
                result['choice'] = 'dir'
                dlg.destroy()

            def choose_cancel():
                result['choice'] = None
                dlg.destroy()

            btn_frame = tk.Frame(dlg)
            btn_frame.pack(pady=(0,12))
            tk.Button(btn_frame, text='파일 선택', width=12, command=choose_file).grid(row=0, column=0, padx=6)
            tk.Button(btn_frame, text='폴더 선택', width=12, command=choose_dir).grid(row=0, column=1, padx=6)
            tk.Button(btn_frame, text='취소', width=8, command=choose_cancel).grid(row=0, column=2, padx=6)

            # make modal
            dlg.grab_set()
            self.wait_window(dlg)
            return result['choice']

        choice = ask_choice()
        if choice == 'file':
            path = filedialog.askopenfilename(title='XLSX 파일 선택', filetypes=[('Excel files', '*.xlsx')])
            if path:
                self.input_var.set(path)
        elif choice == 'dir':
            d = filedialog.askdirectory(title='폴더 선택 (폴더 내 모든 .xlsx 변환)')
            if d:
                self.input_var.set(d)
        else:
            # 취소하거나 창을 닫은 경우 아무 동작 안함
            return

    def browse_output(self):
        d = filedialog.askdirectory(title='출력 폴더 선택')
        if d:
            self.output_var.set(d)

    def log(self, msg):
        def append():
            self.log_area.configure(state='normal')
            self.log_area.insert('end', msg + '\n')
            self.log_area.see('end')
            self.log_area.configure(state='disabled')

        self.after(0, append)

    def start_convert(self):
        input_path = self.input_var.get().strip()
        output_dir = self.output_var.get().strip()
        if not input_path:
            messagebox.showwarning('입력 필요', '변환할 파일 또는 폴더를 선택하세요.')
            return
        if not output_dir:
            messagebox.showwarning('출력 필요', '출력 폴더를 선택하세요.')
            return

        # parse sheet
        sheet_raw = self.sheet_var.get().strip()
        try:
            sheet_val = int(sheet_raw)
        except Exception:
            sheet_val = sheet_raw if sheet_raw != '' else 0

        encoding = self.encoding_var.get().strip() or 'utf-8'

        # run conversion in background
        t = threading.Thread(target=self._run_conversion_thread, args=(input_path, output_dir, sheet_val, encoding), daemon=True)
        t.start()

    def _run_conversion_thread(self, input_path, output_dir, sheet_val, encoding):
        try:
            convert_xlsx_to_csv(input_path, output_dir, sheet_name=sheet_val, encoding=encoding, log_callback=self.log)
            self.log('전체 작업이 완료되었습니다.')
        except Exception as e:
            self.log('예기치 않은 오류: ' + str(e) + '\n' + traceback.format_exc())


def main():
    app = XlsxToCsvGUI()
    app.mainloop()


if __name__ == '__main__':
    main()