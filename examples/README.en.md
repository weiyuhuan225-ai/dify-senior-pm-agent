# Synthetic example: Book Club Lending Log

[简体中文](README.md) · [Back to the project README](../README.en.md)

All product details, numbers, and roles are fictional demo assumptions. They do not describe a user's private project or measured efficiency or business results.

This example serves two purposes: you can paste the input into Dify's preview to observe a real model's interview behavior, or construct structured changes locally to exercise review, confirmation, and fixed-template rendering.

## Chinese and English versions and reproducibility

[input.en.txt](input.en.txt) is an English translation of the Chinese requirements input. [prd.en.md](prd.en.md) is a manually maintained documentation translation of the deterministic Chinese PRD. The runtime and example script do not directly produce this English PRD.

`scripts/make_example.py` regenerates only the original Chinese input, Chinese PRD, and corresponding JSON state and review notes. It does not generate or update the English documentation. `input.txt`, `prd.md`, `review_notes.json`, and `reviewed_state.json` remain the original reproducible example files.

**English natural-language input has not been validated with a real model.** The current runtime's Chinese command literals must be submitted unchanged, including `查看草稿` (view the draft), `审查当前需求` (review current requirements), and `/全部待定` (mark remaining items as TBD). For confirmation, copy the command for the current revision exactly as displayed by the Agent. Do not translate its command text or reuse an old revision number.

## Try the example in Dify

Start a new conversation and send the requirements in [input.txt](input.txt). Do not paste the entire program state: the model should organize the requirements from the natural-language input through the interview.

Check whether the Agent records the product, users, functions, and first-version boundaries. Send `查看草稿` to inspect the record. Then try `审查当前需求`, resolve the outstanding items or explicitly leave them as TBD, and finally copy the confirmation command the Agent provides for the current revision.

The same input may produce different follow-up questions and extracted information with different models. A word-for-word match with the sample PRD is not guaranteed.

## Local deterministic example

Run this command from the repository root:

```bash
python scripts/make_example.py
```

The script does not call an LLM. It explicitly constructs synthetic changes, merges them into the state, marks the remaining fields as TBD, simulates an `UNKNOWN` semantic review result, accepts the disclosed risks, and then passes through the revision gate to call the rendering tool.

| File | Contents |
| --- | --- |
| [input.txt](input.txt) | Fictional requirements and measurement definitions in Chinese |
| [input.en.txt](input.en.txt) | English translation of the input, not validated with a real model |
| [reviewed_state.json](reviewed_state.json) | Reviewed synthetic state snapshot |
| [review_notes.json](review_notes.json) | Outstanding items and risks corresponding to the snapshot |
| [prd.md](prd.md) | Original Chinese Markdown PRD with ten chapters and Review Notes |
| [prd.en.md](prd.en.md) | English documentation translation of the Chinese PRD, preserving the same IDs, numbers, draft status, and outstanding items |

## Review Notes

`review_notes.json` is an array of six warning strings. Their meanings are listed below; the machine-readable state is not duplicated or translated.

| Original string | English meaning |
| --- | --- |
| `业务目标：TBD` | Business goals: TBD |
| `使用叙事：TBD` | Usage narrative: TBD |
| `集成：TBD` | Integrations: TBD |
| `规模性能：TBD` | Scale and performance: TBD |
| `风险：TBD` | Risks: TBD |
| `语义审查状态：UNKNOWN` | Semantic review status: UNKNOWN |

`TBD` means “to be determined.” Here, `UNKNOWN` is the status simulated by the script; it does not mean that semantic review passed.

This example demonstrates that the fixed rules can run. It does not establish that the model's semantic extraction or the professional quality of the PRD has passed acceptance review.
