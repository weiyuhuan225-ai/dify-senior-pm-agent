# 提示词索引 / Prompt index

[项目首页 · 中文](../README.md) · [Project home · English](../README.en.md)

## 中文说明

本目录保留 4 份原始中文设计提示词，并提供完整的英文学习参考。两种语言的文件保留相同的协议字段名、操作名和数据结构，便于对照理解提取、访谈、审查与成稿的设计。

**这 4 份文件属于设计与参考材料；实际运行时访谈提示词的源文件是 [`src/interviewer.md`](../src/interviewer.md)。** 运行时版本增加了 `explain`、`guide`、`interview` 三种回复模式，并细化了工具参数、建议数据结构与确认边界，因此另附一份忠实的英文参考供对照。

新增英文参考文件不会自动替换 Dify DSL 中嵌入的中文提示词，也不会更改工作流、模型、JSON 结构或生成文档的语言。本次文档翻译不代表英文端到端交互已验证。`查看草稿`、`审查当前需求` 等命令字面量继续保留中文；英文释义用于理解，不代表运行时接受等价的英文命令。最终成稿仍需使用系统展示的当前版本确认口令。

## English notes

This directory preserves the four original Chinese design prompts and provides complete English reading references. Protocol field names, operation names, and data structures remain unchanged across languages so that readers can compare the extraction, interview, review, and rendering designs.

**The four numbered files are design and reference material. The runtime interviewer's prompt source is [`src/interviewer.md`](../src/interviewer.md).** The runtime version adds the `explain`, `guide`, and `interview` reply modes, with more detailed constraints for tool arguments, proposal structures, and confirmation authority. A separate faithful English reference is provided for that version.

The English reference files do not automatically replace the Chinese prompts embedded in the Dify DSL, or change the workflow, models, JSON structures, or generated document language. This documentation translation does not establish that end-to-end English interactions have been validated. Command literals such as `查看草稿` and `审查当前需求` remain in Chinese; the English explanations are for understanding and do not imply that equivalent English commands are accepted at runtime. Final generation still requires the current revision's confirmation phrase displayed by the system.

## 设计参考 / Design references

| 功能 / Purpose | 中文 / Chinese | English |
| --- | --- | --- |
| 信息提取：证据、局部变更与待确认提案 / Extraction: evidence, local changes, and pending proposals | [01_extractor.md](01_extractor.md) | [01_extractor.en.md](01_extractor.en.md) |
| 访谈设计：问题选择、追问与建议边界 / Interview design: question selection, follow-up, and suggestion boundaries | [02_interviewer.md](02_interviewer.md) | [02_interviewer.en.md](02_interviewer.en.md) |
| 语义审查：需求一致性与审查结论 / Semantic review: requirement consistency and review outcomes | [03_semantic_reviewer.md](03_semantic_reviewer.md) | [03_semantic_reviewer.en.md](03_semantic_reviewer.en.md) |
| 成稿规则：冻结快照、固定模板与 Review Notes / Rendering rules: frozen snapshots, a fixed template, and Review Notes | [04_renderer_rules.md](04_renderer_rules.md) | [04_renderer_rules.en.md](04_renderer_rules.en.md) |

## 运行时访谈参考 / Runtime interviewer reference

| 版本 / Version | 文件 / File |
| --- | --- |
| 实际运行时提示词源文件 / Runtime prompt source | [src/interviewer.md](../src/interviewer.md) |
| 英文阅读参考 / English reading reference | [interviewer_runtime.en.md](interviewer_runtime.en.md) |
