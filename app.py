import os
from flask import Flask, request, send_file, send_from_directory
from flask_cors import CORS
from io import BytesIO
import fitz  # PyMuPDF
import traceback

app = Flask(__name__, static_folder=".")
CORS(app)  # Enable CORS for frontend access

# Optional: limit uploads to 20MB
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return 'No file part', 400

        file = request.files['file']
        if file.filename == '':
            return 'No selected file', 400

        if not file.filename.lower().endswith('.pdf'):
            return 'Uploaded file is not a PDF', 400

        # Check for file size limit
        if len(file.read()) > 20 * 1024 * 1024:  # 20MB limit
            return 'File size exceeds 20MB', 400
        file.seek(0)  # Reset the file pointer

        pdf_bytes = file.read()
        input_pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

        if input_pdf.page_count == 0:
            return 'Uploaded PDF has no pages', 400

        print(f"PDF has {input_pdf.page_count} pages.")

        # Split odd and even pages
        odd_pages = [i for i in range(input_pdf.page_count) if (i + 1) % 2 == 1]
        even_pages = [i for i in range(input_pdf.page_count) if (i + 1) % 2 == 0]

        output_pdf = fitz.open()
        max_len = max(len(odd_pages), len(even_pages))

        for i in range(0, max_len, 9):
            # Front (odd) pages
            front_pages = odd_pages[i:i + 9]
            front_page = output_pdf.new_page(width=595, height=842)  # A4
            for idx, page_num in enumerate(front_pages):
                row = idx // 3
                col = idx % 3
                pix = input_pdf[page_num].get_pixmap(dpi=150)
                img_rect = fitz.Rect(col * 198.33, row * 280.66,
                                     (col + 1) * 198.33, (row + 1) * 280.66)
                front_page.insert_image(img_rect, pixmap=pix)
                print(f"Inserted odd page {page_num + 1} at position ({row}, {col})")

            # Back (even) pages
            back_pages = even_pages[i:i + 9]
            if back_pages:
                back_page = output_pdf.new_page(width=595, height=842)
                for idx, page_num in enumerate(back_pages):
                    row = idx // 3
                    col = idx % 3
                    pix = input_pdf[page_num].get_pixmap(dpi=150)
                    img_rect = fitz.Rect(col * 198.33, row * 280.66,
                                         (col + 1) * 198.33, (row + 1) * 280.66)
                    back_page.insert_image(img_rect, pixmap=pix)
                    print(f"Inserted even page {page_num + 1} at position ({row}, {col})")

        # Return file
        output_stream = BytesIO()
        output_pdf.save(output_stream)
        output_pdf.close()
        output_stream.seek(0)

        print("PDF processing complete. Sending file.")
        return send_file(output_stream, mimetype='application/pdf',
                         as_attachment=True, download_name='rearranged_duplex.pdf', cache_timeout=0)

    except Exception as e:
        traceback.print_exc()
        return f"Server Error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
