-- 广告制作安装工程管理系统 PostgreSQL 数据库草案
-- 注意：这是规划级 schema，实际开发时建议配合 Alembic 迁移管理。

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 用户与权限
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    real_name VARCHAR(64),
    phone VARCHAR(32),
    email VARCHAR(128),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id),
    role_id UUID NOT NULL REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(128) NOT NULL UNIQUE,
    name VARCHAR(128) NOT NULL,
    description TEXT
);

CREATE TABLE role_permissions (
    role_id UUID NOT NULL REFERENCES roles(id),
    permission_id UUID NOT NULL REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);

-- 客户
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_no VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    customer_type VARCHAR(64),
    level VARCHAR(64),
    phone VARCHAR(64),
    wechat VARCHAR(64),
    address TEXT,
    tax_no VARCHAR(128),
    invoice_info TEXT,
    default_payment_days INTEGER DEFAULT 0,
    default_discount NUMERIC(6,4) DEFAULT 1.0000,
    remark TEXT,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE TABLE customer_contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id),
    name VARCHAR(128) NOT NULL,
    phone VARCHAR(64),
    wechat VARCHAR(64),
    position VARCHAR(128),
    is_primary BOOLEAN DEFAULT FALSE,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 产品、材质、工艺
CREATE TABLE product_categories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(128) NOT NULL,
    parent_id UUID REFERENCES product_categories(id),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category_id UUID REFERENCES product_categories(id),
    name VARCHAR(128) NOT NULL,
    unit VARCHAR(32) NOT NULL DEFAULT '项',
    pricing_method VARCHAR(64) NOT NULL DEFAULT 'quantity',
    default_price NUMERIC(14,2) DEFAULT 0,
    min_charge NUMERIC(14,2) DEFAULT 0,
    remark TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE materials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(128) NOT NULL,
    spec VARCHAR(128),
    unit VARCHAR(32) NOT NULL DEFAULT '张',
    purchase_price NUMERIC(14,2) DEFAULT 0,
    sale_price NUMERIC(14,2) DEFAULT 0,
    loss_rate NUMERIC(8,4) DEFAULT 0,
    safe_stock NUMERIC(14,3) DEFAULT 0,
    remark TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE processes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(128) NOT NULL,
    charge_method VARCHAR(64) NOT NULL DEFAULT 'fixed',
    default_price NUMERIC(14,2) DEFAULT 0,
    remark TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE price_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(128) NOT NULL,
    product_id UUID REFERENCES products(id),
    material_id UUID REFERENCES materials(id),
    process_id UUID REFERENCES processes(id),
    pricing_method VARCHAR(64) NOT NULL,
    unit_price NUMERIC(14,2) NOT NULL DEFAULT 0,
    min_charge NUMERIC(14,2) DEFAULT 0,
    formula JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 报价
CREATE TABLE quotes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_no VARCHAR(64) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    project_name VARCHAR(255) NOT NULL,
    sales_user_id UUID REFERENCES users(id),
    status VARCHAR(64) NOT NULL DEFAULT 'draft',
    subtotal_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    tax_rate NUMERIC(8,4) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    valid_until DATE,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE TABLE quote_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id UUID NOT NULL REFERENCES quotes(id),
    product_id UUID REFERENCES products(id),
    material_id UUID REFERENCES materials(id),
    process_id UUID REFERENCES processes(id),
    item_name VARCHAR(255) NOT NULL,
    length NUMERIC(12,3),
    width NUMERIC(12,3),
    height NUMERIC(12,3),
    quantity NUMERIC(14,3) NOT NULL DEFAULT 1,
    unit VARCHAR(32),
    area NUMERIC(14,3),
    unit_price NUMERIC(14,2) NOT NULL DEFAULT 0,
    process_fee NUMERIC(14,2) NOT NULL DEFAULT 0,
    installation_fee NUMERIC(14,2) NOT NULL DEFAULT 0,
    design_fee NUMERIC(14,2) NOT NULL DEFAULT 0,
    transport_fee NUMERIC(14,2) NOT NULL DEFAULT 0,
    other_fee NUMERIC(14,2) NOT NULL DEFAULT 0,
    subtotal_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    remark TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE quote_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id UUID NOT NULL REFERENCES quotes(id),
    version_no INTEGER NOT NULL,
    snapshot JSONB NOT NULL,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 订单
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_no VARCHAR(64) NOT NULL UNIQUE,
    quote_id UUID REFERENCES quotes(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    project_name VARCHAR(255) NOT NULL,
    sales_user_id UUID REFERENCES users(id),
    status VARCHAR(64) NOT NULL DEFAULT 'pending_confirm',
    total_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    paid_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    unpaid_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    cost_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    gross_profit NUMERIC(14,2) NOT NULL DEFAULT 0,
    delivery_deadline TIMESTAMP,
    installation_address TEXT,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);

CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id),
    source_quote_item_id UUID REFERENCES quote_items(id),
    item_name VARCHAR(255) NOT NULL,
    product_id UUID REFERENCES products(id),
    material_id UUID REFERENCES materials(id),
    process_id UUID REFERENCES processes(id),
    length NUMERIC(12,3),
    width NUMERIC(12,3),
    height NUMERIC(12,3),
    quantity NUMERIC(14,3) DEFAULT 1,
    unit VARCHAR(32),
    unit_price NUMERIC(14,2) DEFAULT 0,
    subtotal_amount NUMERIC(14,2) DEFAULT 0,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE order_status_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID NOT NULL REFERENCES orders(id),
    from_status VARCHAR(64),
    to_status VARCHAR(64) NOT NULL,
    reason TEXT,
    operated_by UUID REFERENCES users(id),
    operated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 任务
CREATE TABLE design_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_no VARCHAR(64) NOT NULL UNIQUE,
    order_id UUID NOT NULL REFERENCES orders(id),
    title VARCHAR(255) NOT NULL,
    requirement TEXT,
    designer_id UUID REFERENCES users(id),
    status VARCHAR(64) NOT NULL DEFAULT 'pending_assign',
    deadline TIMESTAMP,
    confirmed_at TIMESTAMP,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE production_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_no VARCHAR(64) NOT NULL UNIQUE,
    order_id UUID NOT NULL REFERENCES orders(id),
    order_item_id UUID REFERENCES order_items(id),
    title VARCHAR(255) NOT NULL,
    material_desc TEXT,
    process_desc TEXT,
    size_desc TEXT,
    quantity NUMERIC(14,3) DEFAULT 1,
    assigned_to UUID REFERENCES users(id),
    status VARCHAR(64) NOT NULL DEFAULT 'pending',
    planned_finish_at TIMESTAMP,
    actual_finish_at TIMESTAMP,
    qc_status VARCHAR(64),
    rework_reason TEXT,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE installation_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_no VARCHAR(64) NOT NULL UNIQUE,
    order_id UUID NOT NULL REFERENCES orders(id),
    address TEXT NOT NULL,
    contact_name VARCHAR(128),
    contact_phone VARCHAR(64),
    scheduled_at TIMESTAMP,
    assigned_to UUID REFERENCES users(id),
    vehicle VARCHAR(128),
    tools TEXT,
    is_high_altitude BOOLEAN DEFAULT FALSE,
    need_crane BOOLEAN DEFAULT FALSE,
    requirement TEXT,
    status VARCHAR(64) NOT NULL DEFAULT 'pending_dispatch',
    acceptance_result TEXT,
    accepted_at TIMESTAMP,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE outsourcing_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_no VARCHAR(64) NOT NULL UNIQUE,
    order_id UUID NOT NULL REFERENCES orders(id),
    vendor_name VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    amount NUMERIC(14,2) DEFAULT 0,
    sent_at TIMESTAMP,
    expected_receive_at TIMESTAMP,
    received_at TIMESTAMP,
    status VARCHAR(64) DEFAULT 'pending',
    quality_issue TEXT,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 财务
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    payment_no VARCHAR(64) NOT NULL UNIQUE,
    order_id UUID NOT NULL REFERENCES orders(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    amount NUMERIC(14,2) NOT NULL,
    payment_method VARCHAR(64),
    paid_at TIMESTAMP NOT NULL,
    handled_by UUID REFERENCES users(id),
    status VARCHAR(64) NOT NULL DEFAULT 'normal',
    void_reason TEXT,
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE expenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    expense_no VARCHAR(64) NOT NULL UNIQUE,
    order_id UUID REFERENCES orders(id),
    category VARCHAR(128),
    amount NUMERIC(14,2) NOT NULL,
    paid_at TIMESTAMP,
    handled_by UUID REFERENCES users(id),
    remark TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE customer_statements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    statement_no VARCHAR(64) NOT NULL UNIQUE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_order_amount NUMERIC(14,2) DEFAULT 0,
    total_paid_amount NUMERIC(14,2) DEFAULT 0,
    total_unpaid_amount NUMERIC(14,2) DEFAULT 0,
    status VARCHAR(64) DEFAULT 'draft',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE customer_statement_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    statement_id UUID NOT NULL REFERENCES customer_statements(id),
    order_id UUID NOT NULL REFERENCES orders(id),
    order_amount NUMERIC(14,2) DEFAULT 0,
    paid_amount NUMERIC(14,2) DEFAULT 0,
    unpaid_amount NUMERIC(14,2) DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 文件与日志
CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    object_type VARCHAR(64) NOT NULL,
    object_id UUID NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_ext VARCHAR(32),
    file_size BIGINT,
    storage_path TEXT NOT NULL,
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE operation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    object_type VARCHAR(64),
    object_id UUID,
    action VARCHAR(128) NOT NULL,
    before_data JSONB,
    after_data JSONB,
    ip_address VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customers_name ON customers(name);
CREATE INDEX idx_quotes_customer_id ON quotes(customer_id);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_attachments_object ON attachments(object_type, object_id);
