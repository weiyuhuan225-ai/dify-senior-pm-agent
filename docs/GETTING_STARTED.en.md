# Importing and running the Agent

[中文](GETTING_STARTED.md) / [English](GETTING_STARTED.en.md)

> This page translates the documentation. It does not mean that the exported Agent has been fully localized for English interaction. Chinese commands and node labels are preserved below to match the current configuration; their English explanations are not replacement command strings.

## 1. Prepare Dify and the models

The DSL format version in this repository is `0.7.0`, taken from an export of the existing Dify application. The DSL format version is not the Dify service version. The target environment must support the Agent, structured output, variable aggregator, and conversation-variable assignment nodes used in these files. Follow the compatibility checks shown during import.

The main flow declares the following plugin dependencies. Their versions and hashes are retained in the YAML:

| Plugin | Version in the exported configuration | Purpose |
| --- | --- | --- |
| `langgenius/agent` | `0.0.50` | FunctionCalling Agent node |
| `langgenius/deepseek` | `0.0.24` | Model provider in the original configuration |

You can choose your own model provider after import. `N04` and `N11` use structured JSON output; `N08` uses tool calling. Check these capabilities after changing models. The `deepseek-flash` identifier is the model name used in the original configuration; it may not be available in another workspace.

Configure model keys in Dify's provider settings. Neither the repository nor the command-line build requires your keys.

## 2. Import the two tools first

Use Dify Studio's Import DSL action to import each file:

| DSL | Application type | Tool call name after publication | Inputs | Outputs |
| --- | --- | --- | --- | --- |
| `dify/get_slot_guide.yml` | Workflow | `get_slot_guide` | `section_id`, `slot_ids_json` | `guide_json` |
| `dify/render_prd.yml` | Workflow | `render_prd` | `snapshot_json`, `review_notes_json` | `markdown`, `content_hash` |

Save and publish the Workflows, then publish each as a workflow tool. Giving a tool the same name does not reuse its identity from another workspace. You still need to select the new tools after importing the main flow.

The requirements guide is read-only. It returns field explanations, questioning methods, and completion criteria. The renderer requires a valid reviewed snapshot; empty strings are not suitable demonstration inputs.

## 3. Import the main flow and bind its tools

Import `dify/pm_qa_agent.yml`. The public copy contains two explicit replacement markers:

| Node label in the exported configuration | Marker | Action |
| --- | --- | --- |
| `N08 Senior PM 访谈 Agent` | `REPLACE_WITH_GET_SLOT_GUIDE_PROVIDER_ID` | Remove the invalid reference from the tool list and select the newly published `get_slot_guide` |
| `N16 确认后固定模板成稿` | `REPLACE_WITH_RENDER_PRD_PROVIDER_ID` | Select the newly published `render_prd` |

These labels identify the interview Agent and the renderer that runs after confirmation, respectively.

If the importer rejects the main DSL because its tool identities are invalid, obtain the new tool provider IDs from the target workspace, replace these two markers in your local copy, and then import it. Do not use IDs from the old workspace or replace the markers with model API keys.

After selecting the tools, check the following mappings in case the interface cleared any parameters:

| Location | Parameter | Value |
| --- | --- | --- |
| Requirements guide tool in `N08` | `section_id`, `slot_ids_json` | Supplied automatically by the Agent |
| `N16` | `snapshot_json` | `begin.snapshot_json` |
| `N16` | `review_notes_json` | `begin.review_notes_json` |

Add only `get_slot_guide` to the interview Agent's tool list. Keep `render_prd` in the main flow's confirmation branch so that the program controls when rendering occurs.

Select available models in `N04 本轮信息提取` (current-turn information extraction), `N08 Senior PM 访谈 Agent` (the interview Agent), and `N11 语义一致性审查` (semantic consistency review). Their original maximum outputs are 6000, 3000, and 6000 tokens, respectively. The interview Agent allows a maximum of 3 iterations. If the target model does not support a parameter, adjust it in the Dify node before testing.

Confirm that the conversation variable `session_json` starts with the value `{}`. Preserve `N21` as the only node that writes to it.

## 4. Complete a preview

First ask `什么是 MVP` (What is an MVP?) and check that the Agent can explain the method. Then start a new conversation and use the synthetic input in [the example guide](../examples/README.en.md). Observe whether the Agent records the product name, intended users, and scope, then asks the next question.

Continue checking `查看草稿` (View draft), `审查当前需求` (Review current requirements), `不知道` (I do not know), and `跳过` (Skip). To deliberately leave unresolved items open, you can say `其余全部待定` (Mark all remaining fields as to be determined), review the risks, and then confirm. The confirmation command includes the current revision number: copy the exact command the Agent actually provides. Do not treat the example revision `r1` as a fixed value.

After any requirement changes, the old confirmation should become invalid. Review and confirm the new revision before generating the document. The final output is a ten-section Markdown PRD with Review Notes.

## 5. Publish your own application

After completing the preview, publish the main Chatflow from Dify. Check the application name, opening statement, and Web App branding in your workspace. GitHub stores the code and configuration; your Dify environment still handles conversations and model calls.

## Local build

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/build_dsl.py
```

The generator builds three DSL files from `src/runtime.py`, `src/registry.json`, the prompts, schemas, and `src/templates/`, and writes them to `dist/`. It does not modify the sanitized exports in `dify/` or read model keys. Generated files still contain the public tool placeholders and require tool rebinding in the target workspace.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Tools are unavailable after import | Whether `N08` and `N16` are bound to tools published in the current workspace |
| A model is missing or a parameter is invalid | The provider, model, and supported parameters in all three model nodes |
| The same fallback follow-up question keeps appearing | Whether the model's final answer satisfies the JSON Schema; inspect the failed node in Dify's preview |
| Generation is not allowed | Unhandled fields, suggestions awaiting acceptance, the revision number, or an invalidated review |
| A draft can still be generated despite review risks | The current behavior allows a draft after the user explicitly confirms acceptance of unresolved items using the required command |
| You want a Word download | The current output is Markdown; the repository does not include a Word export service |

Official reference: [Dify application import and export](https://docs.dify.ai/en/cloud/use-dify/workspace/app-management). The page explains that DSL exports contain configuration, nodes, and prompts, while inclusion of Secret environment variables is a separate choice. Public exports still need to be checked for credentials hardcoded in ordinary text.
