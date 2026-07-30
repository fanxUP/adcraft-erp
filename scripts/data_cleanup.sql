-- ============================================================
-- 数据适配脚本：清理残留孤立任务
-- 安全：仅影响 pending/draft 状态的记录，不修改已完成的
-- ============================================================

-- 1. 取消过期设计任务（订单已进入生产/安装/验收/完成，但设计任务仍在 pending）
UPDATE design_tasks dt SET status = 'cancelled', updated_at = NOW()
FROM business_documents bd
WHERE bd.id = dt.document_id
  AND bd.doc_type = 'order'
  AND dt.status = 'pending'
  AND bd.status IN ('in_production', 'in_installation', 'pending_acceptance', 'completed');

-- 2. 取消过期生产任务
UPDATE production_tasks pt SET status = 'cancelled', updated_at = NOW()
FROM business_documents bd
WHERE bd.id = pt.document_id
  AND bd.doc_type = 'order'
  AND pt.status = 'pending'
  AND bd.status IN ('in_installation', 'pending_acceptance', 'completed');

-- 3. 取消过期安装任务
UPDATE installation_tasks it SET status = 'cancelled', updated_at = NOW()
FROM business_documents bd
WHERE bd.id = it.document_id
  AND bd.doc_type = 'order'
  AND it.status = 'pending'
  AND bd.status IN ('pending_acceptance', 'completed');

-- 4. 清理过期草稿验收单
UPDATE acceptance_forms af SET deleted_at = NOW()
FROM business_documents bd
WHERE bd.id = af.document_id
  AND af.status = 'draft'
  AND af.deleted_at IS NULL
  AND bd.status IN ('in_production', 'in_installation', 'completed');

-- 5. 报告结果
SELECT 'design_tasks_cancelled' as action, count(*) FROM design_tasks
  WHERE status = 'cancelled' AND updated_at > NOW() - interval '1 minute'
UNION ALL
SELECT 'production_tasks_cancelled', count(*) FROM production_tasks
  WHERE status = 'cancelled' AND updated_at > NOW() - interval '1 minute'
UNION ALL
SELECT 'installation_tasks_cancelled', count(*) FROM installation_tasks
  WHERE status = 'cancelled' AND updated_at > NOW() - interval '1 minute'
UNION ALL
SELECT 'acceptances_cleaned', count(*) FROM acceptance_forms
  WHERE deleted_at > NOW() - interval '1 minute';
