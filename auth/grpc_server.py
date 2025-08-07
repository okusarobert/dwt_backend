import os
import json
import grpc
from concurrent import futures
from shared.proto import auth_pb2, auth_pb2_grpc
from db.connection import session
from db.wallet import Account, CryptoAddress
from shared.crypto.HD import TRX as TRX_WALLET
from db.models import User, Profile
import jwt
from decouple import config
import logging
import pyotp
from db.utils import generate_random_digits
from shared.logger import setup_logging
import traceback
from shared.kafka_producer import get_kafka_producer

USER_REGISTERED_TOPIC = os.getenv("USER_REGISTERED_TOPIC", "user.registered")

logger = setup_logging()

class AuthServiceServicer(auth_pb2_grpc.AuthServiceServicer):
    def QRLogin(self, request, context):
        user = session.query(User).filter_by(id=request.account_ref).first()
        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('Account not found')
            return auth_pb2.QRLoginResponse(status="error")
        # user = account.user
        profile = user.profile
        # Check if profile is complete (implement is_complete logic)
        if not profile or not (profile.first_name and profile.last_name and profile.email and profile.phone_verified):
            return auth_pb2.QRLoginResponse(status="incomplete_profile", user_id=str(user.id))
        # TODO: Generate auth token/session
        token = "dummy_token"  # Replace with real token logic
        return auth_pb2.QRLoginResponse(status="success", user_id=str(user.id), token=token)

    def CompleteProfile(self, request, context):
        user = session.query(User).filter_by(id=request.user_id).first()
        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details('User not found')
            return auth_pb2.CompleteProfileResponse(status="error")
        profile = user.profile
        if not profile:
            profile = Profile(user_id=user.id)
            session.add(profile)
        profile.first_name = request.first_name
        profile.last_name = request.last_name
        profile.email = request.email
        profile.phone_verified = True  # Assume verified for demo
        profile.country = "UG"
        session.commit()
        return auth_pb2.CompleteProfileResponse(status="profile_updated")

    def EmailLogin(self, request, context):
        email = request.email
        password = request.password
        user = session.query(User).filter(User.email == email.lower()).first()
        if not user:
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details('Invalid credentials')
            return auth_pb2.EmailLoginResponse(token="")
        # TODO: Add real password verification here
        secret = config("JWT_SECRET")
        payload = {"user_id": user.id, "email": user.email}  # No expiration
        encoded = jwt.encode(payload, secret, algorithm="HS256")
        return auth_pb2.EmailLoginResponse(token=encoded)

    def Register(self, request, context):
        from db.dto import RegisterDto, validate_registration
        from db.utils import generate_password_hash
        from db.models import User
        try:
            # logger = logging.getLogger("grpc_server")
            data = RegisterDto(
                email=request.email,
                phone_number=request.phone_number,
                first_name=request.first_name,
                last_name=request.last_name,
                password=request.password,
                password_confirm=request.password_confirm,
                sponsor_code=request.sponsor_code
            )
            errors = validate_registration(data, session, logger)
            if errors:
                return auth_pb2.RegisterResponse(status="error", error=json.dumps(errors))
            hashed_pwd = generate_password_hash(data.password)
            ref_code = f"{generate_random_digits(8)}"
            found = True
            while found:
                ref_found = session.query(User).filter_by(ref_code=ref_code).first()
                if not ref_found:
                    found = False
                else:
                    ref_code = f"{generate_random_digits(8)}"
            # user.ref_code = f"{ref_code}"
            logger.info(f"Registering user: {ref_code}")
            user = User(
                email=data.email.lower(),
                phone_number=data.phone_number,
                first_name=data.first_name,
                last_name=data.last_name,
                encrypted_pwd=hashed_pwd,
                sponsor_code=data.sponsor_code,
                default_currency="UGX",
                country="UG",
                ref_code=ref_code
            )
            
            session.add(user)
            # session.commit()
            totp_secret = pyotp.random_base32()
            profile = Profile(
                user_id=user.id, two_factor_key=totp_secret, two_factor_enabled=True)
            session.add(profile)
            session.commit()

            # account = Account()
            # account.user_id = user.id
            # account.currency_code = "UGX"
            # account.balance = 0
            # account.locked_amount = 0
            # # account.status = AccountStatus.ACTIVE
            # session.add(account)
            # session.commit()

            producer = get_kafka_producer()
            producer.send(USER_REGISTERED_TOPIC, {"user_id": user.id})

            # Optionally, provide the provisioning URI for the client to generate a QR code:
            provisioning_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
                name=user.email, issuer_name="Tondeka"
            )

            return auth_pb2.RegisterResponse(status="success", 
                                            uri=provisioning_uri,
                                            user_id=str(user.id))
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            logger.error(traceback.format_exc())

            return auth_pb2.RegisterResponse(status="error", error=str(errors))

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve() 