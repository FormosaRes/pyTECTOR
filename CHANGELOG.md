# Changelog / 更新紀錄

Versions of pyTECTOR. English first, 中文在後。

Back to the [README](../README.md) · 回到 [README](../README.md)。

---

## English

**0.3.1**

- **the one-click setup now actually installs everything.** `install.bat`
  offers to download and install Miniconda when the machine has no Python at
  all, falls back to conda-forge for anything pip cannot supply, and verifies
  that numpy, scipy, matplotlib and PyQt5 really import rather than trusting
  pip's exit code
- it excludes the **Microsoft Store `python` stub** by path. That stub is not a
  real interpreter, PyQt5 does not work under it, and it was the most common
  way the setup failed
- the interpreter it used is recorded in `python-path.txt`, and `pyTECTOR.bat`
  and `pyTECTOR.command` start **that** one. Previously the installer could put
  the dependencies into one Python while the launcher started another
- **`install.command`**, the macOS and Linux counterpart of `install.bat`, with
  the same steps and the same Miniconda offer
- the automatic Miniconda install goes to `C:\Miniconda3` where it can, because
  conda and Qt both misbehave under a home directory whose name is not plain
  ASCII, which is the normal case on a Chinese or Japanese Windows account
- the README and both manuals recommend Anaconda or Miniconda up front, and say
  why

**0.3.0**

- **released under the MIT Licence**, which settles the one item that had been
  blocking public use (see *Licence, credits and use* for what the licence does
  and does not cover)
- renamed pyTENSOR → **pyTECTOR**, after Angelier's own data-base name, to
  stay clear of Delvaux's TENSOR / Win-Tensor and of PyMC's `pytensor`
  package (see *Why the name*). `PYTENSOR_ARCHIVE` still works as a legacy
  spelling of `PYTECTOR_ARCHIVE`.
- one-click setup: `install.bat` installs the dependencies and puts a desktop
  shortcut up; `pip install .` works too and installs a `pytector` command
- MESURE 5.51 and TENSOR 5.45 run on the original machine as oracles;
  docs/mesure_oracle.md transcribes both sessions
- **a public end-to-end fixture**: tests/fixtures/L12-2 is a complete run of
  the original programs on a synthetic site, and tests/test_fixture.py checks
  the whole pipeline against it with no archive needed, axes to 0.05 degrees

**0.2.0**

- back-tilting moved to a window of its own, measured and restored side by side,
  with the measured axes carried through the rotation drawn as open rings
- established, and pinned in a test, that INVDIR is not rotation equivariant
  while S4MIN is; confirmed against the original program on 14 archive pairs
- HPGL export rewritten to replay the real drawing code, so it carries the whole
  figure instead of the primitive and the fault planes only
- corrected the frame box, which is not symmetric about the centre, and the
  caption anchors, on screen and in every export
- ψ scans vectorised: INVERT went from seconds to milliseconds
- interface: a permanent line saying what is on screen, an out-of-date badge
  when the data have changed since the last inversion, per-panel titles,
  hairlines between sidebar sections

**0.1.0**

- criterion, quality estimators and forward model, verified on 35 faults
- INVDIR with PSIDIR, and S4MIN
- file reader, INFO1 and MOHR1 writers in the original layout
- Angelier-style stereograms measured off the archive HPGL
- desktop interface, 1991 mode

## 中文

**0.3.1**

- **一鍵安裝真的把該裝的都裝好了。** 機器上完全沒有 Python 時，
  `install.bat` 會詢問是否代為下載並安裝 Miniconda；pip 裝不起來的部分改用
  conda-forge；並且實際確認 numpy、scipy、matplotlib、PyQt5 都能 import，
  而不是只看 pip 的離開碼
- 依路徑排除 **Microsoft Store 的 `python` 樁**。它不是真正的直譯器，
  PyQt5 在它底下不能用，這是先前安裝失敗最常見的原因
- 用到的直譯器會記進 `python-path.txt`，`pyTECTOR.bat` 與 `pyTECTOR.command`
  啟動的就是**那一個**。先前安裝腳本可能把套件裝進某個 Python，
  啟動器卻跑了另一個
- 新增 **`install.command`**，`install.bat` 的 macOS 與 Linux 對應版本，
  步驟相同，同樣提供 Miniconda 安裝選項
- 自動安裝 Miniconda 時盡量裝到 `C:\Miniconda3`，因為 conda 與 Qt
  在非純 ASCII 的家目錄底下都會出問題，而中文或日文的 Windows 帳號正是如此
- README 與兩份手冊都改為在最前面建議安裝 Anaconda 或 Miniconda，並說明原因

**0.3.0**

- **以 MIT 授權釋出**，解決先前唯一阻礙公開使用的項目
  （授權涵蓋與不涵蓋的範圍見「授權與致謝」）
- 更名 pyTENSOR → **pyTECTOR**，取自 Angelier 自身的資料庫名稱，
  以避開 Delvaux 的 TENSOR／Win-Tensor 與 PyMC 的 `pytensor`
  （見「為什麼叫 pyTECTOR」）。環境變數 `PYTENSOR_ARCHIVE` 仍可使用，
  為 `PYTECTOR_ARCHIVE` 的舊有拼法
- 一鍵安裝：`install.bat` 安裝相依套件並建立桌面捷徑；亦可使用 `pip install .`，
  安裝後提供 `pytector` 指令
- 於原機器實際執行 MESURE 5.51 與 TENSOR 5.45 作為 oracle，
  兩個 session 的完整紀錄見 docs/mesure_oracle.md
- **公開的端到端 fixture**：tests/fixtures/L12-2 為原程式對合成站的完整執行結果，
  tests/test_fixture.py 無須 archive 即可驗證整條流程，軸精度達 0.05°

**0.2.0**

- 回轉功能獨立為一個視窗，實測與回轉結果左右並列，
  並將實測軸經同一旋轉後繪為空心圈
- 確立並以測試固定：INVDIR 非旋轉等變、S4MIN 為等變；
  以原程式的 14 組 archive 配對驗證
- HPGL 匯出改為重播實際的繪圖程式，完整圖面均寫入檔案，
  不再僅含基準圓與斷層面
- 修正外框（非對稱）與標註錨點，螢幕顯示與所有匯出一併修正
- ψ 掃描全面向量化，INVERT 由數秒降至毫秒等級
- 介面調整：常駐一行說明當前繪製內容、資料變更但尚未重算時顯示過期標記、
  各面板加上標題、側欄分段加入細線

**0.1.0**

- 準則、品質估計量與前向模型，以 35 筆資料驗證
- INVDIR ＋ PSIDIR，以及 S4MIN
- 舊檔讀取、原格式的 INFO1 與 MOHR1 輸出
- 依 archive HPGL 量測而得的 Angelier 畫風投影網
- 桌面介面、1991 模式
