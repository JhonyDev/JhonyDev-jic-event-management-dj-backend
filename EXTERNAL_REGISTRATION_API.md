# External Registration API Documentation

## Overview
This API endpoint allows external forms to register users in the system. Users are automatically created with their phone number as the password, allowing them to login immediately after registration.

**Automatic Event Registration:** All users registered through this API are automatically registered to the main event (Event ID: 1) with confirmed status.

## Endpoint Details

**URL:** `https://event.jic.agency/api/auth/external-register/`

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
- `workshop_selection` (string) - Workshop name from the dropdown (see Workshop Options below)

### Workshop Options

If registering for a workshop, use the exact workshop name from your dropdown in the `workshop_selection` field. The API automatically maps these names to the correct sessions in the database.

**Valid workshop names:**
- `Hands-on Workshop on Next-Generation Sequencing (NGS) Data Analysis and Bioinformatics Skills Development`
- `Workshop on Precision in Practice: Advanced Imaging, Physiology and Interventions in the Modern Cath Lab`
- `Workshop on Artificial Intelligence in Instrument Development`
- `Workshop on Regenerative Medicine and 3D Bioprinting: from Concept to Tissue Fabrication`
- `Hands-on Workshop on Nanomedicine Preparation and Characterization Techniques`
- `Symposium cum Workshop on Emerging Trends in Clinical Genetics and Genomics`
- `N-A` (no workshop)
- `I don't want to attend any workshop` (no workshop)

**Note:** The mapping is handled automatically by the API. You don't need to change your dropdown option values - simply pass the exact text as shown in your form.

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
    "registration_type": "Student Participant",
    "workshop_selection": "Workshop on Artificial Intelligence in Instrument Development"
  }'
```

---

## Response Format

### Success Response (201 Created)

**Without Workshop:**
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

**With Workshop Registration:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": 18,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  },
  "workshop": "Workshop on Artificial Intelligence in Instrument Development - Parallel Workshops"
}
```

The `workshop` field will only appear in the response if a valid workshop was selected and the user was successfully registered for it.

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
| workshop_selection | string | - | No | Workshop name (see Workshop Options section) |

---

## Important Notes

1. **API Key Security:** Keep your API key secure and never expose it in client-side code. Store it in environment variables or server-side configuration files.

2. **Password Setup:** Users are created with their phone number as the password. They can login using:
   - Email: Their registered email address
   - Password: Their phone number

3. **Email Uniqueness:** Each email can only be registered once. If you attempt to register an existing email, you'll receive a 400 error.

4. **Phone Number Required:** While technically optional, it's highly recommended to collect the phone number as it's used as the default password. Users without a phone number will have an unusable password and won't be able to login.

5. **Workshop Registration:** The workshop mapping is handled automatically by the API. Just pass the exact workshop name from your dropdown - no need to map to session IDs.

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
        registration_type: formData.registrationType,
        workshop_selection: formData.workshopSelection  // Pass the exact dropdown value
      })
    });

    const data = await response.json();

    if (response.ok) {
      console.log('User registered successfully:', data.user);
      if (data.workshop) {
        console.log('Workshop registered:', data.workshop);
      }
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
    'registration_type' => 'Student Participant',
    'workshop_selection' => 'Workshop on Artificial Intelligence in Instrument Development'
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
    if (isset($result['workshop'])) {
        echo "\nWorkshop: " . $result['workshop'];
    }
} else {
    echo "Error: " . $result['error'];
}
?>
```

---

## Testing

You can test this endpoint using the following curl command:

**Without Workshop:**
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

**With Workshop Registration:**
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
    "registration_type": "Delegate",
    "workshop_selection": "Workshop on Artificial Intelligence in Instrument Development"
  }'
```

---

## Support

For any issues or questions regarding this API, please contact your development team.
