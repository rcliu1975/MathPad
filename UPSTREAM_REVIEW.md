# Upstream Review Record

Date: 2026-05-30

GitHub label: `upstream-reviewed-no-merge`

Reviewed upstream commits:

- `336513e` `fix: fix Chrome height regression`
- `923eab7` `Revert "fix: fix Chrome height regression"`
- `fd3f19d` `Update pull_request_template.md`
- `b9805cc` `Update CONTRIBUTING.md`

Decision:

- Do not merge these commits into `main`.
- These commits have been checked and recorded here so they do not need to be reconsidered in future upstream merge reviews.
- Apply the `upstream-reviewed-no-merge` label to the corresponding tracking item in GitHub.

Notes:

- `336513e` and `923eab7` cancel each other out, so there is no net code change to keep.
- `fd3f19d` and `b9805cc` are documentation-only changes and are not needed for this fork's current maintenance direction.

Operational note:

- When GitHub shows a message such as `This branch is X commits ahead of and Y commits behind mgreminger/EngineeringPaper.xyz:main`, inspect the upstream `behind` commits individually.
- Compare each upstream commit against this review record.
- If every upstream commit is already listed here and marked as `upstream-reviewed-no-merge`, no merge is needed.
- If any upstream commit is not listed here, review that new commit before deciding whether to merge.
