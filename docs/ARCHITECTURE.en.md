# Architecture and design choices

[中文](ARCHITECTURE.md) / [English](ARCHITECTURE.en.md)

> This page translates the documentation. It does not mean that the exported Agent has been fully localized for English interaction. The existing configuration, Chinese command strings, and output templates remain unchanged.

## Responsibilities of the three applications

The main application is a Chatflow with 19 nodes. The requirements guide and PRD renderer are separate Workflows with 3 nodes each, exposed as tools for the main flow. They do not depend on an external knowledge base or a separately built backend.

| Component | Responsibility | Output |
| --- | --- | --- |
| Input and control branches | Distinguish ordinary input, commands, and confirmation; check the current revision | A route, canonical state, or frozen snapshot |
| Model extraction and atomic merging | Propose field updates from the current input and apply them after validation | Updated requirements state and changes from the current turn |
| Interview Agent | Choose follow-up questions from the allowed fields, explain methods, and propose suggestions | A response or suggestion that has passed format checks |
| Read-only requirements guide | Provide field definitions, completion criteria, and ideas for questions | Method guidance, not facts about the project |
| Rule checks and semantic review | Check structure and relationships, and identify gaps or conflicts | A ten-section summary, coverage relationships, and Review Notes |
| Confirmation and rendering | Freeze the current revision, render deterministically, and check the result | A Markdown PRD and state updates |

## Why the design uses both a Workflow and an Agent

Deciding what to ask next, whether the user needs an explanation, and how to propose suggestions involves uncertainty in the conversation, so the model handles those decisions. Fixed program rules control how state is merged, when a PRD can be generated, which sections it contains, and whether changes require a new confirmation.

The Agent's tool list contains only the requirements guide. It cannot directly call the PRD renderer; the main Chatflow's confirmation branch triggers that node. This limits the model's control over the process, but does not guarantee that the model always understands the user's meaning correctly.

## Conversation state

The single conversation variable, `session_json`, stores the canonical requirements state: 21 fields, the content revision number, entity IDs, candidate suggestions, review results, and the most recent generated document. Field states distinguish information that is still unknown, needs more detail, awaits acceptance, has been recorded, has been deferred, or is not applicable.

The model returns proposed changes. The program checks the field allowlist, data types, quoted evidence, entity references, and operations, then merges the changes as a whole. No partial update is written if validation fails. Candidate suggestions generated in the current turn are stored separately from recorded requirements.

Entities use identifiers such as `G-`, `P-`, `US-`, `FR-`, and `M-`. When the model creates temporary entities, it uses the `tmp_` prefix; the program assigns their persistent IDs. These identifiers help maintain relationships, but do not prove that the relationships make sense for the product.

## Revisions, review, and PRD generation

When requirements content changes, the content revision number increases and the previous review and confirmation become invalid. The review stores a content hash, coverage relationships, and risks for that revision. The user confirms with a command containing the current revision number. When risks require acknowledgment, the command must also contain the corresponding acceptance wording. Use the exact Chinese command returned by the current Agent rather than an English translation of it.

The rendering tool reads a frozen snapshot and uses a fixed ten-section template. The main flow then compares its output with the expected result. The hash is for consistency checks, not identity verification or digital signing. An external service calling the renderer directly should not replace the main flow's confirmation gate.

## The ten PRD sections

The English names below explain the existing template; they do not change its Chinese headings.

1. Overview (概述)
2. Goals and boundaries (目标与边界)
3. Users and permissions (用户与权限)
4. User stories (用户故事)
5. Functional requirements (功能需求)
6. User experience (用户体验)
7. Usage narrative (使用叙事)
8. Success metrics (成功指标)
9. Technology and risks (技术与风险)
10. Implementation order (建设顺序)

Missing information remains to be determined and is included in the review notes. A complete template does not mean that research is sufficient or that the requirements have passed professional acceptance review.

## Source code and exported configuration

`dify/` contains public copies of the previously published configuration; `src/` contains the maintainable implementation. `build_dsl.py` embeds the Python rules and field registry in Dify Code nodes, and builds the remaining nodes from prompts and schemas. The templates retain only the structure needed for building the DSL. The original workspace's tool identities have been replaced with placeholders.

Embedding the code avoids a dependency on an external Python service, but duplicates runtime code across several Code nodes and increases the DSL size. The initial public release retains this implementation so that the original flow can be reproduced. New models or Dify versions still require separate validation.
