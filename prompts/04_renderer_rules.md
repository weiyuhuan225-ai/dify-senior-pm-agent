PRD 成稿规则（本项目设计，不是上游原文）
1. 只接收已通过确认门禁的冻结 snapshot_json，以及 review_notes_json。
2. 使用固定十章模板；Version=v1，Status=Draft。内部 content_revision 单独显示为修订号，不冒充产品版本。
3. 逐字段渲染已有值；TBD 输出 _TBD_，不适用输出“不适用：原因”。最终稿不保留 {{placeholder}}。
4. US、FR、G、M、P 的 ID 原样保留，不重新编号；指标表保持名称、类型、基线、目标、期限。
5. Markdown 正文与独立 Review Notes 分隔；后者列出未验证假设、TBD、未解决映射及建议验证。
6. 禁止成稿时补充新功能、验收数字、模型、技术栈或默认权限。需要改动时，回访谈流程并重新确认。
7. 推荐 Code/Template 确定性渲染，不在用户确认后再调用 LLM 自由重写。