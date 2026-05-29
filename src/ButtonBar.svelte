<script lang="ts">
  import appState from "./stores.svelte";
  import { addCell } from "./stores.svelte";
  import AddAlt from "carbon-icons-svelte/lib/AddAlt.svelte";
  import AddComment from "carbon-icons-svelte/lib/AddComment.svelte";
  import Grid from "carbon-icons-svelte/lib/Grid.svelte";
  import Code from "carbon-icons-svelte/lib/Code.svelte";
  import InsertPage from "carbon-icons-svelte/lib/InsertPage.svelte";
  import ChartLine from "carbon-icons-svelte/lib/ChartLine.svelte";
  import IbmWatsonStudio from "carbon-icons-svelte/lib/IbmWatsonStudio.svelte";
  import ChartLineSmooth from "carbon-icons-svelte/lib/ChartLineSmooth.svelte";
  import RainDrop from "carbon-icons-svelte/lib/RainDrop.svelte";
  import IconButton from './IconButton.svelte';
  import DataTable from "carbon-icons-svelte/lib/DataTable.svelte";
  import type { CellTypes } from "./cells/BaseCell";

  interface Props {
    index: number;
    last?: boolean;
    insertSheet: (arg: {detail: {index: number}}) => void;
    mathCellChanged: () => void;
    triggerSaveNeeded: () => void;
  }

  let {
    index,
    last = false,
    insertSheet,
    mathCellChanged,
    triggerSaveNeeded
  }: Props = $props();

  function dispatchInsertSheet(index) {
    insertSheet({detail: {index: index}});
  }

  function mobileInsert() {
    if (!appState.inCellInsertMode) {
      appState.inCellInsertMode = true;
      addCell('insert', index);
      triggerSaveNeeded();
      mathCellChanged();
    }
  }

  function addCellWrapper(type: CellTypes, index: number) {
    addCell(type, index);
    triggerSaveNeeded();
    mathCellChanged();
  }

</script>

<style>

  button.mobile {
    border-radius: 5px;
  } 

  div.mobile-container {
    display: flex;
    justify-content: center;
    padding: 4px;
  }

  div.insert-bar {
    display: flex;
    gap: 4px;
    align-items: center;
    min-height: 0;
    margin: -4px 0;
  }

  div.insert-bar:not(.last) {
    opacity: 0;
    transform: scaleY(0.6);
    transform-origin: center;
    max-height: 8px;
    overflow: hidden;
    transition: opacity 0.2s, transform 0.2s, max-height 0.2s;
  }

  div.insert-bar:not(.last):hover {
    opacity: 1;
    transform: scaleY(1);
    max-height: 18px;
  }

  div.insert-bar:focus-within {
    opacity: 1;
    transform: scaleY(1);
    max-height: 18px;
  }

  hr {
    width: 47.5%;
    border: 0;
    height: 1px;
    border-radius: 1px;
    background: lightgray;
  }

  :global(div.insert-bar button) {
    width: 16px;
    height: 16px;
    min-width: 16px;
    min-height: 16px;
  }

  :global(div.insert-bar div.icon) {
    width: 12px;
    height: 12px;
  }

  div.mobile-spacer {
    height: 4px;
  }

  @media print {
    div.insert-bar {
      visibility: hidden;
    }
  }

</style>

{#if appState.onMobile && (!last || appState.inCellInsertMode) }
  <div class="mobile-spacer"></div>
{:else if appState.onMobile}
  <div class="mobile-container">
    <button 
      class="mobile"
      onclick={mobileInsert}
    >
      Insert New Cell
    </button>
  </div>
{:else}
  <div class="insert-bar" class:last>
    <hr>
    
    <IconButton
      title="Insert Math Cell Here"
      click={() => addCellWrapper('math', index)}
      id={last ? "add-math-cell" : `add-math-cell-${index}`}
      noTouch={!last}
    >
      <AddAlt />
    </IconButton>

    <IconButton 
      title="Insert Documentation Cell Here"
      click={() => addCellWrapper('documentation', index)}
      id={last ? "add-documentation-cell" : `add-documentation-cell-${index}`} 
      noTouch={!last}
    >
      <AddComment />
    </IconButton>

    <IconButton 
      title="Insert Plot Cell Here"
      click={() => addCellWrapper('plot', index)}
      id={last ? "add-plot-cell" : `add-plot-cell-${index}`}
      noTouch={!last}
    >
      <ChartLineSmooth />
    </IconButton>

    <IconButton 
      title="Insert Selector Table Cell Here"
      click={() => addCellWrapper('table', index)}
      id={last ? "add-table-cell" : `add-table-cell-${index}`}
      noTouch={!last}
    >
      <Grid />
    </IconButton>

    <IconButton 
      title="Insert Data Table Cell Here"
      click={() => addCellWrapper('dataTable', index)}
      id={last ? "add-data-table-cell" : `add-data-table-cell-${index}`}
      noTouch={!last}
    >
      <DataTable />
    </IconButton>

    <IconButton 
      title="Insert Piecewise Expression Here"
      click={() => addCellWrapper('piecewise', index)}
      id={last ? "add-piecewise-cell" : `add-piecewise-cell-${index}`}
      noTouch={!last}
    >
      <ChartLine />
    </IconButton>

    <IconButton
      title="Insert System Solve Cell Here"
      click={() => addCellWrapper('system', index)}
      id={last ? "add-system-cell" : `add-system-cell-${index}`}
      noTouch={!last}
    >
      <IbmWatsonStudio />
    </IconButton>

    <IconButton
      title="Insert Code Cell Here"
      click={() => addCellWrapper('code', index)}
      id={last ? "add-code-cell" : `add-code-cell-${index}`}
      noTouch={!last}
    >
      <Code />
    </IconButton>

    <IconButton
      title="Insert Fluid Properties Cell Here"
      click={() => addCellWrapper('fluid', index)}
      id={last ? "add-fluid-cell" : `add-fluid-cell-${index}`}
      noTouch={!last}
    >
      <RainDrop />
    </IconButton>

    <IconButton 
      title="Insert Sheet Here"
      click={() => dispatchInsertSheet(index)}
      id={last ? "insert-sheet" : null}
      noTouch={!last}
    >
      <InsertPage />
    </IconButton>

    <hr>
  </div>
{/if}
