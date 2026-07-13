from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_DIR / "output" / "pdf" / "sample_public_records_integrity_act_2026.pdf"
TOTAL_PAGES = 7

NAVY = colors.HexColor("#17324D")
BLUE_GRAY = colors.HexColor("#DCE6EF")
PALE_BLUE = colors.HexColor("#F2F6FA")
RULE = colors.HexColor("#9EACB8")
INK = colors.HexColor("#20262C")
MUTED = colors.HexColor("#53606B")
NOTICE = colors.HexColor("#8A1C1C")


def build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DocumentTitle",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=21,
            leading=25,
            alignment=TA_CENTER,
            textColor=NAVY,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "DocumentSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            alignment=TA_CENTER,
            textColor=MUTED,
            spaceAfter=10,
        ),
        "part": ParagraphStyle(
            "PartHeading",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=15,
            leading=18,
            alignment=TA_CENTER,
            textColor=NAVY,
            spaceBefore=2,
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10.3,
            leading=13,
            alignment=TA_LEFT,
            textColor=NAVY,
            spaceBefore=5,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "LegalBody",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=9.4,
            leading=12.3,
            alignment=TA_JUSTIFY,
            textColor=INK,
            spaceAfter=5,
        ),
        "body_indented": ParagraphStyle(
            "LegalBodyIndented",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=9.2,
            leading=12,
            alignment=TA_JUSTIFY,
            leftIndent=18,
            firstLineIndent=-12,
            textColor=INK,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "SmallNote",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=10.5,
            textColor=MUTED,
            spaceAfter=4,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.7,
            leading=11.5,
            textColor=INK,
            leftIndent=8,
            rightIndent=8,
            spaceAfter=0,
        ),
        "table": ParagraphStyle(
            "TableText",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.6,
            leading=9.5,
            textColor=INK,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.7,
            leading=9.5,
            textColor=colors.white,
        ),
    }


def draw_page_frame(canvas, doc):
    width, height = LETTER
    page_number = canvas.getPageNumber()
    canvas.saveState()

    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.6)
    canvas.line(0.72 * inch, height - 0.53 * inch, width - 0.72 * inch, height - 0.53 * inch)

    canvas.setFont("Helvetica-Bold", 7.6)
    canvas.setFillColor(NOTICE)
    canvas.drawString(0.72 * inch, height - 0.39 * inch, "SAMPLE - FOR SUMMARIZATION TESTING")
    canvas.setFont("Helvetica", 7.6)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(
        width - 0.72 * inch,
        height - 0.39 * inch,
        "FICTIONAL COMMONWEALTH OF NORTHBRIDGE",
    )

    canvas.line(0.72 * inch, 0.48 * inch, width - 0.72 * inch, 0.48 * inch)
    canvas.setFont("Helvetica", 7.3)
    canvas.setFillColor(MUTED)
    canvas.drawString(0.72 * inch, 0.29 * inch, "MODEL LEGISLATIVE INSTRUMENT - NO LEGAL EFFECT")
    canvas.drawRightString(
        width - 0.72 * inch,
        0.29 * inch,
        f"Page {page_number} of {TOTAL_PAGES}",
    )
    canvas.restoreState()


def paragraph(text, style):
    return Paragraph(text, style)


def add_section(story, styles, number, title, paragraphs):
    story.append(paragraph(f"Section {number}. {title}", styles["section"]))
    for text in paragraphs:
        story.append(paragraph(text, styles["body"]))


def add_part_page(story, styles, part_number, title, sections):
    story.append(paragraph(f"PART {part_number}", styles["part"]))
    story.append(paragraph(title.upper(), styles["part"]))
    for number, heading, paragraphs in sections:
        add_section(story, styles, number, heading, paragraphs)


def sample_notice(styles):
    table = Table(
        [[paragraph("SAMPLE DOCUMENT - THIS FICTIONAL INSTRUMENT HAS NO LEGAL EFFECT", styles["callout"]) ]],
        colWidths=[6.6 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBEAEA")),
                ("BOX", (0, 0), (-1, -1), 0.8, NOTICE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def metadata_table(styles):
    rows = [
        ["Issuing body", "Office of Legislative Counsel, Commonwealth of Northbridge"],
        ["Instrument", "Model Legislative Instrument No. 14 of 2026"],
        ["Subject", "Public records integrity, retention, disclosure, and oversight"],
        ["Status", "Fictional sample prepared solely for PDF summarization testing"],
    ]
    table = Table(rows, colWidths=[1.35 * inch, 5.25 * inch])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.4),
                ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
                ("TEXTCOLOR", (1, 0), (1, -1), INK),
                ("BACKGROUND", (0, 0), (0, -1), BLUE_GRAY),
                ("GRID", (0, 0), (-1, -1), 0.45, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def document_map(styles):
    entries = [
        ("Part I", "Preliminary provisions and definitions"),
        ("Part II", "Records governance, retention, and preservation"),
        ("Part III", "Public access requests and decision procedures"),
        ("Part IV", "Exemptions, severability, and the public interest test"),
        ("Part V", "Independent oversight, enforcement, review, and reporting"),
        ("Schedules", "Retention periods and staged implementation milestones"),
    ]
    rows = [[paragraph("Division", styles["table_header"]), paragraph("Subject", styles["table_header"])]]
    rows.extend(
        [paragraph(left, styles["table"]), paragraph(right, styles["table"])]
        for left, right in entries
    )
    table = Table(rows, colWidths=[1.1 * inch, 5.5 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("BACKGROUND", (0, 1), (-1, -1), PALE_BLUE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def retention_table(styles):
    rows = [
        [
            paragraph("Record category", styles["table_header"]),
            paragraph("Minimum period", styles["table_header"]),
            paragraph("Trigger and disposition", styles["table_header"]),
        ],
        [
            paragraph("Primary legislation, regulations, and signed instruments", styles["table"]),
            paragraph("Permanent", styles["table"]),
            paragraph("Transfer a preservation copy and metadata to the State Archives after official publication.", styles["table"]),
        ],
        [
            paragraph("Final policy decisions and supporting briefing records", styles["table"]),
            paragraph("15 years", styles["table"]),
            paragraph("Period begins when the policy is superseded; archive records of enduring public value.", styles["table"]),
        ],
        [
            paragraph("Procurement awards, evaluations, and executed contracts", styles["table"]),
            paragraph("10 years", styles["table"]),
            paragraph("Period begins at contract completion or final resolution of a dispute, whichever is later.", styles["table"]),
        ],
        [
            paragraph("Financial ledgers, payment approvals, and audit workpapers", styles["table"]),
            paragraph("7 years", styles["table"]),
            paragraph("Period begins at the close of the relevant financial year, subject to any preservation hold.", styles["table"]),
        ],
        [
            paragraph("Routine administrative correspondence", styles["table"]),
            paragraph("3 years", styles["table"]),
            paragraph("Destroy securely after the period expires unless the record documents a material decision.", styles["table"]),
        ],
        [
            paragraph("Access requests, decisions, reviews, and complaint files", styles["table"]),
            paragraph("6 years", styles["table"]),
            paragraph("Period begins after the final decision, review, appeal, or enforcement proceeding concludes.", styles["table"]),
        ],
    ]
    table = Table(rows, colWidths=[2.25 * inch, 1.0 * inch, 3.35 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]),
                ("GRID", (0, 0), (-1, -1), 0.45, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def implementation_table(styles):
    rows = [
        [
            paragraph("Deadline after commencement", styles["table_header"]),
            paragraph("Required action", styles["table_header"]),
            paragraph("Responsible authority", styles["table_header"]),
        ],
        [
            paragraph("90 days", styles["table"]),
            paragraph("Designate a records officer and publish access-request contact details.", styles["table"]),
            paragraph("Each public body", styles["table"]),
        ],
        [
            paragraph("180 days", styles["table"]),
            paragraph("Approve a records governance plan and inventory high-risk record systems.", styles["table"]),
            paragraph("Each public body", styles["table"]),
        ],
        [
            paragraph("12 months", styles["table"]),
            paragraph("Apply minimum metadata standards to newly created digital records.", styles["table"]),
            paragraph("Chief Information Officer", styles["table"]),
        ],
        [
            paragraph("18 months", styles["table"]),
            paragraph("Complete the first independent compliance audit and remediation plan.", styles["table"]),
            paragraph("Information Commissioner", styles["table"]),
        ],
        [
            paragraph("24 months", styles["table"]),
            paragraph("Migrate legacy high-value records to approved preservation formats.", styles["table"]),
            paragraph("Public bodies and State Archives", styles["table"]),
        ],
    ]
    table = Table(rows, colWidths=[1.45 * inch, 3.65 * inch, 1.5 * inch], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]),
                ("GRID", (0, 0), (-1, -1), 0.45, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_document():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    styles = build_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.68 * inch,
        bottomMargin=0.58 * inch,
        title="Sample Public Records Integrity and Digital Access Act 2026",
        author="Fictional Commonwealth of Northbridge",
        subject="Law-related sample document for PDF summarization testing",
    )

    story = []

    story.append(Spacer(1, 0.14 * inch))
    story.append(paragraph("COMMONWEALTH OF NORTHBRIDGE", styles["subtitle"]))
    story.append(paragraph("PUBLIC RECORDS INTEGRITY<br/>AND DIGITAL ACCESS ACT 2026", styles["title"]))
    story.append(paragraph("Model Legislative Instrument No. 14 of 2026", styles["subtitle"]))
    story.append(sample_notice(styles))
    story.append(Spacer(1, 0.18 * inch))
    story.append(metadata_table(styles))
    story.append(Spacer(1, 0.16 * inch))
    story.append(paragraph("Purpose and scope", styles["section"]))
    story.append(
        paragraph(
            "This model Act establishes a government-wide framework for the creation, preservation, disclosure, and lawful disposal of public records. It is designed to protect evidence of official decisions while giving members of the public a practical right to obtain government information.",
            styles["body"],
        )
    )
    story.append(
        paragraph(
            "The instrument applies consistent duties to ministries, agencies, statutory authorities, and publicly controlled corporations. It also creates an independent Information Commissioner with powers to investigate complaints, conduct audits, and issue enforceable compliance notices.",
            styles["body"],
        )
    )
    story.append(paragraph("Document map", styles["section"]))
    story.append(document_map(styles))
    story.append(Spacer(1, 0.11 * inch))
    story.append(
        paragraph(
            "Testing note: each subsequent page focuses on a distinct legal topic so that a page-by-page summarizer can be evaluated for coverage, accuracy, and handling of defined terms.",
            styles["small"],
        )
    )
    story.append(PageBreak())

    add_part_page(
        story,
        styles,
        "I",
        "Preliminary Provisions",
        [
            (
                "1",
                "Short title",
                ["This model instrument may be cited as the <i>Public Records Integrity and Digital Access Act 2026</i>."],
            ),
            (
                "2",
                "Commencement",
                [
                    "The Act commences 60 days after publication. The Minister may set later commencement dates for specified technical obligations, but no extension may exceed 24 months from publication."
                ],
            ),
            (
                "3",
                "Application",
                [
                    "The Act applies to every ministry, department, executive agency, local authority, statutory body, court administration office, and corporation in which the Commonwealth holds a controlling interest. It does not apply to the private notes of an elected member unless those notes are placed in an official record system or relied on to make an administrative decision."
                ],
            ),
            (
                "4",
                "Definitions",
                [
                    "In this Act, <b>public record</b> means recorded information created, received, or maintained by a public body in the conduct of public business, regardless of format or location. <b>Digital record</b> includes email, database entries, messages used for official business, audiovisual files, machine-readable data, and associated metadata.",
                    "<b>Records officer</b> means the person designated under Section 7. <b>Preservation hold</b> means a direction suspending alteration or disposal because a record may be relevant to litigation, investigation, audit, access request, or historical appraisal."
                ],
            ),
            (
                "5",
                "Legal status of electronic records",
                [
                    "A record must not be denied legal effect solely because it is electronic. A reliable digital copy is admissible to the same extent as an original when its integrity, provenance, and chain of custody can be demonstrated."
                ],
            ),
            (
                "6",
                "Principles of interpretation",
                [
                    "Decision-makers must interpret this Act to favor accountable government, timely access, protection of legitimate confidential interests, preservation of evidence, and the use of proportionate administrative procedures. Any exemption from access must be construed narrowly."
                ],
            ),
        ],
    )
    story.append(PageBreak())

    add_part_page(
        story,
        styles,
        "II",
        "Records Governance and Preservation",
        [
            (
                "7",
                "Records governance plans",
                [
                    "Each public body must designate a senior records officer and approve a written governance plan. The plan must identify record systems, assign ownership, establish access controls, describe continuity arrangements, and provide a timetable for reviewing retention rules."
                ],
            ),
            (
                "8",
                "Minimum metadata",
                [
                    "A digital record that documents a material decision must retain its title, creator, date of creation, date of final action, responsible business unit, security classification, retention category, and any later alteration. Metadata must remain linked to the record during migration or transfer."
                ],
            ),
            (
                "9",
                "Retention and archival transfer",
                [
                    "A public body must retain records for at least the periods stated in Schedule 1. When a record has enduring legal, historical, fiscal, or cultural value, the State Archivist may direct permanent retention or transfer to the State Archives."
                ],
            ),
            (
                "10",
                "Preservation holds",
                [
                    "The records officer must issue a preservation hold when litigation, investigation, audit, or an access request is reasonably anticipated. A hold overrides any scheduled disposal and remains in force until written release by the authority that requested it."
                ],
            ),
            (
                "11",
                "Secure disposal",
                [
                    "Records may be destroyed only under an approved disposal authority and after confirming that no preservation hold applies. Disposal must prevent reconstruction of protected information and must be documented by date, category, volume, method, and approving officer."
                ],
            ),
            (
                "12",
                "Annual certification",
                [
                    "The head of each public body must certify annually that recordkeeping controls were tested, unauthorized destruction incidents were investigated, required corrective actions were tracked, and staff with recordkeeping duties completed appropriate training. The certification must be published, subject to lawful redaction."
                ],
            ),
        ],
    )
    story.append(PageBreak())

    add_part_page(
        story,
        styles,
        "III",
        "Public Access to Records",
        [
            (
                "13",
                "Right of access",
                [
                    "Every person has a right to obtain a public record held by a public body unless access is refused under Part IV. A requester need not be a citizen, state an interest, or explain the intended use of the information."
                ],
            ),
            (
                "14",
                "Making a request",
                [
                    "A request may be submitted electronically, by post, or in person. It must reasonably describe the record or subject matter sought and provide a means for communicating with the requester. A public body may not reject a request merely because the requester does not cite this Act."
                ],
            ),
            (
                "15",
                "Duty to assist",
                [
                    "The public body must take reasonable steps to help a requester clarify scope, identify relevant offices, reduce unnecessary cost, and obtain records in an accessible form. When another public body is more likely to hold the record, the request must be transferred promptly with notice to the requester."
                ],
            ),
            (
                "16",
                "Acknowledgment and search",
                [
                    "Receipt must be acknowledged within five working days. The acknowledgment must identify a tracking number, contact officer, estimated decision date, and any clarification needed. Searches must cover locations where responsive records are reasonably likely to exist, including approved archives and official messaging systems."
                ],
            ),
            (
                "17",
                "Decision period",
                [
                    "A decision must be issued within 20 working days after receipt or clarification. One extension of not more than 15 working days is permitted for unusually voluminous records, consultation with third parties, or retrieval from remote storage. The reasons and revised deadline must be given in writing."
                ],
            ),
            (
                "18",
                "Fees",
                [
                    "No fee may be charged for the first two hours of search and review or for electronic delivery. Additional charges must reflect actual reasonable reproduction or retrieval costs. Fees must be waived when disclosure is likely to materially advance public understanding of government operations and is not primarily commercial."
                ],
            ),
            (
                "19",
                "Form of access",
                [
                    "Records must be provided in the requested format when reasonably practicable, including a machine-readable format for structured data. Public bodies must provide accessible alternatives for persons with disabilities and may protect original records by supplying certified copies."
                ],
            ),
        ],
    )
    story.append(PageBreak())

    add_part_page(
        story,
        styles,
        "IV",
        "Exemptions and the Public Interest",
        [
            (
                "20",
                "General rule for exemptions",
                [
                    "A public body may withhold information only when a specific exemption applies and the reasonably foreseeable harm from disclosure outweighs the public interest in access. The decision must identify the exemption, explain the anticipated harm, and state the available review rights."
                ],
            ),
            (
                "21",
                "Personal privacy",
                [
                    "Information may be withheld when disclosure would constitute an unreasonable invasion of personal privacy. Relevant factors include sensitivity, consent, prior publication, the person's public role, and whether disclosure would reveal how public duties were performed or public money was used."
                ],
            ),
            (
                "22",
                "Security and law enforcement",
                [
                    "Information may be withheld when disclosure would reasonably be expected to endanger a person, compromise critical infrastructure, reveal confidential investigative methods, prejudice an active proceeding, or facilitate evasion of the law. General embarrassment or speculative risk is insufficient."
                ],
            ),
            (
                "23",
                "Legal privilege and deliberative material",
                [
                    "A record protected by legal professional privilege may be withheld. Predecisional advice may also be withheld when disclosure would materially inhibit candid deliberation, but purely factual material, final reasons, adopted policy, and instructions governing decisions must be disclosed unless another exemption applies."
                ],
            ),
            (
                "24",
                "Commercial and confidential information",
                [
                    "Trade secrets and confidential commercial information may be withheld when disclosure would cause substantial competitive harm or impair the government's ability to obtain necessary information. Contract prices, performance findings, and the expenditure of public funds are not confidential merely because a supplier prefers secrecy."
                ],
            ),
            (
                "25",
                "Severability and partial access",
                [
                    "When exempt information can reasonably be separated, the remainder of the record must be released. Redactions must be limited to the protected material and, where practicable, marked with the legal basis for each deletion."
                ],
            ),
            (
                "26",
                "Public interest override",
                [
                    "Except for information whose disclosure is prohibited by another law or would create a serious and imminent threat to safety, access must be granted when the public interest in exposing corruption, serious misconduct, significant environmental risk, or a substantial threat to public health clearly outweighs the protected interest."
                ],
            ),
        ],
    )
    story.append(PageBreak())

    add_part_page(
        story,
        styles,
        "V",
        "Oversight, Enforcement, and Review",
        [
            (
                "27",
                "Information Commissioner",
                [
                    "An independent Information Commissioner is established for a single seven-year term. The Commissioner controls the Office's staffing and investigations and may not receive direction from a minister concerning a particular request, complaint, audit, or enforcement matter."
                ],
            ),
            (
                "28",
                "Complaints",
                [
                    "A person may complain about delay, inadequate search, excessive fees, refusal of access, inaccessible format, or failure to preserve a requested record. The Commissioner may resolve a matter informally or issue a written determination after giving affected parties an opportunity to respond."
                ],
            ),
            (
                "29",
                "Audit powers",
                [
                    "The Commissioner may conduct scheduled or risk-based audits, inspect record systems, require production of policies and logs, interview responsible officers, and test compliance controls. Privileged material must be protected from further disclosure while allowing verification of the privilege claim."
                ],
            ),
            (
                "30",
                "Compliance notices",
                [
                    "When a material breach is found, the Commissioner may issue a notice requiring corrective action by a stated date. A notice may require restoration of records, suspension of disposal, improvement of search procedures, staff training, repayment of improper fees, or reconsideration of an access decision."
                ],
            ),
            (
                "31",
                "Administrative and judicial review",
                [
                    "A requester or affected third party may seek administrative review within 30 days of a determination. A final administrative decision may be appealed to the Administrative Court on a question of law or for material procedural unfairness. The public body bears the burden of justifying nondisclosure."
                ],
            ),
            (
                "32",
                "Offenses",
                [
                    "A person commits an offense by knowingly destroying, concealing, falsifying, or removing a public record with intent to defeat this Act, an audit, or a lawful proceeding. Good-faith errors and actions taken under an apparently valid disposal authority are not offenses."
                ],
            ),
            (
                "33",
                "Protected disclosures",
                [
                    "An employee who reports suspected unlawful destruction, concealment, or falsification to the records officer, Commissioner, Auditor-General, or law enforcement is protected from retaliation when the report is made on reasonable grounds."
                ],
            ),
            (
                "34",
                "Annual public report",
                [
                    "The Commissioner must publish statistics on requests, response times, refusals, exemptions, fees, complaints, audit findings, compliance notices, and unresolved systemic risks. Data must be presented by public body and in a reusable machine-readable format."
                ],
            ),
        ],
    )
    story.append(PageBreak())

    story.append(paragraph("SCHEDULE 1", styles["part"]))
    story.append(paragraph("MINIMUM RETENTION PERIODS", styles["part"]))
    story.append(
        paragraph(
            "The following periods are minimum requirements. A longer period applies when another law, a preservation hold, an archival direction, or an approved sector schedule requires it.",
            styles["body"],
        )
    )
    story.append(retention_table(styles))
    story.append(Spacer(1, 0.16 * inch))
    story.append(paragraph("SCHEDULE 2", styles["part"]))
    story.append(paragraph("IMPLEMENTATION MILESTONES", styles["part"]))
    story.append(implementation_table(styles))
    story.append(Spacer(1, 0.13 * inch))
    story.append(paragraph("Drafting certification", styles["section"]))
    story.append(
        paragraph(
            "This fictional sample was prepared as a structured test input for an English-language PDF summarization system. Names, institutions, legal duties, dates, and instrument numbers are invented. No person should rely on this document as law, legal advice, or evidence of government policy.",
            styles["body"],
        )
    )

    doc.build(story, onFirstPage=draw_page_frame, onLaterPages=draw_page_frame)

    reader = PdfReader(str(OUTPUT_PATH))
    if len(reader.pages) != TOTAL_PAGES:
        raise RuntimeError(f"Expected {TOTAL_PAGES} pages, generated {len(reader.pages)}")

    extracted_characters = sum(len(page.extract_text() or "") for page in reader.pages)
    print(f"Created: {OUTPUT_PATH}")
    print(f"Pages: {len(reader.pages)}")
    print(f"Extracted characters: {extracted_characters}")


if __name__ == "__main__":
    build_document()
