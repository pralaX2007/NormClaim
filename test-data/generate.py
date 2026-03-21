"""
NormClaim — Synthetic Test PDF Generator
Generates 4 realistic hospital documents for testing the AI extraction pipeline.
Run: python test-data/generate.py
Requires: pip install reportlab
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Color Palette ──────────────────────────────────────────────────────────
NAVY       = HexColor("#0A1628")
TEAL       = HexColor("#028090")
DARK_GRAY  = HexColor("#333333")
MED_GRAY   = HexColor("#666666")
LIGHT_GRAY = HexColor("#EEEEEE")
WHITE      = HexColor("#FFFFFF")
RED_ACCENT = HexColor("#C0392B")

# ── Styles ─────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

STYLE_HOSPITAL = ParagraphStyle(
    "HospitalName", parent=styles["Title"],
    fontSize=18, leading=22, textColor=TEAL,
    alignment=TA_CENTER, spaceAfter=2*mm,
)
STYLE_SUBTITLE = ParagraphStyle(
    "Subtitle", parent=styles["Normal"],
    fontSize=9, leading=11, textColor=MED_GRAY,
    alignment=TA_CENTER, spaceAfter=4*mm,
)
STYLE_SECTION = ParagraphStyle(
    "Section", parent=styles["Heading2"],
    fontSize=12, leading=14, textColor=NAVY,
    spaceBefore=5*mm, spaceAfter=2*mm,
    borderWidth=0, borderPadding=0,
)
STYLE_BODY = ParagraphStyle(
    "Body", parent=styles["Normal"],
    fontSize=10, leading=13, textColor=DARK_GRAY,
    spaceAfter=2*mm,
)
STYLE_SMALL = ParagraphStyle(
    "Small", parent=styles["Normal"],
    fontSize=8, leading=10, textColor=MED_GRAY,
)
STYLE_LABEL = ParagraphStyle(
    "Label", parent=styles["Normal"],
    fontSize=9, leading=11, textColor=MED_GRAY,
    spaceAfter=1*mm,
)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=LIGHT_GRAY, spaceAfter=3*mm, spaceBefore=2*mm)

def field(label: str, value: str) -> Paragraph:
    return Paragraph(f"<b>{label}:</b> {value}", STYLE_BODY)

def hospital_header(story, name="Saraswati Multi-Specialty Hospital",
                     addr="MG Road, Sector 12, Patna — 800001, Bihar",
                     phone="+91-612-234-5678", reg="REG/BH/2019/04521"):
    story.append(Paragraph(name, STYLE_HOSPITAL))
    story.append(Paragraph(f"{addr}  |  Tel: {phone}", STYLE_SUBTITLE))
    story.append(Paragraph(f"NABH Accredited  •  Registration No: {reg}", STYLE_SMALL))
    story.append(hr())


# ═══════════════════════════════════════════════════════════════════════════
# PDF 1 — discharge_complex.pdf
# ═══════════════════════════════════════════════════════════════════════════

def generate_discharge_complex():
    path = os.path.join(OUTPUT_DIR, "discharge_complex.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    story = []

    hospital_header(story)

    story.append(Paragraph("DISCHARGE SUMMARY", ParagraphStyle(
        "DS", parent=STYLE_SECTION, fontSize=14, alignment=TA_CENTER,
        textColor=RED_ACCENT, spaceBefore=2*mm,
    )))
    story.append(hr())

    # Patient Information
    story.append(Paragraph("PATIENT INFORMATION", STYLE_SECTION))
    patient_data = [
        ["Patient Name:", "Rajesh Kumar",        "Age/Sex:", "58 / Male"],
        ["UHID:",         "SAR-2024-08812",      "ABHA ID:", "91-2345-6789-0123"],
        ["Ward:",         "General Medicine - B3","Bed No:",  "B3-14"],
        ["Consultant:",   "Dr. Anand Prakash, MD (Internal Medicine)", "", ""],
    ]
    t = Table(patient_data, colWidths=[30*mm, 55*mm, 25*mm, 55*mm])
    t.setStyle(TableStyle([
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",  (0, 0), (0, -1), MED_GRAY),
        ("TEXTCOLOR",  (2, 0), (2, -1), MED_GRAY),
        ("FONTNAME",   (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME",   (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(hr())

    # Encounter
    story.append(Paragraph("ENCOUNTER DETAILS", STYLE_SECTION))
    story.append(field("Date of Admission", "2024-08-10"))
    story.append(field("Date of Discharge", "2024-08-17"))
    story.append(field("Length of Stay", "7 days"))
    story.append(field("Mode of Admission", "Emergency"))
    story.append(hr())

    # Chief Complaints
    story.append(Paragraph("CHIEF COMPLAINTS", STYLE_SECTION))
    story.append(Paragraph(
        "Patient presented with high-grade fever (103°F) for 5 days, productive cough with "
        "yellowish sputum, breathlessness on exertion (NYHA Class II), and generalised weakness. "
        "Known case of Type 2 Diabetes Mellitus on oral hypoglycemics for 12 years. "
        "Also a known hypertensive on medication for 8 years.",
        STYLE_BODY
    ))
    story.append(hr())

    # Diagnosis
    story.append(Paragraph("DIAGNOSES", STYLE_SECTION))
    dx_data = [
        ["#", "Diagnosis", "ICD-10", "Type"],
        ["1", "Community-Acquired Pneumonia (right lower lobe)", "J18.9", "Primary"],
        ["2", "Type 2 Diabetes Mellitus without complications", "E11.9", "Secondary"],
        ["3", "Essential Hypertension", "I10", "Secondary"],
        ["4", "Chronic Kidney Disease, Stage 3 (eGFR 42 mL/min)", "N18.3", "Comorbidity"],
    ]
    t = Table(dx_data, colWidths=[8*mm, 80*mm, 22*mm, 25*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#F7F9FC")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(hr())

    # Procedures
    story.append(Paragraph("PROCEDURES PERFORMED", STYLE_SECTION))
    story.append(Paragraph("1. Chest X-ray PA view — 2024-08-10", STYLE_BODY))
    story.append(Paragraph("2. Sputum culture and sensitivity — 2024-08-10", STYLE_BODY))
    story.append(Paragraph("3. IV Antibiotic administration (Ceftriaxone) — 2024-08-10 to 2024-08-15", STYLE_BODY))
    story.append(Paragraph("4. Renal function panel — 2024-08-11", STYLE_BODY))
    story.append(hr())

    # Medications
    story.append(Paragraph("MEDICATIONS AT DISCHARGE", STYLE_SECTION))
    med_data = [
        ["Medication", "Dose", "Frequency", "Duration"],
        ["Amoxicillin + Clavulanic Acid", "625 mg", "TID (three times daily)", "7 days"],
        ["Metformin", "500 mg", "BD (twice daily)", "Ongoing"],
        ["Amlodipine", "5 mg", "OD (once daily)", "Ongoing"],
        ["Pantoprazole", "40 mg", "OD (before breakfast)", "14 days"],
    ]
    t = Table(med_data, colWidths=[50*mm, 25*mm, 40*mm, 25*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(hr())

    # Bill / Claim section — ONLY J18.9 billed
    story.append(Paragraph("BILLING SUMMARY", STYLE_SECTION))
    story.append(Paragraph(
        "<b>Insurance Claim Filed Under:</b> AB-PMJAY (Ayushman Bharat)", STYLE_BODY
    ))
    bill_data = [
        ["Billed Diagnosis Code", "Description", "Package Amount (₹)"],
        ["J18.9", "Pneumonia, unspecified", "8,500"],
    ]
    t = Table(bill_data, colWidths=[40*mm, 65*mm, 35*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#F5A623")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), NAVY),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN",      (2, 0), (2, -1), "RIGHT"),
    ]))
    story.append(t)
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "<i>Note: Only primary diagnosis billed. Secondary diagnoses and comorbidities "
        "not included in current claim submission.</i>", STYLE_SMALL
    ))
    story.append(hr())

    # Footer
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Prepared by: Dr. Anand Prakash, MD", STYLE_BODY))
    story.append(Paragraph("Verified by: Dr. Sunita Devi, Medical Superintendent", STYLE_BODY))
    story.append(Paragraph("Date: 2024-08-17", STYLE_BODY))

    doc.build(story)
    print(f"✓ Generated: {path}")


# ═══════════════════════════════════════════════════════════════════════════
# PDF 2 — discharge_simple.pdf
# ═══════════════════════════════════════════════════════════════════════════

def generate_discharge_simple():
    path = os.path.join(OUTPUT_DIR, "discharge_simple.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    story = []

    hospital_header(story, name="City Care Hospital & Research Centre",
                     addr="Station Road, Boring Canal, Patna — 800001",
                     phone="+91-612-987-6543", reg="REG/BH/2021/07832")

    story.append(Paragraph("DISCHARGE SUMMARY", ParagraphStyle(
        "DS2", parent=STYLE_SECTION, fontSize=14, alignment=TA_CENTER,
        textColor=RED_ACCENT, spaceBefore=2*mm,
    )))
    story.append(hr())

    # Patient
    story.append(Paragraph("PATIENT INFORMATION", STYLE_SECTION))
    patient_data = [
        ["Patient Name:", "Priya Sharma",      "Age/Sex:", "34 / Female"],
        ["UHID:",         "CC-2024-04291",     "ABHA ID:", "91-8765-4321-0987"],
        ["Ward:",         "Surgery - S2",      "Bed No:",  "S2-06"],
        ["Consultant:",   "Dr. Vikram Singh, MS (General Surgery)", "", ""],
    ]
    t = Table(patient_data, colWidths=[30*mm, 55*mm, 25*mm, 55*mm])
    t.setStyle(TableStyle([
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",  (0, 0), (0, -1), MED_GRAY),
        ("TEXTCOLOR",  (2, 0), (2, -1), MED_GRAY),
        ("FONTNAME",   (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME",   (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(hr())

    # Encounter
    story.append(Paragraph("ENCOUNTER DETAILS", STYLE_SECTION))
    story.append(field("Date of Admission", "2024-07-22"))
    story.append(field("Date of Discharge", "2024-07-24"))
    story.append(field("Length of Stay", "2 days"))
    story.append(field("Mode of Admission", "Emergency"))
    story.append(hr())

    # Chief Complaints
    story.append(Paragraph("CHIEF COMPLAINTS", STYLE_SECTION))
    story.append(Paragraph(
        "Patient presented with acute right lower abdominal pain for 2 days, associated with "
        "nausea and low-grade fever (100.2°F). Pain was initially periumbilical and then "
        "localised to the right iliac fossa. No vomiting, no urinary symptoms.",
        STYLE_BODY
    ))
    story.append(hr())

    # Diagnosis
    story.append(Paragraph("DIAGNOSES", STYLE_SECTION))
    dx_data = [
        ["#", "Diagnosis", "ICD-10", "Type"],
        ["1", "Acute Appendicitis (Unspecified)", "K37", "Primary"],
    ]
    t = Table(dx_data, colWidths=[8*mm, 80*mm, 22*mm, 25*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(hr())

    # Procedures
    story.append(Paragraph("PROCEDURES PERFORMED", STYLE_SECTION))
    story.append(Paragraph("1. Laparoscopic Appendectomy — 2024-07-22", STYLE_BODY))
    story.append(Paragraph("2. Histopathological examination of specimen — 2024-07-23", STYLE_BODY))
    story.append(hr())

    # Medications
    story.append(Paragraph("MEDICATIONS AT DISCHARGE", STYLE_SECTION))
    med_data = [
        ["Medication", "Dose", "Frequency", "Duration"],
        ["Cefixime", "200 mg", "BD", "5 days"],
        ["Paracetamol", "500 mg", "TID (as needed)", "3 days"],
        ["Pantoprazole", "40 mg", "OD", "7 days"],
    ]
    t = Table(med_data, colWidths=[50*mm, 25*mm, 40*mm, 25*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(hr())

    # Bill — correctly coded
    story.append(Paragraph("BILLING SUMMARY", STYLE_SECTION))
    story.append(Paragraph(
        "<b>Insurance Claim Filed Under:</b> AB-PMJAY (Ayushman Bharat)", STYLE_BODY
    ))
    bill_data = [
        ["Billed Diagnosis Code", "Description", "Package Amount (₹)"],
        ["K37", "Unspecified appendicitis", "12,000"],
    ]
    t = Table(bill_data, colWidths=[40*mm, 65*mm, 35*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#F5A623")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), NAVY),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN",      (2, 0), (2, -1), "RIGHT"),
    ]))
    story.append(t)
    story.append(hr())

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Prepared by: Dr. Vikram Singh, MS", STYLE_BODY))
    story.append(Paragraph("Date: 2024-07-24", STYLE_BODY))

    doc.build(story)
    print(f"✓ Generated: {path}")


# ═══════════════════════════════════════════════════════════════════════════
# PDF 3 — lab_report.pdf
# ═══════════════════════════════════════════════════════════════════════════

def generate_lab_report():
    path = os.path.join(OUTPUT_DIR, "lab_report.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    story = []

    hospital_header(story, name="Patna Diagnostic & Pathology Centre",
                     addr="Fraser Road, Near Gandhi Maidan, Patna — 800001",
                     phone="+91-612-555-7890", reg="LAB/BH/2020/01234")

    story.append(Paragraph("LABORATORY INVESTIGATION REPORT", ParagraphStyle(
        "LR", parent=STYLE_SECTION, fontSize=14, alignment=TA_CENTER,
        textColor=RED_ACCENT, spaceBefore=2*mm,
    )))
    story.append(hr())

    # Patient
    story.append(Paragraph("PATIENT DETAILS", STYLE_SECTION))
    patient_data = [
        ["Patient Name:", "Amit Singh",        "Age/Sex:", "45 / Male"],
        ["UHID:",         "PD-2024-11205",    "ABHA ID:", "91-5678-1234-5678"],
        ["Referred By:",  "Dr. Meera Gupta, MD (Endocrinology)", "", ""],
        ["Sample Date:",  "2024-09-05",       "Report Date:", "2024-09-06"],
    ]
    t = Table(patient_data, colWidths=[30*mm, 55*mm, 28*mm, 55*mm])
    t.setStyle(TableStyle([
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",  (0, 0), (0, -1), MED_GRAY),
        ("TEXTCOLOR",  (2, 0), (2, -1), MED_GRAY),
        ("FONTNAME",   (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME",   (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(hr())

    # Lab Results
    story.append(Paragraph("INVESTIGATION RESULTS", STYLE_SECTION))
    lab_data = [
        ["Test", "Result", "Unit", "Reference Range", "Flag"],
        ["HbA1c (Glycated Hemoglobin)", "8.2", "%", "4.0 – 5.6", "HIGH ↑"],
        ["Fasting Blood Sugar (FBS)", "168", "mg/dL", "70 – 100", "HIGH ↑"],
        ["Post-Prandial Blood Sugar (PPBS)", "242", "mg/dL", "< 140", "HIGH ↑"],
        ["Serum Creatinine", "2.1", "mg/dL", "0.7 – 1.3", "HIGH ↑"],
        ["Blood Urea Nitrogen (BUN)", "38", "mg/dL", "7 – 20", "HIGH ↑"],
        ["eGFR (CKD-EPI)", "42", "mL/min/1.73m²", "> 90", "LOW ↓"],
        ["Total Cholesterol", "248", "mg/dL", "< 200", "HIGH ↑"],
        ["LDL Cholesterol", "162", "mg/dL", "< 100", "HIGH ↑"],
        ["HDL Cholesterol", "38", "mg/dL", "> 40", "LOW ↓"],
        ["Triglycerides", "210", "mg/dL", "< 150", "HIGH ↑"],
        ["Hemoglobin", "11.2", "g/dL", "13.0 – 17.0", "LOW ↓"],
        ["WBC Count", "7,800", "/µL", "4,500 – 11,000", "Normal"],
        ["Platelet Count", "2,10,000", "/µL", "1,50,000 – 4,00,000", "Normal"],
    ]
    t = Table(lab_data, colWidths=[52*mm, 20*mm, 28*mm, 30*mm, 18*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 8),
        ("GRID",       (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#F7F9FC")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN",      (1, 0), (1, -1), "CENTER"),
        ("ALIGN",      (4, 0), (4, -1), "CENTER"),
    ]))
    story.append(t)
    story.append(hr())

    # Vitals
    story.append(Paragraph("VITALS AT TIME OF SAMPLE COLLECTION", STYLE_SECTION))
    story.append(field("Blood Pressure", "145/92 mmHg (Hypertensive)"))
    story.append(field("Heart Rate", "82 bpm"))
    story.append(field("Weight", "88 kg"))
    story.append(field("Height", "170 cm"))
    story.append(field("BMI", "30.4 (Obese Class I)"))
    story.append(hr())

    # Clinical Impression
    story.append(Paragraph("CLINICAL IMPRESSION", STYLE_SECTION))
    story.append(Paragraph(
        "Findings are consistent with poorly controlled Type 2 Diabetes Mellitus (HbA1c 8.2%), "
        "Chronic Kidney Disease Stage 3 (eGFR 42), Dyslipidemia, and mild anaemia. "
        "Blood pressure reading indicates uncontrolled Essential Hypertension. "
        "Recommend urgent nephrology and endocrinology consultation.",
        STYLE_BODY
    ))
    story.append(hr())

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Pathologist: Dr. R.K. Verma, MD (Pathology)", STYLE_BODY))
    story.append(Paragraph("NABL Accreditation No: MC-4521", STYLE_SMALL))

    doc.build(story)
    print(f"✓ Generated: {path}")


# ═══════════════════════════════════════════════════════════════════════════
# PDF 4 — bill_undercoded.pdf
# ═══════════════════════════════════════════════════════════════════════════

def generate_bill_undercoded():
    path = os.path.join(OUTPUT_DIR, "bill_undercoded.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    story = []

    hospital_header(story)

    story.append(Paragraph("HOSPITAL BILL / CLAIM INVOICE", ParagraphStyle(
        "BI", parent=STYLE_SECTION, fontSize=14, alignment=TA_CENTER,
        textColor=RED_ACCENT, spaceBefore=2*mm,
    )))
    story.append(hr())

    # Bill Info
    story.append(Paragraph("BILL DETAILS", STYLE_SECTION))
    bill_info = [
        ["Bill No:", "SAR-BILL-2024-3827",  "Date:", "2024-08-17"],
        ["Patient:",  "Rajesh Kumar",        "UHID:", "SAR-2024-08812"],
        ["Ward:",     "General Medicine - B3","Bed:",  "B3-14"],
        ["Admission:","2024-08-10",          "Discharge:", "2024-08-17"],
    ]
    t = Table(bill_info, colWidths=[25*mm, 55*mm, 25*mm, 55*mm])
    t.setStyle(TableStyle([
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",  (0, 0), (0, -1), MED_GRAY),
        ("TEXTCOLOR",  (2, 0), (2, -1), MED_GRAY),
        ("FONTNAME",   (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTNAME",   (3, 0), (3, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(hr())

    # Diagnosis on bill
    story.append(Paragraph("DIAGNOSIS (AS BILLED)", STYLE_SECTION))
    dx_bill = [
        ["ICD-10 Code", "Diagnosis Description"],
        ["J18.9", "Pneumonia, unspecified"],
    ]
    t = Table(dx_bill, colWidths=[35*mm, 100*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#F5A623")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), NAVY),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 10),
        ("GRID",       (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(hr())

    # Itemised bill
    story.append(Paragraph("ITEMISED CHARGES", STYLE_SECTION))
    charges = [
        ["S.No.", "Description", "Amount (₹)"],
        ["1", "Room Charges (General Ward, 7 days × ₹500)", "3,500"],
        ["2", "Doctor Consultation Fees", "1,500"],
        ["3", "IV Antibiotics (Ceftriaxone, 6 days)", "4,200"],
        ["4", "Chest X-Ray", "350"],
        ["5", "Sputum Culture & Sensitivity", "800"],
        ["6", "Complete Blood Count (CBC)", "250"],
        ["7", "Renal Function Test (RFT)", "450"],
        ["8", "Blood Sugar (FBS + PPBS)", "200"],
        ["9", "Nursing Charges", "1,200"],
        ["10", "Pharmacy (Discharge Medicines)", "650"],
        ["", "", ""],
        ["", "SUBTOTAL", "13,100"],
        ["", "AB-PMJAY Package Claim (J18.9)", "8,500"],
        ["", "Patient Co-Pay", "4,600"],
    ]
    t = Table(charges, colWidths=[15*mm, 90*mm, 35*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("GRID",       (0, 0), (-1, -2), 0.5, LIGHT_GRAY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN",      (2, 0), (2, -1), "RIGHT"),
        ("LINEABOVE",  (0, -3), (-1, -3), 1, DARK_GRAY),
        ("FONTNAME",   (1, -3), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -2), (-1, -2), HexColor("#E8F5E9")),
        ("BACKGROUND", (0, -1), (-1, -1), HexColor("#FFF3E0")),
    ]))
    story.append(t)
    story.append(hr())

    # Note
    story.append(Paragraph("INSURANCE CLAIM NOTES", STYLE_SECTION))
    story.append(Paragraph(
        "Claim submitted under Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (AB-PMJAY). "
        "Package rate for J18.9 (Pneumonia, unspecified) is ₹8,500 as per AB-PMJAY rate card. "
        "Only primary diagnosis has been coded for insurance claim purposes. "
        "Patient is responsible for the remaining co-pay amount of ₹4,600.",
        STYLE_BODY
    ))
    story.append(Paragraph(
        "<i>This bill is computer-generated and does not require a physical signature.</i>",
        STYLE_SMALL
    ))
    story.append(hr())

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("Billing Department — Saraswati Multi-Specialty Hospital", STYLE_BODY))
    story.append(Paragraph("Authorised Signatory: Accounts Section", STYLE_SMALL))

    doc.build(story)
    print(f"✓ Generated: {path}")


# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("NormClaim — Generating Synthetic Test PDFs...")
    print("=" * 50)
    generate_discharge_complex()
    generate_discharge_simple()
    generate_lab_report()
    generate_bill_undercoded()
    print("=" * 50)
    print("✓ All 4 test PDFs generated successfully!")
    print(f"  Output directory: {OUTPUT_DIR}")
