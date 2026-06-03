"""PDF report generation using ReportLab."""

import io
from datetime import date, datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.services import database, budget_calc
from app.routes import dues


def generate_dashboard_pdf(as_of_date: Optional[str] = None) -> bytes:
    """Generate a PDF report matching the dashboard layout.

    Args:
        as_of_date: Date string (YYYY-MM-DD) for snapshot. Defaults to today.

    Returns:
        PDF content as bytes
    """
    # Parse date or default to today
    if as_of_date:
        try:
            snapshot_date = datetime.strptime(as_of_date, '%Y-%m-%d').date()
        except ValueError:
            snapshot_date = date.today()
    else:
        snapshot_date = date.today()

    year = snapshot_date.year

    # Get data as of the snapshot date
    accounts = budget_calc.get_account_balances(as_of_date=snapshot_date)
    total_cash = sum(a['balance'] for a in accounts)

    # Get starting balances for the year
    beginning_balances = budget_calc.get_account_balances_at_year_start(year)
    starting_balance_map = {b['name']: b['balance'] for b in beginning_balances}
    for account in accounts:
        account['starting_balance'] = starting_balance_map.get(account['name'], 0)
    total_starting = sum(a['starting_balance'] for a in accounts)

    budget_summary = budget_calc.get_budget_summary(year, as_of_date=snapshot_date)
    dues_data = dues.get_dues_status(year, as_of_date=snapshot_date)
    reserve_fund = budget_calc.get_reserve_fund_status(year, as_of_date=snapshot_date)
    last_updated = database.get_config('last_upload_at')

    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch
    )

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=6
    )
    heading_style = ParagraphStyle(
        'Heading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=6
    )
    normal_style = styles['Normal']

    elements = []

    # Format as_of_date for display
    date_display = snapshot_date.strftime('%B %d, %Y')

    # Title
    elements.append(Paragraph("DWCOA Financial Dashboard", title_style))
    elements.append(Paragraph(f"As of: {date_display}", normal_style))
    if last_updated:
        elements.append(Paragraph(f"Last Updated: {last_updated}", normal_style))
    elements.append(Spacer(1, 12))

    # Account Balances - match dashboard with Starting, Current, Change columns
    elements.append(Paragraph("Account Balances", heading_style))

    # Find account data by name
    def find_account(name):
        return next((a for a in accounts if a['name'] == name), None)

    account_order = ['Checking', 'Savings', 'Reserve Fund']
    account_data = [['Account', 'Starting', 'Current', 'Change']]

    for name in account_order:
        acc = find_account(name)
        starting = acc['starting_balance'] if acc else 0
        current = acc['balance'] if acc else 0
        change = current - starting
        change_prefix = '+' if change >= 0 else ''
        account_data.append([
            name,
            format_currency(starting),
            format_currency(current),
            f'{change_prefix}{format_currency(change)}'
        ])

    # Total row
    total_change = total_cash - total_starting
    total_change_prefix = '+' if total_change >= 0 else ''
    account_data.append([
        'Total Cash',
        format_currency(total_starting),
        format_currency(total_cash),
        f'{total_change_prefix}{format_currency(total_change)}'
    ])

    account_table = Table(account_data, colWidths=[1.5*inch, 1.25*inch, 1.25*inch, 1.25*inch])
    account_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(account_table)
    elements.append(Spacer(1, 6))

    # Reserve Fund Goal and Net Income summary boxes (side by side using a nested table)
    expense = budget_summary['expense_summary']

    # Find Reserve Fund goal from expense categories
    reserve_category = next(
        (cat for cat in expense['categories']
         if cat['category'].lower() in ('reserve fund', 'reserve contribution')),
        None
    )
    reserve_goal = reserve_category['annual_budget'] if reserve_category else 0

    # Calculate Reserve Fund actual change (current - starting)
    reserve_acc = find_account('Reserve Fund')
    reserve_starting = reserve_acc['starting_balance'] if reserve_acc else 0
    reserve_current = reserve_acc['balance'] if reserve_acc else 0
    reserve_actual_change = reserve_current - reserve_starting
    reserve_difference = reserve_actual_change - reserve_goal

    reserve_change_prefix = '+' if reserve_actual_change >= 0 else ''
    reserve_diff_prefix = '+' if reserve_difference >= 0 else ''

    # Net Income calculations
    income_actual = budget_summary['income_summary']['ytd_actual']
    expense_actual = expense['ytd_actual']
    net_income = income_actual - expense_actual
    net_prefix = '+' if net_income >= 0 else ''

    # Reserve Fund Goal summary
    reserve_summary_data = [
        [Paragraph('<b>Reserve Fund Goal</b>', normal_style), ''],
        ['Goal:', format_currency(reserve_goal)],
        ['Actual:', f'{reserve_change_prefix}{format_currency(reserve_actual_change)}'],
        ['Difference:', f'{reserve_diff_prefix}{format_currency(reserve_difference)}']
    ]
    reserve_summary_table = Table(reserve_summary_data, colWidths=[1.2*inch, 1.3*inch])
    reserve_summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('SPAN', (0, 0), (1, 0)),
    ]))

    # Net Income summary
    net_income_summary_data = [
        [Paragraph('<b>Net Income</b>', normal_style), ''],
        ['Income:', format_currency(income_actual)],
        ['Expenses:', format_currency(expense_actual)],
        ['Net:', f'{net_prefix}{format_currency(net_income)}']
    ]
    net_income_summary_table = Table(net_income_summary_data, colWidths=[1.2*inch, 1.3*inch])
    net_income_summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('SPAN', (0, 0), (1, 0)),
    ]))

    # Combine the two summary boxes side by side
    combined_summary = Table(
        [[reserve_summary_table, Spacer(0.5*inch, 0), net_income_summary_table]],
        colWidths=[2.5*inch, 0.5*inch, 2.5*inch]
    )
    elements.append(combined_summary)
    elements.append(Spacer(1, 12))

    # Income & Dues - match dashboard layout
    elements.append(Paragraph("Income & Dues", heading_style))

    # Income summary totals
    income = budget_summary['income_summary']
    income_budget = income['annual_budget']
    income_actual = income['ytd_actual']
    income_remaining = income_budget - income_actual
    # Invert for display: surplus positive (green), deficit negative (red)
    display_income_remaining = -income_remaining

    # Summary box (like dashboard)
    summary_data = [
        ['Annual Budget:', format_currency(income_budget)],
        ['Actual:', format_currency(income_actual)],
        ['Remaining:', format_currency(display_income_remaining)]
    ]
    summary_table = Table(summary_data, colWidths=[1.5*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 6))

    # Find Interest from income categories
    interest_cat = next((c for c in income['categories'] if 'interest' in c['category'].lower()), None)
    interest_budget = interest_cat['annual_budget'] if interest_cat else 0
    interest_actual = interest_cat['ytd_actual'] if interest_cat else 0
    interest_remaining = interest_budget - interest_actual

    # Calculate totals
    total_past_due = sum(u['past_due_balance'] for u in dues_data['units'])
    total_budget = sum(u['annual_budget'] for u in dues_data['units']) + interest_budget
    total_actual = sum(u['paid_ytd'] for u in dues_data['units']) + interest_actual
    total_remaining = sum(u['outstanding'] for u in dues_data['units']) + interest_remaining

    # Dues by unit table - match dashboard columns with Past Due
    dues_table_data = [['Unit', 'Share', 'Past Due', 'Budget', 'Actual', 'Remaining']]
    for unit in dues_data['units']:
        past_due_display = format_currency(unit['past_due_balance']) if unit['past_due_balance'] > 0 else '-'
        # Invert remaining for display
        display_remaining = -unit['outstanding']
        dues_table_data.append([
            unit['unit'],
            f"{unit['ownership_pct']*100:.1f}%",
            past_due_display,
            format_currency(unit['annual_budget']),
            format_currency(unit['paid_ytd']),
            format_currency(display_remaining)
        ])

    # Interest row
    display_interest_remaining = -interest_remaining
    dues_table_data.append([
        'Interest', '-', '-',
        format_currency(interest_budget),
        format_currency(interest_actual),
        format_currency(display_interest_remaining)
    ])

    # Totals row
    total_past_due_display = format_currency(total_past_due) if total_past_due > 0 else '-'
    display_total_remaining = -total_remaining
    dues_table_data.append([
        'Total', '-', total_past_due_display,
        format_currency(total_budget),
        format_currency(total_actual),
        format_currency(display_total_remaining)
    ])

    num_rows = len(dues_table_data)
    dues_table = Table(dues_table_data, colWidths=[0.7*inch, 0.65*inch, 0.85*inch, 1*inch, 1*inch, 1*inch])
    dues_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Totals row bold
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.black),  # Thicker line above totals
    ]))
    elements.append(dues_table)

    # Note about past due balances
    note_style = ParagraphStyle('Note', parent=normal_style, fontSize=8, textColor=colors.grey, fontName='Helvetica-Oblique')
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("*Past due balances are not included in the current year's operating budget.", note_style))
    elements.append(Spacer(1, 12))

    # Operating Expenses - match dashboard layout
    elements.append(Paragraph("Operating Expenses", heading_style))

    expense = budget_summary['expense_summary']

    # Expense summary box
    expense_summary_data = [
        ['Annual Budget:', format_currency(expense['annual_budget'])],
        ['Actual:', format_currency(expense['ytd_actual'])],
        ['Remaining:', format_currency(expense['remaining'])]
    ]
    expense_summary_table = Table(expense_summary_data, colWidths=[1.5*inch, 1.5*inch])
    expense_summary_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(expense_summary_table)
    elements.append(Spacer(1, 6))

    # Expense category table - match dashboard columns
    expense_data = [['Category', 'Budget', 'Actual', 'Remaining']]
    for cat in expense['categories']:
        expense_data.append([
            cat['category'],
            format_currency(cat['annual_budget']),
            format_currency(cat['ytd_actual']),
            format_currency(cat['remaining'])
        ])

    # Totals row
    expense_data.append([
        'Total',
        format_currency(expense['annual_budget']),
        format_currency(expense['ytd_actual']),
        format_currency(expense['remaining'])
    ])

    expense_table = Table(expense_data, colWidths=[2.5*inch, 1.15*inch, 1.15*inch, 1.15*inch])
    expense_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Totals row bold
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.black),  # Thicker line above totals
    ]))
    elements.append(expense_table)

    # Note about Reserve Contribution
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("*Reserve Contribution is funded through internal transfers with no outgoing expense.", note_style))

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        "Denny Way Condo Owners Association",
        ParagraphStyle('Footer', parent=normal_style, fontSize=8, textColor=colors.grey)
    ))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    return buffer.getvalue()


def format_currency(amount: float) -> str:
    """Format amount as currency string."""
    return f"${amount:,.2f}"
