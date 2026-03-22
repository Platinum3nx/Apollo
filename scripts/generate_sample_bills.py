"""Generate realistic sample bill images for demo purposes.

Creates PNG images that look like real medical bills with planted errors.
Requires Pillow.
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "public", "sample-bills")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_font(size=16):
    """Get a font, falling back to default if needed."""
    try:
        return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except (OSError, IOError):
            return ImageFont.load_default()


def draw_bill(filename, provider_name, provider_address, patient_name, account_num, dos, line_items, total, insurance_paid=None, notes=None):
    """Draw a medical bill image."""
    width, height = 800, 1100
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    font_title = get_font(24)
    font_heading = get_font(18)
    font_normal = get_font(14)
    font_small = get_font(12)

    y = 30

    # Provider header
    draw.text((50, y), provider_name, fill="black", font=font_title)
    y += 35
    draw.text((50, y), provider_address, fill="gray", font=font_small)
    y += 25
    draw.line([(50, y), (750, y)], fill="black", width=2)
    y += 20

    # Statement label
    draw.text((300, y), "STATEMENT OF CHARGES", fill="black", font=font_heading)
    y += 35

    # Patient info
    draw.text((50, y), f"Patient: {patient_name}", fill="black", font=font_normal)
    draw.text((450, y), f"Account #: {account_num}", fill="black", font=font_normal)
    y += 22
    draw.text((50, y), f"Date of Service: {dos}", fill="black", font=font_normal)
    y += 35

    # Table header
    draw.line([(50, y), (750, y)], fill="gray", width=1)
    y += 5
    draw.text((50, y), "Description", fill="black", font=font_normal)
    draw.text((370, y), "CPT", fill="black", font=font_normal)
    draw.text((460, y), "Qty", fill="black", font=font_normal)
    draw.text((530, y), "Unit Price", fill="black", font=font_normal)
    draw.text((660, y), "Total", fill="black", font=font_normal)
    y += 22
    draw.line([(50, y), (750, y)], fill="gray", width=1)
    y += 8

    # Line items
    for item in line_items:
        desc = item["description"]
        cpt = item.get("cpt", "")
        qty = item.get("qty", 1)
        unit = item["price"]
        total_price = unit * qty

        draw.text((50, y), desc[:40], fill="black", font=font_normal)
        draw.text((370, y), str(cpt), fill="black", font=font_normal)
        draw.text((460, y), str(qty), fill="black", font=font_normal)
        draw.text((530, y), f"${unit:,.2f}", fill="black", font=font_normal)
        draw.text((660, y), f"${total_price:,.2f}", fill="black", font=font_normal)
        y += 25

    # Total
    y += 10
    draw.line([(500, y), (750, y)], fill="black", width=2)
    y += 10
    draw.text((500, y), "Total Charges:", fill="black", font=font_heading)
    draw.text((660, y), f"${total:,.2f}", fill="black", font=font_heading)
    y += 30

    if insurance_paid is not None:
        draw.text((500, y), "Insurance Paid:", fill="gray", font=font_normal)
        draw.text((660, y), f"-${insurance_paid:,.2f}", fill="gray", font=font_normal)
        y += 22
        patient_resp = total - insurance_paid
        draw.text((500, y), "Patient Responsibility:", fill="red", font=font_heading)
        draw.text((660, y), f"${patient_resp:,.2f}", fill="red", font=font_heading)
        y += 30

    if notes:
        y += 20
        draw.text((50, y), "Notes:", fill="gray", font=font_small)
        y += 18
        for note in notes:
            draw.text((50, y), f"  - {note}", fill="gray", font=font_small)
            y += 16

    path = os.path.join(OUTPUT_DIR, filename)
    img.save(path)
    print(f"Generated: {path}")


# Sample A: ER Visit with Labs (has errors)
draw_bill(
    "sample-a.png",
    "UVA Health System",
    "1215 Lee St, Charlottesville, VA 22903 | (434) 924-0000",
    "Jane Doe",
    "ACC-78291",
    "2025-11-15",
    [
        {"description": "Emergency Dept Visit Level 4", "cpt": "99284", "price": 1800.00},
        {"description": "Comprehensive Metabolic Panel", "cpt": "80053", "price": 225.00},
        {"description": "Basic Metabolic Panel", "cpt": "80048", "price": 150.00},
        {"description": "CBC with Differential", "cpt": "85025", "price": 95.00},
        {"description": "Urinalysis, Automated", "cpt": "81003", "price": 60.00},
        {"description": "IV Infusion, First Hour", "cpt": "96365", "price": 450.00},
        {"description": "IV Infusion, First Hour", "cpt": "96365", "price": 450.00},
        {"description": "Facility Fee", "cpt": "", "price": 800.00},
    ],
    total=4030.00,
    insurance_paid=1200.00,
    notes=["Payment due within 30 days", "Questions? Call (434) 924-0000"],
)

# Sample B: Routine Checkup (overcharges only)
draw_bill(
    "sample-b.png",
    "Riverside Medical Group",
    "500 Main Street, Richmond, VA 23219 | (804) 555-1234",
    "John Smith",
    "ACC-45632",
    "2025-10-20",
    [
        {"description": "Office Visit Level 4", "cpt": "99214", "price": 350.00},
        {"description": "Lipid Panel", "cpt": "80061", "price": 180.00},
        {"description": "TSH (Thyroid)", "cpt": "84443", "price": 120.00},
        {"description": "Venipuncture", "cpt": "36415", "price": 75.00},
    ],
    total=725.00,
    insurance_paid=300.00,
)

# Sample C: Clean Bill (passes checks)
draw_bill(
    "sample-c.png",
    "Blue Ridge Family Practice",
    "200 Oak Avenue, Charlottesville, VA 22901 | (434) 555-5678",
    "Sarah Wilson",
    "ACC-91234",
    "2025-12-01",
    [
        {"description": "Office Visit Level 3", "cpt": "99213", "price": 195.00},
        {"description": "Flu Vaccine Admin", "cpt": "G0008", "price": 25.00},
    ],
    total=220.00,
    insurance_paid=180.00,
)

print("\nAll sample bills generated!")
