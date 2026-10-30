# Passenger / cPanel deployment (Phase 6A)

Target: CloudLinux cPanel + Passenger, `DEBUG=False`, HTTPS.

## 1. Environment

1. Copy `.env.example` → `.env` on the server (never commit `.env`).
2. Set a strong `SECRET_KEY` (≥ 40 random characters).
3. Set `DEBUG=False`.
4. Set `ALLOWED_HOSTS` to your domain(s).
5. Set `CSRF_TRUSTED_ORIGINS` to `https://your-domain` (and `www` if used).
6. Set `SITE_URL=https://your-domain`.
7. Leave `ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE=False`.
8. Set `SSLCOMMERZ_IS_SANDBOX=False` only with real production credentials.

## 2. Python / Passenger

- Point Passenger at `passenger_wsgi.py` in the project root.
- Use a virtualenv whose Python matches the app (Django 5 ⇒ Python 3.10+).
- Install deps: `pip install -r requirements.txt`.

Example Application Manager settings:

- Application root: `/home/ACCOUNT/zarrah-foundation`
- Startup file: `passenger_wsgi.py`
- Python: virtualenv interpreter path

## 3. Database & migrate

```bash
python manage.py migrate
python manage.py seed_rbac
python manage.py seed_organizational_positions
python manage.py seed_meeting_types
python manage.py seed_homepage_defaults
python manage.py collectstatic --noinput
python manage.py check --deploy
```

`seed_organizational_positions` is idempotent (Chairman/President/Secretary/Treasurer/council member titles). Member/application profile PDFs reuse the same ReportLab + Noto Sans Bengali stack as resolution documents (`members/documents.py`). Bulk member/application PDFs are RBAC-gated (`members.bulk_report` / `applications.bulk_report`) and are not public CMS downloads.

`seed_homepage_defaults` is idempotent: it creates missing bilingual homepage CMS
sections (and a factual leadership testimonial) and never overwrites admin edits
or publish/unpublish state. Safe to re-run anytime.

## 4. Static files

Run `collectstatic` so assets land in `staticfiles/`.

**Preferred:** Apache/cPanel Alias (outside open document listing):

```
Alias /static/ /home/ACCOUNT/zarrah-foundation/staticfiles/
```

Ensure the Alias directory is readable by the web server user.

Do **not** rely on Django `DEBUG` static serving in production.

## 5. Media files (CRITICAL)

| Kind | URL | Serving |
|------|-----|---------|
| Public (`brand/`, `cms/`, `community/`, `news/`, `donations/`, `reports/`) | `/media/...` | Django `serve_public_media` **or** carefully scoped Alias to those subfolders only |
| Private (`members/photos/`, `members/signatures/`, `identity/`, `cv/`, `requested_docs/`, `documents/`, `resolutions/signatures/`, `meetings/`) | `/protected-media/...` | **Django only** — object-level auth |

**Do not** Alias the entire `MEDIA_ROOT` to `/media/`.

If you must Alias public media, Alias only public subfolders, for example:

```
Alias /media/brand/ /home/ACCOUNT/zarrah-foundation/media/brand/
Alias /media/cms/ /home/ACCOUNT/zarrah-foundation/media/cms/
Alias /media/community/ /home/ACCOUNT/zarrah-foundation/media/community/
Alias /media/news/ /home/ACCOUNT/zarrah-foundation/media/news/
Alias /media/donations/ /home/ACCOUNT/zarrah-foundation/media/donations/
Alias /media/reports/ /home/ACCOUNT/zarrah-foundation/media/reports/
```

Never Alias `/media/members/`, `/media/resolutions/`, or `/media/meetings/`.

Root `.htaccess` returns **403** for `^media/members/` as a safety net.

Private files are linked via `SecureMediaStorage.url()` → `/protected-media/...`.

Official resolution PDF/DOCX are generated **on download** (not stored under open `/media/`). Serve them only through authorized dashboard or public-share endpoints.

## 6. HTTPS / proxy

Settings enable `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` for TLS terminators. Confirm the host sends `X-Forwarded-Proto: https`.

With `DEBUG=False`, defaults expect:

- `SESSION_COOKIE_SECURE=True`
- `CSRF_COOKIE_SECURE=True`
- `SECURE_SSL_REDIRECT=True`
- HSTS enabled (`SECURE_HSTS_SECONDS`)

## 7b. Payment Management Center

Dashboard → **Payment Management**: Overview, Payment Methods, **Recurring Payment Setup**, Recurring Payments (subscription list), Donations, Membership Fees, Registration Fees, Transactions, Refunds, Webhooks/IPN, Payment Logs, Settings, Capabilities.

Recurring Payment Setup (`/dashboard/payments/recurring/setup/`) is the administrator checklist for SSLCommerz recurring, bKash subscription, and Nagad. It shows capability states and whether a secret is stored. It never renders store passwords, SALT keys, app secrets, or API passwords. The SSLCommerz connection test lives on Payment Methods → Configure and does not create a payment.

Capability states used on that page:

`NOT_IMPLEMENTED` · `NOT_CONFIGURED` · `CONFIGURED` · `PENDING_MERCHANT_APPROVAL` · `VERIFIED_IN_SANDBOX` · `VERIFIED_IN_PRODUCTION` · `ENABLED` · `DISABLED` · `FAILED`

bKash and Nagad recurring stay `NOT_IMPLEMENTED` until the Foundation receives the official merchant API contract and approval. Direct one-time bKash/Nagad checkout is also not wired; public online checkout remains SSLCommerz.

### Provider matrix (honest states)

| Provider | One-time | Recurring | Refund |
|----------|----------|-----------|--------|
| SSLCommerz | Configured when store credentials exist; Verified only after live proof | Requires SALT + plan refer + merchant enablement; never Active without config | Not configured until `refunds_enabled` + provider confirmation path |
| bKash | Adapter exists; **Not configured** without merchant credentials | **Not implemented** — not offered as recurring | **Not implemented** |
| Nagad | Same as bKash | **Not implemented** | **Not implemented** |

Never claim production readiness from unit tests alone. Banner: **LIVE VALIDATION PENDING**.

Statuses used in Payment Management → Capabilities:

`Not implemented` · `Not configured` · `Configured` · `Verified` (and connection `Failed` when a test fails).

### Refunds

- `RefundRequest` workflow: REQUESTED → APPROVED/REJECTED → PROCESSING → REFUNDED/FAILED
- **Only Super Admin** may approve (`payments.refunds_approve`)
- Finance may request/view; never approve
- Status is never `REFUNDED` without provider confirmation (no fake success)

### Env (additive)

```bash
SSLCOMMERZ_SALT_KEY=
SSLCOMMERZ_RECURRING_PLAN_REFER=
# Optional DB storage via Payment Methods → Configure (write-only SALT)
```

After deploy: `python manage.py seed_rbac` then `python manage.py migrate`.

### Cron

```bash
0 * * * * ... manage.py charge_due_subscriptions   # reconcile only
# membership MOCK autopay: do not enable on production
# There is no separate process_recurring_donations command.
# charge_due_subscriptions is the reconcile-only job. It must not invent card charges.
```

Public HTTPS is mandatory for real SSLCommerz / bKash / Nagad callbacks.

## 7. Cron (do not enable MOCK autopay in production)

Do **not** schedule `charge_due_membership_fees` against production unless you intentionally set `ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE` for a non-prod staging demo. The command refuses when `DEBUG=False` without that override.

### Recurring donations (PAY-WP3 · SSLCommerz)

General monthly donations use **SSLCommerz EasyCheckout recurring** (encrypted `schedule`). Django does **not** invent merchant-initiated card charges. Gateway-scheduled settlements arrive via IPN.

**Not implemented in WP3:** bKash recurring, Nagad recurring.

#### Environment

```bash
# One-time SSLCommerz (unchanged)
SSLCOMMERZ_STORE_ID=...
SSLCOMMERZ_STORE_PASSWORD=...
SSLCOMMERZ_IS_SANDBOX=True

# Recurring (required for /donation/recurring/ to proceed)
SSLCOMMERZ_SALT_KEY=...                 # merchant SALT for schedule encryption — never commit
SSLCOMMERZ_RECURRING_PLAN_REFER=...     # merchant plan "refer" from SSLCommerz
# RECURRING_DONATION_FAILURE_THRESHOLD=3
# RECURRING_DONATION_MANAGEMENT_TOKEN_TTL=2592000
```

If SALT or plan refer is missing, the app stays in a safe **RECURRING_NOT_CONFIGURED** state: checkout refuses to fake recurring; one-time SSLCommerz continues normally.

After adding RBAC actions, re-seed permissions:

```bash
python manage.py seed_rbac
```

#### Public URLs

| Purpose | Path |
|--------|------|
| Monthly checkout | `/donation/recurring/` |
| Success / fail / cancel return | `/donation/recurring/success|fail|cancel/` |
| IPN (authorization + settlements) | `/donation/recurring/ipn/` |
| Guest manage/cancel (secret token) | `/donation/recurring/manage/<token>/` |

`SITE_URL` / public HTTPS must match the URLs registered with SSLCommerz. IPN must be reachable from the internet on staging/production.

#### Cron (reconciliation only)

```bash
# Every hour — claims overdue ACTIVE subscriptions for ops visibility.
# Does NOT charge cards. Settlements come from SSLCommerz IPN.
0 * * * * cd /home/ACCOUNT/zarrah-foundation && /home/ACCOUNT/virtualenv/zarrah-foundation/VERSION/bin/python manage.py charge_due_subscriptions
```

#### Retry / failure behavior

- Failed settlements increment `consecutive_failures` and notify the donor.
- At `RECURRING_DONATION_FAILURE_THRESHOLD` (default 3) the subscription becomes **SUSPENDED**.
- If SSLCommerz controls retries, reconcile via IPN rather than inventing a second charge loop.

#### Monitoring / troubleshooting

- Admin → Recurring Donations: status, next billing, charge history, IPN events.
- Check `GatewayWebhookEvent` processing status for duplicate/forged IPNs.
- Amount validation uses gateway `amount` (customer charged), not `store_amount`.
- Never log SALT, store password, PAN, CVV, or wallet PINs.

#### Security requirements

- Do not activate a subscription from browser return alone — always validate via SSLCommerz.
- Guest management is token-based (not incrementing IDs); rate-limited.
- Duplicate IPN must not create duplicate Transaction / Donation / Income.
- Production GO requires public HTTPS staging proof of real recurring auth + IPN.

### Meeting reminders

Schedule the existing management command (idempotent; default lead time **24 hours**):

```bash
# Every 15–30 minutes is enough; the command only sends inside a 1-hour window
*/15 * * * * cd /home/ACCOUNT/zarrah-foundation && /home/ACCOUNT/virtualenv/zarrah-foundation/VERSION/bin/python manage.py send_meeting_reminders
```

Optional dry-run: `python manage.py send_meeting_reminders --dry-run`

Do not invent a second scheduler (Celery/Redis are out of scope for this deployment).

## 8. Governance document dependencies

`requirements.txt` already includes:

- `reportlab` + `uharfbuzz` — Bengali-capable PDF shaping (`core/pdf_fonts.py`, Noto Sans Bengali under `static/fonts/`)
- `python-docx` — official Word/DOCX resolution export
- `Pillow` — signature image validation

After `pip install -r requirements.txt`, confirm fonts exist:

```bash
ls static/fonts/NotoSansBengali-Regular.ttf
```

No extra OS packages are required beyond a normal Python virtualenv with those wheels, unless your host lacks a working TrueType path for ReportLab (fonts are bundled in-repo).

## 9. Post-deploy smoke checks

1. `python manage.py check --deploy`
2. Homepage CSS loads from `/static/`
3. Guessing `/media/members/...` returns 403/404
4. Authorized staff can open application docs via `/protected-media/...`
5. Public report download still works
6. Login over HTTPS sets Secure cookies
7. Resolution PDF/DOCX download works for authorized users; public share uses token endpoints only
8. `/protected-media/members/signatures/...` is denied to anonymous users

## 10. Payment staging validation checklist (HTTPS required)

**FINAL STATUS remains NO-GO / VALIDATION PENDING until every applicable item below is proven on public HTTPS staging with real sandbox (or live) credentials.**

Do **not** mark PRODUCTION GO from automated tests alone.

### Preflight

```bash
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test --keepdb
# Focused payment suites
python manage.py test donations.tests_webhook_hardening donations.tests_recurring donations.tests_payment_center members.tests_public_fee_payment members.tests_billing --keepdb
```

Confirm:

- [ ] `DEBUG=False`
- [ ] `SITE_URL` is public HTTPS
- [ ] isolated staging database
- [ ] Secure cookies + `SECURE_SSL_REDIRECT` + HSTS
- [ ] `ALLOW_MOCK_AUTOPAY_WHEN_DEBUG_FALSE` remains unset/`False`
- [ ] SSLCommerz store ID / password configured
- [ ] Recurring: SALT + plan refer present **only if** testing recurring
- [ ] IPN URLs reachable from the internet (not localhost)

### Callback / IPN URLs (register with SSLCommerz)

| Flow | Paths |
|------|--------|
| One-time donation | `/donation/success/`, `/donation/fail/`, `/donation/cancel/`, `/donation/ipn/` |
| Recurring donation | `/donation/recurring/success|fail|cancel/`, `/donation/recurring/ipn/` |
| Membership fee | success/fail/cancel/IPN routes registered for fee checkout |
| Anonymous fee | `/membership-fee-payment/` → SSLCommerz → same fee IPN/callback family |

### SSLCommerz one-time

- [ ] Donation success (browser return + server validation)
- [ ] Donation fail / cancel
- [ ] Donation IPN
- [ ] Duplicate IPN → one Donation / one Income / one `GatewayWebhookEvent` business effect
- [ ] Anonymous membership fee (current month only)
- [ ] Invalid Membership ID rejected
- [ ] Other month blocked for anonymous users

### SSLCommerz recurring

- [ ] Checkout refused when SALT/plan missing (clear message; no MOCK fallback)
- [ ] Authorization → ACTIVE only after validated gateway response
- [ ] Scheduled settlement IPN → one `DonationRecurringCharge` + Transaction + Donation + Income
- [ ] Duplicate recurring IPN → no second charge/Income
- [ ] Failure → `PAYMENT_FAILED`; threshold → `SUSPENDED`
- [ ] Cancel request → `CANCELLED`
- [ ] `charge_due_subscriptions` reconciles only (does not invent card charges)

### Membership AutoPay (separate from DonationSubscription)

- [ ] Authorization + monthly charge path as implemented
- [ ] Prepaid months protected
- [ ] Duplicate gateway event cannot double-pay a month
- [ ] Production MOCK guard refuses when `DEBUG=False`

### Refunds

- [ ] Finance/Executive request per RBAC
- [ ] Only Super Admin approve
- [ ] Approval ≠ money moved
- [ ] Provider confirmation required before `REFUNDED`
- [ ] Provider failure stays `FAILED`
- [ ] Duplicate refund processing blocked

### bKash / Nagad

- [ ] Only test capabilities that are **actually implemented and configured**
- [ ] Recurring must remain **Not implemented** until merchant agreement APIs are wired and verified
- [ ] Public UI must not offer unsupported recurring options

### Evidence to retain

- Screenshots / gateway dashboard refs for auth + IPN
- `GatewayWebhookEvent` rows for first + duplicate deliveries
- Income/Donation/MembershipFeePayment counts proving idempotency
- Cron logs for `charge_due_subscriptions` (reconcile-only)

### Production GO rule

All critical gateway proofs above + full automated suite green + security checks.

If any critical item is missing: **FINAL STATUS = NO-GO**.
