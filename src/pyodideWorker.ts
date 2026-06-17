import QuickLRU from "quick-lru";

const cache = new QuickLRU<string, string>({maxSize: 100}); 

globalThis.importScripts('pyodide/pyodide.js');

let pyodide_ready = false;
let py_funcs;
let recursionError = false;
let pyodide;
let loadedPyodidePackages: Set<string> = new Set(['numpy', 'scipy']);

function difference<T>(a: Set<T>, b: Set<T>): Set<T> {
  const result = new Set<T>();
  for (const value of a) {
    if (!b.has(value)) {
      result.add(value);
    }
  }
  return result;
}

function union<T>(a: Set<T>, b: Set<T>): Set<T> {
  const result = new Set<T>(a);
  for (const value of b) {
    result.add(value);
  }
  return result;
}

async function setup() { 
  try {
    pyodide = await globalThis.loadPyodide({indexURL: 'pyodide/', packages: ['numpy', 'scipy']});
    const response = await fetch("numeric_analysis.py");
    const data = await response.text();
    py_funcs = await pyodide.runPythonAsync(data);
    console.log('Python Ready');
    pyodide_ready = true
    globalThis.postMessage("pyodide_loaded");
  } catch(e) {
    console.error('Pyodide failed to load.');
    console.log(e);
    globalThis.postMessage("pyodide_not_available");
  }
}

const setupPromise = setup();

globalThis.onmessage = async function(e){
  if (e.data.cmd === "sheet_solve") {
    await setupPromise;

    if (!pyodide_ready) {
      globalThis.postMessage("pyodide_not_available");
      return;
    }
    if (recursionError) {
      globalThis.postMessage("max_recursion_exceeded");
      return;
    }
    try {
      const neededPackages = difference(new Set(e.data.neededPyodidePackages as string[]), loadedPyodidePackages);
      if (neededPackages.size > 0) {
        await pyodide.loadPackage([...neededPackages]);
        loadedPyodidePackages = union(loadedPyodidePackages, neededPackages);
      }

      const statementsAndSystems = JSON.stringify(e.data.data);
      let result: string;
      
      if (!cache.has(statementsAndSystems)) {
        result = py_funcs.solveSheet(statementsAndSystems) as string;
        cache.set(statementsAndSystems, result);
      } else {
        result = cache.get(statementsAndSystems)
      }

      globalThis.postMessage(JSON.parse(result));
    } catch (e) {
      // recursion is instance of InternalError (not standard, so cannot use) in Firefox and RangeError in Chrome
      if (e instanceof RangeError) {
        recursionError = true;
        globalThis.postMessage("max_recursion_exceeded");
        return;
      } else {
        globalThis.postMessage({error: `Unhandled exception occurred during Python call. ${e}`, results: []})
      }
    }
  }
}
