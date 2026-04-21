from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    clock_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    date_started = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    daily_logs = db.relationship('DailyLog', backref='employee', lazy='dynamic')

    def __repr__(self):
        return f'<Employee {self.clock_number} - {self.name}>'

    @property
    def display_name(self):
        return f'{self.clock_number} - {self.name}'


class JobType(db.Model):
    __tablename__ = 'job_types'

    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(50), unique=True, nullable=False)
    pay_rate = db.Column(db.Float, nullable=False)
    unit_divisor = db.Column(db.Float, nullable=False)
    payment_type = db.Column(db.String(20), nullable=False)  # 'piece_rate' or 'hourly_piece'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    daily_logs = db.relationship('DailyLog', backref='job_type', lazy='dynamic')

    def __repr__(self):
        return f'<JobType {self.job_name}>'

    @property
    def rate_per_unit(self):
        return self.pay_rate / self.unit_divisor


class DailyLog(db.Model):
    __tablename__ = 'daily_logs'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    job_type_id = db.Column(db.Integer, db.ForeignKey('job_types.id'), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    quantity_complete = db.Column(db.Float, nullable=False)
    clock_in_time = db.Column(db.Time, nullable=True)
    clock_out_time = db.Column(db.Time, nullable=True)
    daily_total = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<DailyLog {self.work_date} - Employee {self.employee_id}>'

    def calculate_daily_total(self):
        if self.job_type:
            return (self.quantity_complete / self.job_type.unit_divisor) * self.job_type.pay_rate
        return 0.0

    def calculate_hours_worked(self):
        if self.clock_in_time and self.clock_out_time:
            from datetime import datetime, timedelta
            today = datetime.today().date()
            in_time = datetime.combine(today, self.clock_in_time)
            out_time = datetime.combine(today, self.clock_out_time)
            if out_time < in_time:
                out_time += timedelta(days=1)
            return (out_time - in_time).total_seconds() / 3600
        return 0.0


class Setting(db.Model):
    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.String(500), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
