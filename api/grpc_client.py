import grpc
from shared.proto import auth_pb2, auth_pb2_grpc

def qr_login(account_ref):
    with grpc.insecure_channel('grpc:50051') as channel:
        stub = auth_pb2_grpc.AuthServiceStub(channel)
        request = auth_pb2.QRLoginRequest(account_ref=account_ref)
        response = stub.QRLogin(request)
        return response

def complete_profile(user_id, first_name, last_name, email, phone_number, country):
    with grpc.insecure_channel('grpc:50051') as channel:
        stub = auth_pb2_grpc.AuthServiceStub(channel)
        request = auth_pb2.CompleteProfileRequest(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            country=country
        )
        response = stub.CompleteProfile(request)
        return response 

def email_login(email, password):
    with grpc.insecure_channel('grpc:50051') as channel:
        stub = auth_pb2_grpc.AuthServiceStub(channel)
        request = auth_pb2.EmailLoginRequest(email=email, password=password)
        response = stub.EmailLogin(request)
        return response.token 

def register(email, phone_number, first_name, last_name, password, password_confirm, sponsor_code, country):
    with grpc.insecure_channel('grpc:50051') as channel:
        stub = auth_pb2_grpc.AuthServiceStub(channel)
        request = auth_pb2.RegisterRequest(
            email=email,
            phone_number=phone_number,
            first_name=first_name,
            last_name=last_name,
            password=password,
            password_confirm=password_confirm,
            sponsor_code=sponsor_code,
            country=country
        )
        response = stub.Register(request)
        return response 