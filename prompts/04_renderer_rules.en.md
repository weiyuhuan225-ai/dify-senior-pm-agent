# PRD rendering rules — English design reference

[中文原文](04_renderer_rules.md) · [Prompt index / 提示词索引](README.md)

This is a complete English translation of the Chinese design reference. These rules were designed for this project; they are not the upstream source text. Adding this reference does not change the renderer, translate the generated PRD, or replace the Chinese prompts embedded in the Dify DSL. English interactions have not been validated by this translation.

---

1. Accept only a frozen `snapshot_json` that has passed the confirmation gate, together with `review_notes_json`.
2. Use the fixed ten-chapter template with `Version=v1` and `Status=Draft`. Display the internal `content_revision` separately as the revision number; do not present it as the product version.
3. Render existing values field by field. Render `TBD` as `_TBD_` and a not-applicable value as the Chinese literal `不适用：原因` (“Not applicable: reason”). The final draft must not retain `{{placeholder}}` markers.
4. Preserve `US`, `FR`, `G`, `M`, and `P` IDs exactly; do not renumber them. Preserve each metric's name, type, baseline, target, and timeframe in the metrics table.
5. Separate the Markdown body from independent Review Notes. The latter lists unverified assumptions, `TBD` items, unresolved mappings, and recommended validation.
6. Do not add new features, acceptance criteria numbers, models, technology stacks, or default permissions during rendering. If changes are needed, return to the interview flow and obtain confirmation again.
7. Prefer deterministic Code/Template rendering. Do not call an LLM to freely rewrite the document after the user has confirmed it.
