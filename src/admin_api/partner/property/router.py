from typing import Annotated

from fastapi import APIRouter, Depends, Query

from luxtj.domain.enums import PartnerStatusControlActionEnum
from admin_api.partner.property.serializers import PartnerBizKpiSummary, PropertyPartnerLineItem, PropertyPartnerDetails
from admin_api.partner.property.service import PartnerService
from common.serializerlib import (
    AmountSerializer,
    ApiSuccessResponse,
    PaginatedResult,
    PaginationParams,
    RequestProcessStatus,
    ImageMetadataSerializer,
    LocationMetadataSerializer,
    BankDetailsSerializer,
)
from luxtj.utils import mockutils

property_partner_router = APIRouter()


@property_partner_router.post(
    "/kpi-summary",
    response_model=ApiSuccessResponse[PartnerBizKpiSummary],
    status_code=200,
    summary="Get partners KPI summary",
    name="Partner KPI Summary",
)
async def property_partner_kpi_summary(
    partner_service: Annotated[PartnerService, Depends(PartnerService)],
) -> ApiSuccessResponse[PartnerBizKpiSummary]:
    """
    Get partner KPI summary
    """
    # TODO: access control: restrict this endpoint to admin users only
    kpi_summary = await partner_service.get_biz_kpi_summary()
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PartnerBizKpiSummary.from_domain_model(kpi_summary),
    )


@property_partner_router.post(
    "/list",
    response_model=ApiSuccessResponse[PaginatedResult[PropertyPartnerLineItem]],
    status_code=200,
    summary="Get list of partners KPI summaries",
    name="List Partner KPI Summaries",
)
async def list_property_partners(
    partner_service: Annotated[PartnerService, Depends(PartnerService)],
    query: Annotated[PaginationParams, Depends()],
) -> ApiSuccessResponse[PaginatedResult[PropertyPartnerLineItem]]:
    """
    Get list of property partners
    """
    # TODO: access control: restrict this endpoint to admin users only

    property_partners_list, pagination_meta = await partner_service.get_list(
        page=query.page, page_size=query.size
    )
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PaginatedResult[PropertyPartnerLineItem](
            total=pagination_meta.total,
            page=pagination_meta.page,
            size=pagination_meta.size,
            items=[
                PropertyPartnerLineItem.from_domain_model(partner)
                for partner in property_partners_list
            ],
        ),
    )


@property_partner_router.post(
    "/{partner_id}/details",
    response_model=ApiSuccessResponse[PropertyPartnerDetails],
    status_code=200,
    summary="Get detailed information about a specific property partner",
    name="Property Partner Details",
)
async def property_partner_details(
    partner_service: Annotated[PartnerService, Depends(PartnerService)],
    partner_id: str,
) -> ApiSuccessResponse[PropertyPartnerDetails]:
    """
    Get detailed information about a specific property partner
    """
    # TODO: access control: restrict this endpoint to admin users only
    # TODO: implement actual update logic here
    # partner_details = await partner_service.get_details(partner_id)
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK,
        output=PropertyPartnerDetails(
            partner_id=partner_id,
            property_name=mockutils.random_property_name(),
            property_owner_name="Mock Owner Name",
            property_contact_number="1234567890",
            partner_email="mockemail@example.com",
            property_address="123 Mock Street, Mock City, Mock Country",
            property_images=[
                ImageMetadataSerializer(
                    url="https://example.com/mock-image.jpg",
                    alt_text="Mock Image",
                    image_size_bytes=102400,
                    mime_type="image/jpeg",
                    luxtj_id=mockutils.random_booking_id(),
                )
            ],
            property_base_price=AmountSerializer(amount=100.0, currency="USD"),
            seasonal_prices=AmountSerializer(amount=150.0, currency="USD"),
            offers=[],
            partner_pan_number="ABCDE1234F",
            partner_gst_number="22ABCDE1234F1Z5",
            partner_bank=BankDetailsSerializer(
                account_holder_name="Mock Owner Name",
                account_number="123456789012",
                ifsc_code="MOCK0001234",
                bank_name="Mock Bank",
            ),
            kyc_documents=[
                ImageMetadataSerializer(
                    url="https://example.com/mock-kyc-document.jpg",
                    alt_text="Mock KYC Document",
                    image_size_bytes=204800,
                    mime_type="image/jpeg",
                    luxtj_id=mockutils.random_booking_id(),
                )
            ],
            property_amenities=["Free Wi-Fi", "Swimming Pool", "Gym"],
            property_description="This is a mock property description.",
            property_location=LocationMetadataSerializer(
                latitude=12.9716,
                longitude=77.5946,
                address_line1="123 Mock Street",
                address_line2=None,
                city="Mock City",
                state="Mock State",
                postal_code="123456",
                country="Mock Country",
            ),
            property_room_types=["Deluxe", "Suite"],
        ),
    )


@property_partner_router.post(
    "/{partner_id}/details-update",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Update detailed information about a specific property partner",
    name="Property Partner Details Update",
)
async def property_partner_details_update(
    partner_service: Annotated[PartnerService, Depends(PartnerService)],
    partner_id: str,
) -> ApiSuccessResponse[str]:
    # TODO: access control: restrict this endpoint to admin users only
    # TODO: implement actual update logic here
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK, 
        output=f"Property partner {partner_id} details updated successfully"
    )


@property_partner_router.post(
    "/{partner_id}/status-control",
    response_model=ApiSuccessResponse[str],
    status_code=200,
    summary="Status control for a property partner",
    name="Property Partner Status Update",
)
async def property_partner_status_control(
    partner_service: Annotated[PartnerService, Depends(PartnerService)],
    updated_status: Annotated[PartnerStatusControlActionEnum, Query(..., alias="to")],
    partner_id: str,
) -> ApiSuccessResponse[str]:
    # TODO: access control: restrict this endpoint to admin users only
    # TODO: implement actual status update logic here
    return ApiSuccessResponse(
        status=RequestProcessStatus.OK, 
        output=f"Property partner {partner_id} status updated to '{updated_status}' successfully"
    )
