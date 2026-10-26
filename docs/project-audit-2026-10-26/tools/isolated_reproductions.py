"""Bounded reproductions using only an explicitly named disposable local DB."""
import asyncio
import importlib
import json
import os
import pkgutil
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

os.environ['APP_ENV']='test'
os.environ['DATABASE_URL']='postgresql+asyncpg:///adcraft_audit_20261026'
os.environ['DATABASE_URL_SYNC']='postgresql+psycopg2:///adcraft_audit_20261026'
import app.models
from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.models.base import Base
from app.models.business_document import BusinessDocument, BusinessDocumentItem, BusinessDocumentGroup
from app.models.customer import Customer
from app.models.user import User
from app.models.payment import Payment
from app.services.business_document_service import BusinessDocumentService
from app.services.finance_center_service import FinanceCenterService
from app.services.report_service import ReportService
from app.services.number_generator import generate_order_no

for item in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module('app.models.'+item.name)

async def main():
    schema='project_audit_'+uuid4().hex
    engine=create_async_engine(os.environ['DATABASE_URL'],connect_args={'server_settings':{'search_path':schema}})
    evidence={'environment':'disposable local schema; production untouched','checks':{}}
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSession(engine,expire_on_commit=False) as db:
            customer_id,user_id,quote_id=uuid4(),uuid4(),uuid4()
            await db.execute(insert(Customer).values(id=customer_id,customer_no='AUDIT-C',name='AUDIT synthetic customer'))
            await db.execute(insert(User).values(id=user_id,username='AUDIT-USER',password_hash='not-a-real-login'))
            await db.execute(insert(Payment),[
                dict(payment_no='AUDIT-P-ACTUAL',customer_id=customer_id,amount=100,paid_at=datetime(2026,10,8,12),created_at=datetime(2026,10,20,12)),
                dict(payment_no='AUDIT-P-REGISTERED',customer_id=customer_id,amount=200,paid_at=datetime(2026,10,20,12),created_at=datetime(2026,10,8,12)),
            ])
            await db.execute(insert(BusinessDocument).values(doc_type='order',doc_no='AUDIT-NEXT-MONTH',project_name='AUDIT',status='confirmed',order_date=date(2026,11,1),total_amount=10))
            await db.execute(insert(BusinessDocument).values(id=quote_id,doc_type='quote',doc_no='AUDIT-QUOTE',project_name='AUDIT',status='confirmed',quote_mode='regular',customer_id=customer_id,subtotal_amount=1000,discount_amount=100,tax_rate=0,tax_amount=0,total_amount=900))
            await db.execute(insert(BusinessDocumentItem).values(document_id=quote_id,item_name='AUDIT line',quantity=1,pieces=1,unit_price=1000,subtotal_amount=1000,group_id='AUDIT-GROUP',group_name='AUDIT group'))
            await db.execute(insert(BusinessDocumentGroup).values(document_id=quote_id,group_id='AUDIT-GROUP',group_name='AUDIT group',sort_order=0))
            await db.commit()
            report=ReportService(db)
            reported=await report._list_payments_in_range(datetime(2026,10,8),datetime(2026,10,8,23,59,59))
            actual=await FinanceCenterService(db).receipt_summary(date(2026,10,8),date(2026,10,8))
            evidence['checks']['receipt_date_basis']={'operating_report_amount':str(sum(p.amount for p in reported)),'finance_center_amount':actual['period']['amount'],'reported_payment_numbers':[p.payment_no for p in reported]}
            monthly=await report._list_orders_in_range(datetime(2026,10,1),datetime(2026,11,1))
            evidence['checks']['monthly_end_boundary']={'next_month_included':any(o.doc_no=='AUDIT-NEXT-MONTH' for o in monthly)}
            svc=BusinessDocumentService(db,doc_type='quote')
            converted=await svc.convert_regular_quote_to_order(quote_id,user_id)
            order_svc=BusinessDocumentService(db,doc_type='order')
            order=await order_svc.repo.get_by_id(converted['id'])
            current_items=[{**order_svc._item_snapshot(i),'id':str(i.id)} for i in order.items]
            groups=[dict(group_id=g.group_id,group_name=g.group_name,sort_order=g.sort_order) for g in order.groups]
            preview=await order_svc.preview_order_edit(order.id,header=None,items=current_items,groups=groups,expected_updated_at=order_svc._version_value(order),reason='isolated verification')
            evidence['checks']['quote_conversion_discount']={'source_discount':100,'converted_discount':str(order.discount_amount),'stored_order_total':str(order.total_amount),'unchanged_edit_preview_before':preview['before'],'unchanged_edit_preview_after':preview['after'],'preview_delta':preview['delta'],'group_ids_preserved':all(i.group_id=='AUDIT-GROUP' for i in order.items)}
            await db.rollback()
        async with AsyncSession(engine) as first, AsyncSession(engine) as second:
            number_a,number_b=await asyncio.gather(generate_order_no(first),generate_order_no(second))
            evidence['checks']['concurrent_number_generation']={'first':number_a,'second':number_b,'same_number':number_a==number_b,'transactions':'two independent uncommitted sessions'}
            await first.rollback()
            await second.rollback()
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await engine.dispose()
    Path('docs/project-audit-2026-10-26/evidence/isolated-reproductions.json').write_text(json.dumps(evidence,indent=2,ensure_ascii=False,default=str))
    print(json.dumps(evidence,indent=2,ensure_ascii=False,default=str))

asyncio.run(main())
