from docx import Document
from docx.shared import Inches


def generate_docx(
    report_title,
    brand_title,
    date_str,
    keywords,
    articles,
    out_path
):
    doc = Document()

    # ---- HEADER ----
    doc.add_heading(report_title, level=1)
    doc.add_paragraph(f"Brand / Subject: {brand_title}")
    doc.add_paragraph(f"Report Date: {date_str}")

    if keywords:
        doc.add_paragraph(f"Keywords Searched: {', '.join(keywords)}")

    doc.add_paragraph("")

    # ---- SUMMARY ----
    total_articles = len(articles)
    flagged_articles = [
        a for a in articles
        if a.get("author_flag") != "Named Author" or a.get("marked_ai")
    ]

    doc.add_heading("Summary", level=2)
    doc.add_paragraph(f"Total articles included: {total_articles}")
    doc.add_paragraph(
        f"Articles with authorship concerns: {len(flagged_articles)}"
    )

    doc.add_paragraph("")

    # ---- TABLE ----
    table = doc.add_table(rows=1, cols=6)
    table.style = "Table Grid"

    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Date"
    hdr_cells[1].text = "Title"
    hdr_cells[2].text = "Source"
    hdr_cells[3].text = "Author"
    hdr_cells[4].text = "Authorship Status"
    hdr_cells[5].text = "URL"

    for a in articles:
        row = table.add_row().cells

        row[0].text = a.get("date", "")
        row[1].text = a.get("title", "")
        row[2].text = a.get("source", "")
        row[3].text = a.get("author", "") or "—"

        status = a.get("author_flag", "Unknown")
        if a.get("marked_ai"):
            status += " (Manually flagged)"

        row[4].text = status
        row[5].text = a.get("url", "")

    doc.save(out_path)
