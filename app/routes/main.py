from flask import Blueprint, render_template
from flask_login import login_required
from datetime import date
from app import db
from app.models import Employee, DailyLog
from sqlalchemy import func, distinct

bp = Blueprint('main', __name__)


@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    current_month_start = date(today.year, today.month, 1)

    active_employees = Employee.query.filter_by(is_active=True).count()

    today_earnings = db.session.query(func.sum(DailyLog.daily_total))\
        .filter(DailyLog.work_date == today).scalar() or 0.0

    month_earnings = db.session.query(func.sum(DailyLog.daily_total))\
        .filter(DailyLog.work_date >= current_month_start,
                DailyLog.work_date <= today).scalar() or 0.0

    days_worked = db.session.query(func.count(distinct(DailyLog.work_date)))\
        .filter(DailyLog.work_date >= current_month_start,
                DailyLog.work_date <= today).scalar() or 0

    recent_logs = DailyLog.query.order_by(DailyLog.created_at.desc()).limit(10).all()

    return render_template('dashboard.html',
                           active_employees=active_employees,
                           today_earnings=today_earnings,
                           month_earnings=month_earnings,
                           days_worked=days_worked,
                           recent_logs=recent_logs)
