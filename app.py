from flask import Flask, request, send_file
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
import os

app = Flask(__name__)
CORS(app)

FONT_PATH = "fonts/Roboto-Regular.ttf"
LOGO_PATH = "static/logo.png"


@app.route('/invoice', methods=['POST'])
def render_invoice():
    data = request.json
    lines = data.get('lines', ['Hóa đơn mẫu'])
    font_size = data.get('font_size', 28)
    include_logo = data.get('include_logo', True)
    qr_data = data.get('qr_data', 'https://example.com')

    font = ImageFont.truetype(FONT_PATH, font_size)

    # Tạo vùng văn bản
    width = 384  # Chiều rộng máy in 58mm (pixels)
    height = 100 + len(lines) * (font_size + 10) + 150  # Tùy biến chiều cao
    img = Image.new("1", (width, height), color=1)  # 1-bit (B/W)
    draw = ImageDraw.Draw(img)

    y = 10

    # Vẽ logo
    # if include_logo and os.path.exists(LOGO_PATH):
    #     logo = Image.open(LOGO_PATH).convert("1")
    #     logo = logo.resize((100, 100))
    #     img.paste(logo, (int((width - 100) / 2), y))
    #     y += 110

    # Vẽ các dòng text
    for line in lines:
        w, h = draw.textsize(line, font=font)
        draw.text(((width - w) / 2, y), line, font=font, fill=0)
        y += h + 5

    # Vẽ mã QR
    if qr_data:
        qr = qrcode.make(qr_data)
        qr = qr.resize((120, 120)).convert("1")
        img.paste(qr, (int((width - 120) / 2), y))
        y += 130

    # Cắt vùng ảnh thực tế
    img = img.crop((0, 0, width, y + 10))

    # Trả ảnh
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
