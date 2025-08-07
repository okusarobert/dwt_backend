import enum
from .base import Base, Timestamped
from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    Text,
    LargeBinary
)
from sqlalchemy.orm import relationship, Mapped, mapped_column


class UserRole(enum.Enum):
    ADMIN = "admin"
    USER = "user"
    # AGENT = "agent"
    # SUPERAGENT = "superagent"
    # MERCHANT = "merchant"


class User(Timestamped):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone_number: Mapped[str] = mapped_column(String(255))
    encrypted_pwd: Mapped[str] = mapped_column(String(255))
    ref_code: Mapped[str] = mapped_column(String(10))
    sponsor_code: Mapped[str | None] = mapped_column(String(10))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    country: Mapped[str] = mapped_column(String(2))
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    default_currency: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)

    profile = relationship("Profile", back_populates="user", uselist=False)
    accounts = relationship("Account", back_populates="user")
    # wallets = relationship("Wallet", back_populates="user")
    # orders = relationship("Order", back_populates="user")
    # deposits = relationship("Deposit", back_populates="user")
    # bets = relationship("Bet", back_populates="user")
    # bonuses = relationship("Bonus", back_populates="user")
    password_codes = relationship(
        "ForgotPassword", back_populates="user", passive_deletes=True)
    email_verify_codes = relationship(
        "EmailVerify", back_populates="user", passive_deletes=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<User {self.id}: {self.first_name} {self.last_name}>"


class Profile(Timestamped):
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_key: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=True, index=True)
    user = relationship("User", back_populates="profile")


class ForgotPasswordStatus(enum.Enum):
    PENDING = "pending"
    USED = "used"
    EXPIRED = "expired"


class ForgotPassword(Timestamped):
    __tablename__ = "forgot_passwords"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(8))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=True, index=True)
    user = relationship("User", back_populates="password_codes")
    status: Mapped[ForgotPasswordStatus] = mapped_column(
        Enum(ForgotPasswordStatus), nullable=False)


class EmailVerifyStatus(enum.Enum):
    PENDING = "pending"
    USED = "used"
    EXPIRED = "expired"


class EmailVerify(Timestamped):
    __tablename__ = "email_verifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(
        "users.id", ondelete="CASCADE"), nullable=True, index=True)
    user = relationship("User", back_populates="email_verify_codes")
    status: Mapped[EmailVerifyStatus] = mapped_column(
        Enum(EmailVerifyStatus), nullable=False)


class CurrencyType(enum.Enum):
    CRYPTO = "crypto"
    FIAT = "fiat"

class Currency(Base):
    __tablename__ = "currencies"
    id = Column(Integer, primary_key=True)
    code = Column(String(8), unique=True, nullable=False, index=True)  # e.g., BTC, ETH, UGX
    name = Column(String(32), nullable=False)
    type = Column(Enum(CurrencyType), nullable=False)
    symbol = Column(String(8), nullable=True)
    decimals = Column(Integer, default=2)
    is_active = Column(Boolean, default=True)

