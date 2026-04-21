from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from datetime import datetime
from app import db
from app.models import Employee, DailyLog
from app.forms import EmployeeForm
from app.utils import get_next_clock_number
from sqlalchemy import or_

bp = Blueprint('employees', __name__)


@bp.route('/')
@login_required
def list():
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    query = Employee.query
    if search:
        query = query.filter(
            or_(Employee.name.contains(search), Employee.clock_number.contains(search))
        )

    employees = query.order_by(Employee.name).paginate(page=page, per_page=20, error_out=False)
    return render_template('employees/list.html', employees=employees, search=search)


@bp.route('/search-suggestions')
@login_required
def search_suggestions():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    results = Employee.query.filter(
        or_(Employee.name.ilike(f'%{q}%'), Employee.clock_number.ilike(f'%{q}%'))
    ).order_by(Employee.name).limit(8).all()
    return jsonify([{
        'id': e.id, 'name': e.name,
        'clock_number': e.clock_number, 'is_active': e.is_active
    } for e in results])


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = EmployeeForm()
    form.clock_number.data = get_next_clock_number()

    if form.validate_on_submit():
        if Employee.query.filter_by(clock_number=form.clock_number.data).first():
            flash('Clock number already exists.', 'danger')
            return render_template('employees/add.html', form=form)

        employee = Employee(
            clock_number=form.clock_number.data,
            name=form.name.data,
            date_started=form.date_started.data
        )
        db.session.add(employee)
        db.session.commit()
        flash('Employee added successfully!', 'success')
        return redirect(url_for('employees.list'))

    return render_template('employees/add.html', form=form)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    employee = Employee.query.get_or_404(id)
    form = EmployeeForm(obj=employee)

    if form.validate_on_submit():
        existing = Employee.query.filter(
            Employee.clock_number == form.clock_number.data,
            Employee.id != id
        ).first()

        if existing:
            flash('Clock number already exists.', 'danger')
            return render_template('employees/edit.html', form=form, employee=employee)

        employee.clock_number = form.clock_number.data
        employee.name = form.name.data
        employee.date_started = form.date_started.data
        employee.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employees.list'))

    return render_template('employees/edit.html', form=form, employee=employee)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    employee = Employee.query.get_or_404(id)
    employee.is_active = False
    employee.updated_at = datetime.utcnow()
    db.session.commit()
    flash('Employee deactivated successfully.', 'success')
    return redirect(url_for('employees.list'))


@bp.route('/<int:id>/activate', methods=['POST'])
@login_required
def activate(id):
    employee = Employee.query.get_or_404(id)
    employee.is_active = True
    employee.updated_at = datetime.utcnow()
    db.session.commit()
    flash(f'{employee.name} has been reactivated successfully.', 'success')
    return redirect(url_for('employees.list'))


@bp.route('/<int:id>/view')
@login_required
def view(id):
    employee = Employee.query.get_or_404(id)
    work_history = DailyLog.query.filter_by(employee_id=id)\
        .order_by(DailyLog.work_date.desc())\
        .paginate(page=request.args.get('page', 1, type=int), per_page=20, error_out=False)
    return render_template('employees/view.html', employee=employee, work_history=work_history)
