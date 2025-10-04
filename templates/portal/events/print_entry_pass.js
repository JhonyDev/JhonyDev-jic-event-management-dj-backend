function printEntryPass() {
  if (!window.currentAttendee) {
    console.error('No attendee data available for printing');
    alert('Please scan a QR code first');
    return;
  }

  // Generate QR code URL
  const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=REG-${window.currentAttendee.registration_id}`;

  // Format check-in time
  const checkInTime = window.currentAttendee.checked_in_at ?
    new Date(window.currentAttendee.checked_in_at).toLocaleString() :
    new Date().toLocaleString();

  // Create a new window for printing
  const printWindow = window.open('', '_blank', 'width=850,height=1100');

  // Build the HTML content
  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>Entry Pass - ${window.currentAttendee.name}</title>
      <style>
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        body {
          font-family: Arial, sans-serif;
          color: #2c3e50;
          padding: 20px;
          background: white;
        }

        .entry-pass-print {
          width: 100%;
          max-width: 800px;
          margin: 0 auto;
          border: 3px solid #2c3e50;
          background: white;
        }

        .entry-pass-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          padding: 20px;
          text-align: center;
          color: white;
        }

        .event-title {
          margin: 0;
          font-size: 28px;
          font-weight: bold;
          letter-spacing: 1px;
        }

        .pass-type {
          font-size: 16px;
          margin-top: 5px;
          font-weight: 500;
          letter-spacing: 3px;
        }

        .entry-pass-body {
          display: flex;
          padding: 30px;
          gap: 30px;
          min-height: 350px;
        }

        .attendee-section {
          flex: 0 0 300px;
          border-right: 2px dashed #e0e0e0;
          padding-right: 30px;
        }

        .attendee-photo {
          width: 150px;
          height: 150px;
          margin: 0 auto 20px;
          border: 3px solid #667eea;
          border-radius: 10px;
          overflow: hidden;
          background: #f5f5f5;
        }

        .attendee-photo img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }

        .attendee-name {
          font-size: 22px;
          font-weight: bold;
          text-align: center;
          margin-bottom: 15px;
          color: #2c3e50;
        }

        .attendee-details {
          font-size: 12px;
        }

        .detail-item {
          margin-bottom: 8px;
          line-height: 1.4;
        }

        .detail-label {
          font-weight: bold;
          color: #667eea;
          display: inline-block;
          min-width: 80px;
        }

        .detail-value {
          color: #2c3e50;
        }

        .event-section {
          flex: 1;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }

        .event-details h3 {
          margin: 0 0 20px 0;
          color: #667eea;
          font-size: 18px;
          border-bottom: 2px solid #e0e0e0;
          padding-bottom: 10px;
        }

        .info-row {
          display: flex;
          margin-bottom: 15px;
          font-size: 13px;
        }

        .info-label {
          flex: 0 0 120px;
          font-weight: bold;
          color: #667eea;
        }

        .info-value {
          flex: 1;
          color: #2c3e50;
          line-height: 1.4;
        }

        .reg-id {
          font-size: 16px;
          font-weight: bold;
          color: #764ba2;
        }

        .qr-section {
          text-align: center;
          margin-top: 20px;
          padding-top: 20px;
          border-top: 2px dashed #e0e0e0;
        }

        .qr-code {
          width: 120px;
          height: 120px;
          border: 2px solid #2c3e50;
          padding: 5px;
          background: white;
        }

        .qr-label {
          font-size: 10px;
          color: #666;
          margin-top: 5px;
          font-style: italic;
        }

        .entry-pass-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 15px 30px;
          background: #f8f9fa;
          border-top: 2px solid #e0e0e0;
          font-size: 11px;
        }

        .footer-left {
          flex: 1;
          color: #dc3545;
        }

        .footer-right {
          text-align: right;
        }

        .organizer-info {
          color: #666;
          line-height: 1.5;
        }

        .security-strip {
          display: flex;
          align-items: center;
          background: linear-gradient(90deg, #667eea, #764ba2, #667eea);
          color: white;
          padding: 8px;
          font-size: 10px;
          font-weight: bold;
          letter-spacing: 2px;
          text-align: center;
        }

        .pattern {
          flex: 1;
          height: 2px;
          background: repeating-linear-gradient(
            90deg,
            white,
            white 5px,
            transparent 5px,
            transparent 10px
          );
        }

        .validation-text {
          padding: 0 20px;
        }

        @media print {
          body {
            padding: 0;
          }
        }
      </style>
    </head>
    <body>
      <div class="entry-pass-print">
        <!-- Header with Event Title -->
        <div class="entry-pass-header">
          <div class="pass-logo">
            <h1 class="event-title">{{ event.title|upper|escapejs }}</h1>
            <div class="pass-type">ENTRY PASS</div>
          </div>
        </div>

        <!-- Main Content Area -->
        <div class="entry-pass-body">
          <!-- Left Section - Attendee Photo and Info -->
          <div class="attendee-section">
            <div class="attendee-photo">
              <img src="${window.currentAttendee.profile_image}" alt="${window.currentAttendee.name}" />
            </div>

            <div class="attendee-name">
              ${window.currentAttendee.name}
            </div>

            <div class="attendee-details">
              ${window.currentAttendee.organization ? `
                <div class="detail-item">
                  <span class="detail-label">Organization:</span>
                  <span class="detail-value">${window.currentAttendee.organization}</span>
                </div>
              ` : ''}
              <div class="detail-item">
                <span class="detail-label">Email:</span>
                <span class="detail-value">${window.currentAttendee.email}</span>
              </div>
              ${window.currentAttendee.phone ? `
                <div class="detail-item">
                  <span class="detail-label">Phone:</span>
                  <span class="detail-value">${window.currentAttendee.phone}</span>
                </div>
              ` : ''}
            </div>
          </div>

          <!-- Right Section - Event Details and QR Code -->
          <div class="event-section">
            <div class="event-details">
              <h3>Event Information</h3>

              <div class="info-row">
                <div class="info-label">Date & Time</div>
                <div class="info-value">{{ event.date|date:"F j, Y"|escapejs }}<br>{{ event.date|date:"g:i A"|escapejs }}</div>
              </div>

              <div class="info-row">
                <div class="info-label">Location</div>
                <div class="info-value">{{ event.location|escapejs }}</div>
              </div>

              <div class="info-row">
                <div class="info-label">Registration ID</div>
                <div class="info-value reg-id">#${window.currentAttendee.registration_id}</div>
              </div>

              <div class="info-row">
                <div class="info-label">Check-In Time</div>
                <div class="info-value">${checkInTime}</div>
              </div>
            </div>

            <!-- QR Code -->
            <div class="qr-section">
              <img src="${qrCodeUrl}" alt="QR Code" class="qr-code" />
              <div class="qr-label">Scan for verification</div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="entry-pass-footer">
          <div class="footer-left">
            <strong>Important:</strong> This pass must be worn visibly at all times during the event
          </div>
          <div class="footer-right">
            <div class="organizer-info">
              Organized by: {{ event.organizer.get_full_name|default:event.organizer.username|escapejs }}<br>
              Contact: {{ event.organizer.email|escapejs }}
            </div>
          </div>
        </div>

        <!-- Security Features -->
        <div class="security-strip">
          <div class="pattern"></div>
          <div class="validation-text">VALID FOR ONE-TIME ENTRY ONLY</div>
          <div class="pattern"></div>
        </div>
      </div>

      <script>
        // Auto-print and close
        window.onload = function() {
          setTimeout(function() {
            window.print();
            // Close the window after printing
            window.onafterprint = function() {
              window.close();
            };
          }, 500);
        };
      </script>
    </body>
    </html>
  `);

  printWindow.document.close();
}