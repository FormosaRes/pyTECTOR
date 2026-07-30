<div align="right">

[English](README.md) | [繁體中文](README.zh.md)

</div>

<div align="center">

![pyTECTOR](docs/img/banner.png)

**Angelier 古應力反演的 Python 重建版，對應 TENSOR 5.45 (jan91)**

依已發表的方法重建，並以原程式自身的輸出檔案驗證

[![TENSOR](https://img.shields.io/badge/TENSOR%205.45-reconstructed-1f6feb)](docs/mesure_oracle.md)
[![version](https://img.shields.io/badge/version-0.3.0-brightgreen)](pyproject.toml)
[![python](https://img.shields.io/badge/python-3.x-555)](#安裝與執行)
[![tests](https://img.shields.io/badge/tests-11%20suites%20passing-2ea44f)](tests/)
[![licence](https://img.shields.io/badge/licence-MIT-8250df)](LICENSE)

[使用手冊 中文](docs/manual.zh.md) · [English manual](docs/manual.en.md) · [原程式對話全文](docs/mesure_oracle.md)

</div>

---

## 這是什麼

Angelier 的直接反演法從一組實測斷層面與擦痕線理，解出最能解釋它們的簡化應力張量，
也就是三個主應力方向與形狀比 Φ。他的程式 `Tensor.exe` 自 1991 年起執行這項計算，
大量已發表的古應力研究建立在其結果之上。

pyTECTOR 執行同一套運算、讀寫同一批檔案、繪製同一種圖，
並補上原程式未提供的部分：回轉（back-tilting）、傾轉檢驗，
以及將同一準則精確最小化的第二種跑法，
用以評估一個結果有多少來自方法本身、多少來自資料。

專案名稱取自 TECTOR，即 Angelier 為這套程式的構造方位資料庫所取的名稱，
見於它產生的每一份 INFO1。

---

## 介面

| 兩種跑法並列 | 回轉與傾轉檢驗 |
|---|---|
| ![methods](docs/img/methods.png) | ![back-tilt](docs/img/backtilt.png) |

<div align="center"><img src="docs/img/mohr.png" width="420" alt="Mohr diagram"></div>

> 以上圖片均由本 repo 所含的公開 fixture `tests/fixtures/L12-2/` 產生。
> 該站為合成資料而非野外資料，因此上述各圖皆可自行重製。

---

## 功能

**重建方式。** 演算法已完整發表於 Angelier (1984, 1990)，因此本專案依論文實作，
未對原始的 16 位元執行檔進行反組譯。

**驗證。** 以原程式產生的 92 個 run 作為回歸測試集。前向量
（SIGMN、TAU、TAUST、RUP、ANG）逐筆吻合至檔案本身的精度；
依各站記錄的 pass 數與 LAMBDA 重新執行反演後，
90 個可比對的站中有 85 站的三軸角度差在 3° 以內。

**INVDIR 與 S4MIN 兩種跑法。** 前者為 Angelier 原方法、亦即原程式的跑法；
後者為同一準則的精確最小值。兩者皆不應視為「真實應力」：
υ 準則本身帶有系統性偏差，即使餵入零雜訊的理想合成資料，
結果仍與真實張量相差約 4°。並列呈現的目的在於顯示差異所在，而非在其中擇一。

**回轉與傾轉檢驗。** 此為原程式未提供的功能。旋轉角度以拉桿調整，
σ₁、σ₂、σ₃ 即時重算。就 INVDIR 而言，回轉前後主軸的差距反映的是方法本身的性質
而非地質意義（14 組 archive 配對，實測 σ₁ 差異中位數為 10.4°）。

**影響力診斷。** 擬合殘差大的資料與實際主導結果的資料未必是同一批。
程式對每一筆資料執行 leave-one-out 重新反演，輸出剔除後殘差 ANG\* 與 RUP\*，
並將「全部資料」與「剔除該筆後」兩組結果並列寫入匯出的 INFO1。

**原格式輸出。** INFO1 與 MOHR1 與原始檔案逐位元組相同；
HPGL 匯出係重播原本的繪圖程序，而非另一套獨立實作。

**Session 存檔。** 全部工作狀態存為單一 JSON 檔。檔中僅保存張量，
其餘數值於載入時重新計算，因此存檔中的 Φ 不可能與存檔中的張量互相矛盾。

---

## 專案來源

演算法已完整發表，因此本專案照論文重建，而非反譯 16 位元的原始執行檔：
編譯已丟棄名稱、型別與結構，分段定址也讓指標無法解析。工作集中於研讀
Angelier (1984, 1990, 1994)，並量測原程式自身的輸出以補足論文未載明的部分。

名稱同樣出自 Angelier。他的論文從未為程式命名，但執行檔在它寫出的每一份
INFO1 上自報其名，而橫幅上兩個名稱之一即為 **TECTOR**，亦即它的構造方位
資料庫。「TENSOR」無法使用：在本領域它現指 Delvaux 的 Win-Tensor，
而 PyPI 上的 `pytensor` 是 PyMC 的張量庫。

兩個問題的完整說明、橫幅原文與參考文獻：
**[docs/background.zh.md](docs/background.zh.md)**。

## 安裝與執行

Windows 一鍵安裝：下載整個 repo 後雙擊 **`install.bat`**。
該腳本會自動尋找 Python（優先使用 Anaconda）、安裝 numpy／scipy／matplotlib／PyQt5，
並在桌面建立 pyTECTOR 捷徑。亦可使用
`pip install .`（或 `pip install git+https://github.com/FormosaRes/pyTECTOR`），
安裝後會提供 `pytector` 指令。

```
pyTECTOR.bat                           桌面介面（Windows）
./pyTECTOR.command                     桌面介面（macOS、Linux）
python demo_report.py [站檔]           反演一個舊站，印出 INFO1 + MOHR1
python run_batch.py [根目錄] [out.csv] 對整棵資料夾跑兩種方法
python make_survey.py [根目錄] [輸出夾] 產生表格、地圖點位與各期玫瑰圖
```

**macOS 與 Linux。** 函式庫本身沒有任何 Windows 專屬程式碼，
因此反演、檔案讀取與各項匯出均可直接執行。安裝四個相依套件後，
使用 `pyTECTOR.command` 啟動（在 Finder 中可直接雙擊）：

```
python3 -m pip install numpy scipy matplotlib PyQt5
./pyTECTOR.command
```

兩點須注意。在 **Apple Silicon** 的 Mac 上，PyQt5 需使用具備 arm64 wheel 的版本
（5.15.10 或更新）；若 pip 開始從原始碼編譯 Qt，請改以 conda 安裝
（`conda install -c conda-forge pyqt`）。另外，若需指定特定的 Python 解譯器，
可設定 `PYTECTOR_PYTHON`，否則啟動器會採用 `PATH` 上第一個能匯入 PyQt5 的解譯器。
介面尚未在 macOS 上實際測試：字體堆疊已納入 macOS 與 Linux 的字型以維持
定寬表格的對齊，若發現顯示異常歡迎回報。

逐項功能的完整操作說明見 **[docs/manual.zh.md](docs/manual.zh.md)**。

輸入分為四個欄位，輸入後即顯示於投影網上：

```
CS - 122 - 87W - 124
|    |     |     |
|    |     |     +-- rake ＋象限（62N），或直接給 trend（124）
|    |     +-------- 傾角＋象限
|    +-------------- 走向
+------------------- 信心度 C/P/S ＋ 運動方式 I/N/S/D
```

亦可直接開啟舊有的 run：指向那個**沒有副檔名、檔名等於站名**的資料檔（例如 `L12`），
斷層資料與 INFO1 會一併載入。

## 準則

- σ = **T**·n（式 3）；τ = σ − (n·σ)n（式 4-5）
- **υ² = λ² + |τ|² − 2λ(s·σ)**（式 A1），最小化 **S₄ = Συ²**（式 13）
- RUP = 100·|υ|/(√3/2)，範圍 0-200 %；ANG = s 與 τ 的夾角，0-180°
- 張量正規化採**特徵值平方和 = 3/2**（式 A16），**並非**固定 σ₁ − σ₃。
  兩種定義僅在 Φ = 0.5 時相同，而此準則不具尺度不變性，故此差異會改變結果。

**此準則本身帶有系統性偏差，並非任何程式的錯誤。**
υ 同時要求「預測剪應力方向與實測滑動一致」與「剪應力大小接近 λ」，
因此即使餵入零雜訊的理想 Bott 合成資料，結果仍與真實張量相差約 4°，
並系統性地偏向使斷層承受高剪應力的方位。
純角度準則 F2 在同一批資料上的誤差為 0.00°。
這即是 TectonicsFP 等軟體與 Angelier 計算結果不一致的根本原因。

## 兩種跑法：INVDIR 與 S4MIN

兩者以其實質內容命名，避免使用暗示優劣的代號。基於上述理由，**兩者皆非「真應力」**。

**INVDIR**（`pytector.invdir`，代碼 `INVD`）為 Angelier 原方法、原程式的跑法，
採用他自己的 (α, β, γ, ψ) 參數化（式 14 / A2）。此張量**未經正規化**，
其最大剪應力隨解的移動而改變，這正是 λ 必須逐趟迭代的原因，
也是 INFO1 所印出的 `LAMBDA` 小於 √3/2 的原因。流程分兩段：

1. **INVDIR 第 k 趟**：在當前 λ 下最小化 S₄，隨後將 λ 更新為該解的 taumax。
   INFO1 印出的 `(NO k)` **為迭代趟數**，而非「在兩個解之間擇一」。
2. **PSIDIR**：將軸凍結於 INVDIR 的結果，改用正規化的 A16 形式、λ = √3/2，
   對 ψ **整圈**重新最小化。此步驟決定 Φ，並修正前一階段可能產生的
   σ₁/σ₃ 人為對調。

兩項實作要點：固定 ψ 時 υ² 對 (α, β, γ) 為二次式，內層即精確的 3×3 線性求解，
無須轉抄附錄中的多項式（現有掃描檔的附錄辨識度不足，此處改以數值方式重新生成）。
另外 ψ 必須掃描整圈：若限制於 [0, π/3] 會得到 Φ = 0 的錯誤結果，
因為最小值常落在 ψ ≈ 336-353°。

**S4MIN**（`pytector.modern`，代碼 `S4MN`）為同一 S₄ 的精確最小值，
採特徵分解參數化，λ 依構造恆為 √3/2，無須調整迴圈，且搜尋為全域。
它在 **92 個 archive 站上無一例外**皆達到更低的 S₄：

| 站 | INVDIR S₄ | S4MIN S₄ |
|---|---|---|
| L12 | 0.3018 | 0.2360 |
| 0406-7 | 7.6198 | 7.3201 |

換言之，原程式並未達到其自身準則的最小值，原因是 λ 在收斂前即停止。

### 更深入的內容

兩種跑法的完整處理、PSIDIR 何時重貼軸標籤、λ 究竟是什麼、迭代為何發散、
如何從 INFO1 判讀收斂程度，以及上面那段回轉警告背後的等變性實測數據，
全部在 **[docs/method.zh.md](docs/method.zh.md)**。

檔案格式、HPGL 畫風判準與專案結構在
**[docs/formats.zh.md](docs/formats.zh.md)**。

## 回轉（back-tilting）

回轉功能有獨立的視窗，由工具列開啟。主視窗僅呈現實測資料、不做任何旋轉，
因此該處的投影網無須額外標註目前所處的方位。

回轉視窗會將資料轉至指定方位，並對前後兩個狀態各執行一次反演，左右並列呈現：
左側為 as measured、右側為 back-tilted，下方列出兩者的數值。設定旋轉的方式有三種：

| 方式 | 輸入 | 作用 |
|---|---|---|
| 參考面 | 走向 / 傾角，或以其 pole 給定 trend / plunge | 將該面轉回水平所需的旋轉 |
| 旋轉軸 | trend / plunge / 角度 | 直接套用，依右手定則 |
| 部分回轉 | 0 到 125 % | 上述任一方式的任意比例 |

斷層面法向與滑動向量會一併旋轉，因此 rake 與運動感亦隨之改變。
此慣例並非推測，而是對 archive 驗證過的：解出原站與其回轉版之間的旋轉
（對法向施以 Kabsch 演算法），七組全部重現至 2° 以內。

參考面以虛線大圓及其 pole 繪出，並隨資料一同旋轉，
因此回轉是否正確可直接目視判斷：虛線圓會壓平至基準圓上，pole 則移至圓心。

**旋轉角度並非計算而得。** 該角度無解析解，須以試誤方式檢視結果，
這也是 archive 資料夾名稱直接記錄當年試用值的原因，例如 `(backtilted 020 -20)`。
本程式的作用僅在於加速試誤過程，並明確標示當前套用的旋轉；
參考面的選擇與旋轉角度的判斷仍由使用者決定。

## 多站彙整

單次反演回答的是一個站。一項研究真正要問的是一整批站說了什麼，
這即是 `make_survey.py` 與 `pytector.survey` 的用途。將它們指向一棵
TENSOR run 資料夾樹，即可產出全部解答的表格、其背後的斷層資料、
可直接投圖的點位（CSV 與 GeoJSON），以及各變形期的軸向玫瑰圖。

兩個側邊檔案為選用，且屬於使用者自己的判斷：`run,stage` 的 CSV 指出哪一個 run
屬於哪一期，以及 `site,longitude,latitude` 的座標 CSV。
**一個解屬於哪一期是判斷而非計算，程式不會替你猜。**

玫瑰圖採軸向而非方向統計，因為應力軸沒有箭頭：020 與 200 是同一條線，
故採倍角法，使兩端互相加強而非互相抵消。
此外，唯有淺傾的軸其 trend 才視為方向；較陡的軸會被剔除，
且剔除了幾個會直接印在圖上而非默默略過。
兩項決定的完整說明見 `pytector/rose.py`。

## 驗證

十一個測試檔全數通過。有 archive 時即讀取，無 archive 時則 skip，不會 fail。

涵蓋範圍包括：整條流程分別對照原程式輸出與公開 fixture、INFO1 與 MOHR1 的
版面、打字輸入的解析、回轉慣例、等變性結果、影響力診斷、軸向統計，
以及 session 存讀一輪。各測試各自驗證什麼見 [`tests/`](tests/)。

0406-7（29 筆，傾角 42-89°）是確立演算法的關鍵站點：

```
前向模型 vs MOHR1        max |SIGMN| 0.001  |TAU| 0.001  |TAUST| 0.001
                         max |RUP|   0.099  |ANG| 0.113
INVDIR 流程              sigma1 0.047 度   sigma2 0.020   sigma3 0.032
                         Phi 0.138（檔案 0.138）
                         平均 ANG 20.898（20.900）  平均 RUP 54.097（54.100）
                         印出的 LAMBDA 0.682（0.680）
```

L12（六個近平行、近垂直的面）為簡併站點，重現程度較為寬鬆：軸約 1°、
平均 RUP 在 0.6 % 以內。容差係**逐站設定**以反映此差異，而非全域放寬。

測試中不會建立任何 Qt 物件：自動化 shell 啟動 QApplication 會彈出平台外掛
錯誤對話框並結束程序。測試改以驗證介面與函式庫之間的契約為主。

## 參考資料集

測試與推導腳本會讀取原程式的實際輸出。該資料屬**未發表的野外資料**，
因此路徑不寫入原始碼中：

```
set PYTECTOR_ARCHIVE=<放 TENSOR run 資料夾的那個目錄>     REM Windows
export PYTECTOR_ARCHIVE=<放 TENSOR run 資料夾的那個目錄>  # macOS、Linux
```

未設定時測試會 skip，不會 fail。資料本身不隨本 repo 發布。

## 授權與致謝

本 repo 的程式碼以 **MIT 授權**釋出，全文見 [LICENSE](LICENSE)。
若本工具對已發表研究有所助益，歡迎在引用 Angelier 原始論文之外一併引用本 repo，
但並非必要。

以下三項不在本授權範圍內，因為它們並非本專案所能授權的對象：

- **方法本身**為 Jacques Angelier 所提出，載於前文所引論文。本專案係依其發表的
  論文，並輔以對其程式輸出檔案的量測所完成的獨立重寫，未自原執行檔取用任何
  程式碼。
- **參考資料集**屬未發表的野外資料，未隨本 repo 發布，亦不在本授權範圍內
  （見「參考資料集」一節）。
- **開啟畫面**採用 Angelier 繪製的台灣弧陸碰撞塊體圖。他以玉里附近的地震震源
  機制作為「將此方法應用於地震學資料」的示範案例（1994, fig. 4.44）。該圖為
  已發表的圖件，**未**納入本 repo，因此新 clone 的版本不會有開啟畫面，
  其後的彩蛋亦無法開啟。將 `Taiwan Tectonic Map.jpg` 置於專案根目錄即可恢復兩者，
  僅限本機使用。

維護者：Chi-Hsiu Pang。

## 尚未實作

- 寫出 TENSOR 格式的資料檔（站頭欄位已由原程式實際執行解出，
  見 [docs/mesure_oracle.md](docs/mesure_oracle.md)）
- R4DT／R4DS／R2DT／R2DS 等 Angelier 的疊代搜尋法，刻意尚未著手
  （TENSOR 自身的說明文件有相關記載，見 docs/mesure_oracle.md）

## 更新紀錄

見 **[CHANGELOG.md](CHANGELOG.md)**。
