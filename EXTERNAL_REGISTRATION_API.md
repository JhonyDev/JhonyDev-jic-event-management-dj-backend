# External Registration API Documentation

## Overview
This API endpoint allows external forms to register users in the system without requiring a password. Users created through this endpoint will need to set up their password later through a separate process.

## Endpoint Details

**URL:** `/api/auth/external-register/`

**Method:** `POST`

**Authentication:** Required via API Key (see below)

**Content-Type:** `application/json`

## Authentication

This endpoint requires an API key to be passed in the request header for security purposes.

**Header Name:** `X-API-Key`

**Header Value:** `[Your API key will be provided separately]`

All requests without a valid API key will receive a `401 Unauthorized` response.

---

## Request Format

### Required Fields
- `email` (string) - User's email address (must be unique)

### Optional Fields
- `first_name` (string) - User's first name
- `last_name` (string) - User's last name
- `designation` (string) - Job title or position
- `affiliations` (string) - Organization or institution affiliation
- `address` (string) - Physical address
- `country` (string) - Country name
- `phone_number` (string) - Contact phone number
- `registration_type` (string) - Type of registration (e.g., "Student Participant", "Delegate")

### Example Request

```bash
curl -X POST https://your-domain.com/api/auth/external-register/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "designation": "Software Engineer",
    "affiliations": "Tech Corporation",
    "address": "123 Main Street, City",
    "country": "USA",
    "phone_number": "+1234567890",
    "registration_type": "Student Participant"
  }'
```

---

## Response Format

### Success Response (201 Created)

```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": 18,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

### Error Responses

#### 401 Unauthorized - Invalid or Missing API Key
```json
{
  "error": "Invalid or missing API key"
}
```

#### 400 Bad Request - Email Already Exists
```json
{
  "error": "A user with this email already exists"
}
```

#### 400 Bad Request - Validation Error
```json
{
  "email": ["This field is required."]
}
```

#### 400 Bad Request - Registration Failed
```json
{
  "error": "Registration failed: [error details]"
}
```

---

## Field Specifications

| Field | Type | Max Length | Required | Description |
|-------|------|------------|----------|-------------|
| email | string | 254 | Yes | Valid email address, must be unique |
| first_name | string | 150 | No | User's first name |
| last_name | string | 150 | No | User's last name |
| designation | string | 200 | No | Job title or position |
| affiliations | string | 300 | No | Organization affiliation |
| address | text | - | No | Physical address |
| country | string | 100 | No | Country name |
| phone_number | string | 20 | No | Contact phone number |
| registration_type | string | 100 | No | Type of participant |

---

## Important Notes

1. **API Key Security:** Keep your API key secure and never expose it in client-side code. Store it in environment variables or server-side configuration files.

2. **Password-less Registration:** Users created through this endpoint will NOT have a password set. They will need to activate their account through a separate password setup process.

3. **Email Uniqueness:** Each email can only be registered once. If you attempt to register an existing email, you'll receive a 400 error.

4. **No Authentication Token:** This endpoint does NOT return an authentication token since users are created without passwords.

5. **User Activation:** After registration, users will need to be directed to a password setup or activation flow to gain full access to the system.

6. **API Key Format:** The API key should be passed as-is in the `X-API-Key` header. No "Bearer" prefix or other formatting is needed.

---

## Integration Examples

### JavaScript (Fetch API)
```javascript
const API_KEY = 'your-api-key-here'; // Store securely, do not expose in client-side code

const registerUser = async (formData) => {
  try {
    const response = await fetch('https://your-domain.com/api/auth/external-register/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: JSON.stringify({
        email: formData.email,
        first_name: formData.firstName,
        last_name: formData.lastName,
        designation: formData.designation,
        affiliations: formData.affiliations,
        address: formData.address,
        country: formData.country,
        phone_number: formData.phoneNumber,
        registration_type: formData.registrationType
      })
    });

    const data = await response.json();

    if (response.ok) {
      console.log('User registered successfully:', data.user);
      return { success: true, data };
    } else {
      console.error('Registration failed:', data.error);
      return { success: false, error: data.error };
    }
  } catch (error) {
    console.error('Network error:', error);
    return { success: false, error: 'Network error occurred' };
  }
};
```

### PHP
```php
<?php
$apiKey = 'your-api-key-here'; // Store securely

$data = [
    'email' => 'user@example.com',
    'first_name' => 'John',
    'last_name' => 'Doe',
    'designation' => 'Software Engineer',
    'affiliations' => 'Tech Corporation',
    'address' => '123 Main Street',
    'country' => 'USA',
    'phone_number' => '+1234567890',
    'registration_type' => 'Student Participant'
];

$ch = curl_init('https://your-domain.com/api/auth/external-register/');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Content-Type: application/json',
    'X-API-Key: ' . $apiKey
]);

$response = curl_exec($ch);
$httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

$result = json_decode($response, true);

if ($httpCode === 201) {
    echo "User registered: " . $result['user']['email'];
} else {
    echo "Error: " . $result['error'];
}
?>
```

---

## Testing

You can test this endpoint using the following curl command:

```bash
curl -X POST http://localhost:8000/api/auth/external-register/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "designation": "Developer",
    "affiliations": "Test Corp",
    "address": "123 Test St",
    "country": "TestLand",
    "phone_number": "+1234567890",
    "registration_type": "Delegate"
  }'
```

---

## Support

For any issues or questions regarding this API, please contact your development team.
