# MathPad

MathPad 是從 [engineeringpaper.xyz](https://engineeringpaper.xyz) / [mgreminger/EngineeringPaper.xyz](https://github.com/mgreminger/EngineeringPaper.xyz) fork 出來的專案，延續其以瀏覽器為核心的工程計算與數學筆記能力。

如果你要了解實際使用方式、功能介紹、教學文件或範例，請直接參考 EngineeringPaper.xyz 的官方資源：

- 產品網站: [engineeringpaper.xyz](https://engineeringpaper.xyz)
- 內建教學: [editable tutorial](https://engineeringpaper.xyz/CUsUSuwHkHzNyButyCHEng)
- 教學影片: [tutorial video](https://youtu.be/r7EZQVhcr5Q)
- 延伸說明: [learning EngineeringPaper.xyz](https://blog.engineeringpaper.xyz/engineeringpaperxyz-tutorial)

本 README 主要整理 `MathPad` 的開發、維護、執行與同步上游版本所需資訊。

## 專案概要

- 前端技術: Svelte 5 + Vite 7
- 計算核心: Pyodide、SymPy
- 本機預覽與測試環境: Wrangler Pages
- 端對端測試: Playwright

## 主要修改項目

1. 支援純量單位，以及 `giga`、`kilo` 等單位前綴。

## 開發需求

- Node.js 20 以上
- npm
- 建議使用 Unix-like shell、macOS、Linux 或 WSL2

## 安裝與本機開發

先安裝依賴：

```bash
npm install
```

啟動開發模式：

```bash
npm run dev
```

這個指令會先編譯 browser workers，再啟動 Vite dev server，預設使用 `127.0.0.1:8788`。

如果你透過反向代理、自訂網域或外部 host 存取 dev server，請建立 `.env.local`，並設定允許的 host：

```dotenv
MATHPAD_ALLOWED_HOSTS=your-dev-host.example.com
```

可參考 [`.env.example`](/home/roger/WorkSpace/MathPad/.env.example:1)。

## 建置與預覽

正式建置：

```bash
npm run build
```

本機預覽：

```bash
npm run preview
```

`preview` 會用 `wrangler pages dev dist --kv SHEETS --local` 啟動本機 Pages 環境，方便驗證接近部署環境的行為。

## 測試

首次使用 Playwright 時，先安裝瀏覽器：

```bash
npx playwright install
```

建立本機測試資料：

```bash
npm run test:seed
```

執行測試：

```bash
npm run test
```

## 常用指令

```bash
npm run dev
npm run build
npm run preview
npm run test:seed
npm run test
```

## 主要腳本說明

- `npm run dev`: 先編譯 workers，再啟動 Vite 開發伺服器
- `npm run build`: 建置前端輸出與 database worker
- `npm run build:workers`: 編譯 `src/pyodideWorker.ts`、`src/parser/parserWorker.ts`、`src/jediWorker.ts`
- `npm run preview`: 以 Wrangler Pages 在本機模擬部署環境
- `npm run test:seed`: 匯入測試用 KV 資料
- `npm run test`: 執行 Playwright 測試

---

# 用 user mode systemd 跑 MathPad 的步驟

根據 README 確認：`npm run build` 完成後，`public/` 資料夾的內容可以作為靜態網站部署到任意 web server。 流程如下：

---

## 1. 前置需求

```bash
# 確認 Node.js ≥ 18、git
node -v
git --version

# 安裝 serve（靜態檔案伺服器）
npm install -g serve
```

---

## 2. Clone 並建置

```bash
git clone https://github.com/mgreminger/EngineeringPaper.xyz.git
cd EngineeringPaper.xyz

npm install
npm run build
# 產出目錄：./public/
```

建置完成後確認：

```bash
ls public/   # 應看到 index.html、_app/、sw.js 等
```

---

## 3. 建立 user-mode systemd service

```bash
# 確保 user systemd 目錄存在
mkdir -p ~/.config/systemd/user
```

建立 service 檔，**路徑請依實際調整**：

```bash
cat > ~/.config/systemd/user/engineeringpaper.service << 'EOF'
[Unit]
Description=EngineeringPaper.xyz static site
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/EngineeringPaper.xyz
ExecStart=/usr/bin/env npx serve public --listen 8080 --no-clipboard
Restart=on-failure
RestartSec=5

# 環境變數（npm global bin 路徑）
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
EOF
```

> `%h` 是 systemd 的 home 目錄展開符號，等同 `$HOME`。

---

## 4. 啟動與管理

```bash
# 重新載入 daemon
systemctl --user daemon-reload

# 啟動服務
systemctl --user start engineeringpaper

# 開機自動啟動（需要 loginctl linger）
systemctl --user enable engineeringpaper
loginctl enable-linger $USER   # 讓登出後服務仍繼續跑

# 查看狀態與 log
systemctl --user status engineeringpaper
journalctl --user -u engineeringpaper -f
```

開啟瀏覽器訪問 `http://localhost:8080`。

---

## 5. 更新版本

```bash
cd ~/EngineeringPaper.xyz
git pull
npm install          # 若 package.json 有變動
npm run build

systemctl --user restart engineeringpaper
```

---

## 常見問題

| 問題 | 原因 | 解法 |
|------|------|------|
| `npx: command not found` | PATH 在 systemd 環境中較精簡 | 改用絕對路徑，`which npx` 找出後寫死到 `ExecStart` |
| WASM 無法載入（MIME 錯誤） | 某些伺服器不回傳 `application/wasm` | 改用 `caddy` 或 `nginx`（見下方） |
| Pyodide 跨來源問題（SharedArrayBuffer）| 需要 COOP/COEP headers | 同下方 caddy 方案解決 |

**改用 Caddy（建議）**：EngineeringPaper.xyz 的 Pyodide 需要 `Cross-Origin-Opener-Policy` 和 `Cross-Origin-Embedder-Policy` headers 才能啟用 `SharedArrayBuffer`。`serve` 預設不加這些 headers，改用 Caddy 更穩：

```bash
# 安裝 caddy（Ubuntu/Debian）
sudo apt install caddy

# 建立 Caddyfile
cat > ~/EngineeringPaper.xyz/Caddyfile << 'EOF'
:8080 {
    root * public
    file_server
    header Cross-Origin-Opener-Policy "same-origin"
    header Cross-Origin-Embedder-Policy "require-corp"
    encode gzip
}
EOF
```

然後把 service 的 `ExecStart` 改為：

```ini
ExecStart=/usr/bin/caddy run --config %h/EngineeringPaper.xyz/Caddyfile
```


## 維護這個 Fork

建議保留 `origin` 與 `upstream` 兩個 remote：

```bash
origin   git@github.com:rcliu1975/MathPad
upstream https://github.com/mgreminger/EngineeringPaper.xyz
```

如果還沒設定 `upstream`，可執行：

```bash
git remote add upstream https://github.com/mgreminger/EngineeringPaper.xyz
```

檢查目前分支與上游的差異：

```bash
git fetch upstream
git rev-list --left-right --count HEAD...upstream/main
git log --oneline upstream/main..HEAD
git log --oneline HEAD..upstream/main
```

`git rev-list --left-right --count HEAD...upstream/main` 的輸出例如 `3 0`，表示本地分支比 `upstream/main` 多 3 個 commit，且沒有落後上游。

## 同步上游更新的建議流程

1. 先確認工作區乾淨，或至少知道哪些本地變更尚未提交。
2. 抓取上游最新內容：`git fetch upstream`
3. 檢查上游新增了哪些提交：`git log --oneline HEAD..upstream/main`
4. 視情況用 `merge` 或 `rebase` 將 `upstream/main` 整合進來
5. 重新執行 `npm install`、`npm run build`、必要時再跑 `npm run test`

## 依賴與上游背景

MathPad 繼承了 EngineeringPaper.xyz 的主要能力與依賴組合，包含：

- [Pyodide](https://pyodide.org)
- [SymPy](https://www.sympy.org)
- [MathLive](https://cortexjs.io/mathlive/)
- [Plotly](https://plotly.com/)
- [Quill](https://quilljs.com/)
- [Math.js](https://mathjs.org/)
- [ANTLR](https://www.antlr.org/)

如果你要了解原始產品設計、功能取向或對外使用情境，請回到上游專案與官方網站文件。
