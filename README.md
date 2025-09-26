# PTU_CPU_Verify
（Albert Style） - **純 Python**：不需 zenity/GTK，跨發行版一致。 - **預設 Summary**：`turbostat` 產出 `Avg_MHz/Bzy_MHz` 時序 → `Albert_Overview.html` 有頻率趨勢。 - **自動判斷 PTAT**：偵測 `ptat/ptu`；無 `/dev/ptusys` 自動加 `-id`。 - **三段降級**：`PTAT → stress-ng → yes soaker`，保證能跑完。 - **乾淨日誌**：`console_*.log` 無 ANSI 碼；同時輸出 `Albert_Overview.txt/.html`。
