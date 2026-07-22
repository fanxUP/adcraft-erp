import uuid

from sqlalchemy import DateTime, Numeric, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, SoftDeleteMixin


class FrameworkContractProject(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "framework_contract_projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="部门/科室")
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="附件存储路径")
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="附件文件名")

    # 关系
    contract: Mapped["Contract"] = relationship(lazy="selectin")
    customer: Mapped["Customer"] = relationship(lazy="selectin")
    documents: Mapped[list["BusinessDocument"]] = relationship(
        secondary="framework_contract_project_documents", lazy="selectin"
    )


class FrameworkContractProjectDocument(Base, TimestampMixin):
    """统一框架合同项目-单据关联表（合并 _orders + _quotes）。"""
    __tablename__ = "framework_contract_project_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("framework_contract_projects.id"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_documents.id"), nullable=False
    )
