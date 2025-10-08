# External Registration API - Credentials

## API Endpoint
**URL:** `https://your-domain.com/api/auth/external-register/`

## Authentication
**Header:** `X-API-Key`

**API Key:** `gJiiVpjIjnZ8rpW5m3cjKYtDsztgTSoxVe5fM6uYjmY`

---

## Quick Test

You can test the API with this curl command:

```bash
curl -X POST https://your-domain.com/api/auth/external-register/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: gJiiVpjIjnZ8rpW5m3cjKYtDsztgTSoxVe5fM6uYjmY" \
  -d '{
    "email": "test@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "designation": "Software Engineer",
    "affiliations": "Tech Corporation",
    "address": "123 Main Street",
    "country": "USA",
    "phone_number": "+1234567890",
    "registration_type": "Student Participant"
  }'
```

---

## Important Security Notes

⚠️ **Keep this API key secure!**

- Do not commit this key to version control
- Do not expose this key in client-side JavaScript
- Store it in server-side environment variables or configuration files
- Only share it through secure channels (e.g., encrypted email, password manager)

---

For full API documentation, see `EXTERNAL_REGISTRATION_API.md`
