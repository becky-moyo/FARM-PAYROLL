from app import db
from app.models import User, JobType


def seed_default_data():
    if not User.query.filter_by(username='Admin').first():
        from config import Config
        admin = User(username=Config.DEFAULT_ADMIN_USERNAME)
        admin.set_password(Config.DEFAULT_ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()

    default_job_types = [
        {'job_name': 'Picking Citrus',    'pay_rate': 50.00,  'unit_divisor': 5,  'payment_type': 'piece_rate'},
        {'job_name': 'Harvesting Maize',  'pay_rate': 80.00,  'unit_divisor': 10, 'payment_type': 'piece_rate'},
        {'job_name': 'Sorting Produce',   'pay_rate': 60.00,  'unit_divisor': 6,  'payment_type': 'piece_rate'},
        {'job_name': 'Weeding',           'pay_rate': 45.00,  'unit_divisor': 5,  'payment_type': 'piece_rate'},
        {'job_name': 'Packing Crates',    'pay_rate': 70.00,  'unit_divisor': 7,  'payment_type': 'piece_rate'},
        {'job_name': 'Pruning & Plucking','pay_rate': 20.00,  'unit_divisor': 5,  'payment_type': 'piece_rate'},
        {'job_name': 'Planting',          'pay_rate': 65.00,  'unit_divisor': 8,  'payment_type': 'piece_rate'},
        {'job_name': 'Loading',           'pay_rate': 90.00,  'unit_divisor': 10, 'payment_type': 'piece_rate'},
        {'job_name': 'Hourly - General',  'pay_rate': 210.00, 'unit_divisor': 8,  'payment_type': 'hourly_piece'},
        {'job_name': 'Factory Piece Work','pay_rate': 210.00, 'unit_divisor': 68, 'payment_type': 'piece_rate'},
    ]

    for job_data in default_job_types:
        if not JobType.query.filter_by(job_name=job_data['job_name']).first():
            db.session.add(JobType(**job_data))

    db.session.commit()


def get_next_clock_number():
    from app.models import Employee
    import re

    last = Employee.query.order_by(Employee.id.desc()).first()
    if last:
        try:
            match = re.search(r'\d+', last.clock_number)
            if match:
                num = int(match.group()) + 1
                prefix = last.clock_number[:match.start()]
                return f"{prefix}{num:04d}"
        except Exception:
            pass
        return f"EMP{last.id + 1:04d}"
    return "EMP0001"


def recalculate_all_daily_totals():
    """Fix any logs saved with daily_total = 0 due to pre-session relationship access."""
    from app.models import DailyLog
    fixed = 0
    for log in DailyLog.query.filter(DailyLog.daily_total == 0.0).all():
        jt = JobType.query.get(log.job_type_id)
        if jt and log.quantity_complete:
            log.daily_total = (log.quantity_complete / jt.unit_divisor) * jt.pay_rate
            fixed += 1
    if fixed:
        db.session.commit()
    return fixed
