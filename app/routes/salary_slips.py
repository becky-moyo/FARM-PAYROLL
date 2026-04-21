# app/routes/salary_slips.py
from flask import Blueprint, render_template, request, send_file, redirect, url_for
from flask_login import login_required
from datetime import datetime, date, timedelta
from calendar import monthrange
from app import db
from app.models import Employee, DailyLog, JobType
from app.forms import SalarySlipSelectForm
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import io

bp = Blueprint('salary_slips', __name__)

@bp.route('/')
@login_required
def select():
    """Select employee and month for salary slip"""
    form = SalarySlipSelectForm()
    form.employee_id.choices = [(0, 'Select Employee')] + [(e.id, e.display_name) 
                                for e in Employee.query.filter_by(is_active=True).order_by(Employee.name).all()]
    
    return render_template('salary_slips/select.html', form=form)

@bp.route('/view/<int:employee_id>/<int:month>/<int:year>')
@login_required
def view(employee_id, month, year):
    """View salary slip via GET — used by reports page links"""
    employee = Employee.query.get_or_404(employee_id)

    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])
    effective_start = max(month_start, employee.date_started) if employee.date_started else month_start
    effective_start = min(effective_start, month_end)

    logs = DailyLog.query.filter(
        DailyLog.employee_id == employee_id,
        DailyLog.work_date >= effective_start,
        DailyLog.work_date <= month_end
    ).order_by(DailyLog.work_date).all()

    total_earnings = sum(log.daily_total for log in logs)
    unique_dates = set(log.work_date for log in logs)
    total_days_worked = len(unique_dates)

    piece_rate_total = 0
    hourly_total = 0
    total_hours = 0
    total_quantity = 0
    job_type_summary = {}

    for log in logs:
        if log.job_type_id not in job_type_summary:
            job_type_summary[log.job_type_id] = {
                'name': log.job_type.job_name,
                'total': 0,
                'quantity': 0,
                'days': set()
            }
        job_type_summary[log.job_type_id]['total'] += log.daily_total
        job_type_summary[log.job_type_id]['quantity'] += log.quantity_complete
        job_type_summary[log.job_type_id]['days'].add(log.work_date)

        if log.job_type.payment_type == 'hourly_piece':
            hourly_total += log.daily_total
            total_hours += log.calculate_hours_worked()
        else:
            piece_rate_total += log.daily_total
            total_quantity += log.quantity_complete

    for jt_id in job_type_summary:
        job_type_summary[jt_id]['days_count'] = len(job_type_summary[jt_id]['days'])

    slip_data = {
        'employee': employee,
        'month': month_start.strftime('%B %Y'),
        'start_date': effective_start,
        'end_date': month_end,
        'total_days_worked': total_days_worked,
        'total_earnings': total_earnings,
        'piece_rate_total': piece_rate_total,
        'hourly_total': hourly_total,
        'total_hours': total_hours,
        'total_quantity': total_quantity,
        'job_type_summary': job_type_summary,
        'logs': logs
    }

    return render_template('salary_slips/view.html', slip=slip_data)


@bp.route('/generate', methods=['POST'])
@login_required
def generate():
    """Generate and display salary slip"""
    employee_id = request.form.get('employee_id', type=int)
    month = request.form.get('month', type=int)
    year = request.form.get('year', type=int)
    
    if not employee_id or not month or not year:
        return redirect(url_for('salary_slips.select'))
    
    employee = Employee.query.get_or_404(employee_id)
    
    # Calculate date range
    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])
    
    # Adjust start date if employee joined mid-month
    effective_start = max(month_start, employee.date_started) if employee.date_started else month_start
    effective_start = min(effective_start, month_end)  # Ensure start <= end
    
    # Get all daily logs for the month
    logs = DailyLog.query.filter(
        DailyLog.employee_id == employee_id,
        DailyLog.work_date >= effective_start,
        DailyLog.work_date <= month_end
    ).order_by(DailyLog.work_date).all()
    
    # Calculate statistics
    total_earnings = sum(log.daily_total for log in logs)
    unique_dates = set(log.work_date for log in logs)
    total_days_worked = len(unique_dates)
    
    # Calculate totals by job type
    piece_rate_total = 0
    hourly_total = 0
    total_hours = 0
    total_quantity = 0
    
    job_type_summary = {}
    for log in logs:
        if log.job_type_id not in job_type_summary:
            job_type_summary[log.job_type_id] = {
                'name': log.job_type.job_name,
                'total': 0,
                'quantity': 0,
                'days': set()
            }
        job_type_summary[log.job_type_id]['total'] += log.daily_total
        job_type_summary[log.job_type_id]['quantity'] += log.quantity_complete
        job_type_summary[log.job_type_id]['days'].add(log.work_date)
        
        if log.job_type.payment_type == 'hourly_piece':
            hourly_total += log.daily_total
            total_hours += log.calculate_hours_worked()
        else:
            piece_rate_total += log.daily_total
            total_quantity += log.quantity_complete
    
    # Convert sets to counts
    for jt_id in job_type_summary:
        job_type_summary[jt_id]['days_count'] = len(job_type_summary[jt_id]['days'])
    
    slip_data = {
        'employee': employee,
        'month': month_start.strftime('%B %Y'),
        'start_date': effective_start,
        'end_date': month_end,
        'total_days_worked': total_days_worked,
        'total_earnings': total_earnings,
        'piece_rate_total': piece_rate_total,
        'hourly_total': hourly_total,
        'total_hours': total_hours,
        'total_quantity': total_quantity,
        'job_type_summary': job_type_summary,
        'logs': logs
    }
    
    return render_template('salary_slips/view.html', slip=slip_data)

@bp.route('/print/<int:employee_id>/<int:month>/<int:year>')
@login_required
def print_slip(employee_id, month, year):
    """Print-friendly version of salary slip"""
    employee = Employee.query.get_or_404(employee_id)
    
    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])
    effective_start = max(month_start, employee.date_started) if employee.date_started else month_start
    
    logs = DailyLog.query.filter(
        DailyLog.employee_id == employee_id,
        DailyLog.work_date >= effective_start,
        DailyLog.work_date <= month_end
    ).order_by(DailyLog.work_date).all()
    
    total_earnings = sum(log.daily_total for log in logs)
    total_days_worked = len(set(log.work_date for log in logs))
    
    slip_data = {
        'employee': employee,
        'month': month_start.strftime('%B %Y'),
        'start_date': effective_start,
        'end_date': month_end,
        'total_days_worked': total_days_worked,
        'total_earnings': total_earnings,
        'logs': logs
    }
    
    return render_template('salary_slips/print.html', slip=slip_data)

@bp.route('/download-pdf/<int:employee_id>/<int:month>/<int:year>')
@login_required
def download_pdf(employee_id, month, year):
    """Generate and download PDF salary slip"""
    employee = Employee.query.get_or_404(employee_id)
    
    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])
    effective_start = max(month_start, employee.date_started) if employee.date_started else month_start
    
    logs = DailyLog.query.filter(
        DailyLog.employee_id == employee_id,
        DailyLog.work_date >= effective_start,
        DailyLog.work_date <= month_end
    ).order_by(DailyLog.work_date).all()
    
    total_earnings = sum(log.daily_total for log in logs)
    total_days_worked = len(set(log.work_date for log in logs))
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    story.append(Paragraph('Farm Payroll - Salary Slip', title_style))
    story.append(Spacer(1, 20))
    
    # Employee details
    employee_data = [
        ['Employee Name:', employee.name],
        ['Clock Number:', employee.clock_number],
        ['Pay Period:', f"{effective_start.strftime('%d %B %Y')} to {month_end.strftime('%d %B %Y')}"],
        ['Days Worked:', str(total_days_worked)],
        ['Total Earnings:', f"R{total_earnings:.2f}"]
    ]
    
    employee_table = Table(employee_data, colWidths=[1.5*inch, 3*inch])
    employee_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4A5568')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(employee_table)
    story.append(Spacer(1, 20))
    
    # Daily logs table
    table_data = [['Date', 'Job Type', 'Quantity', 'Hours', 'Amount']]
    for log in logs:
        hours = log.calculate_hours_worked() if log.clock_in_time else 0
        table_data.append([
            log.work_date.strftime('%d/%m/%Y'),
            log.job_type.job_name,
            f"{log.quantity_complete:.2f}",
            f"{hours:.2f}" if hours > 0 else '-',
            f"R{log.daily_total:.2f}"
        ])
    
    if table_data:
        table = Table(table_data, colWidths=[1.2*inch, 2.5*inch, 1*inch, 1*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4A5568')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')])
        ]))
        story.append(table)
    
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'salary_slip_{employee.clock_number}_{month}_{year}.pdf'
    )