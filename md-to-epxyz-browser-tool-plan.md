• 以下內容可直接複製成 md-to-epxyz-browser-tool-plan.md：

  # 建立極小型 Markdown 公式轉 `.epxyz` Browser 工具

  ## Summary

  建立一個完全獨立、無後端、無 Node.js runtime 依賴的 browser 工具。

  工具只做一件事：

  ```text
  選擇 Markdown 檔
  → 找出獨立的 $$...$$ 公式區塊
  → 建立 MathPad `.epxyz` 檔
  → 自動下載
  ```

  工具不整合 MathPad UI、不修改 MathPad 主程式，也不處理完整 Markdown。

  ## 固定支援範圍

  只支援獨立公式區塊：

  ```md
  $$
  x = 2
  $$
  ```

  以及單行形式：

  ```md
  $$x = 2$$
  ```

  不支援：

  - 行內公式 `$x^2$`
  - `\(...\)` 與 `\[...\]`
  - Markdown 標題、段落、列表
  - Markdown 表格
  - 圖片與連結
  - 公式區塊內的 Markdown
  - 自動修正或翻譯 LaTeX

  公式內容必須原樣寫入 MathPad math cell。其他 Markdown 內容全部忽略。

  ## 建議檔案結構

  ```text
  tools/md-to-epxyz/
  ├── index.html
  ├── app.js
  ├── converter.js
  ├── styles.css
  └── README.md
  ```

  不加入 Vite、不加入 npm dependency、不要求安裝 Node.js。
 
  若直接開啟 `index.html` 受到瀏覽器限制，可使用：

  ```bash
  python3 -m http.server 8000 --directory tools/md-to-epxyz
  ```

  然後開啟：

  ```text
  http://localhost:8000
  ```

  ## 實作內容

  ### `index.html`

  提供：

  - Markdown 檔案選擇器
  - 可選的拖放區
  - 轉換按鈕
  - 檔案名稱與大小顯示
  - 公式數量顯示
  - 錯誤訊息區
  - 下載結果提示
 
  頁面不使用 framework 或 CDN。
 
  ### `app.js`

  負責 browser UI：
 
  1. 讀取使用者選擇的 `.md` 檔案。
  2. 取得 UTF-8 文字。
  3. 呼叫 `extractFormulaBlocks(markdown)`。
  4. 呼叫 `createEpxyz(formulas, title)`。
  5. 將結果轉成 `Blob`。
  6. 以 `<a download>` 觸發下載。
  7. 預設輸出檔名為原始檔名去除 `.md` 後加上 `.epxyz`。

  例如：

  ```text
  calculation.md → calculation.epxyz
  ```

  若無法取得檔名，使用：
 
  ```text
  converted.epxyz
  ```

  ### `converter.js`

  只放純 JavaScript、無 DOM 的轉換邏輯，提供：

  ```js
  export function extractFormulaBlocks(markdown)
  export function createEpxyz(formulas, title)
  export function convertMarkdownToEpxyz(markdown, title)
  ```

  ### `extractFormulaBlocks(markdown)`

  使用逐行掃描，不使用完整 Markdown parser。

  規則：

  - 單獨的 `$$` 開始公式區塊。
  - 下一個單獨的 `$$` 結束公式區塊。
  - 區塊內允許多行。
  - 支援單行 `$$formula$$`。
  - 去除公式前後空白。
  - 忽略空公式。
  - 未關閉的 `$$` 回報錯誤。

  可接受：

  ```md
  $$
  \frac{a}{b}
  $$
  ```

  ```md
  $$\frac{a}{b}$$
  ```

  不可擷取行內公式：

  ```md
  This is $x^2$ inline formula.
  ```

  公式擷取結果：

  ```js
  [
    "\\frac{a}{b}",
    "x = 2"
  ]
  ```
 
  ### `createEpxyz(formulas, title)`
 
  產生符合 MathPad 現有格式的 JSON。
 
  每個公式產生一個 math cell：
 
  ```json
  {
    "type": "math",
    "id": 0,
    "latex": "x = 2",
    "config": null
  }
  ```

  第二個公式使用遞增 ID：

  ```json
  {
    "type": "math",
    "id": 1,
    "latex": "y = x^2",
    "config": null
  }
  ```
 
  輸出的 sheet 必須包含目前格式要求的基本欄位：
 
  - `data.version`
  - `data.config`
  - `data.cells`
  - `data.title`
  - `data.results`
  - `data.system_results`
  - `data.nextId`
  - `data.sheetId`
  - `data.insertedSheets`
  - `history`
 
  實作時參考：

  ```text
  tests/test_sheet.epxyz
  src/sheet/Sheet.ts
  src/cells/BaseCell.ts
  ```

  不要自行發明與現有格式不同的欄位名稱。

  工具不執行 SymPy，也不驗證公式。結果欄位可使用目前格式允許的空結果，MathPad 開啟後重新計算。

  `sheetId` 使用：

  ```js
  crypto.randomUUID()
  ```

  若瀏覽器不支援，使用 fallback UUID。

  `title` 使用輸入檔名去除 `.md` 後的名稱；若無檔名，使用：

  ```text
  Imported Markdown
  ```

  ### `convertMarkdownToEpxyz(markdown, title)`

  執行：

  ```text
  extractFormulaBlocks
  → createEpxyz
  → JSON.stringify
  ```

  輸出縮排兩格的 JSON 字串，方便人工檢查。

  ## 錯誤處理

  必須清楚顯示：

  - 沒有選擇檔案
  - 檔案不是 `.md`
  - Markdown 沒有公式
  - `$$` 未成對
  - 檔案無法讀取
  - 產生 `.epxyz` 失敗

  錯誤時不得讓頁面崩潰，也不得下載不完整檔案。

  沒有公式時顯示：

  ```text
  找不到支援的 $$...$$ 公式區塊。
  ```

  ## UI 行為

  初始狀態：

  - 轉換按鈕 disabled
  - 顯示支援格式說明
  - 顯示「只處理 `$$...$$`，其他 Markdown 會忽略」

  選擇檔案後：

  - 顯示檔案名稱
  - 顯示檔案大小
  - 啟用轉換按鈕
 
  轉換成功後：
 
  - 顯示找到的公式數量
  - 自動下載 `.epxyz`
  - 顯示成功訊息
 
  例如：
 
  ```text
  已轉換 3 個公式，檔案已下載。
  ```
 
  ## 測試計畫
 
  ### 純函式測試

  至少測試：

  1. 多行獨立公式可取得一個公式。
  2. 多個公式可取得正確數量。
  3. 行內公式 `$x^2$` 不被擷取。
  4. 普通 Markdown 不被擷取。
  5. 空公式被忽略。
  6. 未關閉 `$$` 產生明確錯誤。
  7. 多行 LaTeX 的內容與換行不被破壞。
  8. `.epxyz` 可被 `JSON.parse` 讀取。
  9. cell 數量、ID 與 `nextId` 正確。
 
  ### Browser 手動測試
 
  使用以下 Markdown：
 
  ```md
  # Demo
 
  這段文字會被忽略。

  $$
  x = 2
  $$

  這段文字也會被忽略。

  $$
  y = \frac{x^2}{3}
  $$

  行內公式 $z = 4$ 不支援。
  ```

  驗收流程：
 
  1. 開啟 browser 工具。
  2. 選擇測試 Markdown。
  3. 確認顯示找到 2 個公式。
  4. 下載 `.epxyz`。
  5. 在 MathPad 開啟下載的檔案。
  6. 確認出現兩個 math cells。
  7. 確認 MathPad 可以重新計算公式。
  8. 確認 `x` 與 `y` 的公式內容正確。

  ### 失敗案例測試

  - 空白 `.md`
  - 只有普通文字的 `.md`
  - 未關閉公式
  - 取消檔案選擇
  - 選擇非 Markdown 檔案
  - 含有中文內容的 Markdown
  - 含有多行 LaTeX 的 Markdown

  ## 驗收條件

  - 不需要後端。
  - 不需要安裝 npm 套件。
  - 可在 browser 中選取 `.md`。
  - 可產生 `.epxyz`。
  - 產生的 `.epxyz` 可由 MathPad 開啟。
  - 每個支援的 `$$...$$` 區塊變成一個 math cell。
  - 行內公式與其他 Markdown 不會被誤轉。
  - 無效輸入會顯示錯誤。
  - 轉換邏輯可以脫離 UI 測試。
  - 不修改 MathPad 現有的開啟與儲存功能。

  ## 實作順序

  1. 參考 `tests/test_sheet.epxyz` 確認 `.epxyz` 結構。
  2. 建立 `tools/md-to-epxyz/`。
  3. 完成 `converter.js` 的公式擷取函式。
  4. 加入 `.epxyz` JSON 建立函式。
  5. 用簡單輸入測試轉換結果。
  6. 建立 `index.html` 與 `app.js`。
  7. 加入檔案選擇、下載與錯誤顯示。
  8. 執行純函式測試。
  9. 用實際產生的 `.epxyz` 在 MathPad 開啟驗證。
  10. 撰寫 `tools/md-to-epxyz/README.md`。
  11. 確認不需把工具加入 MathPad 主頁面或主要 build 流程。

  ## 明確假設

  - 第一版只處理 `$$...$$` 獨立公式。
  - 公式內容直接視為 MathPad 使用的 LaTeX。
  - 工具不執行計算，計算由 MathPad 開啟後負責。
  - 工具完全在本機 browser 執行，Markdown 不上傳。
  - 產生的 `.epxyz` 不包含原始 Markdown 文字。
  - 預設不修改 MathPad 主程式。
  - 第一版使用純 HTML + JavaScript，不使用 Svelte、Vite 或第三方套件。


