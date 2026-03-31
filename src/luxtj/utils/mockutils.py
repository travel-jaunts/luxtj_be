from datetime import datetime, timezone
import uuid
import random


_random_seed: int = 0
random.seed(_random_seed)


mock_currencies = ["USD", "EUR", "INR", "GBP", "JPY"]

mock_user_ids = [str(uuid.UUID(int=random.getrandbits(128), version=4)) for _ in range(100)]
mock_first_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
mock_last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]
mock_emails = [
    f"{first.lower()}.{last.lower()}@example.com"
    for first in mock_first_names
    for last in mock_last_names
]
mock_isd_codes = ["+1", "+44", "+91", "+81", "+61"]
mock_phone_numbers = [
    f"{random.choice(mock_isd_codes)}{random.randint(1000000000, 9999999999)}" for _ in range(100)
]
mock_base_locations = [
    "New York",
    "Los Angeles",
    "Chicago",
    "Houston",
    "Phoenix",
    "Philadelphia",
    "San Antonio",
    "San Diego",
]
mock_support_ticket_subjects = [
    "Issue with booking",
    "Refund request",
    "Account access problem",
    "Payment failure",
    "General inquiry",
]
mock_support_ticket_descriptions = [
    "I have an issue with my recent booking. Please assist",
    "I would like to request a refund for my last booking.",
    "I am unable to access my account. Please help.",
    "My payment failed during checkout. What should I do?",
    "I have a general inquiry about your services.",
]
mock_offer_title = ["Summer Sale", "Winter Discount", "Festive Offer"]


def random_user_id() -> str:
    return random.choice(mock_user_ids)


def random_user_first_name() -> str:
    return random.choice(mock_first_names)


def random_user_last_name() -> str:
    return random.choice(mock_last_names)


def random_user_email() -> str:
    return random.choice(mock_emails)


def random_user_phone_number() -> str:
    return random.choice(mock_phone_numbers)


def random_user_base_location() -> str:
    return random.choice(mock_base_locations)


def random_registration_date() -> datetime:
    start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
    return start_date + (end_date - start_date) * random.random()


def random_booking_id() -> str:
    return random.choice(mock_user_ids)


def random_booking_amount(start: float = 100.0, end: float = 1000.0) -> float:
    return round(random.uniform(start, end), 2)


def random_transaction_id() -> str:
    return random.choice(mock_user_ids)


def random_support_ticket_subject() -> str:
    return random.choice(mock_support_ticket_subjects)


def random_support_ticket_description() -> str:
    return random.choice(mock_support_ticket_descriptions)


def random_offer_title() -> str:
    return random.choice(mock_offer_title)
