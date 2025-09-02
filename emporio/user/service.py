from sqlalchemy.sql import text

from emporio.core.context import RequestContext
from sqlalchemy.ext.asyncio import AsyncSession


class UserService:
    @staticmethod
    async def register_new_user():
        """
        Register a new user in the system.

        This method should contain the logic to create a new user, including
        validation, database operations, and any other necessary steps.

        Returns:
            dict: A dictionary containing the user ID and phone number of the newly registered user.
        """
        db: AsyncSession = RequestContext.get_db_session()

        # Perform any startup tasks that require a database connection here
        # result = await db.execute(text("SELECT rolname, rolpassword FROM pg_authid;"))
        result = await db.execute(text(f"SELECT '{str(db)}'"))
        print(
            result.all()
        )  # This is just for demonstration; remove in production

        # Placeholder for actual implementation
        return {"user_id": "new_user_id", "phone_number": "1234567890"}
