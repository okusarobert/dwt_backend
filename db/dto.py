from pydantic import BaseModel, Field
from typing import Literal, List, Tuple, Optional
from .models import User, ForgotPassword, ForgotPasswordStatus
from flask import request
from .utils import allowed_file, verify_password
from typing import Optional
from email_validator import validate_email, EmailNotValidError
import redis

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

# auth


class RegisterDto(BaseModel):
    email: str = Field(...)
    phone_number: str = Field(...)
    first_name: str = Field(...)
    last_name: str = Field(...)
    password: str = Field(...)
    password_confirm: Optional[str] = None
    sponsor_code: Optional[str] = None


class UpdateUserDto(BaseModel):
    email: str = Field(...)
    first_name: str = Field(...)
    last_name: str = Field(...)
    password: Optional[str] = None
    password_confirm: Optional[str] = None


def validate_update_user(data: UpdateUserDto, id: int, session) -> dict:
    errors = dict()
    if data.first_name == "":
        errors["first_name"] = "First name is required"
    if data.last_name == "":
        errors["last_name"] = "Last name is required"
    else:
        email = session.query(User).filter(
            User.email == data.email.lower()).filter(User.id != id).first()
        if email is not None:
            errors["email"] = "Email already exists"
    if data.password is not None:
        if data.password != data.password_confirm:
            errors["password_confirm"] = "Passwords do not match"

    return errors


class LoginDto(BaseModel):
    email: str = Field(...)
    password: str = Field(...)


class ForgotPasswordDto(BaseModel):
    email: str = Field(...)


class VerifyEmailDto(BaseModel):
    code: str = Field(...)


class VerifyResetPasswordDto(BaseModel):
    code: str = Field(...)


class ResetPasswordDto(BaseModel):
    code: str = Field(...)
    password: str = Field(...)
    password_confirm: str = Field(...)


def validate_registration(data: RegisterDto, session, logger) -> dict:
    logger.info("session: %r", session)
    logger.info("User: %r", User)
    errors = dict()
    # return errors
    if data.email == "":
        errors["email"] = "Email is required"
    try:
        # Validate and return the normalized email
        validate_email(data.email)

    except EmailNotValidError as e:
        # Return the error message
        errors["email"] = "Invalid email address"
    # check if email is registered already
    if not "email" in errors:
        userExists = session.query(User).filter(
            User.email == data.email.lower()).first()
        if userExists is not None:
            errors["email"] = "Email address is already registered"
    if data.first_name == "":
        errors["first_name"] = "First name is required"
    if data.last_name == "":
        errors["last_name"] = "Last name is required"
    if data.password == "":
        errors["password"] = "Password is required"
    elif data.password != data.password_confirm:
        errors["password_confirm"] = "Passwords do not match"
    is_valid, err = validate_password(data.password)
    if not is_valid and err is not None:
        errors["password"] = err[0]
    if data.sponsor_code is not None:
        sponsor = session.query(User).filter(
            User.ref_code == data.sponsor_code).first()
        # if sponsor is None:
        #     errors["sponsor_code"] = "Invalid referral link used. Please ask your sponsor for the correct link"
    return errors


def validate_reset_pwd(data: ResetPasswordDto) -> dict:
    errors = dict()
    if data.password == "":
        errors["password"] = "Password is required"
    if data.password_confirm != data.password:
        errors["password_confirm"] = "Passwords do not match"
    is_valid, err = validate_password(data.password)
    if not is_valid and err is not None:
        errors["password"] = err[0]
    code = ForgotPassword.query.filter(ForgotPassword.code == data.code).filter(
        ForgotPassword.status == ForgotPasswordStatus.PENDING).first()
    if code is None:
        errors["code"] = "Invalid verification code"
    return errors


def validate_login(data: LoginDto, session) -> dict:
    errors = dict()
    if data.email == "":
        errors["email"] = "Email address is required"
    if data.password == "":
        errors["password"] = "Password is required"

    user = session.query(User).filter(User.email == data.email.lower()).first()
    if user is None:
        errors["general"] = "Email / password combination is incorrect"
    else:
        valid_password = verify_password(data.password, user.encrypted_pwd)
        if not valid_password:
            errors["general"] = "Email / password combination is incorrect"
    return errors


def validate_forgot_password(data: ForgotPasswordDto) -> dict:
    errors = dict()

    if data.email == "":
        errors["email"] = "Email is required"
    try:
        # Validate and return the normalized email
        validate_email(data.email)

    except EmailNotValidError as e:
        # Return the error message
        errors["email"] = "Invalid email address"
    userExists = User.query.filter(User.email == data.email).first()
    if userExists is None:
        errors["message"] = "If account matching the email address is found, a six digit code has been sent to your email address"
    return errors


def validate_password(password) -> tuple[bool, list[str] | None]:
    # Regular expression for validation
    errors: list[str] = []

    if len(password) < 6:
        errors.append("Password must be at least 6 characters long.")
    if not any(char.islower() for char in password):
        errors.append("Password must contain at least one lowercase letter.")
    if not any(char.isupper() for char in password):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(char.isdigit() for char in password):
        errors.append("Password must contain at least one digit.")
    if not any(char in "@$!%*?&" for char in password):
        errors.append(
            "Password must contain at least one special character (@$!%*?&).")

    return False if errors else True,  errors if errors else None
