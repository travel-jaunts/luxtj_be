"""Fixed permission catalog for admin routes.

Permission codes are stable identifiers assigned to roles.
Add new codes here when new admin routes are introduced.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDefinition:
    code: str
    name: str
    description: str
    resource: str
    action: str


# Identity / RBAC management
PERMISSION_DEFINITIONS: tuple[PermissionDefinition, ...] = (
    PermissionDefinition(
        "roles.list", "List roles", "List all admin roles", "roles", "list"
    ),
    PermissionDefinition(
        "roles.view", "View role", "View a single role and its permissions", "roles", "view"
    ),
    PermissionDefinition(
        "roles.create", "Create role", "Create a role and assign permissions", "roles", "create"
    ),
    PermissionDefinition(
        "roles.edit", "Edit role", "Update role details and permissions", "roles", "edit"
    ),
    PermissionDefinition(
        "admin_users.list",
        "List admin users",
        "List admin users",
        "admin_users",
        "list",
    ),
    PermissionDefinition(
        "admin_users.view",
        "View admin user",
        "View a single admin user",
        "admin_users",
        "view",
    ),
    PermissionDefinition(
        "admin_users.create",
        "Create admin user",
        "Create an admin user and assign a role",
        "admin_users",
        "create",
    ),
    PermissionDefinition(
        "admin_users.edit",
        "Edit admin user",
        "Update an admin user",
        "admin_users",
        "edit",
    ),
    # Existing admin surface areas (for future route wiring)
    PermissionDefinition(
        "customers.manage", "Manage customers", "Customer admin APIs", "customers", "manage"
    ),
    PermissionDefinition(
        "partners.manage", "Manage partners", "Partner admin APIs", "partners", "manage"
    ),
    PermissionDefinition(
        "reports.view", "View reports", "Reports admin APIs", "reports", "view"
    ),
    PermissionDefinition(
        "marketing.manage", "Manage marketing", "Marketing admin APIs", "marketing", "manage"
    ),
    PermissionDefinition(
        "action_centre.view",
        "View action centre",
        "Action centre admin APIs",
        "action_centre",
        "view",
    ),
    PermissionDefinition(
        "audit_logs.view", "View audit logs", "Audit log admin APIs", "audit_logs", "view"
    ),
)


def all_permission_codes() -> frozenset[str]:
    return frozenset(item.code for item in PERMISSION_DEFINITIONS)
