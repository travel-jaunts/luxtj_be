# Identity & RBAC

Direct authentication/authorization for LuxTJ (Keycloak removed).

## User types

| Type | Auth APIs | RBAC |
|------|-----------|------|
| `superadmin` | admin login + me | All permissions (bypass) |
| `admin` | admin login + me | Permissions via assigned role |
| `partner` | register / login / forgot / reset / me | No roles |
| `b2c` | register / login / forgot / reset / me | No roles |

Permissions are assigned **only to roles**. Roles are assigned **only to admin users**.

## Token usage

1. Login → receive `accessToken` + `refreshToken`
2. Call protected APIs with header: `Authorization: Bearer <accessToken>`
3. JWT claims include `user_type`, `role_id`, and `permissions`

## Public auth (`/v1/auth`)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/v1/auth/register/partner` | Partner signup |
| POST | `/v1/auth/register/b2c` | B2C signup |
| POST | `/v1/auth/login` | Any user type |
| POST | `/v1/auth/forgot-password` | Issues reset token (returned in `development`) |
| POST | `/v1/auth/reset-password` | Body: token + newPassword |
| POST | `/v1/auth/me` | Requires Bearer token |

## Admin identity (`/v1/admin`)

| Method | Path | Permission |
|--------|------|------------|
| POST | `/v1/admin/auth/login` | superadmin/admin only |
| POST | `/v1/admin/auth/me` | admin portal |
| POST | `/v1/admin/permissions/list` | admin portal |
| POST | `/v1/admin/roles/list` | `roles.list` |
| POST | `/v1/admin/roles/{id}/view` | `roles.view` |
| POST | `/v1/admin/roles/create` | `roles.create` |
| POST | `/v1/admin/roles/{id}/edit` | `roles.edit` |
| POST | `/v1/admin/admin-users/list` | `admin_users.list` |
| POST | `/v1/admin/admin-users/{id}/view` | `admin_users.view` |
| POST | `/v1/admin/admin-users/create` | `admin_users.create` |
| POST | `/v1/admin/admin-users/{id}/edit` | `admin_users.edit` |

## Middleware

- `get_current_principal` — validates Bearer JWT
- `require_user_types(...)` — user-type gate
- `require_permission("code")` — permission gate (superadmin bypasses)

## Seeded superadmin

Configured via env and created on startup if missing:

```env
LTJBE_SUPERADMIN_EMAIL=superadmin@luxtj.local
LTJBE_SUPERADMIN_PASSWORD=SuperAdmin@123
LTJBE_SUPERADMIN_FULL_NAME=Super Admin
```

## Permission catalog

Fixed list in `luxtj.contexts.identity.application.permissions_catalog`.
Add new codes there when new admin routes need RBAC, then seed on next startup.
