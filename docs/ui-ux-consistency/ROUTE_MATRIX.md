# UIX-P01 路由、页面、角色与主动作矩阵

## 1. 使用说明

本矩阵把动态参数路由按路由族归并；具体页面组件以当前 router/index.ts 为准，导航入口以 config/navigation.ts 为准。角色列区分“导航过滤角色”和“路由 meta 角色”，两者不一致的地方单独标记，后续由 P03/P04 收口。

当前角色集合：

- admin：系统管理员
- sales：销售
- designer：设计
- production：制作
- installer：安装
- finance：财务

## 2. 核心链路矩阵

| 业务对象 | 路由 | 页面/组件 | 导航角色 | 路由角色 | 主动作 | 核心状态/数据 |
|---|---|---|---|---|---|---|
| 工作台 | / | home/DashboardView.vue | 登录用户 | requiresAuth | 查看经营摘要和未完成任务 | 订单金额、收款、任务队列、阶段进度 |
| 项目看板 | /projects/board | tasks/ProductionTaskBoard.vue | admin、production；旧入口 /production-tasks/board | 仅 requiresAuth | 查看、筛选、进入任务 | 设计/制作/安装任务、进度、逾期、终态隐藏 |
| 订单列表 | /orders | orders/OrderList.vue | admin、sales | 仅 requiresAuth | 搜索、筛选、打开详情 | 订单状态、金额、收款、毛利 |
| 订单详情 | /orders/:id | orders/OrderDetail.vue | 从订单列表进入 | 仅 requiresAuth | 查看明细、进入任务、成本和收款 | 每条明细阶段、总进度、任务进度、成本 |
| 订单编辑 | /orders/:id/edit | orders/OrderEditor.vue | 订单详情 | 仅 requiresAuth | 编辑订单和明细 | 变更预检、锁定原因、保存 |
| 设计任务 | /design-tasks、/design-tasks/:id | tasks/DesignTaskList.vue、DesignTaskDetail.vue | admin、designer | 仅 requiresAuth | 创建/分配/推进设计明细 | 设计中、已完成、明细选择 |
| 制作任务 | /production-tasks、/production-tasks/:id | tasks/ProductionTaskList.vue、ProductionTaskDetail.vue | admin、production | 仅 requiresAuth | 创建/分配/推进制作明细 | 制作中、外协阻塞、明细选择 |
| 安装任务 | /installation-tasks、/installation-tasks/:id | tasks/InstallationTaskList.vue、InstallationTaskDetail.vue | admin、installer | 仅 requiresAuth | 分配/推进安装明细、现场照片 | 安装中、外协阻塞、明细选择、现场照片 |
| 项目成本 | /project-costs、/project-costs/:orderId | payments/ProjectCostList.vue、ProjectCostDetail.vue | admin、finance | 仅 requiresAuth | 登记、筛选、查看成本 | 整单/明细归属、金额、欠款、成本类别 |

## 3. 路由族矩阵

| 信息架构 | 路由族 | 页面范围 | 导航入口与角色 | 主动作 | 一致性关注点 |
|---|---|---|---|---|---|
| 登录与个人 | /login、/profile、/mobile/profile | 登录、个人中心、移动个人页 | 登录/已登录 | 登录、改密、退出、维护个人信息 | 会话过期、强制改密、桌面/移动反馈 |
| 客户与销售 | /customers、/quotes、/cdr/quotes、/contracts、/orders | 客户、常规报价、智能报价、合同、订单 | 客户与销售；admin、sales | 新建、编辑、查看、转订单 | 列表筛选、表单校验、金额格式和主动作 |
| 项目交付 | /design-tasks、/production-tasks、/installation-tasks、/acceptances、/outsource、/inventory、/products | 设计、制作、安装、外协、库存、产品定价 | 项目交付；按子菜单角色过滤 | 分配、推进、关联明细、外协、查看 | 明细阶段、进度、不可选原因、外协阻塞 |
| 财务中心 | /receivables、/expenses、/statements、/project-costs、/cost-debts、/outsource/payments | 应收、支出、对账、项目成本、欠款、外协付款 | 财务中心；admin、finance | 登记、收款、付款、对账、导出 | 金额精度、整单/明细成本、敏感数据 |
| 人事管理 | /employees、/departments、/salaries、/salary-report、/salary-rules、/employment-histories、/leaves、/attendance | 员工、部门、工资、请假、考勤 | 人事管理；admin | 增删改、计算、审批、打印 | 原有审批页与用户要求的业务审核边界需区分，不能扩展到订单交付 |
| 资源中心 | /vehicle-*、/aerial-* | 公司车辆、高空作业车 | 资源中心；子项角色不完全统一 | 台账、申请、派车、安全检查、费用 | 多种专用布局、移动操作、照片/附件 |
| 经营分析 | /reports/*、/ai/anomalies、/ai/reports | 日报、月报、异常、经营报告 | 经营分析；admin、sales、finance | 查询、分析、导出 | 图表颜色、空态、时间筛选和数字格式 |
| 系统管理 | /admin/*、/operation-logs、/backups、/notifications、/chat | 用户、角色、设置、日志、备份、通知、聊天 | 系统管理；admin；聊天/通知另有入口 | 管理权限、查看日志、备份、沟通 | 权限最终事实、敏感信息、通知入口边界 |
| 移动安装 | /mobile、/mobile/installation、/mobile/profile | 移动首页、安装任务、个人页 | 独立移动布局；已登录 | 查看任务、拍照、上传、提交验收 | 深色主题、触控目标、现场可读性、底部导航 |

## 4. 权限一致性问题

当前代码有三层权限入口：

1. navigation.ts 对菜单项做角色过滤。
2. router/index.ts 只对部分管理路由设置 meta.roles，大多数业务路由只有 requiresAuth。
3. 后端 API 使用权限依赖和角色依赖做最终校验。

这三层并非完全等价。尤其项目看板、订单、任务和成本等核心路由通常没有路由级角色 meta，直接访问 URL 的行为不能仅凭导航隐藏来推断。P03/P04 的处理顺序应当是：

- 先盘点资源-动作-角色-对象状态矩阵。
- 再把页面按钮和明细勾选能力改为后端返回的 capabilities。
- 最后决定哪些页面需要路由级角色兜底，避免前端重复发明权限规则。

## 5. 主动作统一规则

| 页面类型 | 唯一主要动作 | 次要动作 | 高风险动作 |
|---|---|---|---|
| 列表 | 新建或打开筛选后的目标对象 | 搜索、重置、刷新、导出 | 删除、回收、批量变更 |
| 详情 | 推进当前对象的下一步 | 查看明细、任务、成本、收款 | 删除订单/任务、撤销、金额变更 |
| 任务处理 | 只推进当前勾选订单明细 | 刷新状态、保存关联、分配 | 删除任务、跨阶段强制推进 |
| 成本登记 | 提交当前归属范围的一笔成本 | 选择明细、填充摘要、上传凭证 | 影响金额、整单/明细归属切换 |
| 看板 | 打开未完成任务 | 刷新、逾期筛选、阶段筛选 | 直接完成整单或批量推进 |
| 移动安装 | 查看当前安装任务并更新现场状态 | 拍照、相册、查看地址/联系人 | 提交验收、删除照片或任务 |

## 6. 下一阶段动作

- P02：建立页面骨架、状态标签、进度条、表格壳、弹窗/抽屉和反馈原语。
- P03：统一导航、路由可见性、移动端主动作和无权限反馈。
- P04：统一状态视图、动作能力、错误 envelope、request id 和冲突语义。
- P05：优先迁移工作台、项目看板、订单详情、设计/制作/安装任务和项目成本。
