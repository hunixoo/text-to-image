# server.py

from flask import Flask, request, Response
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
import qrcode
import os

app = Flask(__name__)
# Cho phép client truy cập các header tùy chỉnh
CORS(app, expose_headers=['X-Image-Width', 'X-Image-Height'])

# Giả sử font nằm trong thư mục con 'fonts'
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "Roboto-Regular.ttf")


def image_to_raw_raster_bytes(img: Image.Image) -> bytes:
    """
    Chuyển đổi ảnh PIL 1-bit thành dữ liệu raster thô.
    Mỗi byte đại diện cho 8 pixel.
    """
    img = img.convert('1')  # Đảm bảo ảnh là 1-bit
    width, height = img.size
    width_bytes = (width + 7) // 8

    # Tạo một mảng byte để chứa dữ liệu raster
    raster_data = bytearray()

    for y in range(height):
        for x_byte in range(width_bytes):
            byte = 0x00
            for bit in range(8):
                x = x_byte * 8 + bit
                if x < width:
                    # Lấy pixel, 0 là đen, 255 là trắng
                    pixel = img.getpixel((x, y))
                    if pixel == 0:  # Pixel màu đen
                        byte |= (1 << (7 - bit))
            raster_data.append(byte)

    return bytes(raster_data)


@app.route('/invoice', methods=['POST'])
def render_invoice():
    try:
        data = request.json
        lines = data.get('lines', ['Hóa đơn mẫu'])
        font_size = data.get('font_size', 28)
        qr_data = data.get('qr_data', None)

        # Load font
        try:
            font = ImageFont.truetype(FONT_PATH, font_size)
        except IOError:
            return Response("Lỗi: Không tìm thấy file font.", status=500)

        # Chiều rộng cố định cho giấy in 58mm
        width = 384

        # Ước tính chiều cao ban đầu để vẽ
        # Chiều cao thực tế sẽ được crop lại ở cuối
        estimated_height = 100 + len(lines) * (font_size + 10) + (160 if qr_data else 0)
        img = Image.new("1", (width, estimated_height), color=1)  # Nền trắng
        draw = ImageDraw.Draw(img)

        y = 10
        for line in lines:
            # Sử dụng textbbox để tính toán kích thước chính xác
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Căn giữa dòng chữ
            draw.text(((width - text_width) / 2, y), line, font=font, fill=0)  # Mực đen
            y += text_height + 5

        if qr_data:
            y += 10  # Thêm khoảng trống trước QR code
            qr_img = qrcode.make(qr_data).resize((120, 120)).convert("1")
            img.paste(qr_img, ((width - 120) // 2, y))
            y += 120  # Chiều cao của QR code

        # Cắt ảnh về đúng kích thước nội dung
        final_height = y + 10  # Thêm padding ở dưới
        final_img = img.crop((0, 0, width, final_height))

        # Chuyển ảnh thành dữ liệu raster thô
        raw_image_data = image_to_raw_raster_bytes(final_img)

        # Tạo response và thêm header
        response = Response(raw_image_data, mimetype='application/octet-stream')
        response.headers['X-Image-Width'] = str(final_img.width)
        response.headers['X-Image-Height'] = str(final_img.height)

        return response

    except Exception as e:
        # Bắt lỗi chung và trả về thông báo lỗi
        return Response(f"Đã xảy ra lỗi trên server: {e}", status=500)


if __name__ == '__main__':
    # Chạy app, debug=True để tự động reload khi có thay đổi code
    app.run(host='0.0.0.0', port=5000, debug=True)

