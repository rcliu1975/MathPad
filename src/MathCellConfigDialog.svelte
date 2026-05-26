<script lang="ts">
  import { Checkbox } from "carbon-components-svelte";  
  import { defaultConfig, copyMathConfig, isDefaultMathConfig, 
           type MathCellConfig, getSafeMathConfig } from "./sheet/Sheet";
  import NumberFormatOptionsDialog from "./NumberFormatOptionsDialog.svelte";

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

  label.color-control {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  input.color-input {
    width: 100%;
    min-height: 40px;
    padding: 4px;
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
    <label class="color-control">
      Math Text Color
      <input
        class="color-input"
        type="color"
        bind:value={currentMathCellConfig.textColor}
        oninput={() => update(null, true)}
      />
    </label>

    <label class="color-control">
      Math Background Color
      <input
        class="color-input"
        type="color"
        bind:value={currentMathCellConfig.backgroundColor}
        disabled={!currentMathCellConfig.useBackgroundColor}
        oninput={() => update(null, true)}
      />
    </label>
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
