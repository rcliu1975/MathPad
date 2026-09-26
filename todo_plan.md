
  # MathPad 改為 NumPy 數值引擎與循序計算

  ## 摘要

  將目前以 SymPy expression tree 為核心的 Python solver，改成純數值執行模型：

  • 使用 NumPy ndarray、ufunc 與線性代數功能。
  • 依 MathPad cell 順序由上到下計算。
  • 每個 cell 只能使用自己與前面 cell 已產生的數值。
  • 移除符號結果、解析微分、解析積分、符號矩陣與無初值方程求解。
  • 保留數值公式、單位分析、矩陣、繪圖、資料表、插值、CoolProp 與 NumPy code cell。
  • 採破壞式簡化；舊檔只在內容可轉成數值流程時開啟。

  ## 主要實作變更

  ### 1. 重寫 Python 計算核心

  重構 public/dimensional_analysis.py：

  • 移除所有 SymPy import、sympify、Expr、Symbol、solve、nsolve、lambdify、LaTeX printer 與 expression substitution 流程。

  • 建立數值環境，例如：

    namespace = {
        "np": numpy,
        "sin": numpy.sin,
        "cos": numpy.cos,
        "sqrt": numpy.sqrt,
        "log": numpy.log,
        "exp": numpy.exp,
        ...
    }

  • 將 parser 產生的 expression 轉成可安全執行的 Python/NumPy expression。

  • 使用受限 eval 或預先編譯的 evaluator 執行公式，不允許任意 Python globals。

  • 變數環境只保存數值、numpy.ndarray、單位資訊與函式。

  • 所有結果統一為 numeric result；移除 symbolicValue 及 symbolic flags。

  • 矩陣改用 numpy.ndarray，對應：
      • 矩陣乘法：np.matmul
      • 轉置：.T
      • 反矩陣：np.linalg.inv
      • 行列式：np.linalg.det
      • norm：np.linalg.norm
      • dot：np.dot

  ### 2. 改成 cell 順序執行

  修改 App.svelte 與 solver input 結構：

  • 不再將 assignment、function、plot query 等 statement 拆到 endStatements 最後執行。

  • 保留原始 cell 順序建立 execution list。

  • Python solver 逐一處理 execution list：
      1. 讀取目前 namespace。
      2. 驗證依賴變數已存在。
      3. 計算目前 cell。
      4. 將結果寫回 namespace。
      5. 產生該 cell 的 UI result。

  • 一個 cell 失敗時，該 cell 顯示錯誤；後續依賴它的 cell 顯示「前置 cell 無有效結果」。

  • 保留現有 worker，但 worker 只負責單一 sheet request；不再依賴全域 symbolic solver。

  ### 3. 移除 SymPy 相關介面

  前端移除或改名：

  • sympyMode 與「Use SymPy Mode」。
  • symbolicOutput。
  • simplifySymbolicExpressions。
  • sympy 欄位改成中性的 expression 或 sourceExpression。
  • LatexToSympy.ts 改名為數值 expression parser，並移除產生 SymPy 專用語法的內容。
  • 移除符號格式化與 symbolic result 顯示分支。
  • 保留 mathjs，因為它目前負責單位解析與單位換算，不是 SymPy 替代品。

  ### 4. 明確限制不支援的功能

  以下功能在新版本中移除或標記為不支援：

  • 無數值輸入的符號表示式。
  • 解析微分與解析積分。
  • 沒有初始值的 system solve。
  • sympyMode code cell。
  • 符號矩陣與含未定義變數的矩陣運算。
  • 符號輸出、符號化簡與分數保持功能。

  純數值的 piecewise、sum、product、range、插值與繪圖保留；需要 SciPy 的高階數值求解不納入第一版。

  ### 5. Pyodide 與建置清理

  修改：

  • src/pyodideWorker.ts：預設只載入 NumPy。
  • scripts/get_pyodide_files.py：移除 SymPy、isympy 與相關下載檔案。
  • src/pyodide-info.json：移除 SymPy metadata。
  • README.md：更新計算核心、限制與舊資料說明。
  • 移除不再使用的 SymPy runtime assets，確認 npm run build 不會再打包 SymPy。

  ## 測試計畫

  新增或改寫 Playwright 測試，至少涵蓋：

  • 純量公式依序計算：

    a = 2
    b = a + 3
    b * 4 = 20

  • 後方 cell 不能被前方尚未計算的變數使用。

  • 變數不存在時顯示前置依賴錯誤。

  • NumPy 三角函數、平方根、陣列與矩陣運算。

  • NumPy matrix inverse、determinant、transpose。

  • 單位檢查與單位換算仍正常。

  • piecewise、range、plot、data table、interpolation。

  • code cell 可使用 NumPy，但不能使用 SymPy。

  • 一個 cell 錯誤時，後續依賴 cell 的錯誤傳播。

  • 舊 .epxyz：
      • 純數值檔案可開啟並重新計算。
      • 含 symbolic expression、system solve 或 symbolic mode 時顯示明確 migration error。

  • 確認產物與 source 中不再載入 SymPy。

  • 執行既有非符號測試，刪除或改寫所有依賴 symbolic output 的測試。

  ## 假設與預設

  • 「循序處理」採「依 cell 順序計算」。
  • 不保留符號運算與舊 SymPy mode。
  • 第一版只使用 NumPy，不加入 SciPy 數值方程求解。
  • mathjs 保留作為前端單位與輸入解析工具。
  • 舊格式採破壞式相容策略，不保證所有既有 .epxyz 可開啟。


