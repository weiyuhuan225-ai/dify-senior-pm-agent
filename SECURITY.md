# 公开配置与敏感信息 / Public configuration and sensitive data

[中文](#中文) | [English](#english)

## 中文

模型供应商凭据只在自己的 Dify 工作区配置。不要把 API Key、访问令牌、Cookie、真实用户对话、个人联系方式或私有项目材料写进提示词、测试样例、普通环境变量和公开日志。

本仓库使用文件白名单整理，公开副本不包含原始运行日志、原在线应用入口、Word 资料包或原工作区工具提供者 ID。会话变量的初始值为空状态。测试与示例使用合成需求。

重新导出 Dify 应用时，选择不包含 Secret 环境变量，并检查普通字段、代码、工具参数和依赖绑定。`.gitignore` 无法阻止已经被跟踪的文件泄露，也不能代替内容检查。

如果发现真实凭据被提交，先撤销或轮换凭据，再处理仓库内容与历史。请不要在公开 Issue 中粘贴真实凭据、私人对话或可直接访问私有服务的链接。

参考：[Dify 导出说明](https://docs.dify.ai/en/cloud/use-dify/workspace/app-management)、[GitHub 敏感数据处理](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)。

## English

Configure model provider credentials only in your own Dify workspace. Do not put API keys, access tokens, cookies, real user conversations, personal contact details, or private project material into prompts, test fixtures, ordinary environment variables, or public logs.

This repository was prepared from an explicit file allowlist. The public copies do not include the original runtime logs, original live application entry point, Word source package, or original workspace tool provider IDs. Session variables start from an empty state. Tests and examples use synthetic requirements.

When exporting a Dify application again, choose an export without Secret environment variables and inspect ordinary fields, code, tool parameters, and dependency bindings. `.gitignore` cannot prevent disclosure from files that are already tracked and does not replace content review.

If real credentials are committed, revoke or rotate them first, then address the repository content and history. Do not paste real credentials, private conversations, or links that directly expose private services into public issues.

References: [Dify export documentation](https://docs.dify.ai/en/cloud/use-dify/workspace/app-management), [GitHub guidance on removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).
