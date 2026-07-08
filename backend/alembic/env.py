from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.core.config import settings
from app.models.base import Base

# Import all models so Base.metadata knows about them
from app.models.user import User, Role, Permission
from app.models.customer import Customer, CustomerContact
from app.models.product import ProductCategory, Product, Material, Process, PriceRule
from app.models.quote import Quote, QuoteItem, QuoteVersion
from app.models.order import Order, OrderItem, OrderStatusLog
from app.models.operation_log import OperationLog
from app.models.task import DesignTask, ProductionTask, InstallationTask, Attachment
from app.models.payment import Payment, CustomerStatement, Expense
from app.models.outsource import OutsourceVendor, OutsourceTask, OutsourcePayment
from app.models.inventory import InventoryItem, StockRecord
from app.models.project_cost import ProjectCost
from app.models.acceptance import AcceptanceForm, AcceptanceItem, AcceptanceAttachment

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
