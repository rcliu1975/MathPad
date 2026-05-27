<script lang="ts">
  import { Checkbox } from "carbon-components-svelte";  
  import { defaultConfig, copyMathConfig, isDefaultMathConfig, 
           type MathCellConfig, getSafeMathConfig } from "./sheet/Sheet";
  import NumberFormatOptionsDialog from "./NumberFormatOptionsDialog.svelte";

  const colorPalette = [
    "#000000", "#e60000", "#ff9900", "#ffff00", "#008a00", "#0066cc", "#9933ff",
    "#ffffff", "#facccc", "#ffebcc", "#ffffcc", "#cce8cc", "#cce0f5", "#ebd6ff",
    "#bbbbbb", "#f06666", "#ffc266", "#ffff66", "#66b966", "#66a3e0", "#c285ff",
    "#888888", "#a10000", "#b26b00", "#b2b200", "#006100", "#0047b2", "#6b24b2",
    "#444444", "#5c0000", "#663d00", "#666600", "#003700", "#002966", "#3d1466"
  ];

  interface Props {
    mathCellConfig: MathCellConfig;
    cellLevelConfig?: boolean;
    setCellNumberConfig?: (input: MathCellConfig) => void;
    mathCellChanged: () => void;
    triggerSaveNeeded: () => void;
  }

  let {
    mathCellConfig=$bindable(),
    cellLevelConfig=false,
    setCellNumberConfig,
    mathCellChanged,
    triggerSaveNeeded
  }: Props = $props();

  let defaultMathConfig = defaultConfig.mathCellConfig;
  let currentMathCellConfig = $state(copyMathConfig(mathCellConfig) ?? copyMathConfig(defaultMathConfig));
  let numberFormatOptionsDialogElement: NumberFormatOptionsDialog;

  export function resetDefaults() {
    currentMathCellConfig = copyMathConfig(defaultMathConfig);
    numberFormatOptionsDialogElement.resetDefaults(false);
    update();
  }

  function update(event: Event | null = null, resolve:boolean  = false) {
    let newConfig: MathCellConfig | null = getSafeMathConfig(currentMathCellConfig);

    if (cellLevelConfig && isDefaultMathConfig(newConfig)) {
      newConfig = null;
    }

    mathCellConfig = newConfig;

    if (cellLevelConfig && setCellNumberConfig) {
      setCellNumberConfig(mathCellConfig);
    }

    triggerSaveNeeded();
    if (resolve) {
      mathCellChanged();
    }
  }

  function setTextColor(color: string) {
    currentMathCellConfig.textColor = color;
    update(null, true);
  }

  function setBackgroundColor(color: string) {
    currentMathCellConfig.backgroundColor = color;
    currentMathCellConfig.useBackgroundColor = true;
    update(null, true);
  }

</script>

<style>
  div.container {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  div.color-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
  }

  div.color-control {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  div.palette {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 6px;
    max-width: 248px;
  }

  button.swatch {
    width: 100%;
    min-width: 28px;
    min-height: 28px;
    padding: 0px;
    border: 1px solid #8d8d8d;
    border-radius: 4px;
  }

  button.swatch.selected {
    outline: 2px solid #0f62fe;
    outline-offset: 1px;
  }

  div.color-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  span.current-color {
    display: inline-flex;
    width: 20px;
    height: 20px;
    border: 1px solid #8d8d8d;
    border-radius: 4px;
  }
</style>

<Checkbox
  bind:checked={currentMathCellConfig.symbolicOutput}
  labelText="Display Symbolic Results"
  on:change={update}
/>

<div class="container">
  <Checkbox
    bind:checked={currentMathCellConfig.showIntermediateResults}
    labelText="Show Intermediate Results"
    on:change={() => update(null, true)}
  />

  <div class="color-grid">
    <div class="color-control">
      <div class="color-row">
        <span>Math Text Color</span>
        <span class="current-color" style={`background-color: ${currentMathCellConfig.textColor};`}></span>
      </div>
      <div class="palette">
        {#each colorPalette as color}
          <button
            type="button"
            class="swatch"
            class:selected={currentMathCellConfig.textColor === color}
            style={`background-color: ${color};`}
            aria-label={`Select text color ${color}`}
            onclick={() => setTextColor(color)}
          ></button>
        {/each}
      </div>
    </div>

    <div class="color-control">
      <div class="color-row">
        <span>Math Background Color</span>
        <span class="current-color" style={`background-color: ${currentMathCellConfig.backgroundColor};`}></span>
      </div>
      <div class="palette">
        {#each colorPalette as color}
          <button
            type="button"
            class="swatch"
            class:selected={currentMathCellConfig.backgroundColor === color && currentMathCellConfig.useBackgroundColor}
            style={`background-color: ${color}; opacity: ${currentMathCellConfig.useBackgroundColor ? 1 : 0.5};`}
            aria-label={`Select background color ${color}`}
            onclick={() => setBackgroundColor(color)}
          ></button>
        {/each}
      </div>
    </div>
  </div>

  <Checkbox
    bind:checked={currentMathCellConfig.useBackgroundColor}
    labelText="Show Background Color"
    on:change={() => update(null, true)}
  />

  <NumberFormatOptionsDialog
    bind:this={numberFormatOptionsDialogElement}
    bind:numberFormatOptions={currentMathCellConfig.formatOptions}
    onchange={() => update()}
    symbolicOutput={currentMathCellConfig.symbolicOutput}
  />
</div>
