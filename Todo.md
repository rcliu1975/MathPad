# Bookmark-Only Share Plan

Goal: add a bookmark-only shareable link mode for MathPad. The bookmark stores the sheet payload in the URL fragment, and falls back to the existing KV-based share link when the payload is too large.

Status: bookmark-only share flow is implemented; the current checkpoint/recent-sheets refactor is in place, and verification is partially complete as of 2026-05-30.

## Handoff Notes

- Implemented the bookmark-first share flow in `src/App.svelte`.
- Added `src/bookmarkShare.ts` for `bm1` fragment encode/decode, checksum, title formatting, and safe URL sizing.
- Added bookmark reopen support when the app starts on a `#bm1...` fragment.
- Added `tests/test_bookmark_share.spec.mjs` for the oversized fallback path.
- Added `tests/utility.mjs:clickAcceptIfPresent()` so specs can tolerate runs where the `Accept` modal is absent.
- `npm run build` passed.
- `tests/test_bookmark_share.spec.mjs` passed.
- `tests/test_database.spec.mjs` now passes again under the local preview server after:
  - switching the fragile blank-cell insertion to `Shift+Enter`
  - accepting bookmark-too-large fallback in the share-link flow
  - refreshing the chromium reference image to the current UI
- Refactored autosave recovery so the visible URL bar no longer gets rewritten to `/temp-checkpoint-...`.
- Stored autosave checkpoint hashes in history state and Recent Sheets instead of exposing them as a URL path.
- Wired Recent Sheets to reopen the latest autosave checkpoint through the hidden checkpoint hash.
- Updated `tests/test_checkpoints.spec.mjs` to verify the new Recent Sheets recovery path. That test now passes.
- `npx playwright test tests/test_bookmark_share.spec.mjs --project=chromium --workers=1 --retries=0` passed after the checkpoint/UI changes.
- `npx playwright test tests/test_checkpoints.spec.mjs --project=chromium --workers=1 --retries=0` passed after the Recent Sheets change.
- `npx playwright test tests/test_database.spec.mjs --project=chromium --workers=1 --retries=0` was rerun, but the session was interrupted before I could capture the final result, so it still needs a clean rerun.
- The remaining Playwright specs that still call `Accept` directly should still be switched to `clickAcceptIfPresent(page)` if they are intended to run in a reused local browser profile.
- The main files changed for this work are:
  - `src/App.svelte`
  - `src/bookmarkShare.ts`
  - `src/types.ts`
  - `tests/utility.mjs`
  - `tests/test_bookmark_share.spec.mjs`
  - `tests/test_database.spec.mjs`
  - `tests/test_symbolic_expression_error_handling.spec.mjs`
  - `tests/test_file_save_open.spec.mjs`
  - `tests/test_parse_id_bug.spec.mjs`
- The verification commands already used are:
  - `npm run build`
  - `npx playwright test tests/test_bookmark_share.spec.mjs --project=chromium --workers=1 --retries=0`
  - `npx playwright test tests/test_database.spec.mjs --project=chromium --workers=1 --retries=0`

## Product Rules

- Default to bookmark-only when the user chooses `Get Sharable Link`.
- Use the existing share-link flow as fallback when the bookmark URL would exceed a safe limit.
- Keep the current KV/shareable-link path unchanged as the fallback implementation.
- Use a human-readable bookmark title such as `MathPad · <sheet title>`.
- Never rely on the bookmark title for data recovery; only use it as a label.
- Do not keep writing `temp-checkpoint-...` paths into the URL bar for autosave recovery.
- URL updates should happen only when the user explicitly requests sharing, or after background work finishes and the user has been idle long enough that the update will not interrupt them.
- If the bookmark-only URL would exceed the safe limit, keep the current URL unchanged and show a warning instead of updating the URL bar.
- If autosave recovery is needed, use Recent Sheets as the entry point instead of exposing `temp-checkpoint-...` in the URL bar.
- `temp-checkpoint-...` is an internal key only.
- The visible URL bar must not show `temp-checkpoint-...`.
- Autosave recovery should not expose `temp-checkpoint-...` in the URL bar.
- If autosave recovery is needed, use Recent Sheets as the entry point.
- The recent sheets list must be able to open the latest autosave checkpoint.

## Data Format

- Define a versioned fragment format, for example `#bm1.<payload>`.
- Put the full sheet data in the fragment, not in the path or query string.
- Include enough metadata to restore the sheet safely:
  - serialized sheet payload
  - title
  - sheet version
  - history or equivalent navigation metadata
  - checksum or integrity marker
- Compress before encoding.
- Use URL-safe encoding, such as base64url, after compression.

## Capacity Strategy

- Calculate the final bookmark URL length before showing success.
- Use a conservative safety margin instead of aiming at Chrome's hard bookmark limit.
- Treat the payload as too large once it passes the chosen safe threshold.
- On overflow, prompt the user to switch to the original KV-based share link.

## UI Flow

- Keep `Get Sharable Link` as the single entry point.
- Show a modal that first attempts bookmark-only generation.
- If bookmark-only succeeds:
  - show the bookmark URL
  - show the bookmark title to use
  - provide copy controls
- If bookmark-only exceeds the safe limit:
  - show a warning that the bookmark-only version is too large
  - offer a primary action to use the original shareable link
  - offer cancel

## Load Flow

- Extend startup URL parsing to detect bookmark-only fragments.
- Decode and decompress bookmark payloads before restoring the sheet.
- Keep support for existing KV share links and checkpoint URLs.
- If bookmark payload parsing fails, show a clear error instead of silently opening a blank sheet.
- Preserve autosave recovery internally, but stop exposing `/temp-checkpoint-...` in the browser URL bar.
- Allow Recent Sheets to reopen the latest autosave checkpoint without requiring the checkpoint path to appear in the visible URL.
- Keep URL exposure clean while preserving autosave recovery internally via `checkpointHash`.

## Implementation Steps

1. Add a bookmark-only encoder/decoder helper.
2. Add a safe size estimator for the final bookmark URL.
3. Add a bookmark title formatter with truncation.
4. Update the share-link modal flow to attempt bookmark-only first.
5. Add fallback behavior that reuses the current KV upload path.
6. Update initial URL handling so bookmark-only links reopen correctly.
7. Add tests for:
   - bookmark-only encode/decode round trip
   - oversized payload fallback
   - invalid bookmark payload handling
   - backward compatibility with existing KV links
8. Refine URL updates so they occur only on `Get Sharable Link` and on idle after background compute, with cancellation on user activity.
9. Remove the use of `/temp-checkpoint-...` from the visible URL bar.

## Acceptance Criteria

- Small and medium sheets generate bookmark-only links successfully.
- Oversized sheets prompt the user to use the original share link.
- Existing KV share links still work.
- Bookmark-only links can be reopened after restarting the app.
- No existing file-save or autosave behavior regresses.
- The browser URL bar no longer exposes temp checkpoint paths during normal editing.
- Share URL updates do not interrupt active typing or computation.
- Autosave recovery remains available through Recent Sheets even after temp checkpoint paths stop appearing in the URL bar.
