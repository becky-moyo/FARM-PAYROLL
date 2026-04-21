from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, FloatField, DateField, TimeField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError, Regexp, EqualTo
from datetime import date


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('Password', validators=[DataRequired()])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long'),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]',
               message='Password must contain letters, numbers, and symbols')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match')
    ])


class EmployeeForm(FlaskForm):
    clock_number = StringField('Clock Number', validators=[
        DataRequired(), Length(max=20),
        Regexp(r'^[A-Za-z0-9]+$', message='Clock number must be alphanumeric')
    ])
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    date_started = DateField('Date Started', validators=[DataRequired()], default=date.today)

    def validate_date_started(self, field):
        if field.data > date.today():
            raise ValidationError('Date started cannot be in the future.')


class JobTypeForm(FlaskForm):
    job_name = StringField('Job Name', validators=[DataRequired(), Length(max=50)])
    pay_rate = FloatField('Pay Rate (R)', validators=[DataRequired(), NumberRange(min=0.01)])
    unit_divisor = FloatField('Unit Divisor', validators=[DataRequired(), NumberRange(min=0.01)])
    payment_type = SelectField('Payment Type', choices=[
        ('piece_rate', 'Piece Rate'),
        ('hourly_piece', 'Hourly Piece Rate')
    ], validators=[DataRequired()])


class JobTypeEditForm(FlaskForm):
    pay_rate = FloatField('Pay Rate (R)', validators=[DataRequired(), NumberRange(min=0.01)])
    unit_divisor = FloatField('Unit Divisor', validators=[DataRequired(), NumberRange(min=0.01)])
    payment_type = SelectField('Payment Type', choices=[
        ('piece_rate', 'Piece Rate'),
        ('hourly_piece', 'Hourly Piece Rate')
    ], validators=[DataRequired()])
    is_active = BooleanField('Active')


class DailyLogForm(FlaskForm):
    work_date = DateField('Date', validators=[DataRequired()], default=date.today)
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    job_type_id = SelectField('Job Type', coerce=int, validators=[DataRequired()])
    quantity_complete = FloatField('Quantity Complete', validators=[DataRequired(), NumberRange(min=0.01)])
    clock_in_time = TimeField('Clock In Time', validators=[Optional()])
    clock_out_time = TimeField('Clock Out Time', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])

    def validate_work_date(self, field):
        if field.data > date.today():
            raise ValidationError('Work date cannot be in the future.')

    def validate_clock_out_time(self, field):
        if self.clock_in_time.data and field.data:
            if field.data <= self.clock_in_time.data:
                raise ValidationError('Clock out time must be after clock in time.')


class SalarySlipSelectForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    month = SelectField('Month', coerce=int, choices=[(i, f'{i:02d}') for i in range(1, 13)], validators=[DataRequired()])
    year = SelectField('Year', coerce=int, choices=[(y, str(y)) for y in range(2020, 2031)],
                       validators=[DataRequired()], default=date.today().year)


class ReportFilterForm(FlaskForm):
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    employee_id = SelectField('Employee', coerce=int, validators=[Optional()], choices=[(0, 'All Employees')])

    def validate_end_date(self, field):
        if field.data < self.start_date.data:
            raise ValidationError('End date must be after start date.')
