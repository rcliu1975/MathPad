<script lang="ts">
  import Quill from "quill";
  import Embed from "quill/blots/embed";
  import ImageResize from "@mgreminger/quill-image-resize-module";
  import { MathfieldElement } from "mathlive";
  import type { Delta, Range } from "quill";
  import { onMount } from "svelte";
  import appState from "./stores.svelte";

  const BaseImage = Quill.import("formats/image");
  const QuillDelta = Quill.import("delta");
  const IMAGE_FILE_TYPES = [
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml"
  ];
  const IMAGE_FILE_ACCEPT = `${IMAGE_FILE_TYPES.join(",")},.svg`;
  const IMAGE_URL_PATTERN = /\.(jpe?g|gif|png|svg|webp)(?:[?#].*)?$/i;
  const DATA_IMAGE_PATTERN = /^data:image\/(?:gif|png|jpe?g|svg\+xml|webp)(?:;[^,]*)?,/i;

  function isSupportedImageUrl(url: string) {
    return IMAGE_URL_PATTERN.test(url) || DATA_IMAGE_PATTERN.test(url);
  }

  function svgToDataUrl(svgMarkup: string) {
    return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgMarkup)}`;
  }

  function getImageAttributes(node: Element) {
    const attributes: Record<string, string> = {};

    for (const name of ["width", "height", "alt"]) {
      const value = node.getAttribute(name);
      if (value) {
        attributes[name] = value;
      }
    }

    return attributes;
  }

  function matchSvgElement(node: Element) {
    const image = svgToDataUrl(node.outerHTML);
    const attributes = getImageAttributes(node);
    return new QuillDelta().insert({ image }, attributes);
  }

  class SvgFriendlyImage extends BaseImage {
    static match(url: string) {
      return isSupportedImageUrl(url);
    }
  }

  class Formula extends Embed {
    static blotName = 'formula';
    static className = 'ql-formula';
    static tagName = 'SPAN';

    static create(value: string) {

      const node = super.create(value) as Element;
      if (typeof value === 'string') {
        const mathField = new MathfieldElement({minFontScale: 0.75});
        mathField.value = value;
        mathField.readOnly = true;
        mathField.className = "doc-field-math";
        mathField.tabIndex = -1;
        node.setAttribute('data-value', value);
        node.appendChild(mathField);
      }
      return node;
    }

    static value(domNode: Element) {
      return domNode.getAttribute('data-value');
    }

    html() {
      const { formula } = this.value();
      return `<span>${formula}</span>`;
    }
  }

  Quill.register({
    'formats/image': SvgFriendlyImage,
    'formats/formula': Formula,
    'modules/imageResize': ImageResize
  }, true);

  interface Props {
    hideToolbar: boolean;
    quill: Quill;
    shiftEnter: () => void;
    modifierEnter: () => void;
    update: (arg: {detail: {delta: Delta}}) => void;
  }

  let {
    hideToolbar = true,
    quill = $bindable(),
    shiftEnter,
    modifierEnter,
    update
  }: Props = $props();
  
  let editorDiv;

  function selectImageFile(onSelect: (dataUrl: string) => void) {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = IMAGE_FILE_ACCEPT;

    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) {
        return;
      }

      const isImage = file.type.startsWith("image/") || file.name.toLowerCase().endsWith(".svg");
      if (!isImage) {
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === "string") {
          onSelect(reader.result);
        }
      };
      reader.readAsDataURL(file);
    };

    input.click();
  }

  export function setContents(newContents) {
    quill.setContents(newContents);
  }

  onMount(() => {
    const bindings = {
      tab: {
        key: 'Tab', // dissable tab key so that tab can be used for focus
        handler: function() {
          return true;
        }
      },
      custom1: {
        key: 'Enter', // for shift-enter, don't do anthing here and re-dispatch event to window (otherwise quill eats the event)
        shiftKey: true,
        handler: function() {
          shiftEnter();
          return false;
        }
      },
      custom2: {
        key: 'Enter', // for meta-enter, don't do anthing here and re-dispatch event to window (otherwise quill eats the event)
        [appState.modifierKey]: true,
        handler: function() {
          modifierEnter();
          return false;
        }
      },
      custom3: {
        key: 'e',
        [appState.modifierKey]: true,
        handler: function(range: Range) {
          const formulaButton = document.querySelector('div.quill-wrapper:focus-within button.ql-formula');
          if (formulaButton instanceof HTMLButtonElement) {
            formulaButton.click();
          }
          return false;
        }
      },
    };

    quill = new Quill(editorDiv, {
      modules: {
        toolbar: [
          [{ header: [1, 2, 3, false] }],
          ['bold', 'italic', 'underline'],
          [{ 'color': [] }, { 'background': [] }],
          [{list: 'ordered'}, {list: 'bullet'}],
          ['link', 'image', 'formula'],
          ['clean']
        ],
        handlers: {
          image: function() {
            const toolbar = this;
            selectImageFile((dataUrl) => {
              const range = toolbar.quill.getSelection(true);
              const index = range ? range.index : toolbar.quill.getLength();
              toolbar.quill.insertEmbed(index, "image", dataUrl, Quill.sources.USER);
              toolbar.quill.setSelection(index + 1, 0, Quill.sources.SILENT);
            });
          }
        },
        keyboard: {
          bindings: bindings
        },
        clipboard: {
          matchers: [
            ['svg', matchSvgElement]
          ]
        },
        uploader: {
          mimetypes: IMAGE_FILE_TYPES
        },
        imageResize: {
          altTextContainerStyles: {
            zIndex: "10",
          }
        },
      },
      theme: 'snow'  // or 'bubble'
    });

    quill.on('text-change', (delta, oldDelta, source) => {
      update({detail: {delta: quill.getContents()}});
    });
  });

</script>

<style>
  /* Hack to make quill not overflow bottom of flexbox */
  /* From: https://codepen.io/justinpincar/pen/gWdeRJ */
  div.quill-wrapper {
    height: 100%;
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: visible;
  }

  div.editor {
    flex: 1;
    display: flex;
    flex-flow: column nowrap;
    height: fit-content;
  }

  @media print {
    div.editor {
      display: block;
    }

    div.quill-wrapper {
      display: block;
      height: fit-content;
    }
  }

  :global(div.quill-wrapper div.ql-toolbar) {
    position: absolute;
    left: 0;
    top: 0;
    z-index: 20;
    width: calc(100% - 2px);
    background: white;
    box-shadow: 0 4px 12px rgb(0 0 0 / 0.12);
    transform: translateY(calc(-100% - 6px));
    transition: opacity 0.2s, transform 0.2s;
    transition-delay: .1s;
    max-height: 99px;
    overflow: visible;
    opacity: 1;
  }

  :global(math-field.doc-field-math) {
    border: none;
    padding: 0px;
  }

  :global(math-field.doc-field-math::part(content)) {
    padding: 1px;
  }

  div.hideToolbar :global(.ql-toolbar) {
    opacity: 0;
    pointer-events: none;
    transform: translateY(calc(-100% - 2px));
  }

  @media screen {
    :global(div.quill-wrapper .ql-container.ql-snow) {
      border: 1px solid #ddd !important;
      border-top: 1px solid #ddd !important;
      border-radius: 2px;
      background: white;
    }
  }

  :global(.ql-toolbar.ql-snow) {
    border: 1px solid #ddd !important;
    border-radius: 2px;
  }

  :global(div.quill-wrapper .ql-container:focus-within) {
    outline: 5px auto Highlight;
  }

  :global(div.quill-wrapper .ql-snow .ql-tooltip) {
    /* make sure url tooltip is above other elements (specifically, the button bar) */
    z-index: 100;
  }

  :global(div.quill-wrapper .ql-snow .ql-editor) {
    padding: 2px;
    font-size: 16px;
    overflow-y: visible;
    height: fit-content;
  }

  :global(div.quill-wrapper .ql-snow .ql-editor h1) {
    font-size: 1.625em;
  }

  :global(div.quill-wrapper .ql-snow .ql-editor h2) {
    font-size: 1.4375em;
  }

  :global(div.quill-wrapper .ql-snow .ql-editor h3) {
    font-size: 1.25em;
  }

  :global(div.quill-wrapper .ql-snow .ql-editor p) {
    font-size: 1em;
  }

  @media print {
    :global(div.quill-wrapper .ql-toolbar) {
      display: none;
    }

    :global(div.quill-wrapper .ql-container.ql-snow) {
      border: none;
    }    
  }

</style>


<div
  class="quill-wrapper" 
  class:hideToolbar 
>
  <div class="editor" bind:this={editorDiv}></div>
</div>
