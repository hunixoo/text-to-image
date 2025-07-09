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

    font = ImageFont.truetype(FONT_PATH, font_size)

    width = 384  # in pixel, 58mm giấy
    height = 100 + len(lines) * (font_size + 10) + (150 if qr_data else 0)
    img = Image.new("1", (width, height), color=1)
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
        img.paste(qr, (int((width - 120) / 2), y))
        y += 130

    img = img.crop((0, 0, width, y + 10))

    escpos_data = image_to_escpos(img)
    return Response(escpos_data, mimetype='application/octet-stream')


def image_to_escpos(image: Image.Image) -> bytes:
    image = image.convert("1")  # Ensure 1-bit mode
    width, height = image.size
    data = bytearray()

    for y in range(0, height, 24):
        # ESC * m nL nH : m=33 (24-dot double density)
        data += b'\x1B*\x21'
        nL = width & 0xFF
        nH = (width >> 8) & 0xFF
        data += bytes([nL, nH])

        for x in range(width):
            for k in range(3):  # 3 bytes per column (24 pixels)
                byte = 0x00
                for b in range(8):
                    yy = y + k * 8 + b
                    if yy >= height:
                        continue
                    pixel = image.getpixel((x, yy))
                    if pixel == 0:  # black pixel
                        byte |= (1 << (7 - b))
                data.append(byte)

        data += b'\x0A'  # line feed after each band

    data += b'\x0A\x0A\x1D\x56\x00'  # feed and full cut
    return bytes(data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
