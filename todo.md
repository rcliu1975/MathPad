# Math Cell spacing command 問題

問題:
- math cell 內輸入 `\quad`、`\qquad`、`\,`、`\;`、`\!` 會引發 syntax error。

原因:
- 目前 parser/lexer 不接受這些 spacing command。
- 這些命令是顯示層用的語法，應該在送進 parser/solver 前先做 normalization。

結論:
- 不應該直接濾掉使用者看到的原字串。
- 應該保留輸入/顯示原文，只對 evaluation copy 做轉換。

Plan:
1. 在 parser 前加一層 normalization。
2. 將 spacing command 轉成 lexer 已支援且會被 skip 的表示法。
3. 加回歸測試，確認 spacing 不再觸發 syntax error。
