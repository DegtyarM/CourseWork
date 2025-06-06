from sqlalchemy import Column, Integer, VARCHAR, DATE, select, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

BaseModel = declarative_base()


class User(BaseModel):
    __tablename__ = "users"

    user_id = Column(Integer, unique=True, nullable=False, primary_key=True)

    username = Column(VARCHAR(32), nullable=True)

    first_name = Column(VARCHAR(64), nullable=True)

    last_name = Column(VARCHAR(64), nullable=True)

    reg_date = Column(DATE, default=datetime.today())

    upd_date = Column(DATE, onupdate=datetime.today())

    wrong_addresses = relationship("WrongAddresses", back_populates="user", cascade="all, delete-orphan")

    def __str__(self):
        return f"User: {self.user_id}"

    @staticmethod
    async def user_exists(event, session: AsyncSession) -> bool:
        result = await session.execute(select(User).where(User.user_id == event.from_user.id))
        user: User = result.scalar_one_or_none()
        return user


class WrongAddresses(BaseModel):
    __tablename__ = "wrong_addresses"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)

    address = Column(VARCHAR(100), nullable=False)

    place = Column(VARCHAR(32), nullable=False)

    message_date = Column(DATE, default=datetime.today())

    user = relationship("User", back_populates="wrong_addresses")
