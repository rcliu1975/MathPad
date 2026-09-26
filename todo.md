# MathPad：NumPy 數值引擎與循序計算

## 目標

- 將目前以 SymPy expression tree 為核心的計算流程改為純數值計算。
- 使用 NumPy `ndarray`、ufunc 與線性代數功能。
- 依 MathPad cell 順序由上到下計算。
- 每個 cell 只能使用自己與前面 cell 已產生的數值。
- 保留數值公式、單位、矩陣、繪圖、資料表、插值、CoolProp 與 NumPy code cell。
- 移除符號輸出、解析微分、解析積分、符號矩陣與無初值方程求解。

## 明確範圍與限制

- [ ] 不支援符號表示式與符號結果。
- [ ] 不支援解析微分與解析積分。
- [ ] 不支援沒有初始值的 system solve。
- [ ] 不保留 `sympyMode` code cell。
- [ ] 不保留 `symbolicOutput` 與 `simplifySymbolicExpressions` 設定。
- [ ] 純數值的 piecewise、sum、product、range、插值與繪圖保留。
- [ ] 第一版只使用 NumPy，不加入 SciPy 數值方程求解。
- [ ] 保留 `mathjs`，因為它仍負責前端單位解析與換算。
- [ ] 舊 `.epxyz` 採破壞式相容策略；不可轉成數值流程的內容顯示明確錯誤。

## Phase 1：盤點與介面設計

- [ ] 列出 `public/dimensional_analysis.py` 中所有 SymPy 相依函式、型別與資料流。
- [ ] 定義數值 execution environment 的結構：變數、函式、單位、矩陣與 cell result。
- [ ] 定義數值 expression 的輸入格式，將 `sympy` 欄位改成中性的 `expression` 或 `sourceExpression`。
- [ ] 定義錯誤傳播規則：目前 cell 錯誤、後續依賴錯誤與獨立 cell 的行為。
- [ ] 定義結果格式，移除 `symbolicValue` 以及 symbolic flags。

## Phase 2：建立 NumPy 數值核心

### Python solver

- [ ] 移除 `public/dimensional_analysis.py` 的 SymPy import。
- [ ] 移除 `Expr`、`Symbol`、`sympify`、`solve`、`nsolve`、`lambdify`、LaTeX printer 與 expression substitution 流程。
- [ ] 建立受限 NumPy namespace，提供 `sin`、`cos`、`sqrt`、`log`、`exp` 等常用函式。
- [ ] 建立安全的 expression 編譯與執行流程，不暴露任意 Python globals 或 builtins。
- [ ] 以數值環境取代 SymPy expression tree。
- [ ] 將純量結果統一為 numeric result。
- [ ] 將矩陣改用 `numpy.ndarray`。
- [ ] 以 NumPy 實作矩陣乘法、轉置、反矩陣、行列式、norm 與 dot。
- [ ] 以 NumPy 實作數值 piecewise、sum、product 與 range。
- [ ] 保留並改接現有單位分析、CoolProp、插值與繪圖資料產生流程。
- [ ] 移除 symbolic simplification、symbolic formatting 與 symbolic result output。

### Pyodide

- [ ] 修改 `src/pyodideWorker.ts`，預設只載入 NumPy。
- [ ] 修改 `scripts/get_pyodide_files.py`，移除 SymPy、`isympy` 與相關下載項目。
- [ ] 修改 `src/pyodide-info.json`，移除 SymPy metadata。
- [ ] 確認必要的 CoolProp、SciPy 或 scikit-learn 只在仍保留的功能需要時載入；第一版不以 SciPy 實作 system solve。
- [ ] 清理不再使用的 SymPy runtime assets。

## Phase 3：改為依 cell 順序計算

### 前端 statement pipeline

- [ ] 修改 `src/App.svelte`，保留 cell 原始順序建立 execution list。
- [ ] 移除將 assignment、function、plot query 等 statement 延後放入 `endStatements` 的全域重排邏輯。
- [ ] 移除依賴全域 SymPy solver 的 sub-query 與 expression substitution 流程。
- [ ] 讓每個 cell 的輸入、輸出與結果位置可直接對應。
- [ ] 保留 refresh counter，避免舊計算結果覆蓋新輸入。
- [ ] 確認同一時間只處理一個 sheet solve request。

### Python execution pipeline

- [ ] 逐一讀取 execution list 中的 cell。
- [ ] 讀取目前 namespace 與前置 cell 結果。
- [ ] 驗證依賴變數已存在且為有效數值。
- [ ] 計算目前 cell。
- [ ] 將成功結果寫回 namespace。
- [ ] 產生對應的 UI result。
- [ ] cell 失敗時保留錯誤資訊，後續依賴該 cell 的內容顯示前置依賴錯誤。
- [ ] 不影響與該錯誤 cell 無關的後續數值 cell。

## Phase 4：移除 SymPy UI 與 TypeScript 型別

- [ ] 移除 `sympyMode` 與「Use SymPy Mode」選項。
- [ ] 移除 `symbolicOutput` 控制項與相關格式化分支。
- [ ] 移除 `simplifySymbolicExpressions` 設定、dialog 與序列化欄位。
- [ ] 將 `LatexToSympy.ts` 改為數值 expression parser，移除 SymPy 專用命名與語法。
- [ ] 更新 parser types，將 `sympy` 欄位改成 `expression`。
- [ ] 更新 `resultTypes.ts`，移除 symbolic result 欄位。
- [ ] 移除 `CodeCell` 的 `sympyMode` 儲存與傳遞。
- [ ] 確認 `GenerateCodeDialog` 產生的程式碼只使用 NumPy / 數值 API。
- [ ] 更新舊檔讀取時的明確錯誤訊息與 migration 提示。

## Phase 5：測試

### 數值計算

- [ ] 測試依序計算：`a = 2`、`b = a + 3`、`b * 4 = 20`。
- [ ] 測試前方變數不存在時的錯誤。
- [ ] 測試 cell 錯誤後，後續依賴 cell 的錯誤傳播。
- [ ] 測試獨立 cell 不受其他 cell 錯誤影響。
- [ ] 測試 NumPy 三角函數、平方根、對數、指數與陣列。
- [ ] 測試矩陣乘法、轉置、反矩陣、行列式、norm 與 dot。
- [ ] 測試 piecewise、sum、product、range 與數值繪圖。

### 既有功能

- [ ] 測試單位檢查與單位換算。
- [ ] 測試 data table 與欄位計算。
- [ ] 測試 interpolation、polyfit 與相關數值結果。
- [ ] 測試 CoolProp fluid cell。
- [ ] 測試 NumPy code cell；確認 SymPy 不可用。
- [ ] 測試 worker request 排隊與 stale result 防護。

### 不支援功能

- [ ] 測試符號輸入會顯示明確錯誤。
- [ ] 測試解析微分與積分會顯示不支援錯誤。
- [ ] 測試無初值 system solve 會顯示不支援錯誤。
- [ ] 測試舊檔含 symbolic expression 或 `sympyMode` 時的 migration error。

## Phase 6：清理與文件

- [ ] 更新 `README.md` 的計算核心、支援範圍與限制。
- [ ] 移除或改寫所有依賴 symbolic output 的測試。
- [ ] 搜尋整個 repo，確認不再載入或執行 SymPy。
- [ ] 執行 `npm run build`。
- [ ] 執行完整 Playwright 測試。
- [ ] 檢查產物大小，確認 SymPy runtime assets 未被打包。
- [ ] 更新版本或 sheet format version，避免新舊格式被誤判為完全相容。

## 完成條件

- [ ] 新建數值工作表可正常由上到下計算。
- [ ] 後方 cell 可使用前方 cell 的數值結果。
- [ ] 結果、錯誤與 cell 順序可穩定對應。
- [ ] NumPy scalar、array 與矩陣測試通過。
- [ ] 單位、繪圖、資料表、插值與 fluid 功能測試通過。
- [ ] UI 不再出現 SymPy mode、symbolic output 或 symbolic simplification 選項。
- [ ] build 與完整測試通過，且 runtime 不再載入 SymPy。
