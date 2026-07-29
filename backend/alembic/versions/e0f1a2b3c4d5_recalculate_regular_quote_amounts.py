"""重算常规报价金额并修复订单收款余额。

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-07-30
"""

from alembic import op


revision = "e0f1a2b3c4d5"
down_revision = "d9e0f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH calculated AS (
            SELECT
                item.id,
                ROUND(
                    COALESCE(item.width, 0)
                    * CASE item.width_unit
                        WHEN 'cm' THEN 0.01
                        WHEN 'mm' THEN 0.001
                        ELSE 1
                      END
                    * COALESCE(item.height, 0)
                    * CASE item.height_unit
                        WHEN 'cm' THEN 0.01
                        WHEN 'mm' THEN 0.001
                        ELSE 1
                      END
                    * COALESCE(item.pieces, 1),
                    2
                ) AS calculated_area
            FROM business_document_items AS item
            JOIN business_documents AS document
                ON document.id = item.document_id
            WHERE document.doc_type = 'quote'
              AND document.quote_mode = 'regular'
        )
        UPDATE business_document_items AS item
        SET
            area = calculated.calculated_area,
            subtotal_amount = ROUND(
                (
                    CASE
                        WHEN item.use_area
                        THEN calculated.calculated_area
                        ELSE COALESCE(item.quantity, 0)
                    END
                ) * COALESCE(item.unit_price, 0)
                + COALESCE(item.process_fee, 0)
                + COALESCE(item.installation_fee, 0)
                + COALESCE(item.design_fee, 0)
                + COALESCE(item.transport_fee, 0)
                + COALESCE(item.other_fee, 0),
                2
            )
        FROM calculated
        WHERE item.id = calculated.id
        """
    )

    op.execute(
        """
        WITH totals AS (
            SELECT
                document.id,
                COALESCE(SUM(item.subtotal_amount), 0) AS subtotal
            FROM business_documents AS document
            LEFT JOIN business_document_items AS item
                ON item.document_id = document.id
            WHERE document.doc_type = 'quote'
              AND document.quote_mode = 'regular'
            GROUP BY document.id
        )
        UPDATE business_documents AS document
        SET
            subtotal_amount = totals.subtotal,
            tax_amount = ROUND(
                GREATEST(
                    totals.subtotal - COALESCE(document.discount_amount, 0),
                    0
                ) * COALESCE(document.tax_rate, 0) / 100,
                2
            ),
            total_amount = ROUND(
                GREATEST(
                    totals.subtotal - COALESCE(document.discount_amount, 0),
                    0
                )
                + GREATEST(
                    totals.subtotal - COALESCE(document.discount_amount, 0),
                    0
                ) * COALESCE(document.tax_rate, 0) / 100,
                2
            )
        FROM totals
        WHERE document.id = totals.id
        """
    )

    op.execute(
        """
        UPDATE payments
        SET
            is_voided = TRUE,
            void_reason = COALESCE(
                void_reason,
                '系统迁移：该记录是历史应收占位，不是实际收款'
            ),
            voided_at = COALESCE(voided_at, NOW())
        WHERE is_voided = FALSE
          AND paid_at IS NULL
          AND remark = '来自报价自动转换，待收款'
        """
    )

    op.execute(
        """
        WITH receipts AS (
            SELECT
                document.id,
                COALESCE(
                    SUM(payment.amount) FILTER (
                        WHERE payment.is_voided = FALSE
                    ),
                    0
                ) AS paid
            FROM business_documents AS document
            LEFT JOIN payments AS payment
                ON payment.document_id = document.id
            WHERE document.doc_type = 'order'
            GROUP BY document.id
        )
        UPDATE business_documents AS document
        SET
            paid_amount = receipts.paid,
            unpaid_amount = GREATEST(
                COALESCE(document.total_amount, 0) - receipts.paid,
                0
            ),
            gross_profit = COALESCE(document.total_amount, 0)
                - COALESCE(document.cost_amount, 0)
        FROM receipts
        WHERE document.id = receipts.id
        """
    )


def downgrade() -> None:
    # 金额是从业务明细确定性重算的结果，不恢复历史错误值。
    pass
