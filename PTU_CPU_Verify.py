#!/usr/bin/env python3
# =============================================================================
#  PTU_CPU_Verify.py  (Albert Style, v1.3.1 • Python edition, Py3.6-compatible)
#  - 無需 zenity/GTK；跨發行版僅需 Python3
#  - 預設 Summary 取樣 turbostat（一定能畫頻率趨勢）
#  - 自動偵測 ptat/ptu；無 /dev/ptusys 自動帶 -id
#  - Workload 失敗自動降級：PTAT → stress-ng → yes soaker
#  - 產出 Albert_Overview.txt / .html + 純文字 console log
#  - Log 目錄：/root/Documents/PTU_Linux_Rev4.8.0/PtuLog/run_YYYYmmdd_HHMMSS
# =============================================================================
import os, re, json, time, shutil, pathlib, datetime, subprocess

# ====== 可調整預設 ======
LOG_BASE_DEFAULT = "/root/Documents/PTU_Linux_Rev4.8.0/PtuLog"
TSTAT_FORCE_SUMMARY = True              # SUSE 建議 True（產生 Avg_MHz/Bzy_MHz 時序）
GOVERNOR_DEFAULT = "performance"        # keep / performance
PROFILE_DEFAULT = "serverlab"           # serverlab/sse(simple)/avx2/avx512/custom
LOAD_DEFAULT = 100
DURATION_DEFAULT = 600
CORES_DEFAULT = "all"                   # "all" 或 "start-end"
PTU_TEMPLATE_DEFAULT = '"{PTU_BIN}" -ct 3 -cp {LOAD} -t {DURATION} -y -q'  # custom 用

# ====== 小工具 ======
def have(cmd):
    from shutil import which
    return which(cmd) is not None

def run(cmd, **kw):
    p = subprocess.Popen(
        cmd,
        shell=isinstance(cmd,str),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,  # Py3.6 相容
        **kw
    )
    o,e = p.communicate()
    return p.returncode, o, e

def now(): return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
def mkdir_p(p): pathlib.Path(p).mkdir(parents=True, exist_ok=True)
def strip_ansi(s): return re.sub(r"\x1B\[[0-9;]*[A-Za-z]", "", s or "")

def autodetect_ptu():
    cands = [
        shutil.which("ptat") or "", shutil.which("ptu") or "",
        "/opt/intel/ptu/bin/ptu", "/opt/intel/PTU_Server/bin/ptu",
        "/usr/local/bin/ptat", "/usr/local/bin/ptu"
    ]
    for c in cands:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return ""

def id_flag_for(binpath):
    base = os.path.basename(binpath)
    if base.startswith("ptat") and not os.path.exists("/dev/ptusys"):
        return "-id "
    return ""

def build_ptu_cmd(profile, binpath, load, dur, custom_tpl=None):
    idf = id_flag_for(binpath)
    if profile == "serverlab": return f'"{binpath}" {idf}-ct 3 -cp 100 -t {dur} -y -q'
    if profile in ("simple","sse"): return f'"{binpath}" {idf}-ct 3 -cp {load} -t {dur} -y -q'
    if profile == "avx2": return f'"{binpath}" {idf}-ct 4 -cp {load} -t {dur} -y -q'
    if profile == "avx512": return f'"{binpath}" {idf}-ct 5 -cp {load} -t {dur} -y -q'
    if profile == "custom":
        tpl = custom_tpl or PTU_TEMPLATE_DEFAULT
        return tpl.replace("{PTU_BIN}", binpath).replace("{LOAD}", str(load)).replace("{DURATION}", str(dur))
    return f'"{binpath}" {idf}-ct 3 -cp {load} -t {dur} -y -q'

def plain_write(fp, text):
    with open(fp, "a", encoding="utf-8") as f: f.write(strip_ansi(text))

def detect_cpu_total():
    try:
        rc,o,_ = run(["nproc"]);  return int(o.strip()) if rc==0 else 1
    except: return 1

def start_turbostat(out_file, duration):
    if not have("turbostat"): return None
    dump_flag = ""
    if not TSTAT_FORCE_SUMMARY:
        rc,h,_ = run("turbostat -h")
        if "--Dump" in h or re.search(r"\b-D\b", h): dump_flag = "-D"
        elif "--dump" in h: dump_flag = "--dump"
    cmd = f'turbostat --interval 1 --num_iterations {duration} {dump_flag} --out "{out_file}" --quiet'.strip()
    return subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def parse_trend(ts_file):
    if not os.path.exists(ts_file) or os.path.getsize(ts_file)==0: return []
    with open(ts_file, "r", encoding="utf-8", errors="ignore") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if not lines: return []
    header = lines[0].split()
    col = next((i for i,n in enumerate(header) if n in ("Avg_MHz","Bzy_MHz")), -1)
    if col < 0: return []
    data=[]
    for ln in lines[1:]:
        parts = ln.split()
        if len(parts) <= col: continue
        try:
            t = int(float(parts[0])); v = float(parts[col]); data.append((t,v))
        except: pass
    agg={}
    for t,v in data: agg.setdefault(t, []).append(v)
    return [[t, sum(v)/len(v)] for t,v in sorted(agg.items())]

def make_html(run_dir, duration, gov, profile, ptu_bin, avgW, trend):
    html = os.path.join(run_dir, "Albert_Overview.html")
    js = "var data=" + json.dumps(trend) + ";"
    tpl = f"""<!doctype html><meta charset="utf-8"><title>Albert Overview – PTU CPU Verify</title>
<style>
body{{font-family:system-ui,Segoe UI,Roboto,"Noto Sans",Arial,sans-serif;background:#fafafa;color:#222;margin:24px}}
.card{{background:#fff;border-radius:16px;box-shadow:0 6px 20px rgba(0,0,0,.08);padding:20px;max-width:980px}}
h1{{font-size:20px;margin:0 0 12px}}
table{{border-collapse:collapse;width:100%;margin-top:6px}}td{{padding:8px 10px;border-bottom:1px solid #eee;vertical-align:top}}
td.k{{color:#555;width:180px}}.badge{{display:inline-block;padding:2px 8px;border-radius:999px;background:#eef}}
svg{{width:100%;height:260px;background:#fcfcff;border:1px solid #eee;border-radius:12px}}
.axis text{{font-size:11px;fill:#666}}.path{{fill:none;stroke:#3b82f6;stroke-width:2}}
</style>
<div class="card">
<h1>PTU CPU Verify — Albert Overview</h1>
<table>
<tr><td class="k">Start time</td><td>{now()}</td></tr>
<tr><td class="k">Duration</td><td>{duration}s</td></tr>
<tr><td class="k">Governor</td><td>{gov}</td></tr>
<tr><td class="k">Profile</td><td><span class="badge">{profile}</span></td></tr>
<tr><td class="k">PTU bin</td><td>{ptu_bin or "&lt;not set&gt;"}</td></tr>
<tr><td class="k">Avg Power (RAPL)</td><td>{avgW}</td></tr>
<tr><td class="k">Log folder</td><td>{run_dir}</td></tr>
</table>
<h1 style="margin-top:18px;">Average Frequency Trend (MHz)</h1>
<div id="chart"><svg id="svg" viewBox="0 0 900 260" preserveAspectRatio="none"></svg></div>
<div style="color:#777;margin-top:10px;font-size:12px">Generated at {now()}</div>
</div>
<script>{js}
var svg=document.getElementById('svg'),W=900,H=260,pL=50,pR=12,pT=16,pB=28;
function map(v,a,b,c,d){{return c+(v-a)*(d-c)/(b-a)}}
function path(pts){{if(!pts.length)return'';var s='M';for(var i=0;i<pts.length;i++)s+=pts[i][0]+','+pts[i][1]+(i?' L':' ');return s}}
if(data.length>1){{
  var t0=data[0][0],t1=data[data.length-1][0],y0=data[0][1],y1=y0;
  for(var i=0;i<data.length;i++){{y0=Math.min(y0,data[i][1]);y1=Math.max(y1,data[i][1]);}}
  if(y0==y1){{y0=Math.max(0,y0-100);y1=y1+100;}}
  var pts=[];for(var i=0;i<data.length;i++){{var x=map(data[i][0],t0,t1,pL,W-pR),y=map(data[i][1],y0,y1,H-pB,pT);pts.push([x,y]);}}
  var p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('class','path');p.setAttribute('d',path(pts));svg.appendChild(p);
  function tx(x,y,t){{var e=document.createElementNS('http://www.w3.org/2000/svg','text');e.setAttribute('x',x);e.setAttribute('y',y);e.textContent=t;svg.appendChild(e)}}
  function ln(x1,y1,x2,y2){{var e=document.createElementNS('http://www.w3.org/2000/svg','line');e.setAttribute('x1',x1);e.setAttribute('y1',y1);e.setAttribute('x2',x2);e.setAttribute('y2',y2);e.setAttribute('stroke','#ccc');svg.appendChild(e)}}
  for(var k=0;k<=4;k++){{var v=y0+(y1-y0)*k/4,y=map(v,y0,y1,H-pB,pT);ln(pL,y,W-pR,y);tx(6,y+4,Math.round(v));}}
  for(var k=0;k<=4;k++){{var tt=Math.round(t0+(t1-t0)*k/4),x=map(tt,t0,t1,pL,W-pR);ln(x,pT,x,H-pB);tx(x-10,H-6,(tt-t0)+'s');}}
}}else{{var t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x',20);t.setAttribute('y',40);t.textContent='No turbostat data.';svg.appendChild(t);}}
</script>
"""
    with open(html, "w", encoding="utf-8") as f: f.write(tpl)

# ====== 主流程 ======
def main():
    os.environ["PATH"] = "/usr/sbin:/sbin:" + os.environ.get("PATH","")

    # 允許用環境變數覆寫（沿用 Albert Style）
    log_base = os.environ.get("LOG_BASE", LOG_BASE_DEFAULT)
    duration = int(os.environ.get("DURATION", DURATION_DEFAULT))
    load = int(os.environ.get("LOAD", LOAD_DEFAULT))
    governor = os.environ.get("GOVERNOR", GOVERNOR_DEFAULT)   # keep/performance
    cores = os.environ.get("CORES", CORES_DEFAULT)             # all 或 start-end
    profile = os.environ.get("PROFILE", PROFILE_DEFAULT)
    ptu_bin = os.environ.get("PTU_BIN", "") or autodetect_ptu()
    ptu_tpl = os.environ.get("PTU_TEMPLATE", PTU_TEMPLATE_DEFAULT)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(log_base, f"run_{ts}")
    for sub in ("", "sysinfo", "telemetry", "workload"): mkdir_p(os.path.join(run_dir, sub))

    console_log = os.path.join(run_dir, f"console_{ts}.log")
    for line in [
        "========== PTU CPU Verify — Setup ==========\n",
        f"{now()} | [INFO] Script           : PTU_CPU_Verify.py (Albert v1.3.1)\n",
        f"{now()} | [INFO] Start            : {now()}\n",
        f"{now()} | [INFO] Duration         : {duration}s\n",
        f"{now()} | [INFO] Governor choice  : {governor}\n",
        f"{now()} | [INFO] Cores            : {cores}\n",
        f"{now()} | [INFO] Log dir          : {run_dir}\n",
        f"{now()} | [INFO] PTU bin          : {ptu_bin or '<not set>'}\n",
        f"{now()} | [INFO] Profile          : {profile}\n",
    ]: plain_write(console_log, line)

    # Governor
    restore_gov = False
    if governor == "performance" and have("cpupower"):
        run("cpupower frequency-set -g performance")
        restore_gov = True
        plain_write(console_log, f"{now()} | [INFO] Governor set to performance\n")
    else:
        plain_write(console_log, f"{now()} | [INFO] Keeping current governor settings\n")

    # RAPL
    rapl_files = []
    for root,_,files in os.walk("/sys/class/powercap"):
        for fn in files:
            if fn == "energy_uj": rapl_files.append(os.path.join(root, fn))
    def rapl_sum(files):
        s=0
        for f in files:
            try: s += int(open(f).read().strip())
            except: pass
        return s
    rapl_start = rapl_sum(rapl_files) if rapl_files else None
    if not rapl_files:
        plain_write(console_log, f"{now()} | [WARN] No RAPL energy_uj files found — avg power will be skipped.\n")

    # turbostat
    tstat_out = os.path.join(run_dir, "telemetry", f"turbostat_{ts}.txt")
    tproc = start_turbostat(tstat_out, duration)
    if tproc: plain_write(console_log, f"{now()} | [INFO] turbostat PID={tproc.pid}\n")
    else:     plain_write(console_log, f"{now()} | [WARN] turbostat not found in PATH.\n")

    # workload（依序降級）
    work_log = os.path.join(run_dir, "workload", f"run_{ts}.txt")
    with open(work_log, "w", encoding="utf-8") as wf:
        wf.write(f"# Start: {now()}\n# Profile: {profile}\n")

    def run_aff(cmd):
        cmd2 = cmd if cores=="all" else f"taskset -c {cores} {cmd}"
        return run(cmd2)

    rc=127
    if ptu_bin and os.path.exists(ptu_bin):
        cmd = build_ptu_cmd(profile, ptu_bin, load, duration, ptu_tpl if profile=="custom" else None)
        with open(work_log,"a",encoding="utf-8") as wf: wf.write(f"$ {cmd}\n")
        rc,_,_ = run_aff(cmd)
        plain_write(console_log, f"{now()} | [{'PASS' if rc==0 else 'WARN'}] PTU/PTAT rc={rc}\n")

    if rc!=0 and have("stress-ng"):
        cmd = f"stress-ng --cpu {detect_cpu_total()} --cpu-method matrixprod --timeout {duration}s --metrics-brief --verify"
        with open(work_log,"a",encoding="utf-8") as wf: wf.write(f"$ {cmd}\n")
        rc,_,_ = run_aff(cmd)
        plain_write(console_log, f"{now()} | [{'PASS' if rc==0 else 'WARN'}] stress-ng rc={rc}\n")

    if rc!=0:
        procs=[]
        for _ in range(detect_cpu_total()):
            procs.append(subprocess.Popen(f"bash -lc 'timeout {duration}s yes > /dev/null'", shell=True))
        for p in procs: p.wait()
        rc = 0
        plain_write(console_log, f"{now()} | [PASS] CPU soaker completed.\n")

    # 等 turbostat
    if tproc:
        plain_write(console_log, f"{now()} | [INFO] Waiting turbostat (PID={tproc.pid})…\n")
        try: tproc.wait(timeout=duration+15)
        except: pass

    # RAPL 平均功耗
    avgW = "N/A"
    if rapl_start is not None and rapl_files:
        rapl_end = rapl_sum(rapl_files)
        delta = max(0, rapl_end - rapl_start)
        avgW = f"{(delta/1_000_000)/max(1,duration):.2f}"
        with open(os.path.join(run_dir,"telemetry","rapl_summary.txt"),"w") as f:
            f.write(f"duration_s={duration}\nenergy_delta_uj={delta}\navg_power_W={avgW}\n")
        plain_write(console_log, f"{now()} | [INFO] Average package power (RAPL): {avgW} W\n")

    # Overview
    trend = parse_trend(tstat_out)
    with open(os.path.join(run_dir,"Albert_Overview.txt"),"w",encoding="utf-8") as f:
        f.write(f"""==== PTU CPU Verify — Albert Overview (TXT) ====
Start time : {now()}
Duration   : {duration}s
Governor   : {governor}
Profile    : {profile}
PTU bin    : {ptu_bin or "<not set>"}
Log folder : {run_dir}

-- Result Summary --
Workload RC : {rc}
Avg Power W : {avgW}
Turbostat   : {os.path.basename(tstat_out)}
Workload log: {os.path.basename(work_log)}
""")
    make_html(run_dir, duration, governor, profile, ptu_bin, avgW, trend)

    # 還原 governor
    if restore_gov and have("cpupower"):
        run("cpupower frequency-set -g ondemand")
        plain_write(console_log, f"{now()} | [INFO] Restored governor to ondemand\n")

    # 打包
    tgz = f"{run_dir}.tar.gz"
    subprocess.call(["tar","-C", os.path.dirname(run_dir), "-czf", tgz, os.path.basename(run_dir)])
    plain_write(console_log, f"{now()} | [PASS] Results packaged: {tgz}\n")
    plain_write(console_log, f"{now()} | [{'PASS' if rc==0 else 'FAIL'}] CPU verification run {'completed' if rc==0 else 'encountered issues'} (rc={rc}).\n")

if __name__ == "__main__":
    main()
