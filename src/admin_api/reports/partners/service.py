from __future__ import annotations

from admin_api.reports.partners.domainmodel import (
    PartnerOptionDomainModel,
    PartnerReportDomainModel,
    PartnerReportTypeEnum,
    PartnerTypeEnum,
    mock_partner_report_row,
)

PARTNER_OPTIONS = [
    ("PTR-001", "Aurea Voyages"),
    ("PTR-002", "Privy Escapes"),
    ("PTR-003", "Elite Travel House"),
    ("PTR-004", "Echelon Concierge"),
    ("PTR-005", "Luxe Journey Co"),
]

B2B_OPTIONS = [
    ("B2B-001", "Atlas Corporate Travel"),
    ("B2B-002", "Nimbus Retreats"),
    ("B2B-003", "Summit Meetings"),
    ("B2B-004", "Vista Business Travel"),
    ("B2B-005", "Orbit Incentives"),
]

AFFILIATE_OPTIONS = [
    ("AFF-001", "Luxury Trails"),
    ("AFF-002", "The Stay Journal"),
    ("AFF-003", "Weekend Curator"),
    ("AFF-004", "Nomad Luxe"),
    ("AFF-005", "Escape Letter"),
]


class PartnerReportService:
    async def get_report(
        self,
        *,
        report_type: PartnerReportTypeEnum,
        partner_ids: list[str] | None = None,
        b2b_partner_ids: list[str] | None = None,
        affiliate_ids: list[str] | None = None,
        iso_currency_str: str,
    ) -> PartnerReportDomainModel:
        if report_type == PartnerReportTypeEnum.B2B:
            return self._b2b_performance(
                b2b_partner_ids=b2b_partner_ids,
                iso_currency_str=iso_currency_str,
            )
        if report_type == PartnerReportTypeEnum.AFFILIATE:
            return self._affiliate_performance(
                affiliate_ids=affiliate_ids,
                iso_currency_str=iso_currency_str,
            )
        return self._partner_performance(
            partner_ids=partner_ids,
            iso_currency_str=iso_currency_str,
        )

    async def search_partners(
        self,
        *,
        partner_type: PartnerTypeEnum,
        search_query: str | None = None,
    ) -> list[PartnerOptionDomainModel]:
        options = self._options_for_partner_type(partner_type)
        normalized_query = (search_query or "").strip().lower()
        if normalized_query:
            options = [
                (option_id, option_name)
                for option_id, option_name in options
                if normalized_query in option_id.lower() or normalized_query in option_name.lower()
            ]

        return [
            PartnerOptionDomainModel(
                partner_type=partner_type,
                partner_id=option_id,
                partner_name=option_name,
            )
            for option_id, option_name in options
        ]

    def _partner_performance(
        self,
        *,
        partner_ids: list[str] | None,
        iso_currency_str: str,
    ) -> PartnerReportDomainModel:
        partners = self._filter_options_by_id(PARTNER_OPTIONS, partner_ids)
        rows = [
            mock_partner_report_row(
                partner_type=PartnerTypeEnum.PARTNER,
                partner_id=partner_id,
                partner_name=partner_name,
                currency=iso_currency_str,
            )
            for partner_id, partner_name in partners
        ]
        return PartnerReportDomainModel.from_rows(
            report_type=PartnerReportTypeEnum.PARTNER,
            title="Partner Performance",
            currency=iso_currency_str,
            rows=rows,
        )

    def _b2b_performance(
        self,
        *,
        b2b_partner_ids: list[str] | None,
        iso_currency_str: str,
    ) -> PartnerReportDomainModel:
        partners = self._filter_options_by_id(B2B_OPTIONS, b2b_partner_ids)
        rows = [
            mock_partner_report_row(
                partner_type=PartnerTypeEnum.B2B,
                partner_id=partner_id,
                partner_name=partner_name,
                currency=iso_currency_str,
            )
            for partner_id, partner_name in partners
        ]
        return PartnerReportDomainModel.from_rows(
            report_type=PartnerReportTypeEnum.B2B,
            title="B2B Performance",
            currency=iso_currency_str,
            rows=rows,
        )

    def _affiliate_performance(
        self,
        *,
        affiliate_ids: list[str] | None,
        iso_currency_str: str,
    ) -> PartnerReportDomainModel:
        partners = self._filter_options_by_id(AFFILIATE_OPTIONS, affiliate_ids)
        rows = [
            mock_partner_report_row(
                partner_type=PartnerTypeEnum.AFFILIATE,
                partner_id=partner_id,
                partner_name=partner_name,
                currency=iso_currency_str,
            )
            for partner_id, partner_name in partners
        ]
        return PartnerReportDomainModel.from_rows(
            report_type=PartnerReportTypeEnum.AFFILIATE,
            title="Affiliate Performance",
            currency=iso_currency_str,
            rows=rows,
        )

    def _options_for_partner_type(self, partner_type: PartnerTypeEnum) -> list[tuple[str, str]]:
        if partner_type == PartnerTypeEnum.B2B:
            return B2B_OPTIONS
        if partner_type == PartnerTypeEnum.AFFILIATE:
            return AFFILIATE_OPTIONS
        return PARTNER_OPTIONS

    def _filter_options_by_id(
        self,
        options: list[tuple[str, str]],
        selected_ids: list[str] | None,
    ) -> list[tuple[str, str]]:
        if not selected_ids:
            return options

        normalized_ids = {selected_id.lower() for selected_id in selected_ids}
        return [
            (option_id, option_name)
            for option_id, option_name in options
            if option_id.lower() in normalized_ids
        ]
