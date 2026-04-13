from admin_api.customer.users.domainmodel import (
    CustomerBizKpiSummaryDomainModel,
    CustomerDomainModel,
)
from admin_api.customer.users.serializers import SignupOptionParams
from common.service.metadata import PaginationMeta
from luxtj.utils import mockutils
from admin_api.customer.users.dto import UpdateUserDTO


class CustomerUserService:
    def __init__(self):
        pass

    async def create_new_user(
        self,
        first_name: str,
        last_name: str,
        phone_number: str,
        email: str,
        *,
        signup_options: SignupOptionParams | None = None,
    ) -> CustomerDomainModel:
        """
        Create a new customer user with the provided details and signup options.
        """
        # TODO: implement actual create logic here
        # interface with keycloak to create user and assign roles based on signup options
        return CustomerDomainModel.generate_mock()
    
    async def update_user(
        self,
        customer_id: str,
        update_user_dto: UpdateUserDTO,
    ) -> CustomerDomainModel:
        """
        Update an existing customer user with the provided details.
        """
        # TODO: implement actual update logic here
        # interface with keycloak to update user details and roles based on update_user_dto
        return CustomerDomainModel.generate_mock()

    async def delete_user(self, customer_id: str) -> None:
        """
        Delete a customer user
        """
        # TODO: implement actual delete logic here
        # interface with keycloak to delete user
        pass

    async def get_list(
        self, page: int, page_size: int, *, iso_currency_str: str
    ) -> tuple[list[CustomerDomainModel], PaginationMeta]:
        """
        Fetch a paginated list of customers from the database.
        - page: The page number to fetch (starting from 1)
        - page_size: The number of items per page
        Returns a tuple of (list of customers, pagination metadata)
        """
        # TODO: Implement actual fetching logic here

        num_items = mockutils.random.randint(1, 10)  # To ensure randomness in generated mock data
        customer_list = [
            CustomerDomainModel.generate_mock(mock_currency=iso_currency_str)
            for _ in range(num_items)
        ]
        return customer_list, PaginationMeta(total=num_items, page=page, size=page_size)

    async def get_biz_kpi_summary(
        self, *, iso_currency_str: str
    ) -> CustomerBizKpiSummaryDomainModel:
        """
        Fetch business KPI summary for customers.
        - iso_currency_str: The ISO currency code to use for monetary values in the summary
        Returns a CustomerBizKpiSummaryDomainModel containing the KPI data.
        """
        # TODO: Implement actual fetching logic here
        return CustomerBizKpiSummaryDomainModel.generate_mock(mock_currency=iso_currency_str)
