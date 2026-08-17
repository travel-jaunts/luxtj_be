# Account Status

Accounts have one of three statuses: `ACTIVE`, `SUSPENDED`, or `DISABLED`.

OTP verification and refresh-token exchange issue tokens only for active accounts. Protected account requests re-check the persisted status, so suspension and disablement invalidate existing access tokens immediately. Re-enabling an account permits a new OTP verification or refresh session.

Every status transition records the affected account, actor identifier, reason, previous status, new status, and timestamp in `account_status_changes`.
