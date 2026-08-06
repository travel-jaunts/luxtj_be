# Identity & RBAC

Direct authentication/authorization for LuxTJ admin.

## Seeded superadmin (local)

| Email | Password |
|-------|----------|
| `superadmin@luxtj.local` | `SuperAdmin@123` |

## Permission catalog (menu / route aligned)

Source of truth: `luxtj.contexts.identity.application.permissions_catalog`  
Frontend mirror: `luxtj_admin_app/src/lib/permissions.ts`

| Area | Codes |
|------|-------|
| Core | `dashboard.view`, `action_centre.view` |
| Access | `roles.*`, `admin_users.*` |
| Bookings | `bookings.modifications.view`, `bookings.cancellations.view` |
| Inventory | `inventory.villas.view`, `inventory.activities.view` |
| Customers | `customers.view`, `customers.bookings.view`, `customers.payments.view`, `customers.pricing.view`, `customers.support.view` |
| Partners | `partners.property/activity/b2b/affiliates.view`, `partners.approvals(.kyc\|.content).view`, `partners.pricing.view`, `partners.payments.view` |
| Pricing | `pricing.base/promotions/commissions/coupons.view` |
| Payments hub | `payments.customer/refunds/payouts/commissions.view` |
| Marketing | `marketing.view`, `marketing.campaigns/promos/leads.view` |
| CMS | `cms.pages/blogs/seo.view` |
| Reports | `reports.sales/finance/customer/operations/booking/partner/marketing.view` |
| Approvals hub | `approvals.content/discounts/refunds.view` |
| Support | `support.tickets/complaints.view` |
| Audit | `audit_logs.view` |

## Binding

- **Frontend**: `ROUTE_PERMISSIONS` + `AuthGuard` + sidebar filter by permission; superadmin bypasses.
- **Backend**: router-level `Depends(require_permission(...))` / `require_any_permission(...)` on admin mounts (customers, partners, reports, marketing, action-centre, audit-logs). Identity role/admin-user routes already use fine-grained codes.
- New codes are upserted on API startup via `seed_permissions`.

## Admin UI modules

- **Login** → `POST /v1/admin/auth/login` then `POST /v1/admin/auth/me`
- **Roles** → `/settings/roles` (permission picker)
- **Admin users** → `/settings/admin-users` (assign role)

## Token header

```http
Authorization: Bearer <accessToken>
```
