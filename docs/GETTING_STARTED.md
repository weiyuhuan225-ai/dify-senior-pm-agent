# 导入与运行

## 1. 准备 Dify 与模型

本仓库 DSL 格式版本为 `0.7.0`，来源于已有 Dify 应用的导出配置。DSL 格式号不是 Dify 服务版本号。目标环境必须支持本文件使用的 Agent、结构化输出、变量聚合器与会话变量写入节点；请以导入时的兼容性检查为准。

主流程声明了以下插件依赖，版本与散列保留在 YAML 中：

| 插件 | 导出配置中的版本 | 用途 |
| --- | --- | --- |
| `langgenius/agent` | `0.0.50` | FunctionCalling Agent 节点 |
| `langgenius/deepseek` | `0.0.24` | 原配置的模型供应商 |

你可以在导入后选择自己的模型供应商。`N04`、`N11` 使用结构化 JSON 输出，`N08` 使用工具调用；替换模型后要检查这些能力。原配置中的 `deepseek-flash` 是当时使用的模型标识，其他工作区可能没有它。

模型密钥应配置在 Dify 的供应商设置中。仓库和命令行构建均不需要你的密钥。

## 2. 先导入两个工具

通过 Dify Studio 的“导入 DSL”分别导入：

| DSL | 应用类型 | 发布为工具后的调用名 | 输入 | 输出 |
| --- | --- | --- | --- | --- |
| `dify/get_slot_guide.yml` | Workflow | `get_slot_guide` | `section_id`、`slot_ids_json` | `guide_json` |
| `dify/render_prd.yml` | Workflow | `render_prd` | `snapshot_json`、`review_notes_json` | `markdown`、`content_hash` |

保存并发布工作流后，将各自发布为工作流工具。名称相同不会复用其他工作区的工具身份，导入主流程后仍然需要重新选择。

需求指南为只读工具，返回字段说明、追问方法与完成标准。成稿工具需要有效审查快照，不适合直接把空字符串当演示输入。

## 3. 导入并重新绑定主流程

导入 `dify/pm_qa_agent.yml`。公开副本中保留两个明确的替换标记：

| 节点 | 标记 | 要做的事 |
| --- | --- | --- |
| `N08 Senior PM 访谈 Agent` | `REPLACE_WITH_GET_SLOT_GUIDE_PROVIDER_ID` | 在工具列表删除失效引用，选择刚发布的 `get_slot_guide` |
| `N16 确认后固定模板成稿` | `REPLACE_WITH_RENDER_PRD_PROVIDER_ID` | 重新选择刚发布的 `render_prd` |

如果导入器拒绝带无效工具身份的主 DSL，先取得目标工作区的新工具提供者 ID，在本地副本中替换这两个标记，再导入。不要用旧工作区的 ID，也不要用模型 API Key 替换它们。

重新选择工具后，核对以下映射，防止界面操作清空参数：

| 位置 | 参数 | 取值 |
| --- | --- | --- |
| `N08` 的需求指南工具 | `section_id`、`slot_ids_json` | 由 Agent 自动提供 |
| `N16` | `snapshot_json` | `begin.snapshot_json` |
| `N16` | `review_notes_json` | `begin.review_notes_json` |

只把 `get_slot_guide` 加入访谈 Agent 工具列表。`render_prd` 留在主流程的确认分支，保持成稿顺序由程序控制。

在 `N04 本轮信息提取`、`N08 Senior PM 访谈 Agent`、`N11 语义一致性审查` 重新选择可用模型。原配置最大输出分别为 6000、3000、6000 tokens；访谈 Agent 最大迭代次数为 3。目标模型若不支持某个参数，请在 Dify 节点中调整后再测试。

确认会话变量 `session_json` 的初始值为 `{}`，保留 `N21` 对它的唯一写入路径。

## 4. 完成一次预览

先问“什么是 MVP”，确认可以得到方法解释。再开一个新会话，使用 [examples/README.md](../examples/README.md) 的合成输入，观察是否记录产品名、对象与范围，并提出下一步问题。

继续检查“查看草稿”“审查当前需求”“不知道”和“跳过”。有意保留未明确项时，可以说“其余全部待定”，查看风险后再确认。确认命令包含当前修订号，应复制 Agent 实际给出的命令，不要把示例中的 `r1` 当成固定值。

修改任意需求后，旧确认应该失效；再次审查并确认新修订后才成稿。最终结果为十章 Markdown 与 Review Notes。

## 5. 发布自己的应用

预览完成后，从 Dify 发布主 Chatflow。应用名称、开场白与 Web App 品牌设置需要在你的工作区核对。GitHub 保存代码与配置；实际对话和模型调用仍由你的 Dify 环境提供。

## 本地构建

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python src/build_dsl.py
```

生成器从 `src/runtime.py`、`src/registry.json`、提示词、Schema 和 `src/templates/` 构建三个 DSL，写入 `dist/`。不会修改 `dify/` 中的已清理导出文件，也不会读取模型密钥。构建产物仍包含公开工具占位符，需要在目标工作区重新绑定。

## 常见问题

| 现象 | 检查位置 |
| --- | --- |
| 导入后工具不可用 | `N08` 和 `N16` 是否已绑定当前工作区发布的工具 |
| 模型不存在或参数无效 | 三个模型节点的供应商、模型和支持的参数 |
| 反复出现固定追问 | 模型最终答案是否满足 JSON Schema；查看 Dify 预览中的失败节点 |
| 不允许生成 | 尚未处理的字段、未采纳建议、修订号或审查是否已经失效 |
| 审查有风险仍可出稿 | 用户精确确认接受待确认项后可生成草案，这是当前行为 |
| 想下载 Word | 当前仅生成 Markdown；仓库没有 Word 导出服务 |

官方参考：[Dify 应用导入与导出](https://docs.dify.ai/en/cloud/use-dify/workspace/app-management)。该页说明 DSL 包含配置、节点和提示词；Secret 环境变量是否随导出包含需要单独选择。公开导出仍需检查普通文本中的硬编码凭据。
