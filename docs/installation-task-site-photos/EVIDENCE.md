# 安装任务现场照片验证证据

验证时间：2026-09-10 16:06（Asia/Shanghai）

## 本地基线

- 仓库：`/tmp/adcraft-current`
- 分支：`master`
- 基线提交：`2bf40f7a9067417ead2ed582a6020fa8ced828b2`
- 工作树：包含本需求未提交变更；未执行服务器部署。

## 已执行结果

| 验证项 | 命令 | 结果 |
|---|---|---|
| 前端全量单元测试 | `cd frontend && npm test` | 25 个测试文件、145 项测试通过 |
| 后端全量测试 | `cd backend && ./.venv/bin/python -m pytest -q` | 1006 项通过，2 个依赖弃用警告 |
| 前端类型检查 | `cd frontend && npm run typecheck` | 退出码 0 |
| 前端 Lint | `cd frontend && npm run lint` | 退出码 0 |
| 前端生产构建 | `cd frontend && npm run build` | 退出码 0，首屏 gzip 154.50 KiB / 200 KiB |
| 前端照片专项测试 | `cd frontend && npm test -- --run src/utils/taskPhotoUpload.test.ts` | 4 项通过 |
| 后端照片专项测试 | `cd backend && ./.venv/bin/python -m pytest -q tests/test_task_attachments.py` | 6 项通过 |
| 差异空白检查 | `git diff --check` | 通过 |

## 覆盖内容

- 前端 JPG/PNG/WEBP、10MB 限制、历史附件兼容和上传路径处理。
- 后端图片 MIME、文件签名、10MB 限制、任务存在性、精确任务权限和安全扩展名。
- 拖拽/点击批量队列、3 路并发、单张失败重试。
- 缩略图列表、点击放大、多图切换、缩放/旋转和删除按钮隔离。
- 未新增依赖、数据库迁移或任务状态/进度规则。

## 交付状态

- [x] 本地代码实现
- [x] 本地自动化验证（16:04 复跑）
- [ ] 提交 Git
- [ ] 部署服务器
- [ ] 线上浏览器回归
