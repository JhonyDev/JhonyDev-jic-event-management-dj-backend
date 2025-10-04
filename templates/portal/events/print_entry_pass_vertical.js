function printEntryPass() {
  if (!window.currentAttendee) {
    console.error('No attendee data available for printing');
    alert('Please scan a QR code first');
    return;
  }

  // Generate QR code URL
  const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=100x100&data=REG-${window.currentAttendee.registration_id}`;

  // Format check-in time
  const checkInTime = window.currentAttendee.checked_in_at ?
    new Date(window.currentAttendee.checked_in_at).toLocaleString() :
    new Date().toLocaleString();

  // Create a new window for printing - vertical badge format
  const printWindow = window.open('', '_blank', 'width=400,height=650');

  // Build simple vertical badge HTML
  const htmlContent = `
<!DOCTYPE html>
<html>
<head>
  <title>Entry Pass - ${window.currentAttendee.name}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }

    body {
      font-family: 'Arial', sans-serif;
      background: white;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      margin: 0;
    }

    /* Badge Card - Vertical Design */
    .badge {
      width: 3.5in;
      height: 6in;
      border: 2px solid #333;
      border-radius: 10px;
      background: white;
      overflow: hidden;
      position: relative;
    }

    /* Header Section */
    .badge-header {
      background: linear-gradient(180deg, #5B21B6, #7C3AED);
      color: white;
      padding: 15px;
      text-align: center;
      position: relative;
    }

    .badge-header::before {
      content: '';
      position: absolute;
      top: 8px;
      left: 50%;
      transform: translateX(-50%);
      width: 30px;
      height: 5px;
      background: white;
      border-radius: 3px;
      opacity: 0.5;
    }

    .event-name {
      font-size: 16px;
      font-weight: bold;
      margin-top: 10px;
      text-transform: uppercase;
      line-height: 1.2;
    }

    .event-type {
      font-size: 12px;
      margin-top: 5px;
      opacity: 0.9;
      letter-spacing: 2px;
    }

    /* Photo Section */
    .photo-container {
      padding: 20px 20px 10px;
      text-align: center;
      background: white;
    }

    .attendee-photo {
      width: 120px;
      height: 120px;
      border-radius: 50%;
      margin: 0 auto;
      border: 3px solid #7C3AED;
      overflow: hidden;
      background: #f0f0f0;
    }

    .attendee-photo img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .attendee-name {
      font-size: 18px;
      font-weight: bold;
      color: #333;
      margin-top: 12px;
    }

    .attendee-org {
      font-size: 12px;
      color: #666;
      margin-top: 4px;
    }

    /* Info Section */
    .info-section {
      padding: 15px 20px;
      background: #F9FAFB;
      margin: 0 15px;
      border-radius: 8px;
    }

    .info-item {
      font-size: 11px;
      margin-bottom: 8px;
      color: #333;
    }

    .info-label {
      font-weight: bold;
      color: #7C3AED;
    }

    /* QR Section */
    .qr-container {
      text-align: center;
      padding: 15px;
    }

    .qr-code {
      width: 80px;
      height: 80px;
    }

    .reg-number {
      font-size: 14px;
      font-weight: bold;
      color: #7C3AED;
      margin-top: 8px;
    }

    /* Footer */
    .badge-footer {
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      background: #333;
      color: white;
      padding: 8px;
      text-align: center;
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: 1px;
    }

    @media print {
      body {
        margin: 0;
        padding: 0;
      }
      .badge {
        border: 1px solid #ccc;
        page-break-inside: avoid;
      }
    }
  </style>
</head>
<body>
  <div class="badge">
    <!-- Header with event info -->
    <div class="badge-header">
      <div class="event-name">{{ event.title|upper|escapejs }}</div>
      <div class="event-type">ENTRY PASS</div>
    </div>

    <!-- Photo and name -->
    <div class="photo-container">
      <div class="attendee-photo">
        <img src="${window.currentAttendee.profile_image}" alt="${window.currentAttendee.name}" />
      </div>
      <div class="attendee-name">${window.currentAttendee.name}</div>
      ${window.currentAttendee.organization ? `<div class="attendee-org">${window.currentAttendee.organization}</div>` : ''}
    </div>

    <!-- Event details -->
    <div class="info-section">
      <div class="info-item">
        <span class="info-label">DATE:</span> {{ event.date|date:"F j, Y"|escapejs }}
      </div>
      <div class="info-item">
        <span class="info-label">TIME:</span> {{ event.date|date:"g:i A"|escapejs }}
      </div>
      <div class="info-item">
        <span class="info-label">VENUE:</span> {{ event.location|escapejs }}
      </div>
      <div class="info-item">
        <span class="info-label">CHECK-IN:</span> ${checkInTime}
      </div>
    </div>

    <!-- QR Code -->
    <div class="qr-container">
      <img src="${qrCodeUrl}" alt="QR Code" class="qr-code" />
      <div class="reg-number">ID: #${window.currentAttendee.registration_id}</div>
    </div>

    <!-- Footer -->
    <div class="badge-footer">
      Valid for one-time entry only
    </div>
  </div>

  <scr` + `ipt>
    window.onload = function() {
      setTimeout(function() {
        window.print();
        window.onafterprint = function() {
          window.close();
        };
      }, 500);
    };
  </scr` + `ipt>
</body>
</html>`;

  // Write content to new window
  printWindow.document.write(htmlContent);
  printWindow.document.close();
}