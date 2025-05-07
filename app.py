from flask import Flask, request, send_file
import fitz  # PyMuPDF
from flask_cors import CORS
from io import BytesIO

app = Flask(__name__)
CORS(app)  # Allow frontend to access backend

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    pdf_bytes = file.read()
    input_pdf = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Odd pages go on front (1,3,5...), even pages on back (2,4,6...)
    odd_pages = [i for i in range(input_pdf.page_count) if (i + 1) % 2 == 1]
    even_pages = [i for i in range(input_pdf.page_count) if (i + 1) % 2 == 0]

    output_pdf = fitz.open()
    max_len = max(len(odd_pages), len(even_pages))

    for i in range(0, max_len, 9):
        # Create front side (odd pages)
        front_pages = odd_pages[i:i+9]
        front_page = output_pdf.new_page(width=595, height=842)  # A4 size in points
        for idx, page_num in enumerate(front_pages):
            row = idx // 3
            col = idx % 3
            pix = input_pdf[page_num].get_pixmap(dpi=150)
            img_rect = fitz.Rect(col * 198.33, row * 280.66,
                                 (col + 1) * 198.33, (row + 1) * 280.66)
            front_page.insert_image(img_rect, pixmap=pix)

        # Create back side (even pages)
        back_pages = even_pages[i:i+9]
        if back_pages:  # Only create if we have even pages left
            back_page = output_pdf.new_page(width=595, height=842)
            for idx, page_num in enumerate(back_pages):
                row = idx // 3
                col = idx % 3
                pix = input_pdf[page_num].get_pixmap(dpi=150)
                img_rect = fitz.Rect(col * 198.33, row * 280.66,
                                     (col + 1) * 198.33, (row + 1) * 280.66)
                back_page.insert_image(img_rect, pixmap=pix)

    # Return downloadable file
    output_stream = BytesIO()
    output_pdf.save(output_stream)
    output_pdf.close()
    output_stream.seek(0)
    return send_file(output_stream, mimetype='application/pdf', as_attachment=True, download_name='rearranged_duplex.pdf')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
