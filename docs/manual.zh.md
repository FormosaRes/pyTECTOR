# pyTECTOR 使用手冊

介面每個功能、完整操作流程、輸入與輸出格式。
方法本身（準則、兩種跑法、λ、等變性）在 [README](../README.md)；
這份只講**怎麼用**。

---

## 目錄

1. [安裝與啟動](#1-安裝與啟動)
2. [主視窗總覽](#2-主視窗總覽)
3. [輸入資料](#3-輸入資料)
4. [反演（INVERT）](#4-反演invert)
5. [讀結果](#5-讀結果)
6. [讀圖：Angelier 畫風的符號](#6-讀圖angelier-畫風的符號)
7. [回轉視窗（Back-tilt）](#7-回轉視窗back-tilt)
8. [傾轉檢驗（Tilt test）](#8-傾轉檢驗tilt-test)
9. [輸出](#9-輸出)
10. [1991 模式](#10-1991-模式)
11. [批次與命令列](#11-批次與命令列)
12. [疑難排解](#12-疑難排解)

---

## 1. 安裝與啟動

**請先裝 Anaconda 或 Miniconda。** 各平台都強烈建議：可以避開 Microsoft Store
的 `python` 樁（PyQt5 在它底下不能用，這是安裝失敗最常見的原因），
而且 scipy 與 Qt 都以預先編譯好的二進位檔提供，不需要現場編譯。
Miniconda 就夠了。<https://www.anaconda.com/download/success>，
預設選項就好，不需要管理員權限，也不用勾「Add to PATH」。

**一鍵安裝**：雙擊 repo 根目錄的 **`install.bat`**，
macOS 與 Linux 則跑 **`install.command`**。兩者都會自己找 Python
（優先 Anaconda 與 Miniconda，並排除 Store 樁）、裝好四個依賴
（numpy、scipy、matplotlib、PyQt5，pip 裝不起來就改用 conda-forge）、
確認四個真的能 import、把用的直譯器記進 `python-path.txt` 讓啟動器用同一個、
做編譯檢查、在桌面放一個 pyTECTOR 捷徑。可以重複執行，不會弄壞什麼。

機器上完全沒有 Python 的話，安裝腳本會問要不要代為從 `repo.anaconda.com`
下載並安裝 Miniconda（約 80 MB，只裝給目前使用者）；回答 `n` 則改開下載頁。

手動的話：Python 3.8 或更新，加上那四個套件（Anaconda 只缺 PyQt5），然後：

```
pyTECTOR.bat        雙擊啟動
python pyTECTOR.py  或從命令列
pip install .       亦可，會安裝 pytector 指令
```

開啟畫面（Angelier 的台灣塊體圖）顯示 4 秒，點一下、按任意鍵、或等它自己消失都會進入主程式。
沒有 `Taiwan Tectonic Map.jpg` 時直接進主程式。

選用的環境變數：

```
set PYTECTOR_ARCHIVE=<放 TENSOR run 資料夾的目錄>
```

只有測試與推導腳本用它；日常操作不需要。

## 2. 主視窗總覽

```
┌───────────────────────────────────────────────────────────────────┐
│ 工具列  Open site  Scan folder  Clear │ ☑INVDIR ☑S4MIN ☐Fitted   │
│         INVDIR pass [1]  ☐archive LAMBDA  decl [1.95]             │
│         [INVERT]  Back-tilt │ Save PNG  HPGL  INFO1  MOHR1  About │
├──────────────┬────────────────────────────────────────────────────┤
│ 側欄         │  SITE L12   6 faults   1 excluded      (context 行)│
│  SITE        │ ┌────────────────────────────────────────────────┐ │
│  NEW RECORD  │ │            立體投影網（一到三格）              │ │
│  REFERENCE   │ └────────────────────────────────────────────────┘ │
│  PLANES      ├────────────────────────────────────────────────────┤
│  FAULT SLIPS │  Results │ INFO1 │ MOHR1                (下方分頁) │
│  （表格）    │                                                    │
├──────────────┴────────────────────────────────────────────────────┤
│ 狀態列                                          [進度條]          │
└───────────────────────────────────────────────────────────────────┘
```

分工原則：**主視窗只呈現實測資料、只做反演**。旋轉一律在回轉視窗做（第 7 節），
所以主視窗的圖永遠不需要標題來說明「現在畫的是轉過的還是沒轉的」。

投影圖上方常駐一行 context：站名、幾筆斷層、幾筆排除、幾個參考面。
資料改過而結果還是舊的時，這一行旁邊會出現紅色 **press INVERT** 標記，
圖上也會蓋半透明的 OUT OF DATE 浮水印。看到它就是要重按 INVERT。

## 3. 輸入資料

### 3.1 手動輸入（NEW RECORD）

四個欄位，對應原程式 MESURE 的格式：

```
CS - 122 - 87W - 124
│     │     │     └─ rake＋象限字母（62N），或不帶字母的 trend（124）
│     │     └─────── 傾角＋象限字母
│     └───────────── 走向 000–360
└─────────────────── 信心度＋運動方式
```

**第一欄**兩個字母：

| 字母 1（信心度） | 字母 2（運動方式） |
|---|---|
| C = certain 確定 | I = inverse 逆斷 |
| P = probable 可能 | N = normal 正斷 |
| S = supposé 推測 | S = senestral 左移 |
| | D = dextral 右移 |

信心度決定圖上擦痕符號的箭頭頭部（C 完整頭、P 單邊倒鉤、S 無頭）。
運動字母只是備註；實際滑動方向由第四欄的 rake/trend 決定。

這只是 MESURE 代碼系統中「有擦痕斷層」的部分；原系統第一字母還有
`*`（有擦痕、動向未知）、`F`（無擦痕斷層）、`J`（節理與層面）、
`M`（變質面）、`L`（線理）、`A`（褶皺軸），各有自己的第二字母表，
而且原程式明講兩個特例：鉛直擦痕填**下滑側**方位字母（N/E/W/S）、
水平斷層填**下盤運動方向**。pyTECTOR 讀的是有擦痕斷層的記錄；
從程式內嵌 HELP 文字還原的完整代碼表見
[mesure_oracle.md](mesure_oracle.md#mesures-own-help-the-complete-structure-code-system)。

**第三欄**：傾角 + 傾向象限。`87W` = 傾角 87°、往西傾。
程式用象限字母從走向解出真正的傾向，所以走向寫 `122` 或 `302` 都可以。

**第四欄**兩種寫法：
- **帶字母** = rake（pitch），0–180，從象限字母指的那一端走向線量起。例 `62N`。
- **不帶字母** = 滑動線的 trend，0–360。程式自己解出它在面上的 rake。例 `124`。

archive 兩種都有：0406-7 是 rake 式、L12 是 trend 式。

操作細節：欄位打滿自動跳下一欄；空欄按 Backspace 退回上一欄；
任何欄按 **Enter** 送出整筆。格式錯會彈訊息說明哪一欄錯。

### 3.2 開舊檔（Open site / Scan folder）

**Open site**：選一個 TENSOR 站檔，就是那個**沒有副檔名、檔名＝站名**的檔（例 `L12`、`0406-04`）。

**Scan folder**：選一個根目錄，程式遞迴找出底下所有 TENSOR run 列成清單，雙擊或按 Open 載入。

載入時會發生的事：

1. 斷層資料全部進表格，站名進側欄的 SITE 欄
2. 檔案裡如果有當年的 `03` 結果行，**archive** 結果條會出現，顯示當年算的 σ₁σ₂σ₃／Φ
3. 同資料夾如果有 `INFO1`：
   - `(NO k)` 自動填進工具列的 **INVDIR pass**
   - 記錄的 λ 自動啟用並勾選 **archive LAMBDA**（按鈕上直接顯示數值）

也就是說開一個舊 run 之後直接按 INVERT，就是照當年的設定重跑。

### 3.3 斷層表（FAULT SLIPS）

| 欄 | 內容 |
|---|---|
| # | 編號 |
| use | 勾選框。取消＝這筆不進反演、不進圖，整列變灰但留著 |
| type | 信心度＋運動字母 |
| as typed | 當初輸入的原字串 |
| strike / dip / rake | 解出來的正規值 |

排除是可逆的：勾回來就恢復。排除筆數顯示在表格下方與 context 行。
選取列後按 **Delete** 鍵或 Delete 按鈕才是真的刪除。

**Clear**（工具列）清空整站，回到空白狀態。

### 3.4 參考面（REFERENCE PLANES）

給回轉視窗用的面（通常是 S₃ 葉理或層面）。輸入兩種：

- **plane**：走向＋傾角象限，跟斷層同一套寫法（`122` `87W`）
- **pole**：面的極點 trend／plunge（`045` `12`）

可以放多個。清單裡**雙擊**（或選取後按 Set as reference）把某一面設為回轉基準面，
前面出現 `*`，圖上畫成**長虛線**；其他面是短虛線。每個面都帶著自己的空心圓 pole。

## 4. 反演（INVERT）

至少要 4 筆有效斷層（張量四個未知數）。按 **INVERT** 或 **Ctrl+Enter**。
計算在背景執行緒跑，狀態列出現進度條；算完各結果條與 INFO1／MOHR1 分頁一起更新。

工具列選項：

| 選項 | 作用 |
|---|---|
| ☑ INVDIR | 跑 Angelier 原方法（含 PSIDIR 收尾）。要對舊 run、對文獻就用它 |
| ☑ S4MIN | 跑同一準則的精確最小值。當穩健性檢驗 |
| INVDIR pass | `(NO k)` 的 k，λ 迭代趟數。重現舊 run 要跟 INFO1 記的一致；開舊檔會自動帶入 |
| ☐ archive LAMBDA | 採用該站 INFO1 記錄的 λ 而不是重新推導。**重現當年那次 run 用的**；只有載入帶 INFO1 的站才能勾。細節見 README |
| ☐ Fitted shear | 多畫一格：同一批面載著解算出的剪應力方向，Angelier 用來目視檢查擬合好壞的那張圖 |
| decl | 磁偏角，只移動圖上的 M 記號，**不旋轉資料** |

## 5. 讀結果

Results 分頁最多四條結果條，每條都標明自己是什麼：

```
ARCHIVE   what the old run recorded     ← 檔案裡當年的結果（有 03 行才出現）
INVDIR    as TENSOR 5.45 runs it
S4MIN     exact minimum of the same criterion
```

每條顯示：σ₁ σ₂ σ₃（trend/plunge）、Φ、ANG（平均剪應力–擦痕夾角）、
RUP（平均 RUP %）、小字 n／S₄／RUP>75 筆數。

兩種方法都勾時，下面多一行**差異行**：兩解各軸夾角、ΔΦ、ΔS₄。
Φ 接近 0 或 1 時它會提醒你有一根軸近簡併、分歧多半集中在那裡。

品質判讀的慣例（Angelier 1990）：

| 指標 | 好 | 可疑 |
|---|---|---|
| 單筆 ANG | < 22.5° | > 45° 該筆與解不合 |
| 平均 ANG | 7–19° 是他發表例子的範圍 | |
| 單筆 RUP | < 50 % | > 75 % 該筆可疑 |

單筆的 ANG／RUP 去 INFO1 分頁看，超標的筆會帶 `!`／`!!` 旗標。

**INFO1 / MOHR1 分頁**：螢幕顯示精簡版（略去橫幅），存檔時是完整版。
欄位意義：SIGMA=|σ|、SIGMN=σₙ、TAU=|τ|、TAUST=s·τ、RMU=|τ|/|σₙ|、
OBL=arctan(|σₙ|/|τ|)、RUP、ANG。

## 6. 讀圖：Angelier 畫風的符號

畫風逐筆量自原程式的 HPGL 檔，等面積（Schmidt）下半球投影。

| 符號 | 意義 |
|---|---|
| 細實線大圓 | 斷層面 |
| 實心圓點＋雙軸線 | 擦痕：點是滑動線出點，兩支平行短線是剪切對偶（所以呈 Z 形不是一直線），沿上盤運動的水平方向 |
| 箭頭頭部 | C 兩段式細長頭／P 單邊倒鉤／S 無頭，跟輸入的信心度對應 |
| 五角星 | σ₁ |
| 四角星（斜置） | σ₂ |
| 三角星 | σ₃ |
| 星形大小 | 隨 Φ 與特徵值變化（大小順序在 Φ=0.5 兩側翻轉），跟原程式同一條公式 |
| 圓外粗箭頭 | 沿 σ₁ 向內＝壓縮、沿 σ₃ 向外＝伸張；軸傾沒 >45° 那對不畫 |
| N | 地理北，圓外正上方 |
| M＋折線 | 磁北，位置由 decl 欄控制 |
| 虛線大圓＋空心圓 | 參考面與其 pole；長虛線＝回轉基準面 |
| 站碼（圖上方） | 側欄 SITE 欄的內容 |

螢幕上每格圖多一行標題（INVDIR／S4MIN／FITTED SHEAR）；
匯出的 PNG／HPGL 不帶這行，維持 Angelier 原版面。

## 7. 回轉視窗（Back-tilt）

工具列 **Back-tilt** 開啟，非強制回應（可以跟主視窗來回切換）。

開啟時把主視窗的資料**拷貝**進來（不是連動；主視窗改了資料要按 **Reload data** 重新帶入，
確保螢幕上的一對圖永遠對應同一批數字）。

### 7.1 設定旋轉

上方下拉選旋轉來源：

- **restore the reference surface to horizontal**：把主視窗標了 `*` 的參考面轉回水平。
  沒有標基準面時會提示你回主視窗標。
- **rotation axis trend / plunge / angle**：直接給軸與角度，右手定則。

**restore %**（0–125）：部分回轉。100 % = 全轉；低於 100 把斷層當成在傾轉中途就形成。

視窗上方永遠顯示當前旋轉：軸、角度、以及 archive 命名格式（`backtilted 020 -20`）。

### 7.2 Invert both

按 **Invert both**：實測與回轉後**兩個狀態各跑一次**勾選的方法，左右並排：

- 左圖 AS MEASURED：實測資料＋實測的解
- 右圖 BACK-TILTED：轉過的資料＋重算的解，參考面跟著轉
  （回轉正確時虛線圓會壓平、pole 走向圓心）

**☑ carried axes**：右圖多畫三個**空心圈＋虛線弧**——
實測的 σ₁σ₂σ₃ 經同一旋轉轉過去的位置，弧連到重算的星形。
圈＝「答案跟著轉」、星＝「轉了資料重算」。

⚠️ 圈星不重合時讀法要小心：S4MIN 兩者必然重合（S₄ 旋轉不變）；
INVDIR 天生不重合（參數化釘在地理座標），那個差距是方法不是地質，
archive 實測中位 σ₁ 10°、σ₂σ₃ 約 24°。**判斷軸有沒有回到水平／垂直，看 S4MIN。**
詳細見 README「回轉」一節。

### 7.3 下方數字區

每個方法四行：實測與回轉後的 σ₁σ₂σ₃／Φ／ANG／S₄／Andersonian 失配（含應力體制判斷）、
carried vs re-inverted 各軸夾角。回轉後軸**遠離**水平垂直時直接警告
「this rotation is not supported」。

**Save PNG** 存這個視窗的並排圖（帶 Angelier 式數字標註）。

## 8. 傾轉檢驗（Tilt test）

回轉視窗按 **Tilt test**。把當前旋轉從 0 % 掃到 125 %，每一步都反演，畫兩條曲線：

| 曲線 | 意義 |
|---|---|
| 擬合品質（ANG／RUP／S₄） | 最佳落在 ~100 %：斷層早於傾轉，全回轉合理。最佳落在中途：同傾轉斷層 |
| Andersonian 失配 | 最陡軸離鉛直多遠。落到 0 = 一垂直兩水平 |

兩條曲線最佳位置差超過旋轉量 20 % 時程式會標出來——那個分歧要先解釋，兩個都先別信。

看完可以在 **adopt** 欄選一個百分比按 **Use this restoration**，
回轉視窗自動切到「rotation axis」模式並填入對應的軸與角度。

## 9. 輸出

| 按鈕 | 內容 |
|---|---|
| Save PNG（主視窗） | 目前的圖，300 dpi。匯出版去掉螢幕標題、加上 Angelier 式兩行數字標註（S1 S2 S3／PHI ANG RUP N），維持原版面 |
| Save PNG（回轉視窗） | 實測＋回轉並排圖，同樣帶標註 |
| Save HPGL | 繪圖機向量檔，**原程式的方言與座標**（scale 2002、origin 2908,3008，可跟 archive 的 HPGL 疊圖）。內容＝重播螢幕畫圖程式，整張圖都在：擦痕、刻度、十字、N/M、外框、粗箭頭、參考面 |
| Save INFO1 | 完整版 INFO1（含橫幅），版面與原程式逐欄一致，可被 `pytector.tensorfile` 讀回 |
| Save MOHR1 | 同上，MOHR1 |

注意：INFO1／MOHR1 以畫面上**第一個有結果的方法**為準（勾了 INVDIR 就是 INVDIR）。
橫幅寫 pyTECTOR，不冒充 TENSOR 5.45；機器讀的部分（定寬表、03 行）維持原樣。

## 10. 1991 模式

彩蛋。觸發：**開啟畫面上點 J.A. 簽名**。

變化：Turbo Pascal 藍的 DOS 配色、雙線框、等寬字、
投影圖變黑底磷光綠、關掉反鋸齒（線條呈像素階梯）、
介面文字切成法文——其中標為 ORIGINAL 的詞彙直接取自原程式輸出檔
（CALCUL DU TENSEUR DES CONTRAINTES、MOYENNE、ECART-…），
哪些是原文哪些是我們補譯的，About 的「1991 mode」分頁有完整清單。

**計算完全不變。** 回到現代介面：工具列右側會出現 **MODE 1991 ×**，按它。

## 11. 批次與命令列

```
python demo_report.py [站檔]          反演一個舊站，印 INFO1＋MOHR1 到終端
python run_batch.py [根目錄] [out.csv] 掃描所有 run，兩種方法都跑，結果進 CSV
python demo_fitted.py                  畫 observed vs fitted 對照圖
```

函式庫可以直接 import 用，不經 GUI：

```python
from pytector import read_site, invdir, modern, core
site = read_site(r'...\L12\L12')
r = invdir.run(site.n, site.s, n_pass=2)      # INVDIR
b = modern.run(site.n, site.s)                # S4MIN
print(core.summary(r['T'], site.n, site.s)['sigma1'])
```

## 12. 疑難排解

| 症狀 | 原因與解法 |
|---|---|
| 按 INVERT 跳「Four fault slips are the minimum」 | 有效斷層不足 4 筆。檢查 use 欄是不是排除太多 |
| 輸入被拒（訊息說哪一欄錯） | 對照第 3.1 節格式；dip 0–90、rake 0–180、trend 0–360 |
| archive LAMBDA 是灰的 | 該站不是從帶 INFO1 的資料夾載入的。手動輸入的資料沒有「當年的 λ」可以採用 |
| 圖上出現 OUT OF DATE | 資料或設定在上次反演後改過。重按 INVERT |
| Back-tilt 視窗說 mark a reference surface | 回主視窗參考面清單雙擊一個面標成 `*`，再按 Reload data |
| 回轉視窗資料不對 | 忘了按 Reload data。它用的是開窗當下的拷貝 |
| 兩種方法答案差很多 | 先看 n 與 Φ：n<7 或 Φ 近 0/1 時本來就會（README 有統計）。差距跨過你的分期界線才需要追 |
| 想重現舊 run 但差 1° | 確認 INVDIR pass 跟 INFO1 的 (NO k) 一致、archive LAMBDA 有勾 |
| HPGL 疊不上舊圖 | 用 0.2.0 之後的版本（舊版尺度錯 1/4） |
| `ModuleNotFoundError: No module named 'PyQt5'` | 啟動器跑的 Python 跟裝套件的那個不是同一個。重跑 `install.bat`（或 `install.command`）：它會把直譯器記進 `python-path.txt`，之後啟動器就用那一個 |
| 打 `python` 會跳出 Microsoft Store | 那是 Store 樁不是直譯器。裝 Miniconda 後重跑安裝腳本，它會依路徑排除那個樁 |
| 安裝腳本什麼都裝不起來 | 多半是 proxy 擋 pip，或根本沒網路。有 conda 時它會自己改用 conda-forge，所以先裝 Miniconda 常常就解決了 |
| 桌面捷徑點了沒反應 | 捷徑指向你跑安裝腳本時那個資料夾裡的 `pyTECTOR.bat`。資料夾搬走或改名就會失效，在新位置重跑一次 `install.bat` 即可 |
