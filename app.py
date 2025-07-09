from flask import Flask, request, send_file, Response
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import qrcode
import io
import os

app = Flask(__name__)
CORS(app)


def get_font(size=28):
    """Tìm font phù hợp cho hệ thống"""
    font_paths = "fonts/Roboto-Regular.ttf"

    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue

    # Fallback to default font
    return ImageFont.load_default()


@app.route('/invoice', methods=['POST'])
def render_invoice():
    try:
        data = request.json
        lines = data.get('lines', ['Hóa đơn mẫu'])
        font_size = data.get('font_size', 24)
        qr_data = data.get('qr_data', None)

        # Đảm bảo lines là list
        if isinstance(lines, str):
            lines = [lines]

        font = get_font(font_size)

        width = 384  # 58mm paper in pixels

        # Tính toán chiều cao cần thiết
        temp_img = Image.new("1", (width, 100), color=1)
        temp_draw = ImageDraw.Draw(temp_img)

        total_height = 20  # Margin top
        line_heights = []

        for line in lines:
            # Xử lý text wrapping cho dòng dài
            wrapped_lines = wrap_text(line, font, width - 20, temp_draw)
            for wrapped_line in wrapped_lines:
                bbox = temp_draw.textbbox((0, 0), wrapped_line, font=font)
                line_height = bbox[3] - bbox[1]
                line_heights.append((wrapped_line, line_height))
                total_height += line_height + 5

        # Thêm khoảng trống cho QR code
        if qr_data:
            total_height += 140

        total_height += 20  # Margin bottom

        # Tạo image chính
        img = Image.new("1", (width, total_height), color=1)
        draw = ImageDraw.Draw(img)

        # Vẽ từng dòng
        y = 10
        for line_text, line_height in line_heights:
            bbox = draw.textbbox((0, 0), line_text, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2  # Center align
            draw.text((x, y), line_text, font=font, fill=0)
            y += line_height + 5

        # Thêm QR code nếu có
        if qr_data:
            y += 10
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=3,
                border=1,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((120, 120)).convert("1")

            qr_x = (width - 120) // 2
            img.paste(qr_img, (qr_x, y))

        # Chuyển đổi sang ESC/POS
        escpos_data = image_to_escpos(img)

        return Response(escpos_data, mimetype='application/octet-stream')

    except Exception as e:
        return {'error': str(e)}, 500


def wrap_text(text, font, max_width, draw):
    """Chia nhỏ text dài thành nhiều dòng"""
    words = text.split(' ')
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Từ quá dài, cắt từng ký tự
                lines.append(word)

    if current_line:
        lines.append(' '.join(current_line))

    return lines if lines else [text]


def image_to_escpos(image: Image.Image) -> bytes:
    """Chuyển đổi image thành ESC/POS commands"""
    image = image.convert("1")
    width, height = image.size
    data = bytearray()

    # ESC/POS initialization
    data += b'\x1B\x40'  # Initialize printer
    data += b'\x1B\x61\x01'  # Center align

    # In theo từng khối 24 pixel chiều cao
    for y in range(0, height, 24):
        # ESC * m nL nH - Bit image mode
        data += b'\x1B\x2A\x21'  # 24-dot single-density

        nL = width & 0xFF
        nH = (width >> 8) & 0xFF
        data += bytes([nL, nH])

        for x in range(width):
            for k in range(3):  # 3 bytes cho 24 dots
                byte = 0x00
                for b in range(8):
                    y_offset = y + k * 8 + b
                    if y_offset < height:
                        pixel = image.getpixel((x, y_offset))
                        if pixel == 0:  # Black pixel
                            byte |= (1 << (7 - b))
                data.append(byte)

        data += b'\x0A'  # Line feed

    # Kết thúc
    data += b'\x0A\x0A\x0A'  # Feed paper
    data += b'\x1D\x56\x00'  # Cut paper (full cut)

    return bytes(data)


@app.route('/test', methods=['GET'])
def test_endpoint():
    """Endpoint test để kiểm tra server"""
    return {'status': 'ok', 'message': 'Server đang chạy'}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
