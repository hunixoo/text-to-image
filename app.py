from flask import Flask, request, send_file
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
import os

app = Flask(__name__)
CORS(app)

FONT_PATH = "fonts/Roboto-Regular.ttf"


@app.route('/invoice', methods=['POST'])
def render_invoice():
    try:
        data = request.json
        lines = data.get('lines', ['Hóa đơn mẫu'])
        font_size = data.get('font_size', 28)
        qr_data = data.get('qr_data', None)

        try:
            font = ImageFont.truetype(FONT_PATH, font_size)
        except:
            print("⚠️ Font không tồn tại, dùng mặc định")
            font = ImageFont.load_default()

        # Kích thước khung in
        width = 384
        height = 100 + len(lines) * (font_size + 10) + (150 if qr_data else 0)
        img = Image.new("1", (width, height), color=1)
        draw = ImageDraw.Draw(img)

        y = 10

        # Vẽ từng dòng
        for line in lines:
            w, h = draw.textsize(line, font=font)
            draw.text(((width - w) / 2, y), line, font=font, fill=0)
            y += h + 5

        # Mã QR
        if qr_data:
            qr = qrcode.make(qr_data)
            qr = qr.resize((120, 120)).convert("1")
            img.paste(qr, (int((width - 120) / 2), y))
            y += 130

        # Cắt lại chiều cao thực tế
        img = img.crop((0, 0, width, y + 10))

        # Trả về ảnh
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return send_file(buf, mimetype='image/png')

    except Exception as e:
        print("🔥 Lỗi khi tạo hóa đơn:", e)
        return f"Lỗi server: {str(e)}", 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
