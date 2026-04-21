from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required
from datetime import datetime, date, timedelta
from app import db
from app.models import DailyLog, Employee, JobType
from app.forms import DailyLogForm
import csv
import io
import pandas as pd

bp = Blueprint('daily_logs', __name__)


@bp.route('/')
@login_required
def list():
    start_date = request.args.get('start_date', date.today().replace(day=1).isoformat())
    end_date = request.args.get('end_date', date.today().isoformat())
    employee_id = request.args.get('employee_id', type=int)
    job_type_id = request.args.get('job_type_id', type=int)

    query = DailyLog.query

    if start_date:
        query = query.filter(DailyLog.work_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(DailyLog.work_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if employee_id:
        query = query.filter(DailyLog.employee_id == employee_id)
    if job_type_id:
        query = query.filter(DailyLog.job_type_id == job_type_id)

    logs = query.order_by(DailyLog.work_date.desc(), DailyLog.created_at.desc()).all()
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    job_types = JobType.query.filter_by(is_active=True).order_by(JobType.job_name).all()

    return render_template('daily_logs/list.html',
                           logs=logs,
                           employees=employees,
                           job_types=job_types,
                           filters={
                               'start_date': start_date,
                               'end_date': end_date,
                               'employee_id': employee_id,
                               'job_type_id': job_type_id
                           })


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = DailyLogForm()

    employees = Employee.query.filter_by(is_active=True).order_by(Employee.name).all()
    job_types = JobType.query.filter_by(is_active=True).order_by(JobType.job_name).all()

    form.employee_id.choices = [(e.id, e.display_name) for e in employees]
    form.job_type_id.choices = [(j.id, f"{j.job_name} (R{j.pay_rate:.2f}/{j.unit_divisor} units)")
                                for j in job_types]

    job_types_data = [{'id': jt.id, 'name': jt.job_name, 'payment_type': jt.payment_type,
                       'pay_rate': jt.pay_rate, 'unit_divisor': jt.unit_divisor} for jt in job_types]

    if form.validate_on_submit():
        employee = Employee.query.get(form.employee_id.data)
        job_type = JobType.query.get(form.job_type_id.data)

        if not employee.is_active:
            flash('Selected employee is not active.', 'danger')
            return render_template('daily_logs/add.html', form=form, job_types_data=job_types_data)

        if not job_type.is_active:
            flash('Selected job type is not active.', 'danger')
            return render_template('daily_logs/add.html', form=form, job_types_data=job_types_data)

        quantity = form.quantity_complete.data
        if job_type.payment_type == 'hourly_piece' and form.clock_in_time.data and form.clock_out_time.data:
            in_time = datetime.combine(date.today(), form.clock_in_time.data)
            out_time = datetime.combine(date.today(), form.clock_out_time.data)
            if out_time < in_time:
                out_time += timedelta(days=1)
            quantity = (out_time - in_time).total_seconds() / 3600

        # Calculate before session.add — relationship unavailable on unsaved objects
        daily_total = (quantity / job_type.unit_divisor) * job_type.pay_rate

        daily_log = DailyLog(
            employee_id=form.employee_id.data,
            job_type_id=form.job_type_id.data,
            work_date=form.work_date.data,
            quantity_complete=quantity,
            clock_in_time=form.clock_in_time.data if job_type.payment_type == 'hourly_piece' else None,
            clock_out_time=form.clock_out_time.data if job_type.payment_type == 'hourly_piece' else None,
            notes=form.notes.data,
            daily_total=daily_total
        )

        db.session.add(daily_log)
        db.session.commit()

        flash(f'Daily log added successfully! Daily total: R{daily_log.daily_total:.2f}', 'success')

        if request.form.get('submit_add_another'):
            return redirect(url_for('daily_logs.add'))
        return redirect(url_for('daily_logs.list'))

    return render_template('daily_logs/add.html', form=form, job_types_data=job_types_data)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    daily_log = DailyLog.query.get_or_404(id)
    form = DailyLogForm(obj=daily_log)

    job_types = JobType.query.filter_by(is_active=True).order_by(JobType.job_name).all()

    form.employee_id.choices = [(e.id, e.display_name) for e in Employee.query.filter_by(is_active=True).order_by(Employee.name).all()]
    form.job_type_id.choices = [(j.id, f"{j.job_name} (R{j.pay_rate:.2f}/{j.unit_divisor} units)") for j in job_types]

    job_types_data = [{'id': jt.id, 'name': jt.job_name, 'payment_type': jt.payment_type,
                       'pay_rate': jt.pay_rate, 'unit_divisor': jt.unit_divisor} for jt in job_types]

    if form.validate_on_submit():
        job_type = JobType.query.get(form.job_type_id.data)

        quantity = form.quantity_complete.data
        if job_type.payment_type == 'hourly_piece' and form.clock_in_time.data and form.clock_out_time.data:
            in_time = datetime.combine(date.today(), form.clock_in_time.data)
            out_time = datetime.combine(date.today(), form.clock_out_time.data)
            if out_time < in_time:
                out_time += timedelta(days=1)
            quantity = (out_time - in_time).total_seconds() / 3600

        daily_log.employee_id = form.employee_id.data
        daily_log.job_type_id = form.job_type_id.data
        daily_log.work_date = form.work_date.data
        daily_log.quantity_complete = quantity
        daily_log.clock_in_time = form.clock_in_time.data if job_type.payment_type == 'hourly_piece' else None
        daily_log.clock_out_time = form.clock_out_time.data if job_type.payment_type == 'hourly_piece' else None
        daily_log.notes = form.notes.data
        daily_log.daily_total = (quantity / job_type.unit_divisor) * job_type.pay_rate

        db.session.commit()
        flash('Daily log updated successfully!', 'success')
        return redirect(url_for('daily_logs.list'))

    return render_template('daily_logs/edit.html', form=form, daily_log=daily_log, job_types_data=job_types_data)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    daily_log = DailyLog.query.get_or_404(id)
    db.session.delete(daily_log)
    db.session.commit()
    flash('Daily log deleted successfully.', 'success')
    return redirect(url_for('daily_logs.list'))


@bp.route('/bulk-delete', methods=['POST'])
@login_required
def bulk_delete():
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        deleted = DailyLog.query.filter(
            DailyLog.work_date >= start,
            DailyLog.work_date <= end
        ).delete()
        db.session.commit()
        flash(f'{deleted} daily logs deleted successfully.', 'success')

    return redirect(url_for('daily_logs.list'))


@bp.route('/export')
@login_required
def export():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    employee_id = request.args.get('employee_id', type=int)
    job_type_id = request.args.get('job_type_id', type=int)

    query = DailyLog.query

    if start_date:
        query = query.filter(DailyLog.work_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(DailyLog.work_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    if employee_id:
        query = query.filter(DailyLog.employee_id == employee_id)
    if job_type_id:
        query = query.filter(DailyLog.job_type_id == job_type_id)

    logs = query.order_by(DailyLog.work_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Employee', 'Clock Number', 'Job Type', 'Quantity',
                     'Clock In', 'Clock Out', 'Daily Total', 'Notes'])

    for log in logs:
        writer.writerow([
            log.work_date.strftime('%Y-%m-%d'),
            log.employee.name,
            log.employee.clock_number,
            log.job_type.job_name,
            log.quantity_complete,
            log.clock_in_time.strftime('%H:%M') if log.clock_in_time else '',
            log.clock_out_time.strftime('%H:%M') if log.clock_out_time else '',
            f'R{log.daily_total:.2f}',
            log.notes or ''
        ])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'daily_logs_{date.today()}.csv'
    )


@bp.route('/calculate-preview', methods=['POST'])
@login_required
def calculate_preview():
    data = request.json
    job_type_id = data.get('job_type_id')
    quantity = float(data.get('quantity', 0))

    job_type = JobType.query.get(job_type_id)
    if job_type:
        total = (quantity / job_type.unit_divisor) * job_type.pay_rate
        return jsonify({'total': round(total, 2)})
    return jsonify({'total': 0})
