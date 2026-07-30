# 為什麼照論文重建,以及為什麼叫 pyTECTOR

關於本專案來源的兩個問題:為什麼沒有反譯原始執行檔,以及名稱的由來。

回到 [README](../README.md)。

---

## 為什麼不反譯

`Tensor.exe` 是 208 KB 的 16 位元 MS-DOS 執行檔，含 5252 個重定位項、無符號表、
疑似以 Turbo Pascal 編譯、含 overlay，浮點運算很可能採軟體模擬。
64 位元 Windows 已移除 NTVDM，因此它無法執行。
反譯不可行的理由相當常見：編譯過程已移除名稱、型別與結構，
而 16 位元分段定址使指標無法靜態解析。

演算法本身在論文中已完整發表（見上方英文段落所列三篇）。
因此本專案的工作集中於研讀論文，以及**量測原程式自身產生的輸出檔案**，
以補足論文未載明的部分。

## 為什麼叫 pyTECTOR

Angelier 的論文全篇未為程式命名，只稱之為「the new direct inversion
method」。名稱出自程式自身，印在它產生的每一份 INFO1 上：

```
Progr. TENSOR, 1975-1991,  version 5.45, jan91
Copyright 1987,1988,1989,1990,1991 J. Angelier

*** DATA BASE FOR TECTONIC ORIENTATIONS "TECTOR" ***
```

最直接的致敬名稱應為 TENSOR，但該名稱已有兩處衝突：在古應力領域中，
「the TENSOR program」現指 Delvaux 的 TENSOR／Win-Tensor（Delvaux & Sperner 2003），
與 Angelier 無關；而 PyPI 上的 `pytensor` 是 PyMC 團隊持續維護的張量運算庫，
import 名稱會與實際安裝環境衝突。橫幅上的另一個名稱 **TECTOR** 同樣出自 Angelier，
且目前無其他專案使用，故定名為 pyTECTOR。
