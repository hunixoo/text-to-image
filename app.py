from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import qrcode
import os
import traceback

app = Flask(__name__)
CORS(app, expose_headers=['X-Image-Width', 'X-Image-Height'])

# Font đường dẫn
FONT_PATH_REGULAR = os.path.join(os.path.dirname(__file__), "fonts", "Roboto-Regular.ttf")
FONT_PATH_BOLD = os.path.join(os.path.dirname(__file__), "fonts", "Roboto-Bold.ttf")


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

        if not isinstance(data, dict):
            return jsonify({"error": "Dữ liệu không hợp lệ: không phải dict"}), 400

        lines = data.get('lines')
        if not lines or not isinstance(lines, list):
            return jsonify({"error": "Thiếu 'lines' hoặc không phải danh sách"}), 400

        base_font_size = data.get('font_size', 28)
        qr_data = data.get('qr_data', None)

        try:
            font_regular = ImageFont.truetype(FONT_PATH_REGULAR, base_font_size)
            font_bold = ImageFont.truetype(FONT_PATH_BOLD, base_font_size)
        except IOError:
            return jsonify({"error": "Không tìm thấy font Roboto"}), 500

        width = 384
        # estimated_height = 100 + len(lines) * (base_font_size + 10) + (240 if qr_data else 0)
        estimated_height = 2400
        img = Image.new("1", (width, estimated_height), color=1)
        draw = ImageDraw.Draw(img)

        y = 10
        for item in lines:
            if isinstance(item, str):
                item = {"text": item}

            size = item.get("size", base_font_size)
            bold = item.get("bold", False)
            font = ImageFont.truetype(FONT_PATH_BOLD if bold else FONT_PATH_REGULAR, size)

            if 'columns' in item:
                x = 0
                max_height = 0
                for col in item['columns']:
                    col_text = str(col.get("text", ""))
                    col_align = col.get("align", "left")
                    col_width = col.get("width", 100)

                    bbox = draw.textbbox((0, 0), col_text, font=font)
                    col_text_width = bbox[2] - bbox[0]
                    col_text_height = bbox[3] - bbox[1]

                    if col_align == "center":
                        text_x = x + (col_width - col_text_width) / 2
                    elif col_align == "right":
                        text_x = x + col_width - col_text_width
                    else:  # left
                        text_x = x

                    draw.text((text_x, y), col_text, font=font, fill=0)
                    x += col_width
                    max_height = max(max_height, col_text_height)

                y += max_height + 5

            else:
                text = str(item.get("text", ""))
                align = item.get("align", "center")
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                if align == "center":
                    x = (width - text_width) / 2
                elif align == "right":
                    x = width - text_width - 10
                else:
                    x = 10

                draw.text((x, y), text, font=font, fill=0)
                y += text_height + 5

        if qr_data:
            y += 20
            qr_size = 180
            qr_img = qrcode.make(str(qr_data)).resize((qr_size, qr_size)).convert("1")
            qr_x = (width - qr_size) // 2
            img.paste(qr_img, (qr_x, y))
            y += qr_size + 20

        final_height = y + 20
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
