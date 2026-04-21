from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app import db
from app.models import JobType, DailyLog
from app.forms import JobTypeForm, JobTypeEditForm

bp = Blueprint('job_types', __name__)


@bp.route('/')
@login_required
def list():
    job_types = JobType.query.order_by(JobType.job_name).all()
    return render_template('job_types/list.html', job_types=job_types)


@bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    form = JobTypeForm()

    if form.validate_on_submit():
        if JobType.query.filter_by(job_name=form.job_name.data).first():
            flash('Job type with this name already exists.', 'danger')
            return render_template('job_types/add.html', form=form)

        job_type = JobType(
            job_name=form.job_name.data,
            pay_rate=form.pay_rate.data,
            unit_divisor=form.unit_divisor.data,
            payment_type=form.payment_type.data
        )
        db.session.add(job_type)
        db.session.commit()
        flash('Job type added successfully!', 'success')
        return redirect(url_for('job_types.list'))

    return render_template('job_types/add.html', form=form)


@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    job_type = JobType.query.get_or_404(id)
    form = JobTypeEditForm(obj=job_type)

    if form.validate_on_submit():
        job_type.pay_rate = form.pay_rate.data
        job_type.unit_divisor = form.unit_divisor.data
        job_type.payment_type = form.payment_type.data
        job_type.is_active = form.is_active.data
        db.session.commit()
        flash('Job type updated successfully!', 'success')
        return redirect(url_for('job_types.list'))

    return render_template('job_types/edit.html', form=form, job_type=job_type)


@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    job_type = JobType.query.get_or_404(id)

    if DailyLog.query.filter_by(job_type_id=id).first():
        flash('Cannot delete job type with existing daily logs.', 'danger')
    else:
        db.session.delete(job_type)
        db.session.commit()
        flash('Job type deleted successfully.', 'success')

    return redirect(url_for('job_types.list'))
