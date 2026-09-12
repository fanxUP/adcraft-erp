# 用户个人设置实施计划

## 1. 任务分类

- 类型：账号安全、用户偏好持久化、桌面端/移动端设置体验。
- 风险：STRICT。涉及密码修改、用户级数据隔离、数据库迁移和登录后的全局样式初始化。
- 模式：STRICT。
- 变更预算：1 张用户偏好表、认证资料/API 契约、个人中心与移动端“我的”页面、应用 store 和主题变量、针对密码/越权/迁移/兼容性的测试；不扩展到完整账号安全中心。
- 部署：本计划只覆盖设计和实施，不默认执行 Git 提交或服务器部署，需后续单独授权。

## 2. 计划项

### USER-PREF-P01：冻结入口、范围与重复设置清理策略

目标：确定所有角色的入口、设置项、保存交互，并消除管理员系统设置与个人设置的职责冲突。

工作内容：

- 桌面端使用现有 `/profile`，移动端使用现有 `/mobile/profile`；
- 个人设置覆盖主题、字号，并兼容迁移现有字重；
- 所有已登录用户可修改自己，前端不新增权限码；
- 管理员系统设置移除主题/字号/字重重复控件，只保留真正全局参数；
- 明确安全默认值、保存/回退/恢复默认和未保存提示。

对应验收：A-USER-PREF-01。

### USER-PREF-P02：建立用户偏好数据模型和接口契约

目标：让偏好跨浏览器、跨设备持久化，并且只能由当前用户修改。

工作内容：

- 新增 `user_preferences` SQLAlchemy 模型和一对一用户关系；
- 新增可回滚 Alembic 迁移，为现有用户创建默认记录；
- 扩展 `/auth/me` 返回 `preferences`；
- 新增 `PATCH /auth/preferences`，使用当前登录用户 ID 做目标；
- 服务端白名单校验主题、字号、字重，保存后返回完整偏好；
- 补齐 TypeScript/Pydantic 类型及错误响应契约。

对应验收：A-USER-PREF-02。

### USER-PREF-P03：收紧密码修改与重置后的安全语义

目标：复用现有密码能力，保证用户只能改自己的密码，并让管理员重置后的强制改密行为与文案一致。

工作内容：

- 保持 `POST /auth/change-password` 的当前用户边界；
- 为密码请求增加服务端长度、空值、新旧密码相同等校验；
- 不记录密码内容，必要时增加不含敏感信息的操作日志；
- 管理员重置密码时设置 `must_change_password = true`；
- 保持当前会话和首次登录强制改密兼容，不引入设备会话管理。

对应验收：A-USER-PREF-03。

### USER-PREF-P04：统一用户偏好加载、应用和按账号缓存

目标：登录、刷新和切换账号时应用正确的个人主题和字号，不发生跨账号串用。

工作内容：

- 在 `authStore.fetchProfile()` 完成后由 `appStore` 统一应用服务端偏好；
- 增加按用户 ID 隔离的缓存键和清理逻辑；
- 复用 `THEME_LIST`、`FONT_SIZE_OPTIONS`、`FONT_WEIGHT_OPTIONS`，统一更新 body、Element Plus 和公共 UI token；
- 对无偏好或旧后端返回做安全默认兼容；
- 保存失败时恢复最后一次服务端状态。

对应验收：A-USER-PREF-04。

### USER-PREF-P05：实现桌面端和移动端个人设置界面

目标：所有角色都能在自己常用的端上完成设置，且交互和视觉语言一致。

工作内容：

- 在 `ProfileCenter.vue` 增加“我的设置”卡片；
- 抽取共享偏好类型/逻辑，避免桌面和移动端各写一套保存规则；
- 在 `MobileProfile.vue` 增加纵向设置入口或面板；
- 提供主题预览、字号示例、保存、恢复默认和保存状态反馈；
- 保留现有修改密码表单，并统一错误提示和 loading；
- 移除 `SystemSettings.vue` 中重复的个人样式控件。

对应验收：A-USER-PREF-05。

### USER-PREF-P06：安全、回归和交付质量验证

目标：证明个人设置不会影响现有角色权限、业务数据和登录流程。

工作内容：

- 后端测试覆盖偏好 CRUD、白名单、当前用户隔离、迁移默认值和密码规则；
- 前端测试覆盖登录应用、切换账号缓存隔离、保存失败回退和桌面/移动端契约；
- 执行现有完整测试、类型检查、Lint、构建和迁移 schema 检查；
- 检查修改差异中无密码、令牌、任意 CSS 注入和目标用户越权参数；
- 记录验收证据；Git 提交和服务器部署作为后续授权动作。

对应验收：A-USER-PREF-06。

## 3. 推荐执行顺序

```text
USER-PREF-P01
       ├──────────────> USER-PREF-P02 ─────┐
       └──────────────> USER-PREF-P03 ─────┼──> USER-PREF-P04 ──> USER-PREF-P05 ──> USER-PREF-P06
```

## 4. 主要文件范围

预计涉及：

- `backend/app/models/user.py` 或独立的用户偏好模型文件；
- `backend/app/schemas/auth.py`、`backend/app/api/auth.py`、`backend/app/services/auth_service.py`；
- `backend/app/services/user_service.py`、`backend/app/api/users.py`；
- `backend/alembic/versions/*_add_user_preferences.py`；
- `backend/alembic/env.py`；
- `frontend/src/types/api.ts`、`frontend/src/api/auth.ts`、`frontend/src/stores/auth.ts`、`frontend/src/stores/app.ts`；
- `frontend/src/views/profile/ProfileCenter.vue`、`frontend/src/views/mobile/MobileProfile.vue`；
- `frontend/src/views/admin/SystemSettings.vue`；
- `frontend/src/styles/tokens.scss`、`frontend/src/styles/global.scss` 及必要的公共设置组件。

不应修改：

- 订单、报价、任务、项目看板、成本和外协的数据模型；
- 角色权限组合、设计/制作/安装的数据可见范围；
- 现有主题名称和业务状态语义；
- 短信、邮件、飞书通知渠道。

## 5. 变更控制

- 不通过 `user_id` 请求参数让用户写入他人数据；
- 不把偏好放入 JWT，避免修改偏好后产生旧令牌数据问题；
- 不以未隔离的 localStorage 作为最终数据源；
- 不在管理员系统设置和个人中心保留两套主题/字号保存入口；
- 不删除现有修改密码和强制改密流程，只做契约收紧和一致性修复；
- 不把本阶段扩展成用户资料编辑或账号安全中心。

## 6. 后置 Backlog

- B-USER-PREF-01：退出其他设备和登录设备列表；
- B-USER-PREF-02：短信/邮件/飞书密码找回或安全提醒；
- B-USER-PREF-03：系统默认主题和新用户默认偏好管理；
- B-USER-PREF-04：界面密度、语言、时区和通知偏好；
- B-USER-PREF-05：管理员按授权为指定用户重置界面偏好；
- B-USER-PREF-06：更强密码策略、密码历史和双因素认证。
