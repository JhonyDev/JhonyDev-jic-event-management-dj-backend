# JazzCash Sandbox Testing Guide

## Official Test Cards

Use these EXACT card details for JazzCash sandbox testing:

### Test Cards (All 3-D Secure Enrolled)

| Scheme | Card Number | CVV | 3-D Secure |
|--------|-------------|-----|------------|
| **Master Card** | `5123450000000008` | `100` | Yes |
| **Master Card** | `2223000000000008` | `100` | Yes |
| **VISA** | `4508750015741019` | `100` | Yes |

---

## Test Scenarios (Expiry Date)

The **expiry date** determines the transaction outcome:

| Expiry Date | Result | Response Code | Description |
|-------------|--------|---------------|-------------|
| **01/39** | ✅ **APPROVED** | 000 | Transaction successful |
| **05/39** | ❌ **DECLINED** | varies | Transaction declined |
| **04/27** | ❌ **EXPIRED_CARD** | varies | Card has expired |

---

## How to Test Successfully

### ✅ For SUCCESSFUL Payment:

```
Card Number: 5123450000000008  (or any from table above)
Expiry Date: 01/39  ← CRITICAL!
CVV: 100
Name: Test User
```

### ❌ To Test DECLINED Payment:

```
Card Number: 5123450000000008
Expiry Date: 05/39  ← Use this to test failure
CVV: 100
Name: Test User
```

### ❌ To Test EXPIRED CARD:

```
Card Number: 5123450000000008
Expiry Date: 04/27  ← Card expired
CVV: 100
Name: Test User
```

---

## Testing Workflow

### 1. Card Payment (Page Redirection)

1. **Start Payment** in your React Native app
2. **Select "Credit/Debit Card"**
3. **Enter Test Card Details:**
   - Card: `5123450000000008`
   - Expiry: `01/39`
   - CVV: `100`
   - Name: Any name
4. **Complete 3-D Secure** (if prompted)
5. **Verify Success:**
   - JazzCash page: "Transaction Successful"
   - Your app: "Payment Successful"
   - Response Code: `000`

### 2. Mobile Wallet Payment

1. **Start Payment** in your React Native app
2. **Select "Mobile Wallet"**
3. **Enter:**
   - Mobile: `03123456789` (any valid format)
   - CNIC: `123456` (last 6 digits)
4. **Check Mobile** for OTP (sandbox)
5. **Verify Success**

---

## Response Codes Reference

| Code | Description | Status |
|------|-------------|--------|
| `000` | Approved | ✅ Success |
| `121` | Pending | ⏳ Awaiting action |
| `199` | Transaction not successful | ❌ Failed |
| `134` | Transaction timeout | ❌ Failed |
| `999` | Technical error | ❌ Failed |

---

## Troubleshooting

### Payment Shows "Failed" but JazzCash Said "Success"

**Cause:** Wrong expiry date used
**Solution:** Use expiry `01/39` for successful transactions

### No IPN Received

**Issue:** JazzCash cannot reach your IPN URL
**Check:**
1. IPN URL is publicly accessible
2. Port 8000 is open
3. No firewall blocking JazzCash IPs

**Test IPN:**
```bash
curl -X POST http://165.232.126.196:8000/api/payments/jazzcash/ipn/ \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### Hash Verification Failed

**Cause:** Incorrect HMAC calculation
**Test:**
```bash
cd django-backend
source env/bin/activate
python manage.py shell
>>> from src.payments.jazzcash.hmac_utils import test_hmac_generation
>>> test_hmac_generation()
```

---

## Production Checklist

Before going live:

- [ ] Update to production credentials
- [ ] Set `JAZZCASH_ENVIRONMENT=production`
- [ ] Use HTTPS for Return URL and IPN URL
- [ ] Register URLs in JazzCash merchant portal
- [ ] Test with real card (small amount)
- [ ] Monitor IPN logs for issues
- [ ] Setup error alerts

---

## Quick Commands

### Check Recent Transactions
```bash
cd django-backend && source env/bin/activate
python manage.py shell
>>> from src.payments.models import JazzCashTransaction
>>> JazzCashTransaction.objects.order_by('-created_at')[:5]
```

### Check IPN Logs
```bash
python manage.py shell
>>> from src.payments.models import JazzCashIPNLog
>>> JazzCashIPNLog.objects.order_by('-received_at')[:5]
```

### View Transaction Details
```bash
python manage.py shell
>>> from src.payments.models import JazzCashTransaction
>>> txn = JazzCashTransaction.objects.get(txn_ref_no='T20251013...')
>>> print(f"Status: {txn.status}")
>>> print(f"Response: {txn.pp_response_message}")
```

---

## Support

For issues, check:
1. Django logs: Check server console
2. JazzCash docs: Refer to PDF guides in project root
3. Transaction logs: Query `JazzCashTransaction` model

**Remember:** Always use test cards with expiry `01/39` for successful sandbox payments!
