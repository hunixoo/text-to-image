from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import qrcode
import os
import traceback

app = Flask(__name__)
CORS(app, expose_headers=['X-Image-Width', 'X-Image-Height'])

FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "Roboto-Regular.ttf")

def image_to_raw_raster_bytes(img: Image.Image) -> bytes:
    img = img.convert('1')
    width, height = img.size
    width_bytes = (width + 7) // 8
    raster_data = bytearray()

    for y in range(height):
        for x_byte in range(width_bytes):
            byte = 0x00
            for bit in range(8):
                x = x_byte * 8 + bit
                if x < width:
                    pixel = img.getpixel((x, y))
                    if pixel == 0:
                        byte |= (1 << (7 - bit))
            raster_data.append(byte)
    return bytes(raster_data)


@app.route('/invoice', methods=['POST'])
def render_invoice():
    try:
        if not request.is_json:
            return jsonify({"error": "Nội dung gửi lên không phải JSON"}), 400

        data = request.get_json(force=True)

        # Kiểm tra đầu vào
        if not isinstance(data, dict):
            return jsonify({"error": "Dữ liệu không hợp lệ: không phải dict"}), 400

        lines = data.get('lines')
        if not lines or not isinstance(lines, list):
            return jsonify({"error": "Thiếu 'lines' hoặc không phải danh sách"}), 400

        font_size = data.get('font_size', 28)
        qr_data = data.get('qr_data', None)

        # Load font
        try:
            font = ImageFont.truetype(FONT_PATH, font_size)
        except IOError:
            return jsonify({"error": "Không tìm thấy font Roboto-Regular.ttf"}), 500

        width = 384
        estimated_height = 100 + len(lines) * (font_size + 10) + (160 if qr_data else 0)
        img = Image.new("1", (width, estimated_height), color=1)
        draw = ImageDraw.Draw(img)

        y = 10
        for line in lines:
            line = str(line)  # Đảm bảo là chuỗi
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            draw.text(((width - text_width) / 2, y), line, font=font, fill=0)
            y += text_height + 5

        if qr_data:
            y += 10
            qr_img = qrcode.make(str(qr_data)).resize((120, 120)).convert("1")
            img.paste(qr_img, ((width - 120) // 2, y))
            y += 120

        final_height = y + 10
        final_img = img.crop((0, 0, width, final_height))
        raw_image_data = image_to_raw_raster_bytes(final_img)

        response = Response(raw_image_data, mimetype='application/octet-stream')
        response.headers['X-Image-Width'] = str(final_img.width)
        response.headers['X-Image-Height'] = str(final_img.height)
        return response

    except Exception as e:
        print("Lỗi server:", traceback.format_exc())
        return jsonify({"error": f"Đã xảy ra lỗi server: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
