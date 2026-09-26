import {
  extractFormulaBlocks,
  createEpxyz,
  convertMarkdownToEpxyz
} from "./converter.js";

const fileInput = document.getElementById("fileInput");
const dropZone = document.getElementById("dropZone");
const convertBtn = document.getElementById("convertBtn");
const fileInfo = document.getElementById("fileInfo");
const errorBox = document.getElementById("errorBox");
const statusBox = document.getElementById("statusBox");

let selectedFile = null;

function showError(message) {
  errorBox.textContent = message;
}

function clearMessages() {
  errorBox.textContent = "";
  statusBox.textContent = "";
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function setSelectedFile(file) {
  clearMessages();
  selectedFile = file;

  if (!file) {
    fileInfo.textContent = "";
    convertBtn.disabled = true;
    return;
  }

  fileInfo.textContent = `${file.name}（${formatSize(file.size)}）`;
  convertBtn.disabled = false;
}

fileInput.addEventListener("change", () => {
  setSelectedFile(fileInput.files && fileInput.files[0] ? fileInput.files[0] : null);
});

["dragover", "dragenter"].forEach((evt) =>
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.add("active");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.remove("active");
  })
);
dropZone.addEventListener("drop", (e) => {
  const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
  if (file) {
    setSelectedFile(file);
  }
});

function baseNameWithoutMd(fileName) {
  if (!fileName) return "converted";
  const lower = fileName.toLowerCase();
  if (lower.endsWith(".md")) return fileName.slice(0, -3);
  if (lower.endsWith(".markdown")) return fileName.slice(0, -9);
  return fileName.replace(/\.[^.]+$/, "") || "converted";
}

convertBtn.addEventListener("click", async () => {
  clearMessages();

  if (!selectedFile) {
    showError("請先選擇檔案。");
    return;
  }

  if (!/\.m(arkdown|d)$/i.test(selectedFile.name) && selectedFile.type !== "text/markdown") {
    // 允許 .txt 但提示；非 md 副檔名直接擋下
    if (!/\.txt$/i.test(selectedFile.name)) {
      showError("檔案不是 .md，請選擇 Markdown 檔案。");
      return;
    }
  }

  let markdown;
  try {
    markdown = await selectedFile.text();
  } catch (e) {
    showError("檔案無法讀取。");
    return;
  }

  let formulas;
  try {
    formulas = extractFormulaBlocks(markdown);
  } catch (e) {
    showError(e instanceof Error ? e.message : "解析 Markdown 失敗。");
    return;
  }

  if (formulas.length === 0) {
    showError("找不到支援的 $$...$$ 公式區塊。");
    return;
  }

  const title = baseNameWithoutMd(selectedFile.name) === "converted"
    ? "Imported Markdown"
    : baseNameWithoutMd(selectedFile.name);

  let jsonText;
  try {
    // 保留 convertMarkdownToEpxyz 作為單一入口，同時驗證 JSON 可解析
    jsonText = convertMarkdownToEpxyz(markdown, title);
    const parsed = JSON.parse(jsonText);
    if (!parsed.data || !Array.isArray(parsed.data.cells)) {
      throw new Error("產生 .epxyz 失敗。");
    }
  } catch (e) {
    showError(e instanceof Error ? e.message : "產生 .epxyz 失敗。");
    return;
  }

  try {
    const blob = new Blob([jsonText], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const outName = `${baseNameWithoutMd(selectedFile.name)}.epxyz`;
    a.href = url;
    a.download = outName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);

    statusBox.textContent = `已轉換 ${formulas.length} 個公式，檔案已下載。`;
  } catch (e) {
    showError("產生 .epxyz 失敗。");
  }
});

// 讓測試可引用（不影響 browser 行為）
export { baseNameWithoutMd };
