from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable

import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .scraper import AnimalEntry, ANIMAL_TYPES


def download_image(url: str, timeout: int = 10) -> bytes | None:
    """Download image from URL and return bytes."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Warning: Failed to download image from {url}: {e}")
        return None


def generate_pdf_report(
    animals: Iterable[AnimalEntry],
    output_path: Path,
    *,
    title: str = "Dierenasiel Alert - Available Animals",
) -> None:
    """Generate a PDF report with animal photos and information.
    
    Args:
        animals: Iterable of AnimalEntry objects to include in the report
        output_path: Path where the PDF should be saved
        title: Title for the report
    """
    # Create PDF document
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm,
    )
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2d5f3f'),
        spaceAfter=30,
        alignment=1,  # Center
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2d5f3f'),
        spaceAfter=12,
    )
    normal_style = styles['Normal']
    
    # Title
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Summary info
    animal_list = list(animals)
    summary_text = f"Total animals found: <b>{len(animal_list)}</b>"
    elements.append(Paragraph(summary_text, normal_style))
    elements.append(Spacer(1, 1*cm))
    
    # Add each animal
    for i, animal in enumerate(animal_list):
        if i > 0:
            elements.append(PageBreak())
        
        # Animal name as heading
        animal_name = animal.name or f"Animal {animal.id}"
        elements.append(Paragraph(animal_name, heading_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Photo if available
        if animal.photo_url:
            try:
                img_data = download_image(animal.photo_url)
                if img_data:
                    img = Image(io.BytesIO(img_data))
                    # Scale image to fit width (max 12cm)
                    img.drawHeight = 10*cm
                    img.drawWidth = 12*cm
                    elements.append(img)
                    elements.append(Spacer(1, 0.5*cm))
            except Exception as e:
                print(f"Warning: Could not add image for {animal.name}: {e}")
        
        # Animal details table
        data = []
        
        if animal.id:
            data.append(['ID:', animal.id])
        
        if animal.animal_type:
            animal_type_display = ANIMAL_TYPES.get(animal.animal_type, animal.animal_type)
            data.append(['Type:', animal_type_display.title()])
        
        if animal.location:
            data.append(['Location:', animal.location])
        
        if animal.site:
            data.append(['Site:', animal.site])
        
        if animal.availability:
            data.append(['Availability:', animal.availability.title()])
        
        if animal.url:
            data.append(['URL:', animal.url])
        
        if data:
            table = Table(data, colWidths=[4*cm, 12*cm])
            table.setStyle(TableStyle([
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONT', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.grey),
            ]))
            elements.append(table)
    
    # Build PDF
    doc.build(elements)
    print(f"PDF report saved to: {output_path}")
