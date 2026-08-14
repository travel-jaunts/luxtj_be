"""Fixed permission catalog for every admin page / API area.

Keep in sync with luxtj_admin_app/src/lib/permissions.ts
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDefinition:
    code: str
    name: str
    description: str
    resource: str
    action: str


def _p(code: str, name: str, description: str) -> PermissionDefinition:
    resource, _, action = code.rpartition(".")
    return PermissionDefinition(code, name, description, resource or code, action or "view")


PERMISSION_DEFINITIONS: tuple[PermissionDefinition, ...] = (
    # Core
    _p("dashboard.view", "View dashboard", "Access the admin dashboard"),
    _p("action_centre.view", "View action centre", "Access the action centre"),
    # Access control
    _p("roles.list", "List roles", "List all admin roles"),
    _p("roles.view", "View role", "View a single role and its permissions"),
    _p("roles.create", "Create role", "Create a role and assign permissions"),
    _p("roles.edit", "Edit role", "Update role details and permissions"),
    _p("admin_users.list", "List staff users", "List staff users"),
    _p("admin_users.view", "View admin user", "View a single admin user"),
    _p("admin_users.create", "Create admin user", "Create an admin user and assign a role"),
    _p("admin_users.edit", "Edit admin user", "Update an admin user"),
    # Inventory
    _p("inventory.villas.view", "View villa inventory", "Access villa inventory"),
    _p("inventory.activities.view", "View activity inventory", "Access activity inventory"),
    _p("inventory.hotels.view", "View hotel inventory", "Browse CRS hotel catalogue and rooms"),
    # Customers
    _p("customers.view", "View customers", "Access customer list"),
    _p("customers.bookings.view", "View customer bookings", "Access customer bookings"),
    _p("customers.payments.view", "View customer payments", "Access customer payments and refunds"),
    _p(
        "customers.pricing.view",
        "View customer pricing",
        "Access customer pricing, offers and discounts",
    ),
    _p("customers.support.view", "View customer support", "Access customer support tickets"),
    # Partners
    _p("partners.property.view", "View property partners", "Access property partners"),
    _p("partners.activity.view", "View activity partners", "Access activity partners"),
    _p("partners.b2b.view", "View B2B agents", "Access B2B agents"),
    _p("partners.affiliates.view", "View affiliates", "Access affiliates"),
    _p("partners.approvals.view", "View partner approvals", "Access partner approval APIs"),
    _p("partners.approvals.kyc.view", "View KYC approvals", "Access partner KYC approvals"),
    _p(
        "partners.approvals.content.view",
        "View content approvals",
        "Access partner content approvals",
    ),
    _p(
        "partners.pricing.view",
        "View partner pricing",
        "Access partner pricing, offers and discounts",
    ),
    _p("partners.payments.view", "View partner payments", "Access partner payments and refunds"),
    # Pricing
    _p("pricing.base.view", "View base pricing", "Access base pricing"),
    _p("pricing.promotions.view", "View promotions", "Access pricing promotions"),
    _p("pricing.commissions.view", "View agent commissions", "Access agent commission pricing"),
    _p("pricing.coupons.view", "View coupon codes", "Access coupon codes"),
    # Payments
    _p("payments.customer.view", "View customer payment hub", "Access customer payments hub"),
    _p("payments.refunds.view", "View refunds hub", "Access refunds hub"),
    _p("payments.payouts.view", "View partner payouts", "Access partner payouts"),
    _p("payments.commissions.view", "View commission tracking", "Access commission tracking"),
    # Refund queues (ops)
    _p(
        "refund_queues.flight.view",
        "View flight refund queues",
        "Access flight bookings awaiting refund",
    ),
    _p(
        "refund_queues.flight.refund",
        "Issue flight refunds",
        "Process API or manual refunds for flight payments",
    ),
    _p(
        "refund_queues.hotel.view",
        "View hotel refund queues",
        "Access hotel bookings awaiting refund",
    ),
    _p(
        "refund_queues.hotel.refund",
        "Issue hotel refunds",
        "Process API or manual refunds for hotel payments",
    ),
    # Marketing
    _p("marketing.view", "View marketing", "Access marketing module"),
    _p("marketing.campaigns.view", "View campaigns", "Access marketing campaigns"),
    _p("marketing.promos.view", "View promo codes", "Access marketing promo codes"),
    _p("marketing.leads.view", "View lead sources", "Access marketing lead sources"),
    # CMS
    _p("cms.pages.view", "View CMS pages", "Access CMS pages"),
    _p("cms.blogs.view", "View CMS blogs", "Access CMS blogs"),
    _p("cms.seo.view", "View CMS SEO", "Access CMS SEO"),
    # Reports
    _p("reports.sales.view", "View sales reports", "Access sales reports"),
    _p("reports.finance.view", "View finance reports", "Access finance reports"),
    _p("reports.customer.view", "View customer reports", "Access customer reports"),
    _p("reports.operations.view", "View operations reports", "Access operations reports"),
    _p("reports.booking.view", "View booking reports", "Access booking reports"),
    _p(
        "reports.flight_bookings.view",
        "View flight booking reports",
        "Access flight booking list and detail reports",
    ),
    _p(
        "reports.flight_bookings.cancel",
        "Cancel flight bookings",
        "Cancel or VOID flight bookings from admin reports",
    ),
    _p(
        "reports.hotel_bookings.view",
        "View hotel booking reports",
        "Access hotel booking list and detail reports",
    ),
    _p(
        "reports.hotel_bookings.cancel",
        "Cancel hotel bookings",
        "Cancel hotel bookings from admin reports",
    ),
    _p("reports.partner.view", "View partner reports", "Access partner reports"),
    _p("reports.marketing.view", "View marketing reports", "Access marketing reports"),
    # Approvals (global)
    _p("approvals.content.view", "View content approvals hub", "Access content approvals hub"),
    _p("approvals.discounts.view", "View discount approvals", "Access discount approvals"),
    _p("approvals.refunds.view", "View refund approvals", "Access refund approvals"),
    # Support
    _p("support.tickets.view", "View support tickets", "Access support tickets"),
    _p("support.complaints.view", "View complaints", "Access complaints"),
    # Audit
    _p("audit_logs.view", "View audit logs", "Access audit logs"),
    # Integrations / settings
    _p("integrations.view", "View integrations", "View integration registry settings"),
    _p("integrations.edit", "Edit integrations", "Activate integrations and save credentials"),
    # Booking API logs (supplier HTTP audit)
    _p(
        "booking_api_logs.view", "View booking API logs", "Access booking API request/response logs"
    ),
    _p("booking_api_logs.hotel.view", "View hotel API logs", "Access hotel booking API logs"),
    _p(
        "booking_api_logs.hotel.ratehawk.view",
        "View Ratehawk API logs",
        "Access Ratehawk supplier HTTP logs",
    ),
    _p("booking_api_logs.flight.view", "View flight API logs", "Access flight booking API logs"),
    _p(
        "booking_api_logs.flight.citytravel.view",
        "View City Travel API logs",
        "Access City Travel supplier HTTP logs",
    ),
    # Currency
    _p("currencies.view", "View currencies", "View active currencies"),
    _p("currencies.edit", "Edit currencies", "Activate or deactivate currencies"),
    # CRS mapping
    _p("crs.mapping.view", "View CRS mapping", "View hotel CRS supplier mapping"),
    _p("crs.mapping.edit", "Edit CRS mapping", "Run CRS city/hotel mapping jobs"),
    # Hotel markup
    _p("hotel_markup.view", "View hotel markup", "View hotel markup rules"),
    _p("hotel_markup.edit", "Edit hotel markup", "Create and edit hotel markup rules"),
    # Flight markup
    _p("flight_markup.view", "View flight markup", "View flight markup rules"),
    _p("flight_markup.edit", "Edit flight markup", "Create and edit flight markup rules"),
    # Promo codes
    _p("promo_codes.flight.view", "View flight promo codes", "View flight promo codes"),
    _p("promo_codes.flight.edit", "Edit flight promo codes", "Create and edit flight promo codes"),
    _p("promo_codes.hotel.view", "View hotel promo codes", "View hotel promo codes"),
    _p("promo_codes.hotel.edit", "Edit hotel promo codes", "Create and edit hotel promo codes"),
)


def all_permission_codes() -> frozenset[str]:
    return frozenset(item.code for item in PERMISSION_DEFINITIONS)
