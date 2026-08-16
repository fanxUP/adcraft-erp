# 数据修复记录（source_quote_id 残留清理）

> 日期：2026-08-16
> 类型：一次性数据修正（无 schema 变更，不入迁移）

## 背景

历史版本「同 ID 翻转」的报价转订单逻辑存在 `source_quote_id = doc.id` 自引用 bug，
加上「订单转报价」时未彻底清除来源引用，导致 `business_documents` 表残留脏数据。

## 修复范围

2026-08-16 在线执行 `UPDATE`，共 **9 行**置 NULL：

| 类型 | 行 | 说明 |
|------|----|------|
| 订单自引用（`source_quote_id` = 自身 id） | 4 | `O20260803-0006`、`O20260804-0002`、`O20260813-0001`、`O20260813-0002` |
| 草稿报价误带 `source_quote_id` | 5 | `Q20260722-0001`、`Q20260813-0001`、`Q20260813-0002`、`Q20260813-0003`、`Q20260813-0004` |

其中 `O20260804-0001` 的来源报价已在此前单独修复（回链 `Q20260717-0001`），不在本次范围。

## 修复语句

```sql
UPDATE business_documents
SET source_quote_id = NULL
WHERE (doc_type = 'order' AND source_quote_id = id)
   OR (doc_type = 'quote' AND source_quote_id IS NOT NULL);
```

## 修复后校验

- 自引用订单数：0
- 带 `source_quote_id` 的报价数：0
- 订单→来源报价：13 单中 7 单正确回链（其余为手工单/历史单，NULL 合理）

## 预防

- 代码侧已修复：`convert_doc_type` 转单不再写 `source_quote_id = self`（见提交 `707aa67`）。
- 架构侧已修复：常规报价转单改为「新建订单 + 回链来源报价」，见 ADR-002。
