# 统一供应商档案与多业务身份

## 功能与兼容

- 在资源中心保留一个“供应商管理”入口。`/outsource/vendors` 跳转至 `/suppliers?supplier_type=outsource`。
- 一份档案保留一个 UUID 与编号；`supplier_types` 为多选业务身份，`service_types` 为多选外协能力。
- 材料与外协可以同时勾选。成本/支出使用同一 UUID；外协选商检查启用状态、外协身份和具体能力。
- 旧 `supplier_type`、`service_type` 字段保留用于接口兼容；筛选与权限范围使用新的列表字段。
- 取消外协能力或停用仅阻断新的任务及改派；原任务的说明、进度与付款继续按原流程处理。
- 原外协商权限可以进入统一页面，但仅管理有外协身份的档案，不能改变业务身份或停用多业务供应商。银行信息与账务权限继续独立。
- 旧删除接口转为停用，不再写 `deleted_at`。历史已经软删除的档案维持原状态。
- 不自动合并可能同名的两份档案，也不重算或合并财务金额。

## 迁移 `sup02_supplier_capabilities`

前置版本：`obd01_order_business_date`。迁移只扩展 `outsource_vendors`，不修改任务、成本、支出、付款的外键。

转换规则：旧单选业务类型转换为单元素列表。已知旧外协服务类型转换为能力列表，并加入该供应商历史任务实际使用过的四类标准能力；没有指定或为自定义文字的旧服务类型，为保留原可选范围，初始化为制作、安装、设计、运输四项。自定义原文字仍保留在旧字段中。上线后可在编辑中核对并收窄能力。

新增两列 JSONB、两个 GIN 索引与选项范围约束。增加字段、全表回填、设置非空、建索引会持有表锁；上线前应检查档案/任务规模并安排短维护窗口。当前验证使用的是合成历史数据，不是生产备份副本。

发布前检查：

```sql
SELECT supplier_type, count(*) FROM outsource_vendors GROUP BY supplier_type;
SELECT service_type, count(*) FROM outsource_vendors
 WHERE supplier_type = 'outsource' GROUP BY service_type;
SELECT count(*) FROM outsource_vendors;
SELECT count(*) FROM outsource_tasks;
```

确认旧业务类型全部属于 `outsource/material/equipment/transport/service/other`。检查空名称、同名档案和已软删除档案，仅输出数量或待核对结果，不自动删除或重绑。

生产发布前对数据库做可恢复备份，并在备份副本执行迁移。暂停写入，部署匹配的新后端与前端，执行迁移后检查供应商数量、UUID、启停/删除状态以及外键关联数量保持一致；验证双身份档案两边可选、停用后新建受阻、历史付款仍可完成，再恢复使用。

## 恢复策略

产生多选数据后，降级到旧单选结构会丢失业务身份，迁移的 downgrade 会主动拒绝。先修复并向前发布；如必须回退，暂停写入，导出上线后新增/修改数据，再协调恢复匹配的数据库备份与应用版本，核对补录数据后恢复。不要直接让旧应用对新增非空字段的结构继续写入。

## 本地验证

默认测试不连接实际数据库。两个 PostgreSQL 演练用例只在显式设置 `SUPPLIER_MIGRATION_TEST_URL` 时运行；每次使用随机独立 schema，并在结束时清理自己的 schema。该变量必须指向临时测试实例。

```sh
cd backend
SUPPLIER_MIGRATION_TEST_URL='<isolated-test-PostgreSQL-URL>' .venv/bin/python -m pytest \
  tests/test_supplier_capabilities_migration.py tests/test_supplier_capabilities_integration.py -q
```

迁移用例检查旧数据回填、关联保留、启停状态、多角色筛选与有损降级拦截；业务用例实际创建双身份供应商和任务，取消外协身份后编辑任务，停用后付款并核对余款。
