// 純轉換邏輯，無 DOM 依賴，可在 browser 與 Node 測試中重用。

export const EPXYZ_VERSION = 20260414;

export function getDefaultEpxyzConfig() {
  return {
    mathCellConfig: {
      symbolicOutput: false,
      showIntermediateResults: false,
      formatOptions: {
        notation: "auto",
        precision: 15,
        lowerExp: -3,
        upperExp: 5
      }
    },
    customBaseUnits: {
      mass: "kg",
      length: "m",
      time: "s",
      current: "A",
      temperature: "K",
      luminous_intensity: "cd",
      amount_of_substance: "mol",
      force: "N",
      area: "m^2",
      volume: "m^3",
      energy: "J",
      power: "W",
      pressure: "Pa",
      charge: "C",
      capacitance: "F",
      electric_potential: "V",
      resistance: "ohm",
      inductance: "H",
      conductance: "S",
      magnetic_flux: "Wb",
      magnetic_flux_density: "T",
      angle: "rad",
      information: "b"
    },
    simplifySymbolicExpressions: true,
    convertFloatsToFractions: true,
    fluidConfig: {
      fluid: "Water",
      incompMixConc: 0.5,
      customMixture: [
        { fluid: "R32", moleFraction: 0.697615 },
        { fluid: "R125", moleFraction: 0.302385 }
      ]
    }
  };
}

function emptyResult() {
  return {
    value: "",
    symbolicValue: "",
    units: "",
    unitsLatex: "",
    numeric: false,
    customUnitsDefined: false,
    customUnits: "",
    customUnitsLatex: "",
    real: false,
    finite: false,
    isSubResult: false,
    subQueryName: ""
  };
}

function generateUuid() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // RFC4122 v4 fallback
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * 逐行掃描 Markdown，只擷取獨立 $$...$$ 公式區塊。
 * - 單獨一行的 `$$` 開始 / 結束區塊
 * - 單行 `$$formula$$` 視為一個公式
 * - 其他內容（行內 $...$、標題、段落、表格等）全部忽略
 * @throws {Error} 當 `$$` 未成對時
 */
export function extractFormulaBlocks(markdown) {
  const lines = String(markdown ?? "").split(/\r?\n/);
  const formulas = [];
  let inBlock = false;
  let buffer = [];

  for (const line of lines) {
    const trimmed = line.trim();

    if (!inBlock) {
      if (trimmed === "$$") {
        inBlock = true;
        buffer = [];
      } else if (
        trimmed.length > 4 &&
        trimmed.startsWith("$$") &&
        trimmed.endsWith("$$")
      ) {
        const inner = trimmed.slice(2, -2).trim();
        if (inner !== "") {
          formulas.push(inner);
        }
        // 空公式忽略，不報錯
      }
      // 其他行（含行內 $...$）一律忽略
    } else {
      if (trimmed === "$$") {
        const formula = buffer.join("\n").trim();
        if (formula !== "") {
          formulas.push(formula);
        }
        inBlock = false;
        buffer = [];
      } else {
        buffer.push(line);
      }
    }
  }

  if (inBlock) {
    throw new Error("$$ 未成對：找到未關閉的公式區塊。");
  }

  return formulas;
}

export function createEpxyz(formulas, title) {
  const safeTitle =
    typeof title === "string" && title.trim() !== ""
      ? title
      : "Imported Markdown";

  const cells = formulas.map((latex, index) => ({
    type: "math",
    id: index,
    latex,
    config: null
  }));

  const data = {
    version: EPXYZ_VERSION,
    config: getDefaultEpxyzConfig(),
    cells,
    title: safeTitle,
    results: formulas.map(() => emptyResult()),
    system_results: [],
    codeCellResults: {},
    sub_results: [],
    nextId: formulas.length,
    sheetId: generateUuid(),
    insertedSheets: []
  };

  return {
    data,
    history: []
  };
}

export function convertMarkdownToEpxyz(markdown, title) {
  const formulas = extractFormulaBlocks(markdown);
  const doc = createEpxyz(formulas, title);
  return JSON.stringify(doc, null, 2);
}
