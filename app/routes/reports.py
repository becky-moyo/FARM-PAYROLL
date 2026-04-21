from flask import Blueprint, render_template, request, send_file, redirect, url_for, flash
from flask_login import login_required
from datetime import datetime, date
from app import db
from app.models import Employee, DailyLog, JobType
from app.forms import ReportFilterForm
from sqlalchemy import func
import pandas as pd
import io

bp = Blueprint('reports', __name__)


@bp.route('/')
@login_required
def index():
    return render_template('reports/index.html')


@bp.route('/monthly-payroll')
@login_required
def monthly_payroll():
    form = ReportFilterForm()
    form.employee_id.choices = [(0, 'All Employees')] + [
        (e.id, e.display_name) for e in Employee.query.order_by(Employee.name).all()
    ]

    start_date = request.args.get('start_date', date.today().replace(day=1).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    employee_id = request.args.get('employee_id', 0, type=int)

    query = db.session.query(
        Employee.id,
        Employee.clock_number,
        Employee.name,
        func.sum(DailyLog.daily_total).label('total_earnings'),
        func.count(func.distinct(DailyLog.work_date)).label('days_worked')
    ).join(DailyLog).filter(
        DailyLog.work_date >= datetime.strptime(start_date, '%Y-%m-%d').date(),
        DailyLog.work_date <= datetime.strptime(end_date, '%Y-%m-%d').date()
    )

    if employee_id:
        query = query.filter(Employee.id == employee_id)

    results = query.group_by(Employee.id).order_by(Employee.name).all()

    return render_template('reports/monthly_payroll.html',
                           results=results, form=form,
                           filters={'start_date': start_date, 'end_date': end_date, 'employee_id': employee_id})


@bp.route('/employee-productivity')
@login_required
def employee_productivity():
    form = ReportFilterForm()
    form.employee_id.choices = [(0, 'All Employees')] + [
        (e.id, e.display_name) for e in Employee.query.order_by(Employee.name).all()
    ]

    start_date = request.args.get('start_date', date.today().replace(day=1).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    employee_id = request.args.get('employee_id', 0, type=int)

    query = db.session.query(
        Employee.clock_number,
        Employee.name,
        JobType.job_name,
        func.sum(DailyLog.quantity_complete).label('total_quantity'),
        func.sum(DailyLog.daily_total).label('total_earnings'),
        func.count(DailyLog.id).label('entries')
    ).select_from(Employee)\
     .join(DailyLog, DailyLog.employee_id == Employee.id)\
     .join(JobType, JobType.id == DailyLog.job_type_id)\
     .filter(
        DailyLog.work_date >= datetime.strptime(start_date, '%Y-%m-%d').date(),
        DailyLog.work_date <= datetime.strptime(end_date, '%Y-%m-%d').date()
    )

    if employee_id:
        query = query.filter(Employee.id == employee_id)

    results = query.group_by(Employee.id, JobType.id).order_by(Employee.name, JobType.job_name).all()

    return render_template('reports/productivity.html',
                           results=results, form=form,
                           filters={'start_date': start_date, 'end_date': end_date, 'employee_id': employee_id})


@bp.route('/attendance')
@login_required
def attendance():
    start_date = request.args.get('start_date', date.today().replace(day=1).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())

    logs = DailyLog.query.filter(
        DailyLog.work_date >= datetime.strptime(start_date, '%Y-%m-%d').date(),
        DailyLog.work_date <= datetime.strptime(end_date, '%Y-%m-%d').date(),
        DailyLog.clock_in_time != None
    ).order_by(DailyLog.work_date, DailyLog.clock_in_time).all()

    return render_template('reports/attendance.html', logs=logs, start_date=start_date, end_date=end_date)


@bp.route('/export/<report_type>')
@login_required
def export_report(report_type):
    start_date = request.args.get('start_date') or date.today().replace(day=1).isoformat()
    end_date = request.args.get('end_date') or date.today().isoformat()
    employee_id = request.args.get('employee_id', 0, type=int)

    if report_type == 'monthly_payroll':
        query = db.session.query(
            Employee.clock_number,
            Employee.name,
            func.sum(DailyLog.daily_total).label('total_earnings'),
            func.count(func.distinct(DailyLog.work_date)).label('days_worked')
        ).join(DailyLog).filter(
            DailyLog.work_date >= datetime.strptime(start_date, '%Y-%m-%d').date(),
            DailyLog.work_date <= datetime.strptime(end_date, '%Y-%m-%d').date()
        )

        if employee_id:
            query = query.filter(Employee.id == employee_id)

        results = query.group_by(Employee.id).all()
        data = [{'Clock Number': r.clock_number, 'Employee Name': r.name,
                 'Total Earnings': f"R{r.total_earnings:.2f}", 'Days Worked': r.days_worked}
                for r in results]

    elif report_type == 'productivity':
        query = db.session.query(
            Employee.clock_number,
            Employee.name,
            JobType.job_name,
            func.sum(DailyLog.quantity_complete).label('total_quantity'),
            func.sum(DailyLog.daily_total).label('total_earnings'),
            func.count(DailyLog.id).label('entries')
        ).select_from(Employee)\
         .join(DailyLog, DailyLog.employee_id == Employee.id)\
         .join(JobType, JobType.id == DailyLog.job_type_id)\
         .filter(
            DailyLog.work_date >= datetime.strptime(start_date, '%Y-%m-%d').date(),
            DailyLog.work_date <= datetime.strptime(end_date, '%Y-%m-%d').date()
        )

        if employee_id:
            query = query.filter(Employee.id == employee_id)

        results = query.group_by(Employee.id, JobType.id).all()
        data = [{'Clock Number': r.clock_number, 'Employee Name': r.name, 'Job Type': r.job_name,
                 'Total Quantity': r.total_quantity, 'Total Earnings': f"R{r.total_earnings:.2f}",
                 'Number of Entries': r.entries}
                for r in results]

    else:
        flash('Invalid report type.', 'danger')
        return redirect(url_for('reports.index'))

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(data).to_excel(writer, sheet_name=report_type.replace('_', ' ').title(), index=False)

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'{report_type}_{date.today()}.xlsx'
    )
