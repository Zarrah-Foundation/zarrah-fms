# Membership fee business rules

1. Membership monthly fee is configurable (Dashboard → Membership Fees → Settings).
2. Default monthly fee is ৳50.
3. Membership fee starting month is configurable.
4. Existing members become liable from the configured starting month.
5. New members become liable from their membership approval month.
6. Registration fee default is ৳100.
7. Registration fee is separate from monthly membership fee (`MEMBERSHIP_REG` vs `MEMBERSHIP_FEE`).
8. Approval notification includes registration fee + running month fee.
9. Members may manually pay one or more months (including future prepaid months).
10. Prepaid future coverage keeps AutoPay OFF according to existing rules.
11. Historical completed payments are immutable (configuration changes do not rewrite paid rows).

Liability start is implemented as `max(configured_start_month, approval_month)`.
