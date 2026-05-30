<script lang="ts">
  import { onMount } from "svelte";
  import { SettingsAdjust, Download, RowCollapse, ChevronDown, ChevronUp } from "carbon-icons-svelte";
  import { renderMathInElement } from "mathlive";
  import appState from "./stores.svelte";

  const modifier = appState.modifierKey === "ctrlKey" ? "Ctrl" : "Cmd"

  onMount(() => {
    const mathSpans = document.querySelectorAll(".math");
    // @ts-ignore
    for (const span of mathSpans) {
      renderMathInElement(span);
    }
  });
</script>

<style>
  img {
    display: block;
  }

  ul {
   list-style: initial;
   margin-left: 20px;
  }
</style>

<em>May 30, 2026</em>
<h4>分享網址列同步與教程入口清理</h4>
<p>
   這次調整了分享流程的網址列行為，讓按下 Get Sharable Link 之後能立即同步更新目前的網址。
   同時也移除了已經沒有對應頁面的 Tutorial 圖示與死連結。
</p>
<ul>
   <li>Bookmark 分享成功後會同步更新網址列。</li>
   <li>維持原本 KV 分享作為 bookmark 太大時的回退路徑。</li>
   <li>刪除沒有對應內容的 Tutorial 入口與相關死連結。</li>
</ul>
<br>

<em>May 29, 2026</em>
<h4>Release 文案與 MathPad 啟用說明整理</h4>
<p>
   這一天主要整理了 Releases 的敘述方式，讓內容改成中文版本的修改記錄。
   同時也把 MathPad 的啟用說明重新潤飾，讓轉換說明更精簡、更一致。
</p>
<ul>
   <li>保留 <strong>Releases</strong> 這個英文名稱，內容改為中文。</li>
   <li>重新整理 MathPad 啟用段落的文字與語氣。</li>
   <li>讓更新頁的標題與側欄項目保持一致。</li>
</ul>
<br>

<em>May 26, 2026</em>
<h4>EngineeringPaper fork 到 MathPad</h4>
<p>
   這一天是專案從 EngineeringPaper fork 成 MathPad 的時間點。
</p>
<ul>
   <li>正式切換為 MathPad 名稱與品牌識別。</li>
   <li>刷新主畫面外殼與導覽區塊的配置。</li>
   <li>讓左側導覽和主要工作區的結構更清楚。</li>
</ul>
<br>
