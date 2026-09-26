# md-to-epxyz Browser 工具

極小型、無後端、無 npm 依賴的 browser 工具：選擇 Markdown 檔 → 擷取獨立 `$$...$$` 公式 → 下載 MathPad `.epxyz`。

## 支援範圍

支援：

```md
$$
x = 2
$$
```

```md
$$x = 2$$
```

不支援：行內 `$x^2$`、`\(...\)`、`\[...\]`、標題/段落/列表/表格/圖片、公式區塊內的 Markdown、LaTeX 自動修正。公式原樣寫入 math cell，其他內容忽略。

## 使用

直接用 browser 開啟 `index.html`，或經由本地 server（避免 `file://` 模組限制）：

```bash
python3 -m http.server 8000 --directory tools/md-to-epxyz
# http://localhost:8000
```

1. 選擇 `.md` 檔（可拖放）。
2. 按「轉換並下載 .epxyz」。
3. 在 MathPad 開啟下載的 `.epxyz`，確認 math cells 與重新計算。

輸出檔名：`calculation.md → calculation.epxyz`，無檔名時為 `converted.epxyz`。

## 檔案

- `converter.js`：純邏輯 `extractFormulaBlocks` / `createEpxyz` / `convertMarkdownToEpxyz`，無 DOM。
- `app.js`：檔案讀取、檔名處理、`Blob` 下載、錯誤顯示。
- `index.html` / `styles.css`：UI，無 framework/CDN。

`.epxyz` 格式參考 `tests/test_sheet.epxyz`、`src/sheet/Sheet.ts`、`src/cells/BaseCell.ts`，`version` 使用 `src/stores.svelte.ts` 的 `currentVersion`（20260414），每個公式一個 `{type:"math", id, latex, config:null}` cell，結果為空、由 MathPad 開啟後重算。

## 測試

純函式（Node，無依賴）：

```bash
node --input-type=module -e "
import { extractFormulaBlocks } from './tools/md-to-epxyz/converter.js';
console.log(extractFormulaBlocks('\$\$x=2\$\$'));
"
```

手動驗收用 Markdown：

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

預期：找到 2 個公式，下載後 MathPad 顯示兩個 math cells，可重算。
