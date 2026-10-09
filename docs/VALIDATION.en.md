# Validation record and known limitations

[中文](VALIDATION.md) / [English](VALIDATION.en.md)

> This page translates the documentation. It does not mean that the exported Agent has been fully localized for English interaction. The Chinese inputs below are preserved exactly because their wording matters to the reproduced failures. The validation record describes the existing implementation and the checks performed on 2026-10-08.

The initial release is a **prototype** for demonstrating and learning product requirements interviews, state management, and PRD draft generation. Program checks and model reviews cannot replace real user research, requirements review, or product acceptance.

## Validation performed

On 2026-10-08, the existing tests were first run against an isolated copy of the original implementation and then run again in the prepared public repository: **all 31 existing Python regression tests passed, with exit code 0**. The tests used synthetic cases and did not call live models, Dify services, or other external systems.

The three public DSL files and the three DSL files rebuilt by the generator passed YAML parsing, graph connection and reachability checks, and syntax checks for embedded Python. The generator successfully built all three workflows. The synthetic example went through rule-based review, revision confirmation, and rendering to produce a ten-section PRD. Relative file links in the Markdown documents were also checked.

The release preparation changed the directory layout, public templates, and build paths; removed the tests' side effect of writing temporary examples; and fixed a duplicate keyword error when the generator reused node data containing a `desc` field. The business logic in `runtime.py` remained unchanged.

The checks cover field changes, reference relationships, evidence matching, suggestion acceptance and rejection, skipping fields, early review, invalidation of confirmation for an old revision, rendering from a snapshot, and fallback behavior on errors. This validates local rules only. It does not establish model extraction accuracy, PRD quality, response speed, or online availability.

Descriptions of earlier operation in Dify are historical records. **They do not mean that this release preparation revalidated the online application, model configuration, tool bindings, or import into another workspace.**

To reproduce the existing tests from the repository root:

```bash
python -m unittest discover -s tests -v
```

The rule implementation is in `src/runtime.py`, the field guide is in `src/registry.json`, and the model-output compatibility fixture is in `tests/fixtures/provider_output.json`. After importing into Dify, validate the complete conversation flow using your own models and tool configuration.

## Reproduced gaps in semantic safeguards

The following two issues were reproduced with local synthetic cases. The initial release retains the original runtime logic. These cases show the limits of the rule checks; they do not mean the failures will necessarily occur in ordinary conversations.

| Scenario | Reproduction conditions and result | Effect during use |
| --- | --- | --- |
| A negated acceptance is treated as acceptance | The user enters `不同意 D-1` (I do not agree to D-1), but the model incorrectly produces an `accept_proposal` patch. The current regular expression matches `同意` (agree) inside `不同意` (do not agree), so the suggestion may be accepted. | The program cannot guarantee rejection of every negated acceptance. Check the updated content and the final review summary. |
| Negation is lost from a requirement | The user enters `不自动发给客户` (Do not send automatically to the client), but the model extracts `自动发给客户` (Send automatically to the client) as evidence and records an affirmative requirement. The current substring check passes. | Matching quoted evidence is not semantic validation and cannot guarantee that the full scope of negation is preserved. |

The model interprets input and proposes changes; the program primarily validates format, state, and references. For public use or further development, include these cases in regression checks and review negation, ambiguity, numbers, and units. Do not describe structural validation as a guarantee of factual correctness.

## Current capability limits

- **Output format:** The current output is a Markdown PRD with Review Notes. There is no Word file download service or attachment parsing flow. A Word export request only returns an explanation and any existing Markdown.
- **Knowledge sources:** Product-method answers rely on the configured model's knowledge, without external retrieval. Current product, market, or technical facts need separate verification.
- **Review outcomes:** Hard structural errors or unhandled fields block generation. Semantic review results of `FAIL` or `UNKNOWN` are disclosed as risks. A draft can still be generated when field states meet the requirements and the user accepts unresolved items with the exact required command. Semantic review is not an absolute quality gate.
- **Unresolved information:** Users can explicitly retain TBD items. A processed field or a complete section does not mean that requirements are sufficient, metrics have been measured, or the plan is ready to implement.
- **Hash purpose:** The content hash checks consistency between the reviewed snapshot and the generated document. It is not a digital signature, does not authenticate identity, and is not a security boundary against tampering.
- **Test scope:** The 31 passing tests establish only that the existing local test cases pass. This work did not validate live-model stability, concurrency performance, attachment processing, configuration in another workspace, or online service status.

## Minimum checks before use

After importing into your own Dify workspace and binding the tools and models, complete one full flow: describe an idea, add requirements, review them, confirm the exact revision, and generate Markdown. Then check suggestion rejection, negated statements, renewed confirmation after requirement changes, and invalid model output. Before using a generated PRD externally, manually verify its requirement boundaries, the basis for its metrics, and unresolved items.
