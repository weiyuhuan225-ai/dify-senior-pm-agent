# 合成示例：书会借阅簿

[English](README.en.md) · [返回项目说明](../README.md)

所有产品信息、数字和角色均为演示设定，不是用户的私人项目，也不是实测效率或业务成绩。

这个示例有两种用途：把输入复制到 Dify 预览中，观察真实模型的访谈表现；或者在本地直接构造结构化变更，验证审查、确认和固定模板渲染。

## 中英对照与可复现性

[input.en.txt](input.en.txt) 是中文需求输入的英文译文；[prd.en.md](prd.en.md) 是中文确定性成稿的人工维护文档译文。英文 PRD 不是运行时或脚本直接生成的英文输出。

`scripts/make_example.py` 仅重建原始中文输入、中文成稿及对应 JSON 状态和风险记录，不生成或更新英文文档。`input.txt`、`prd.md`、`review_notes.json` 和 `reviewed_state.json` 保留为原始可复现示例。

英文自然语言输入尚未经过真实模型端验证。当前运行时的中文命令须原样提交，例如 `查看草稿`、`审查当前需求`、`/全部待定`；确认时应复制 Agent 展示的当前修订命令，不要翻译命令文字或沿用旧修订号。

## 在 Dify 中体验

新建对话，发送 [input.txt](input.txt) 中的需求。不要一次复制完整程序状态；自然语言访谈应由模型从输入开始整理。

观察 Agent 是否记录产品、用户、功能与第一版边界；输入“查看草稿”检查记录。然后尝试“审查当前需求”，处理或明确保留待定项，最后复制 Agent 给出的当前修订确认命令。

同一输入在不同模型中可能产生不同的追问和提取结果。这里不承诺与示例稿逐字一致。

## 本地确定性示例

在仓库根目录运行：

```bash
python scripts/make_example.py
```

脚本不调用 LLM。它显式构造合成变更，运行状态合并，将其余字段标记待定，模拟 `UNKNOWN` 语义审查结果，接受已披露风险，再经过版本门禁调用渲染工具。

| 文件 | 内容 |
| --- | --- |
| [input.txt](input.txt) | 虚构需求与口径设定 |
| [input.en.txt](input.en.txt) | 需求输入的英文对照译文，未经过模型端验证 |
| [reviewed_state.json](reviewed_state.json) | 经审查的合成状态快照 |
| [review_notes.json](review_notes.json) | 与快照对应的待定项和风险 |
| [prd.md](prd.md) | 十章 Markdown PRD 与 Review Notes |
| [prd.en.md](prd.en.md) | 中文 PRD 的英文文档译文，保留相同 ID、数字、草案状态和待定项 |

`review_notes.json` 是六条风险字符串组成的数组：业务目标、使用叙事、集成、规模性能和风险均为 `TBD`，语义审查状态为 `UNKNOWN`。英文说明中的[对应表](README.en.md#review-notes)提供这些字符串的译义，不另建或翻译机器状态文件。这里的 `UNKNOWN` 是脚本模拟的状态，不代表语义审查通过。

该示例验证固定规则能运行，不代表模型语义提取或 PRD 专业质量通过验收。
