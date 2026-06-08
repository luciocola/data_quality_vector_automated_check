"""Report export utilities for Data Quality Check for Vectors."""

import json
import os
from qgis.PyQt.QtGui import QTextDocument
from qgis.PyQt.QtPrintSupport import QPrinter


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def export_report_json(out_dir, base_name, payload):
    _ensure_dir(out_dir)
    path = os.path.join(out_dir, base_name + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def export_report_html(out_dir, base_name, report_text, payload):
    _ensure_dir(out_dir)
    path = os.path.join(out_dir, base_name + ".html")
    html = [
        "<html><head><meta charset='utf-8'><title>Data Quality Report</title></head><body>",
        "<h1>Data Quality Validation Report</h1>",
        "<p><b>Profile:</b> {}</p>".format(payload.get("profile", "default")),
        "<pre style='white-space: pre-wrap; font-family: monospace;'>{}</pre>".format(
            report_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ),
        "</body></html>",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(html))
    return path


def export_report_pdf(out_dir, base_name, report_text, payload):
    _ensure_dir(out_dir)
    path = os.path.join(out_dir, base_name + ".pdf")
    doc = QTextDocument()
    html = (
        "<h1>Data Quality Validation Report</h1>"
        + "<p><b>Profile:</b> {}</p>".format(payload.get("profile", "default"))
        + "<pre style='white-space: pre-wrap; font-family: monospace;'>{}</pre>".format(
            report_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
    )
    doc.setHtml(html)

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(path)
    doc.print_(printer)
    return path
