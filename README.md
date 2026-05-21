Add Change 20250926
# PTU CPU Verify — Albert v1.3.1（Python 版，含 Tk GUI）

## 特色（Albert Style）
- **純 Python**：跨發行版，不需 zenity/GTK。
- **Py3.6 相容**：已用 `universal_newlines=True`。
- **預設 Summary**：`turbostat` 產出 `Avg_MHz/Bzy_MHz` 時序 → `Albert_Overview.html` 有頻率曲線。
- **自動判斷 PTAT**：偵測 `ptat/ptu`；無 `/dev/ptusys` 自動加 `-id`。
- **三段降級**：`PTAT → stress-ng → yes soaker`，保證能跑完。
- **乾淨日誌**：`console_*.log` 無 ANSI 碼；同時輸出 `Albert_Overview.txt/.html`。

## 安裝建議
- 以 **root** 執行。
- 建議套件（有就會用）：`kernel-tools`（含 `turbostat`）、`cpupower`、`stress-ng`  
  - SUSE：`zypper in kernel-tools cpupower stress-ng`
- GUI 需 Tkinter（SUSE：`zypper in python3-tk`）。

## 使用

chmod +x PTU_CPU_Verify.py PTU_CPU_Verify_GUI.py
export PATH="$PWD:/usr/sbin:/sbin:$PATH"

# (A) GUI
sudo -E python3 PTU_CPU_Verify_GUI.py

# (B) CLI 範例：1h、100%、serverlab、performance、全核
sudo -E ./PTU_CPU_Verify.py \
  DURATION=3600 LOAD=100 GOVERNOR=performance PROFILE=serverlab CORES=all PTU_BIN="$PWD/ptat"



## 這版做了什麼（Albert Style）
- **純 Python**：不需 zenity/GTK，跨發行版一致。
- **預設 Summary**：`turbostat` 產出 `Avg_MHz/Bzy_MHz` 時序 → `Albert_Overview.html` 有頻率趨勢。
- **自動判斷 PTAT**：偵測 `ptat/ptu`；無 `/dev/ptusys` 自動加 `-id`。
- **三段降級**：`PTAT → stress-ng → yes soaker`，保證能跑完。
- **乾淨日誌**：`console_*.log` 無 ANSI 碼；同時輸出 `Albert_Overview.txt/.html`。

## 先備條件
- 以 **root** 執行。
- 建議套件（有就會用）：`kernel-tools`（含 `turbostat`）、`cpupower`、`stress-ng`  
  - SUSE：`zypper in kernel-tools cpupower stress-ng`

## 快速開始

chmod +x PTU_CPU_Verify.py
export PATH="$PWD:/usr/sbin:/sbin:$PATH"

# 1 小時、100%、serverlab、performance、all cores、指定 ptat
sudo -E ./PTU_CPU_Verify.py \
  DURATION=3600 LOAD=100 GOVERNOR=performance PROFILE=serverlab CORES=all PTU_BIN="$PWD/ptat"



## 🔒 無網路 / 用 ISO 安裝（你之前常用的方式）

掛載 RHEL 9.6 的 ISO 或 DVD

# 以 root；把路徑換成你的 ISO 檔。
mount -o loop /root/Downloads/RHEL-9.6.0-*.iso /mnt


直接用 ISO 內的 rpm 安裝（不必改 repo）

# tkinter 本體
dnf -y install /mnt/AppStream/Packages/python3-tkinter-*.rpm

# 可能需要的 X 授權工具（遠端圖形常用）
dnf -y install /mnt/AppStream/Packages/xorg-x11-xauth-*.rpm

#（可選）tk 套件本身
dnf -y install /mnt/AppStream/Packages/tk-*.rpm




#### 小提醒

必須 root（你們本來就用 root）。GUI 會檢查，不是 root 會跳錯。

顯示環境：在 X 下跑即可；若是遠端，記得 xhost +SI:localuser:root（你之前流程已做過）。

參數保存：GUI 會把你的欄位記住到 ~/.ptu_cpu_verify_gui.json，下次自動帶回。

監看進程：按「View processes」會跑 pgrep -af 'ptat|turbostat|stress-ng|yes' 顯示目前執行狀態。

Albert Style：核心仍照你的 Style 產出 Albert_Overview.txt/.html、乾淨 console log、telemetry 等。




## 這套 Tk 版 GUI 就是把參數餵給 PTU_CPU_Verify.py 用的。照下面填就能跑起來：

怎麼設定（逐欄位）

Log base folder
留 /root/Documents/PTU_Linux_Rev4.8.0/PtuLog（預設），或改你要的路徑。每次跑都會在底下產生 run_YYYYmmdd_HHMMSS/。

PTU/PTAT binary

有 ptat 檔：按「瀏覽…」選到你的 ptat 可執行檔（同資料夾也行）。

沒填也可以：程式會自動偵測 PATH 裡的 ptat/ptu。

沒 /dev/ptusys 時會自動加 -id（不用自己管）。

Duration (sec)

直接輸入秒數，或按快選：

1h = 3600、6h = 21600、12h = 43200、24h = 86400

你要的長跑：1h/6h/12h/24h 就按一下對應按鈕。

Target load %

填 100（你要 CPU 100%）。

serverlab 模式內建 100%，但這裡還是照填 100 價值一致。

Governor

推薦 performance（程式會暫時切 performance，結束還原）。

Cores (all or start-end)

全核：填 all。

指定區段：例 0-95（會用 taskset 綁定）。

PTU profile

serverlab：你們實驗室一鍵設定（ct3 / 100%），建議用這個。

simple/sse：等同 SSE（ct3）。

avx2、avx512：分別選 AVX2 / AVX-512。

custom：要自己寫命令模板時才選（看下一欄）。

Custom template (PROFILE=custom)

只有當 Profile=custom 時才使用。

範例（預設）："{PTU_BIN}" -ct 3 -cp {LOAD} -t {DURATION} -y -q

可把 -ct 換 4（AVX2）、5（AVX-512），或加你要的額外參數。{PTU_BIN}/{LOAD}/{DURATION} 會自動代入。

按 Start 開跑

底下文字框會印出摘要。

等 3–5 秒後可按 View processes 看目前進程：ptat / turbostat / stress-ng / yes 是否在跑。




## 快速範例（你常用的三種）

Serverlab 長跑 6h，100%，全核，performance

Duration：點 6h（=21600）

Load：100

Governor：performance

Cores：all

Profile：serverlab

Start

AVX2 長跑 12h

Duration：點 12h（=43200）

Load：100

Governor：performance

Cores：all

Profile：avx2

Start

AVX-512 長跑 24h（全核）

Duration：點 24h（=86400）

Load：100

Governor：performance

Cores：all

Profile：avx512

Start





## 執行前小叮嚀（SUSE 15 SP7）

用 root 跑 GUI：

sudo -E python3 PTU_CPU_Verify_GUI.py


有圖形桌面就好；遠端 X 要先做一次：

xhost +SI:localuser:root


建議套件（有就會用；缺也能跑降級路徑）：

zypper in -y kernel-tools cpupower stress-ng


kernel-tools 內含 turbostat，HTML 才會有「平均頻率曲線」。





### 跑完看哪裡

到 Log base folder/run_YYYYmmdd_HHMMSS/ 看：

Albert_Overview.html：平均頻率趨勢（MHz）。

Albert_Overview.txt：文字摘要。

console_*.log：乾淨的 console log。

telemetry/turbostat_*.txt、telemetry/rapl_summary.txt（有 RAPL 時）。

workload/run_*.txt：實際執行命令。

自動打包：同層 run_*.tar.gz。




### 小故障排查

沒看到曲線：代表 turbostat 沒裝或沒出 Avg_MHz/Bzy_MHz。先 zypper in kernel-tools 再跑。

PTAT 不支援 / 無驅動：會自動退到 stress-ng，再不行就 yes soaker；驗證仍會完成。

想確認真的在跑：按 GUI 的 View processes（等同 pgrep -af 'ptat|turbostat|stress-ng|yes'）。

如果你要我把 GUI 再加一顆「Open Overview」按鈕（自動開最新 Albert_Overview.html），或加「Stop」按鈕（pkill ptat turbostat），我可以直接幫你補上。
