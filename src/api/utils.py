import qrcode
from io import BytesIO
from django.core.files import File
import uuid


def generate_ticket_qr_code(ticket):
    """Generate QR code for a ticket"""
    # Create QR code data
    qr_data = f"TICKET:{ticket.ticket_number}|EVENT:{ticket.ticket_type.event.id}|ATTENDEE:{ticket.attendee.id}"

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    file_name = f'qr_{ticket.ticket_number}.png'
    return File(buffer, name=file_name)


def generate_unique_ticket_number():
    """Generate a unique ticket number"""
    return f"TKT{uuid.uuid4().hex[:8].upper()}"


def generate_agenda_qr_code(event):
    """Generate QR code for an event agenda"""
    # Create QR code data with event agenda URL
    qr_data = f"EVENT_AGENDA:{event.id}|TITLE:{event.title}"

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    file_name = f'agenda_qr_{event.id}.png'
    return File(buffer, name=file_name)


def generate_registration_qr_code(event, request):
    """Generate QR code for event registration"""
    # Create registration URL
    registration_url = f"{request.scheme}://{request.get_host()}/register/{event.id}/"

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(registration_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    file_name = f'registration_qr_{event.id}.png'
    return File(buffer, name=file_name)


def verify_qr_code(qr_data):
    """Verify and parse QR code data"""
    try:
        parts = qr_data.split('|')
        data = {}
        for part in parts:
            key, value = part.split(':')
            data[key.lower()] = value
        return data
    except:
        return None