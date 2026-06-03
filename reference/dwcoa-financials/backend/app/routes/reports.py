"""Report generation routes."""

import base64
from datetime import date
from typing import Optional

from app.services import pdf_generator


def handle_generate_pdf(as_of_date: Optional[str] = None) -> dict:
    """Generate and return PDF report.

    Args:
        as_of_date: Date string (YYYY-MM-DD) for snapshot. Defaults to today.

    Returns:
        Response with PDF content
    """
    try:
        pdf_bytes = pdf_generator.generate_dashboard_pdf(as_of_date)

        # Determine filename date
        date_str = as_of_date or date.today().isoformat()

        # Return as base64 for API Gateway
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/pdf',
                'Content-Disposition': f'attachment; filename="DWCOA_Report_{date_str}.pdf"'
            },
            'body': base64.b64encode(pdf_bytes).decode('utf-8'),
            'isBase64Encoded': True
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': f'{{"error": "internal_error", "message": "{str(e)}"}}'
        }
