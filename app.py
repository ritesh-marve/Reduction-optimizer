import os
import io
import fitz  # PyMuPDF
from flask import Flask, request, send_file, abort, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow all origins (adjust as needed)

import logging
from logging.handlers import RotatingFileHandler
import sys

# Logging to console (Render dashboard)
app.logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
app.logger.addHandler(console_handler)

# Logging to file (rotating file handler)
log_file = "server.log"
file_handler = RotatingFileHandler(log_file, maxBytes=100000, backupCount=3)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
file_handler.setFormatter(file_formatter)
app.logger.addHandler(file_handler)

app.logger.info("App has started and logging is configured.")


# Limit max upload to 20 MB (optional)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 MB

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Serve index.html from the current directory
    return send_from_directory(os.getcwd(), 'index.html')

@app.route('/convert', methods=['POST'])
def convert_pdf():
    # Check file part
    if 'file' not in request.files:
        return abort(400, 'No file part')
    
    file = request.files['file']
    
    if file.filename == '' or not allowed_file(file.filename):
        return abort(400, 'Invalid file')

    # Read PDF from the uploaded file
    pdf_bytes = file.read()
    
    try:
        src_pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        return abort(400, f'Cannot open PDF: {e}')

    # Prepare output PDF
    output_pdf = fitz.open()

    # Define output page size (e.g. A4 in points: 595×842)
    # For a 3×3 grid, using landscape to fit 9 portrait pages
    page_width, page_height = 842, 595  # landscape A4 (rotated 90°)
    cols, rows = 3, 3
    per_page = cols * rows

    for i in range(src_pdf.page_count):
        if i % per_page == 0:
            # Start a new output page
            page = output_pdf.new_page(width=page_width, height=page_height)
            # Make a grid of 3×3 boxes with 1/72" margins
            cells = fitz.make_table(page.rect, cols=cols, rows=rows)

        # Compute which box to place this page in
        box = cells[i % per_page]
        # Insert the source page (scaled to fit) into the cell
        # `overlay=False` puts it under any existing content, but order doesn't matter here
        page.show_pdf_page(box, src_pdf, i, keep_proportion=True)

    # Duplex support: if total pages odd, add a blank page to make count even
    if output_pdf.page_count % 2 != 0:
        output_pdf.new_page(width=page_width, height=page_height)

    # Save to a BytesIO and send as response
    out_bytes = io.BytesIO()
    output_pdf.save(out_bytes)
    output_pdf.close()
    out_bytes.seek(0)  # rewind after writing

    return send_file(out_bytes,
                     mimetype='application/pdf',
                     as_attachment=True,
                     download_name='converted.pdf')

# Optional: log to Render dashboard
import logging, sys
app.logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
app.logger.addHandler(handler)
app.logger.info("App has started.")
