import qrcode
import io
import base64
import random
import string

def generate_unique_code(case_number):
    """Generate unique code: CASE_NUMBER-1234"""
    suffix = ''.join(random.choices(string.digits, k=4))
    return f"{case_number}-{suffix}"

def generate_qr_code(data):
    """Generate QR code as base64 image"""
    try:
        qr = qrcode.QRCode(
            version=1, 
            error_correction=qrcode.constants.ERROR_CORRECT_L, 
            box_size=10, 
            border=4
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"QR Error: {e}")
        return None