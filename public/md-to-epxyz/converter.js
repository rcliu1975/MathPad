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

/**
 * 移除 LaTeX 公式中的 \\boxed{...} wrapper，保留 wrapper 內的內容。
 * 使用大括號配對而非正則，避免被 \\frac{...}{...} 等巢狀內容截斷。
 * 未完整配對的 \\boxed{} 會原樣保留。
 */
export function stripBoxed(formula) {
  let result = String(formula ?? "");
  let searchFrom = 0;

  while (searchFrom < result.length) {
    const commandIndex = result.indexOf("\\boxed", searchFrom);
    if (commandIndex === -1) break;

    let openIndex = commandIndex + "\\boxed".length;
    while (/\s/.test(result[openIndex] ?? "")) openIndex += 1;

    if (result[openIndex] !== "{") {
      searchFrom = commandIndex + "\\boxed".length;
      continue;
    }

    let depth = 0;
    let closeIndex = -1;
    let escaped = false;

    for (let index = openIndex; index < result.length; index += 1) {
      const character = result[index];

      if (escaped) {
        escaped = false;
        continue;
      }
      if (character === "\\") {
        escaped = true;
        continue;
      }
      if (character === "{") {
        depth += 1;
      } else if (character === "}") {
        depth -= 1;
        if (depth === 0) {
          closeIndex = index;
          break;
        }
      }
    }

    if (closeIndex === -1) {
      searchFrom = commandIndex + "\\boxed".length;
      continue;
    }

    result = result.slice(0, commandIndex) +
      result.slice(openIndex + 1, closeIndex).trim() +
      result.slice(closeIndex + 1);
    searchFrom = Math.max(0, commandIndex - 1);
  }

  return result;
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
    config: {
      disableCalculation: true
    }
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
  const formulas = extractFormulaBlocks(markdown).map(stripBoxed);
  const doc = createEpxyz(formulas, title);
  return JSON.stringify(doc, null, 2);
}
