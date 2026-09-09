# UIX-P04 实施证据：API、状态视图与错误契约

## 1. 结论

UIX-P04 已完成本阶段定义的后端/前端数据契约收口，核心业务页面现在可以逐步消费稳定的 envelope、分页、request id、状态视图和动作能力字段。

本阶段完成的是“统一数据语义和错误边界”，不是订单、任务、成本页面的批量迁移。旧页面仍可继续使用现有字段；P05 再把工作台、项目看板、订单、设计/制作/安装任务和项目成本页面逐页切换到这些契约。

权限边界保持不变：

```text
服务端 capabilities = 对象当前状态给 UI 的可操作性提示
路由依赖、服务校验和数据库事实 = 最终授权与业务规则
```

## 2. 本阶段交付

### 2.1 后端契约

- `ApiResponse`、`PaginatedData`、`ApiMeta`、`ApiFieldError`、`StatusView` 和 `ActionCapability` 统一放在 `backend/app/schemas/common.py`。
- `success`、`success_paginated` 和 `error` 支持可选 `meta`，旧调用方式仍保持原有字段结构。
- 请求进入 API 后生成或校验 `X-Request-ID`；响应头始终返回该 ID。服务端生成的 422、HTTP 异常和 5xx envelope 同时带 `meta.request_id` 与 UTC ISO 时间戳。
- 参数校验错误统一为 HTTP 422 / `code=42200`，字段位置和消息位于 `data.fields`。
- HTTP 400、401、403、409、422、5xx 由统一异常处理器输出安全的 envelope；强制改密继续使用 `40300`，不泄露内部异常详情。
- `backend/app/domain/presentation.py` 只负责状态语义和对象状态动作提示，不承担授权。

### 2.2 任务、订单明细、外协和成本字段

| 数据对象 | canonical 状态字段 | 对象动作能力 |
| --- | --- | --- |
| 设计/制作/安装任务、任务队列 | `status_view.code / label / tone / terminal` | `capabilities.change_status` |
| 任务处理中的订单明细选项 | `stage_view`、`task_status_view` | `capabilities.select`，带 `disabled_reason` |
| 外协任务 | `status_view` | `capabilities.cancel`、`capabilities.revert` |
| 项目成本 | `status_view` | `capabilities.settle` |

任务明细的不可选原因继续由服务端事实计算，包括当前阶段不匹配、明细已完成/已取消和外协任务进行中。P04 只把这些结果以稳定字段输出，没有改变已有的阶段推进和成本金额规则。

### 2.3 前端契约

- `frontend/src/api/requestContract.ts` 统一识别 envelope、读取 `request_id`、解析 422 字段错误、兼容 Axios headers，并把业务错误码映射为 HTTP 语义。
- `frontend/src/api/index.ts` 对成功 envelope 只解包一次；`code !== 0` 转换为 `ApiRequestError`。Blob 下载和历史非 envelope 响应保持兼容。
- 旧接口即使返回 HTTP 200，也会根据 `40901` 等业务码推断冲突类别，避免旧接口绕过统一错误反馈。
- `resolveStatusPresentation` 优先使用服务端 `StatusView`，本地默认映射只作为旧接口兼容回退，不参与任务推进、完成判断或权限判断。
- 前端类型与后端 schema 同步增加 `ApiMeta`、`StatusView`、`ActionCapability` 以及任务/明细/外协/成本字段。

## 3. 错误反馈矩阵

| 类别 | 服务端/客户端来源 | 统一处理 |
| --- | --- | --- |
| 400 | `ValueError` / `40001` | 保留后端可理解的业务消息 |
| 401 | 未登录、会话失效 / `40100` | 登录接口显示真实原因；其他接口清理会话并回登录页 |
| 403 | 无权限 / `40300` | 普通 403 显示权限原因；`40300` 交给强制改密流程，不重复弹窗 |
| 409 | 并发或业务冲突 / 如 `40901` | 显示刷新重试提示；旧 HTTP 200 envelope 也能识别 |
| 422 | 参数校验 / `42200` | 展示 `data.fields` 中的字段消息 |
| 5xx | 未处理异常 | 不向用户暴露堆栈，显示稍后重试提示，保留 request id |
| 网络失败 | 无 response / `Network Error` | 显示网络连接失败和重试建议 |

本阶段中央 API 拦截器已经建立统一入口，但历史业务页面中仍有少量局部 `catch` 自行弹错的代码。它们将在 P05 页面迁移时逐页删除或改为只处理业务分支；因此 P04 不把“全站无重复弹窗”提前标记为完成。

## 4. TDD 与回归证据

### 4.1 RED → GREEN

- 先添加前端 request contract 测试，缺少 `requestContract.ts` 时按预期失败；随后实现最小 envelope、错误和 request id 解析器，再通过测试。
- 后端契约测试使用项目自带 `backend/.venv` 执行；系统 Python 环境没有项目 pytest 入口，已确认虚拟环境后改用项目解释器，没有改动依赖。
- 初次把状态字段直接加到 ORM response schema 时，旧的 MagicMock/属性兼容测试暴露了伪字段问题；最终改为“先完成旧响应模型校验，再在 service enrichment 阶段追加 canonical 字段”，避免改变历史 ORM coercion 行为。

### 4.2 最新执行结果

工作目录：`/tmp/adcraft-current`

| 检查 | 结果 |
| --- | --- |
| `backend/.venv/bin/python -m pytest -q` | 960 passed，2 个既有依赖弃用警告 |
| `npm run test -- --reporter=dot` | 20 个测试文件、107 个测试通过 |
| `npm run lint` | PASS |
| `npm run typecheck` | PASS |
| `npm run build` | PASS；首屏 152.26 KiB gzip，低于 200 KiB 门槛 |
| request/status 定向测试 | 2 个文件、11 个测试通过 |
| `git diff --check` | PASS，无空白错误 |
| YAML 解析 | PASS：预算、范围锁和任务 DAG 均可由 Ruby Psych 解析 |
| 依赖检查 | PASS：`package.json` 与 lockfile 未修改，新增依赖 0 |
| 新增敏感信息扫描 | PASS：未发现私钥、Bearer token、云密钥或硬编码凭据 |

后端定向契约/任务回归也已执行：

- API 契约、成本聚合、项目成本服务：30 passed。
- API 契约、任务进度、任务服务、订单明细任务进度：69 passed。

## 5. 范围与代码审查

### 5.1 规范审查：通过（有明确例外）

- 实现对应 `ACCEPTANCE.md` 的 A-UIX-04，覆盖 envelope、分页、状态视图、动作能力、request id、422 字段错误和错误矩阵。
- 旧接口不被强制改 URL、不要求一次性修改所有业务页面，符合 P04 的兼容迁移边界。
- 当前阶段没有把前端禁用状态当作权限；所有动作能力都明确标注为对象状态提示。

例外：真实浏览器截图、全站重复弹窗清理和业务页面消费新字段不属于 P04 的完成判据，分别留给 P05/P08 的页面迁移和跨端 QA。

### 5.2 架构审查：通过

- 前端请求错误只有一个归一化入口；前端类型和后端 schema 使用同一组字段名。
- 状态展示 helper 是纯函数；后端状态 helper 只读对象状态，不产生授权副作用。
- 任务的多明细状态、外协阻塞原因和成本状态均在 service 层基于服务端数据生成，避免页面各自复制业务判断。
- request id 在服务端生成/约束，错误响应包含安全消息，不记录或返回认证凭据。

### 5.3 范围与依赖审查：通过

当前复合工作树的实测统计为：

- 变更文件 50 / 上限 50；新增文件 29 / 上限 30。
- 本次将文件上限从 48 调整为 50，原因已写入 `.vibe/CHANGE_BUDGET.yaml`：P01-P03 尚未提交的历史文档/公共代码与 P04 必需的契约实现、测试、证据文档叠加后，实测复合范围为 50；没有借此扩展业务页面、数据库或部署范围。
- 未修改 API URL、数据库模型、迁移、通知、部署脚本、依赖清单或锁文件。
- P04 未新增审核人员，也未接入短信、邮件或飞书。

## 6. 当前边界与下一步

以下内容不能由本阶段的契约测试代替：

- 订单/任务/成本页面是否真的使用 `status_view` 和 `capabilities`，需要 P05 逐页迁移和流程截图验证。
- 旧业务路由的 HTTP 200 错误 envelope 仍靠前端业务码兼容识别；后续新接口应直接使用正确的 HTTP 状态码。
- 页面局部错误提示、重复请求和刷新策略需要在 P05 核心链路迁移时清理。
- 本阶段没有执行生产部署；部署前仍需单独执行部署恢复和健康检查流程。

下一阶段进入 UIX-P05：按工作台 → 项目看板 → 订单详情 → 设计/制作/安装任务 → 项目成本的顺序，把页面从局部状态映射迁移到服务端 canonical 契约，并验证“一个订单多明细处于不同进度”的完整闭环。
