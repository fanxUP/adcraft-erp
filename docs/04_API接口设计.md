# 04. API 接口设计

## 1. API 风格

建议采用 RESTful API。

统一前缀：

```text
/api/v1
```

统一返回格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

错误示例：

```json
{
  "code": 40001,
  "message": "参数错误",
  "data": null
}
```

## 2. 认证接口

```text
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/change-password
```

## 3. 用户与权限

```text
GET    /api/v1/users
POST   /api/v1/users
GET    /api/v1/users/{id}
PUT    /api/v1/users/{id}
DELETE /api/v1/users/{id}

GET    /api/v1/roles
POST   /api/v1/roles
PUT    /api/v1/roles/{id}
DELETE /api/v1/roles/{id}
```

## 4. 客户管理

```text
GET    /api/v1/customers
POST   /api/v1/customers
GET    /api/v1/customers/{id}
PUT    /api/v1/customers/{id}
DELETE /api/v1/customers/{id}
GET    /api/v1/customers/{id}/quotes
GET    /api/v1/customers/{id}/orders
GET    /api/v1/customers/{id}/payments
GET    /api/v1/customers/{id}/balance
```

## 5. 产品/材质/工艺

```text
GET    /api/v1/product-categories
POST   /api/v1/product-categories
GET    /api/v1/products
POST   /api/v1/products
PUT    /api/v1/products/{id}
DELETE /api/v1/products/{id}

GET    /api/v1/materials
POST   /api/v1/materials
PUT    /api/v1/materials/{id}
DELETE /api/v1/materials/{id}

GET    /api/v1/processes
POST   /api/v1/processes
PUT    /api/v1/processes/{id}
DELETE /api/v1/processes/{id}

GET    /api/v1/price-rules
POST   /api/v1/price-rules
PUT    /api/v1/price-rules/{id}
DELETE /api/v1/price-rules/{id}
```

## 6. 报价管理

```text
GET    /api/v1/quotes
POST   /api/v1/quotes
GET    /api/v1/quotes/{id}
PUT    /api/v1/quotes/{id}
DELETE /api/v1/quotes/{id}
POST   /api/v1/quotes/{id}/items
PUT    /api/v1/quotes/{id}/items/{item_id}
DELETE /api/v1/quotes/{id}/items/{item_id}
POST   /api/v1/quotes/{id}/calculate
POST   /api/v1/quotes/{id}/confirm
POST   /api/v1/quotes/{id}/convert-to-order
GET    /api/v1/quotes/{id}/versions
GET    /api/v1/quotes/{id}/export-pdf
```

## 7. 订单管理

```text
GET    /api/v1/orders
POST   /api/v1/orders
GET    /api/v1/orders/{id}
PUT    /api/v1/orders/{id}
POST   /api/v1/orders/{id}/change-status
GET    /api/v1/orders/{id}/status-logs
POST   /api/v1/orders/{id}/generate-tasks
GET    /api/v1/orders/{id}/tasks
GET    /api/v1/orders/{id}/payments
GET    /api/v1/orders/{id}/attachments
```

## 8. 设计任务

```text
GET    /api/v1/design-tasks
POST   /api/v1/design-tasks
GET    /api/v1/design-tasks/{id}
PUT    /api/v1/design-tasks/{id}
POST   /api/v1/design-tasks/{id}/assign
POST   /api/v1/design-tasks/{id}/upload-draft
POST   /api/v1/design-tasks/{id}/request-revision
POST   /api/v1/design-tasks/{id}/confirm
```

## 9. 制作任务

```text
GET    /api/v1/production-tasks
POST   /api/v1/production-tasks
GET    /api/v1/production-tasks/{id}
PUT    /api/v1/production-tasks/{id}
POST   /api/v1/production-tasks/{id}/start
POST   /api/v1/production-tasks/{id}/finish
POST   /api/v1/production-tasks/{id}/qc-pass
POST   /api/v1/production-tasks/{id}/rework
```

## 10. 安装任务

```text
GET    /api/v1/installation-tasks
POST   /api/v1/installation-tasks
GET    /api/v1/installation-tasks/{id}
PUT    /api/v1/installation-tasks/{id}
POST   /api/v1/installation-tasks/{id}/dispatch
POST   /api/v1/installation-tasks/{id}/start
POST   /api/v1/installation-tasks/{id}/upload-photo
POST   /api/v1/installation-tasks/{id}/accept
POST   /api/v1/installation-tasks/{id}/rework
```

## 11. 外协管理

```text
GET    /api/v1/outsourcing-tasks
POST   /api/v1/outsourcing-tasks
GET    /api/v1/outsourcing-tasks/{id}
PUT    /api/v1/outsourcing-tasks/{id}
POST   /api/v1/outsourcing-tasks/{id}/send
POST   /api/v1/outsourcing-tasks/{id}/receive
POST   /api/v1/outsourcing-tasks/{id}/quality-issue
```

## 12. 收款与对账

```text
GET    /api/v1/payments
POST   /api/v1/payments
GET    /api/v1/payments/{id}
POST   /api/v1/payments/{id}/void

GET    /api/v1/statements
POST   /api/v1/statements
GET    /api/v1/statements/{id}
GET    /api/v1/statements/{id}/export-pdf
POST   /api/v1/statements/{id}/confirm
```

## 13. 文件上传

```text
POST /api/v1/attachments/upload
GET  /api/v1/attachments/{id}
GET  /api/v1/attachments/{id}/download
POST /api/v1/attachments/{id}/archive
```

## 14. 报表

```text
GET /api/v1/reports/dashboard
GET /api/v1/reports/sales-daily
GET /api/v1/reports/sales-monthly
GET /api/v1/reports/customer-balance-ranking
GET /api/v1/reports/order-status-summary
GET /api/v1/reports/salesperson-performance
GET /api/v1/reports/payment-summary
```

## 15. 备份

```text
POST /api/v1/admin/backup/create
GET  /api/v1/admin/backup/list
POST /api/v1/admin/backup/restore
```

恢复接口必须仅管理员可用，且需要二次确认。
