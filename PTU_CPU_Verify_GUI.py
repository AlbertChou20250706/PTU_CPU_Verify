#!/usr/bin/env python3
# =============================================================================
#  PTU_CPU_Verify_GUI.py  (Albert Style, Tkinter 版, Py3.6-compatible)
#  - 零相依：只用 Python3 內建 Tkinter
#  - 跟 PTU_CPU_Verify.py 搭配：透過環境變數傳參數並啟動核心
#  - 內建常用預設：serverlab / 100% / performance / all cores
#  - 一鍵 1h / 6h / 12h / 24h；也可自訂秒數
#  - 儲存/載入上次參數（~/.ptu_cpu_verify_gui.json）
#  - 內建「檢視目前進程」：pgrep -af 'ptat|turbostat|stress-ng|yes'
# =============================================================================
import os, json, subprocess, sys, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

APP_TITLE = "PTU CPU Verify — Albert GUI (Tk)"
STATE_FILE = Path.home()/".ptu_cpu_verify_gui.json"
CORE_FILE = "PTU_CPU_Verify.py"   # 與核心同資料夾

def which(cmd):
    from shutil import which as _w
    return _w(cmd)

def run_cmd(cmd, env=None):
    return subprocess.Popen(cmd, shell=True, env=env)

def pgrep_snapshot():
    try:
        out = subprocess.check_output(
            "pgrep -af 'ptat|turbostat|stress-ng|yes'",
            shell=True,
            universal_newlines=True,  # Py3.6 相容
            stderr=subprocess.STDOUT
        )
        return out.strip()
    except subprocess.CalledProcessError:
        return ""

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}

def save_state(d):
    try:
        STATE_FILE.write_text(json.dumps(d, indent=2))
    except Exception:
        pass

def ensure_root():
    if os.geteuid() != 0:
        messagebox.showerror("Need root", "請用 root 執行（sudo -E python3 PTU_CPU_Verify_GUI.py）。")
        return False
    return True

def core_path():
    here = Path(__file__).resolve().parent
    p = here/CORE_FILE
    if p.exists():
        return str(p)
    w = which(CORE_FILE)
    return w or str(p)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x520")
        self.minsize(720, 500)

        self.state = load_state()

        self.var_log = tk.StringVar(value=self.state.get("LOG_BASE", "/root/Documents/PTU_Linux_Rev4.8.0/PtuLog"))
        self.var_ptu = tk.StringVar(value=self.state.get("PTU_BIN", ""))
        self.var_duration = tk.StringVar(value=str(self.state.get("DURATION", 600)))
        self.var_load = tk.StringVar(value=str(self.state.get("LOAD", 100)))
        self.var_governor = tk.StringVar(value=self.state.get("GOVERNOR", "performance"))
        self.var_cores = tk.StringVar(value=self.state.get("CORES", "all"))
        self.var_profile = tk.StringVar(value=self.state.get("PROFILE", "serverlab"))
        self.var_template = tk.StringVar(value=self.state.get("PTU_TEMPLATE", '"{PTU_BIN}" -ct 3 -cp {LOAD} -t {DURATION} -y -q'))

        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        r = 0
        ttk.Label(frm, text="Log base folder").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_log, width=60).grid(row=r, column=1, sticky="we", padx=8)
        ttk.Button(frm, text="選擇…", command=self.pick_log).grid(row=r, column=2, sticky="e")
        r += 1

        ttk.Label(frm, text="PTU/PTAT binary").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_ptu, width=60).grid(row=r, column=1, sticky="we", padx=8)
        ttk.Button(frm, text="瀏覽…", command=self.pick_ptu).grid(row=r, column=2, sticky="e")
        r += 1

        ttk.Label(frm, text="Duration (sec)").grid(row=r, column=0, sticky="w")
        row_fr = ttk.Frame(frm); row_fr.grid(row=r, column=1, columnspan=2, sticky="w")
        ttk.Entry(row_fr, textvariable=self.var_duration, width=12).pack(side="left", padx=(0,8))
        for txt,sec in [("1h",3600),("6h",21600),("12h",43200),("24h",86400)]:
            ttk.Button(row_fr, text=txt, command=lambda s=sec:self.var_duration.set(str(s))).pack(side="left", padx=4)
        r += 1

        ttk.Label(frm, text="Target load %").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_load, width=12).grid(row=r, column=1, sticky="w", padx=8)
        ttk.Label(frm, text="Governor").grid(row=r, column=1, sticky="e")
        gov_cb = ttk.Combobox(frm, values=["keep","performance"], textvariable=self.var_governor, width=14, state="readonly")
        gov_cb.grid(row=r, column=2, sticky="w")
        r += 1

        ttk.Label(frm, text="Cores (all or start-end)").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_cores, width=20).grid(row=r, column=1, sticky="w", padx=8)
        r += 1

        ttk.Label(frm, text="PTU profile").grid(row=r, column=0, sticky="w")
        prof = ttk.Combobox(frm, values=["serverlab","simple","sse","avx2","avx512","custom"], textvariable=self.var_profile, width=20, state="readonly")
        prof.grid(row=r, column=1, sticky="w", padx=8)
        r += 1

        ttk.Label(frm, text="Custom template (PROFILE=custom)").grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_template).grid(row=r, column=1, columnspan=2, sticky="we", padx=8)
        r += 1

        btn_row = ttk.Frame(frm); btn_row.grid(row=r, column=0, columnspan=3, pady=8, sticky="we")
        ttk.Button(btn_row, text="Start", command=self.start).pack(side="left")
        ttk.Button(btn_row, text="View processes", command=self.show_processes).pack(side="left", padx=8)
        ttk.Button(btn_row, text="Save defaults", command=self.save_defaults).pack(side="left", padx=8)
        ttk.Button(btn_row, text="Quit", command=self.destroy).pack(side="right")
        r += 1

        self.txt = tk.Text(frm, height=14); self.txt.grid(row=r, column=0, columnspan=3, sticky="nsew", pady=(8,0))
        frm.grid_rowconfigure(r, weight=1); frm.grid_columnconfigure(1, weight=1)

        self._append("提示：這個 GUI 只是一層殼，會以 root 身份啟動 PTU_CPU_Verify.py（Albert Style）。\n")

    def _append(self, s):
        self.txt.insert("end", s); self.txt.see("end")

    def pick_log(self):
        d = filedialog.askdirectory(title="Select log base folder", initialdir=self.var_log.get() or "/root")
        if d: self.var_log.set(d)

    def pick_ptu(self):
        f = filedialog.askopenfilename(title="Select PTU/PTAT binary", initialdir=self.var_ptu.get() or "/root")
        if f: self.var_ptu.set(f)

    def save_defaults(self):
        d = {
            "LOG_BASE": self.var_log.get(),
            "PTU_BIN": self.var_ptu.get(),
            "DURATION": int(self.var_duration.get() or "600"),
            "LOAD": int(self.var_load.get() or "100"),
            "GOVERNOR": self.var_governor.get(),
            "CORES": self.var_cores.get(),
            "PROFILE": self.var_profile.get(),
            "PTU_TEMPLATE": self.var_template.get(),
        }
        save_state(d)
        messagebox.showinfo("Saved", f"已儲存預設到 {STATE_FILE}")

    def show_processes(self):
        out = pgrep_snapshot() or "(無相關進程)"
        self._append("\n=== pgrep -af 'ptat|turbostat|stress-ng|yes' ===\n"+out+"\n")

    def start(self):
        if not ensure_root(): return
        core = core_path()
        if not Path(core).exists():
            messagebox.showerror("Core not found", f"找不到核心：{core}\n請確認 {CORE_FILE} 與此 GUI 同資料夾。")
            return
        env = os.environ.copy()
        env["LOG_BASE"] = self.var_log.get().strip()
        if self.var_ptu.get().strip(): env["PTU_BIN"] = self.var_ptu.get().strip()
        env["DURATION"] = str(int(self.var_duration.get() or "600"))
        env["LOAD"] = str(int(self.var_load.get() or "100"))
        env["GOVERNOR"] = self.var_governor.get()
        env["CORES"] = self.var_cores.get().strip() or "all"
        prof = self.var_profile.get()
        env["PROFILE"] = "simple" if prof=="sse" else prof
        if prof=="custom": env["PTU_TEMPLATE"] = self.var_template.get().strip()

        cmd = f'python3 "{core}"'
        try:
            run_cmd(cmd, env=env)
        except Exception as e:
            messagebox.showerror("Launch failed", str(e)); return

        self._append("\n=== Launch ===\n")
        self._append(f"Core      : {core}\n")
        self._append(f"Log base  : {env['LOG_BASE']}\n")
        self._append(f"Duration  : {env['DURATION']} s\n")
        self._append(f"Load      : {env['LOAD']} %\n")
        self._append(f"Governor  : {env['GOVERNOR']}\n")
        self._append(f"Cores     : {env['CORES']}\n")
        self._append(f"Profile   : {env['PROFILE']}\n")
        self._append(f"PTU bin   : {env.get('PTU_BIN','<auto>')}\n")
        if env.get("PTU_TEMPLATE"): self._append(f"Template  : {env['PTU_TEMPLATE']}\n")
        self._append("已啟動。建議 5 秒後點「View processes」確認 ptat / turbostat 有在跑。\n")

def main():
    try:
        import tkinter  # noqa
    except Exception:
        print("ERROR: 此 GUI 需要 Tkinter。SUSE 可安裝 python3-tk。", file=sys.stderr)
        sys.exit(1)
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
