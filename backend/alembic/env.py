from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.config import settings
from app.models.base import Base

# Import all models so Base.metadata knows about them
from app.models.user import User, Role, Permission
from app.models.customer import Customer, CustomerContact
from app.models.product import ProductCategory, Product, Material, Process, PriceRule
from app.models.business_document import BusinessDocument, BusinessDocumentItem, BusinessDocumentStatusLog, BusinessDocumentVersion
from app.models.operation_log import OperationLog
from app.models.task import DesignTask, ProductionTask, InstallationTask, Attachment
from app.models.payment import Payment, CustomerStatement, Expense
from app.models.outsource import OutsourceVendor, OutsourceTask, OutsourcePayment
from app.models.inventory import InventoryItem, StockRecord
from app.models.project_cost import ProjectCost
from app.models.chat import Conversation, ConversationMember, Message, MessageReadReceipt, UserPresence
from app.models.notification import Notification
from app.models.acceptance import AcceptanceForm, AcceptanceItem, AcceptanceAttachment
from app.models.contract import Contract, ContractDocument
from app.models.framework_contract import FrameworkContractProject, FrameworkContractProjectDocument
from app.models.vehicle import (
    Vehicle, VehicleDriver, VehicleUseRequest, VehicleDispatch, VehicleTripRecord,
    VehicleFuelRecord, VehicleMaintenanceRecord, VehicleCertificate, VehicleIncident,
    VehicleCostAllocation, VehicleAgentDraft,
)
from app.models.aerial import (
    AerialVehicle, AerialDriver, AerialDailyLedger, AerialDriverExpense,
    AerialDriverWage, AerialVehicleCost, AerialSafetyCheck,
    AerialLedgerAttachment, AerialLedgerAuditLog, AerialAgentDraft,
)

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
