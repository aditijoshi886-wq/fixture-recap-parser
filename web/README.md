# Hosted review page

`index.html` is the review page from the PRD (US-1 to US-5): paste a recap, Claude extracts the 16 terms with the words each came from, the same validation rules as `parser/validate.py` run in the browser, flagged fields are listed first, and export stays locked until every critical field is confirmed or checks out.

It is published as a Claude artifact. There it calls Claude on the viewer's own account, so it needs no API key, and it saves the exported JSON through the artifact's download prompt. Opened as a plain file, it shows the worked example and the review flow, but it cannot parse.

Note: the page's prompt is an inline copy of `parser/prompts/v1.md`, rewritten to answer in JSON instead of through a tool call. Keep the two in step when the prompt changes.
