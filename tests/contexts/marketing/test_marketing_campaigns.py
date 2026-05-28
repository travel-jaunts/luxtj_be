import asyncio
from datetime import date

from fastapi.testclient import TestClient

from api.main import server_factory
from luxtj.contexts.marketing.application.commands import CreateCampaignCommand
from luxtj.contexts.marketing.application.use_cases import MarketingService
from luxtj.contexts.marketing.infrastructure.persistence import InMemoryMarketingRepository
from luxtj.domains.enums import CampaignChannelEnum, CampaignStatusEnum, ScheduleFrequencyEnum
from luxtj.domains.event.base import BaseDomainEvent


class CapturingEventPublisher:
    def __init__(self) -> None:
        self.events: list[BaseDomainEvent] = []

    async def publish(self, event: BaseDomainEvent) -> None:
        self.events.append(event)


def test_create_campaign_persists_campaign_and_publishes_event() -> None:
    async def run_case() -> None:
        repository = InMemoryMarketingRepository()
        event_publisher = CapturingEventPublisher()
        service = MarketingService(
            marketing_repository=repository,
            event_publisher=event_publisher,
        )

        campaign = await service.create_campaign(
            CreateCampaignCommand(
                name="Summer Escapes",
                description="Promote luxury summer itineraries",
                channel=CampaignChannelEnum.EMAIL,
                audience_segments=[],
                audience_user_ids=["user-1", "user-2"],
                content_template="Hello {{ first_name }}",
                start_date=date(2026, 6, 1),
                frequency=ScheduleFrequencyEnum.ONE_TIME,
            )
        )

        assert campaign.status == CampaignStatusEnum.DRAFT
        assert campaign.audience == ["user-1", "user-2"]
        assert await repository.get_by_id(str(campaign.id)) == campaign
        assert len(event_publisher.events) == 1
        assert event_publisher.events[0].type == "com.luxtj.marketing.campaign.created.v1"
        assert event_publisher.events[0].subject == str(campaign.id)

    asyncio.run(run_case())


def test_marketing_campaign_http_create_uses_context_adapter() -> None:
    with TestClient(server_factory()) as client:
        response = client.post(
            "/v1/admin/marketing/campaigns/create",
            json={
                "campaignName": "Festive Luxury",
                "description": "Holiday campaign",
                "channel": "email",
                "audience": {
                    "segments": [],
                    "specificUsers": ["user-42"],
                },
                "content": {
                    "template": "Book now",
                },
                "schedule": {
                    "startDate": "2026-06-15",
                    "frequency": "one-time",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["output"]["campaignName"] == "Festive Luxury"
    assert payload["output"]["status"] == "draft"
    assert payload["output"]["audience"][0]["userId"] == "user-42"
