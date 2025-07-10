from flask import Flask, request, send_file, Response
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
    data = request.json
    lines = data.get('lines', ['Hóa đơn mẫu'])
    font_size = data.get('font_size', 28)
    qr_data = data.get('qr_data', None)

    # Load font
    font = ImageFont.truetype(FONT_PATH, font_size)

    width = 384  # in pixel, 58mm giấy
    height = 100 + len(lines) * (font_size + 10) + (160 if qr_data else 0)
    img = Image.new("1", (width, height), color=1)  # 1-bit image
    draw = ImageDraw.Draw(img)

    y = 10
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        draw.text(((width - w) / 2, y), line, font=font, fill=0)
        y += h + 5

    if qr_data:
        qr = qrcode.make(qr_data).resize((120, 120)).convert("1")
        img.paste(qr, ((width - 120) // 2, y))
        y += 130

    img = img.crop((0, 0, width, y + 10))

    escpos_data = image_to_raster_escpos(img)
    return Response(escpos_data, mimetype='application/octet-stream')


def image_to_raster_escpos(img: Image.Image) -> bytes:
    img = img.convert('1')  # chuyển ảnh về 1-bit B/W
    width, height = img.size
    width_bytes = (width + 7) // 8
    data = bytearray()

    # Header: GS v 0
    data += b'\x1D\x76\x30\x00'  # GS v 0 m=0
    data += bytes([width_bytes % 256, width_bytes // 256])
    data += bytes([height % 256, height // 256])

    for y in range(height):
        for x_byte in range(width_bytes):
            byte = 0x00
            for bit in range(8):
                x = x_byte * 8 + bit
                if x < width:
                    pixel = img.getpixel((x, y))
                    if pixel == 0:
                        byte |= (1 << (7 - bit))
            data.append(byte)

    # Thêm line feed và cut
    data += b'\x0A\x0A\x1D\x56\x00'
    return bytes(data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
