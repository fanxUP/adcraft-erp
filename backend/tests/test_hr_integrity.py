"""Attendance, historical wages, payment provenance and isolated migration regression."""
import os
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select, func, text
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from app.models.employee import Employee
from app.models.attendance import AttendanceRecord, AttendanceRule
from app.models.salary import SalaryRecord
from app.models.salary_grid import SalaryItem, SalaryGridValue
from app.models.salary_rule import SalaryRule
from app.models.leave import LeaveRequest
from app.models.payment import Expense
from app.services.attendance_summary_service import summarize_employee, AttendanceSummaryService
from app.services.salary_service import SalaryRecordService
from app.services.salary_rule_service import SalaryRuleService
from app.services.leave_service import LeaveRequestService
from app.services.company_account_service import CompanyAccountService
from app.services.payment_service import ExpenseService
from app.services.payable_service import PayableService
from app.services.expenditure_service import ExpenditureFilters
from tests.test_expenditure_integration import fixture_db  # noqa: F401

sql = pytest.mark.skipif(not os.getenv('EXPENDITURE_TEST_URL'), reason='requires explicit isolated PostgreSQL')


def test_attendance_missing_future_half_leave_and_custom_week():
    emp = SimpleNamespace(hire_date=date(2026, 7, 2), resignation_date=date(2026, 7, 7))
    records = [SimpleNamespace(date=date(2026,7,2), check_in_status='normal', check_out_status='half_day', overtime_hours=1),
               SimpleNamespace(date=date(2026,7,3), check_in_status='normal', check_out_status='missed', overtime_hours=0)]
    leaves = [SimpleNamespace(start_date=date(2026,7,6), end_date=date(2026,7,6), duration_days=1)]
    result, days = summarize_employee(emp, date(2026,7,1), date(2026,7,31), records, leaves,
        ['mon','tue','wed','thu','fri','sat'], today=date(2026,7,6))
    assert result['half'] == 1 and result['normal'] == 0
    assert result['missed'] == 1 and result['absent'] == 0
    assert result['leave'] == 1 and result['unregistered'] == 1  # Sat, not Sun/future
    assert result['work_days'] == 4
    assert days['2026-07-01']['status'] == 'outside_employment'
    assert days['2026-07-07']['status'] == 'future'


@sql
@pytest.mark.asyncio
async def test_history_paid_lock_partial_payment_and_one_expense(fixture_db):
    db, expenses, _ = fixture_db
    emp = Employee(employee_no='HR01', name='工资测试', hire_date=date(2026,1,1), department='design')
    db.add(emp); await db.flush()
    service = SalaryRecordService(db)
    rules = SalaryRuleService(db)
    old = await rules.create_rule(dict(employee_id=emp.id, effective_date=date(2026,1,1), base_salary=5000, social_insurance=200))
    for key, formula in [('basic','base'), ('deduction','social'), ('net','basic-deduction')]:
        db.add(SalaryItem(key=key,label=key,formula=formula,sort_order=1,is_active=True,is_builtin=False,is_manual=False))
    await db.flush()
    assert (await service.compute_month('2026-07'))['computed'] == 1
    rec = await service._existing_record(emp.id, '2026-07')
    assert rec.net_salary == Decimal('4800')
    assert rec.snapshot['rule']['id'] == old['id']
    with pytest.raises(ValueError, match='核算记录'):
        await rules.update_rule(UUID(old['id']), {'base_salary':9000})
    await rules.create_rule(dict(employee_id=emp.id,effective_date=date(2026,8,1),base_salary=6000))
    assert await db.scalar(select(func.count()).select_from(SalaryRule)) == 2
    assert (await service._latest_rule(emp.id,date(2026,7,31))).base_salary == 5000
    account = await CompanyAccountService(db).save(dict(name='HR现金',account_type='cash'))
    request = dict(amount=2000,paid_at='2026-08-03',payment_account_id=account['id'],idempotency_key=str(uuid4()))
    await service.register_payment('2026-07',emp.id,request,None)
    await service.register_payment('2026-07',emp.id,request,None)  # request retry is idempotent
    row = (await service.get_grid('2026-07'))['rows'][0]
    assert (row['paid_amount'],row['remaining_amount'],row['payment_status']) == (2000,2800,'partial')
    assert row['paid_at'].startswith('2026-08-03')
    assert (await service.compute_month('2026-07'))['skipped_locked'] == 1
    with pytest.raises(ValueError, match='不能覆盖'):
        await service.save_cells('2026-07',cells=[dict(employee_id=str(emp.id), item_key='net',value=1)])
    with pytest.raises(ValueError, match='不能覆盖'):
        await service.update_record(rec.id,{'net_salary':1})
    with pytest.raises(ValueError, match='不能覆盖'):
        await service.delete_record(rec.id)
    with pytest.raises(ValueError, match='工资发放生成'):
        await ExpenseService(db).delete_expense(rec.expense_id)
    await service.register_payment('2026-07',emp.id,{**request,'idempotency_key':str(uuid4()),'amount':2800,'paid_at':'2026-08-20'},None)
    row = (await service.get_grid('2026-07'))['rows'][0]
    assert row['payment_status'] == 'paid' and row['paid_at'].startswith('2026-08-20')
    # Payroll uses the existing ledger, so it contributes one principal and two payments.
    ledgers = await expenses.list_records('ledger',filters=ExpenditureFilters(category='工资'))
    payments = await expenses.list_records('disbursements',filters=ExpenditureFilters(category='工资'))
    assert ledgers['total'] == 1 and ledgers['summary']['amount'] == 4800
    assert payments['total'] == 2 and payments['summary']['amount'] == 4800
    # Later source edits and departures do not erase July payroll or change paid numbers.
    emp.name = '改名'; emp.department='new'; emp.employment_status='resigned'; emp.deleted_at=datetime(2026,8,31)
    for item in (await db.execute(select(SalaryItem))).scalars().all(): item.is_active=False; item.label='已修改'
    await db.flush()
    grid = await service.get_grid('2026-07')
    assert len(grid['rows']) == 1 and grid['rows'][0]['employee_name'] == '工资测试'
    assert grid['rows'][0]['values']['net'] == 4800 and all(i['label'] != '已修改' for i in grid['items'])
    financial = await PayableService(db).get_payable('expense',rec.expense_id)
    await PayableService(db).void_payment('expense',rec.expense_id,UUID(financial['payments'][0]['id']),'测试更正')
    row = (await service.get_grid('2026-07'))['rows'][0]
    assert row['remaining_amount'] > 0 and row['locked']


@sql
@pytest.mark.asyncio
async def test_leave_validation_approval_and_shared_summary(fixture_db):
    db, _, _ = fixture_db
    emp=Employee(employee_no='HR02',name='请假测试',hire_date=date(2026,1,1))
    db.add(emp); await db.flush()
    service=LeaveRequestService(db)
    data=dict(employee_id=emp.id,leave_type='personal',start_date=date(2026,7,6),end_date=date(2026,7,7),duration_days=2,reason='测试')
    leave=await service.create_request(data)
    with pytest.raises(ValueError,match='重叠'): await service.create_request(data)
    await service.approve_request(UUID(leave['id']),'approved',None)
    with pytest.raises(ValueError,match='仅待审批'): await service.update_request(UUID(leave['id']),{'reason':'改'})
    with pytest.raises(ValueError,match='不能删除'): await service.delete_request(UUID(leave['id']))
    att=(await SalaryRecordService(db)._attendance_stats(date(2026,7,1),date(2026,7,31)))[str(emp.id)]
    sheet=(await AttendanceSummaryService(db).monthly('2026-07'))['rows'][0]['summary']
    assert att==sheet and att['leave']==2 and att['absent']==0
    await service.approve_request(UUID(leave['id']),'cancelled',None,'取消测试')
    assert (await AttendanceSummaryService(db).monthly('2026-07'))['rows'][0]['summary']['leave']==0
    with pytest.raises(ValueError,match='结束日期'): await service.create_request({**data,'end_date':date(2026,7,1)})


@sql
@pytest.mark.asyncio
async def test_old_paid_and_legacy_leaver_records_are_preserved(fixture_db):
    db, _, _ = fixture_db
    emp=Employee(employee_no='OLD',name='历史离职',employment_status='resigned',resignation_date=date(2026,8,31),deleted_at=datetime(2026,9,1))
    db.add(emp); await db.flush()
    db.add(SalaryRecord(employee_id=emp.id,month='2026-07',base_salary=500,net_salary=500,payment_status='paid'))
    db.add(SalaryItem(key='net',label='实发',formula='base',is_active=True))
    await db.flush()
    svc=SalaryRecordService(db)
    row=(await svc.get_grid('2026-07'))['rows'][0]
    assert row['values']['net']==500 and row['locked'] and not row['has_snapshot']
    before=await db.scalar(select(func.count()).select_from(Expense))
    with pytest.raises(ValueError,match='历史已发'):
        await svc.register_payment('2026-07',emp.id,{'idempotency_key':str(uuid4())},None)
    assert await db.scalar(select(func.count()).select_from(Expense))==before


@sql
@pytest.mark.asyncio
async def test_migration_preserves_money_blocks_duplicates_and_rollback(fixture_db):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from importlib.util import module_from_spec,spec_from_file_location
    from pathlib import Path
    db,_,_=fixture_db
    # Recreate the immediately preceding schema on the disposable test connection.
    await db.execute(text('ALTER TABLE salary_records DROP COLUMN snapshot, DROP COLUMN expense_id'))
    await db.execute(text('ALTER TABLE salary_records DROP CONSTRAINT uq_salary_employee_month'))
    await db.execute(text('ALTER TABLE attendance_records DROP CONSTRAINT uq_attendance_employee_date'))
    await db.execute(text('ALTER TABLE salary_rules DROP CONSTRAINT uq_salary_rules_employee_date, ADD CONSTRAINT uq_salary_rules_employee UNIQUE (employee_id)'))
    await db.execute(text('ALTER TABLE employment_histories DROP COLUMN is_automatic'))
    await db.execute(text('ALTER TABLE leave_requests DROP COLUMN cancelled_by, DROP COLUMN cancelled_at, DROP COLUMN cancellation_reason'))
    eid=uuid4()
    await db.execute(text("INSERT INTO employees (id,employee_no,name,department,employment_status,is_active) VALUES (:id,'MIG','迁移测试','design','active',true)"),{'id':eid})
    await db.execute(text("INSERT INTO salary_records (id,employee_id,month,base_salary,net_salary,payment_status) VALUES (:id,:eid,'2026-07',500,500,'paid')"),{'id':uuid4(),'eid':eid})
    spec=spec_from_file_location('hr_migration',Path(__file__).parents[1]/'alembic/versions/hr01_payroll_integrity.py')
    migration=module_from_spec(spec);spec.loader.exec_module(migration)
    conn=await db.connection()
    def run(c,fn):
        with Operations.context(MigrationContext.configure(c)): fn()
    # An actual duplicate is detected before adding columns/constraints.
    duplicate=uuid4()
    await db.execute(text("INSERT INTO salary_records (id,employee_id,month,base_salary,net_salary,payment_status) VALUES (:id,:eid,'2026-07',600,600,'pending')"),{'id':duplicate,'eid':eid})
    with pytest.raises(Exception,match='Duplicate rows'):
        async with conn.begin_nested(): await conn.run_sync(run,migration.upgrade)
    await db.execute(text('DELETE FROM salary_records WHERE id=:id'),{'id':duplicate})
    before=(await db.execute(text('SELECT count(*),sum(net_salary) FROM salary_records'))).one()
    await conn.run_sync(run,migration.upgrade)
    assert (await db.execute(text('SELECT count(*),sum(net_salary) FROM salary_records'))).one()==before
    assert await db.scalar(text('SELECT count(*) FROM salary_records WHERE snapshot IS NOT NULL OR expense_id IS NOT NULL'))==0
    assert await db.scalar(text("SELECT count(*) FROM departments WHERE code='design'"))==1
    await conn.run_sync(run,migration.downgrade)
    await conn.run_sync(run,migration.upgrade)
    assert (await db.execute(text("SELECT count(*),sum(net_salary) FROM salary_records"))).one()==before
    await db.execute(text("UPDATE salary_records SET snapshot='{}'::jsonb"))
    with pytest.raises(Exception,match='HR history exists'):
        async with conn.begin_nested(): await conn.run_sync(run,migration.downgrade)

@pytest.mark.asyncio
async def test_hr_routes_readers_cannot_write_or_access_other_domains():
    from app.api import employees,attendance,leaves,salaries,salary_rules,departments,employment_histories
    from app.core.database import get_db
    from app.core.deps import get_current_user
    from tests.test_expenditure_service import viewer
    app=FastAPI()
    for module in (employees,attendance,leaves,salaries,salary_rules,departments,employment_histories): app.include_router(module.router)
    current=viewer('employee:read')
    app.dependency_overrides[get_current_user]=lambda: current
    db=MagicMock(); db.rollback=AsyncMock()
    async def database(): yield db
    app.dependency_overrides[get_db]=database
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        for method,url,body in [('POST','/employees/',{'name':'越权'}),('DELETE','/employees/'+str(uuid4()),None),
                ('GET','/salaries/grid?month=2026-07',None),('GET','/attendance/monthly?month=2026-07',None),
                ('GET','/leaves/',None),('GET','/employees/'+str(uuid4())+'/attachments',None)]:
            assert (await client.request(method,url,json=body)).status_code==403
        current=viewer('salary:read')
        assert (await client.post('/salaries/grid/compute',json={'month':'2026-07'})).status_code==403
        assert (await client.post('/salaries/payments',json={})).status_code==403


def test_employee_private_fields_require_separate_capability():
    from app.api.employees import employee_visible,employee_write
    from tests.test_expenditure_service import viewer
    user=viewer('employee:read','employee:manage')
    item=dict(id='test',name='姓名',id_card='sensitive',bank_account='sensitive',id_card_front_url='/uploads/test.jpg')
    assert employee_visible(item,user)==dict(id='test',name='姓名')
    assert 'id_card' not in employee_write({'name':'改名','id_card':'sensitive'},user)

@sql
@pytest.mark.asyncio
async def test_employee_changes_log_and_department_references(fixture_db):
    from app.services.employee_service import EmployeeService
    from app.services.employment_history_service import EmploymentHistoryService
    from app.services.department_service import DepartmentService
    from app.models.employment_history import EmploymentHistory
    db,_,_=fixture_db
    departments=DepartmentService(db)
    first=await departments.create_department({'code':'first','name':'原部门'})
    await departments.create_department({'code':'second','name':'新部门'})
    emp=Employee(employee_no='HR03',name='调岗测试',department='first',hire_date=date(2026,1,1))
    db.add(emp);await db.flush()
    await EmployeeService(db).update_employee(emp.id,{'department':'second'})
    history=(await db.execute(select(EmploymentHistory).where(EmploymentHistory.employee_id==emp.id))).scalar_one()
    assert history.is_automatic and history.previous_department=='first' and history.new_department=='second'
    with pytest.raises(ValueError,match='不能删除'): await EmploymentHistoryService(db).delete_history(history.id)
    with pytest.raises(ValueError,match='请停用'): await departments.delete_department(UUID(first['id']))
    await EmployeeService(db).update_employee(emp.id,{'employment_status':'resigned','resignation_date':date(2026,7,31)})
    assert await db.scalar(select(func.count()).select_from(EmploymentHistory).where(EmploymentHistory.change_type=='resignation'))==1


@sql
@pytest.mark.asyncio
async def test_salary_save_preflight_prevents_partial_write(fixture_db):
    db,_,_=fixture_db
    staff=[Employee(employee_no='ATOMIC'+str(i),name='保护测试') for i in range(2)]
    db.add_all(staff);await db.flush()
    db.add(SalaryItem(key='net',label='工资',formula='1',is_active=True))
    for index,e in enumerate(staff): db.add(SalaryRecord(employee_id=e.id,month='2026-07',base_salary=100,net_salary=100,payment_status='paid' if index else 'calculated'))
    await db.flush()
    with pytest.raises(ValueError,match='不能覆盖'):
        await SalaryRecordService(db).save_cells('2026-07',cells=[dict(employee_id=str(e.id),item_key='net',value=1) for e in staff])
    assert await db.scalar(select(func.count()).select_from(SalaryGridValue))==0

@pytest.mark.asyncio
async def test_hr_manager_cannot_disable_super_admin_or_delete_other_attachment():
    from app.api.employees import router
    from app.core.database import get_db
    from app.core.deps import get_current_user
    from tests.test_expenditure_service import viewer
    user=viewer('employee:read','employee:manage','employee:private')
    db=MagicMock(); db.get=AsyncMock(return_value=SimpleNamespace(user=viewer('system:super_admin')))
    async def database(): yield db
    app=FastAPI();app.include_router(router)
    app.dependency_overrides[get_db]=database
    app.dependency_overrides[get_current_user]=lambda:user
    async with AsyncClient(transport=ASGITransport(app=app),base_url='http://test') as client:
        assert (await client.put('/employees/'+str(uuid4()),json={'employment_status':'resigned'})).status_code==403
        assert (await client.delete('/employees/'+str(uuid4()))).status_code==403
        db.get.return_value=SimpleNamespace(related_type='order')
        assert (await client.delete('/employees/attachments/'+str(uuid4()))).status_code==403


def test_historical_payment_timestamp_also_locks_reversed_status():
    record=SimpleNamespace(payment_status='calculated',paid_at=datetime(2026,8,20),expense_id=None)
    with pytest.raises(ValueError,match='不能覆盖'):
        SalaryRecordService._assert_editable(record)
