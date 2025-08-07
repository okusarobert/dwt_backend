import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# --- CRITICAL: Patch engine/session BEFORE importing app/models ---
engine = create_engine("sqlite:///:memory:")
Session = scoped_session(sessionmaker(bind=engine))

import db.connection
# Patch db connection globally

db.connection.engine = engine
db.connection.session = Session()
db.connection.Session = Session

import service
service.session = db.connection.session
service.Session = Session

from db import Base, User
Base.metadata.create_all(engine)

import db.utils
from flask import g
# Patch token_required BEFORE importing the app

def always_authenticated(f):
    def wrapper(*args, **kwargs):
        g.user = db.connection.session.query(User).filter_by(id=1).first()
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

db.utils.token_required = always_authenticated

from app import app as flask_app

# Register teardown handler ONCE at module level
def remove_session(exception=None):
    if hasattr(flask_app, 'Session'):
        flask_app.Session.remove()
flask_app.teardown_appcontext(remove_session)

@pytest.fixture(scope="function")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db.connection.session = Session  # assign the scoped_session, not an instance
    service.session = db.connection.session

    # Add a test user for each test
    session = db.connection.session()
    user = User(
        id=1,
        first_name="Test",
        last_name="User",
        email="test@example.com",
        phone_number="1234567890",
        encrypted_pwd="dummy",
        ref_code="ref1",
        sponsor_code=None,
        role="USER",
        country="US",
        blocked=False,
        deleted=False
    )
    session.add(user)
    session.commit()

    flask_app.Session = Session
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client

    Session.remove()

# --- INTEGRATION TESTS ---
def test_create_account(client):
    resp = client.post('/wallet/account', headers={"Authorization": "Bearer testtoken"})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["user_id"] == 1

def test_duplicate_account(client):
    client.post('/wallet/account', headers={"Authorization": "Bearer testtoken"})
    resp = client.post('/wallet/account', headers={"Authorization": "Bearer testtoken"})
    assert resp.status_code == 400
    assert "already exists" in resp.get_json()["error"]

def test_get_balance(client):
    client.post('/wallet/account', headers={"Authorization": "Bearer testtoken"})
    resp = client.get('/wallet/balance', headers={"Authorization": "Bearer testtoken"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["balance"] == 0
    assert data["available_balance"] == 0

def test_deposit(client):
    client.post('/wallet/account', headers={"Authorization": "Bearer testtoken"})
    resp = client.post('/wallet/deposit', json={"amount": 100, "reference_id": "dep-1", "description": "Test deposit"}, headers={"Authorization": "Bearer testtoken"})
    if resp.status_code != 201:
        print('deposit:', resp.get_json())
    assert resp.status_code == 201
    data = resp.get_json()
    assert float(data["amount"]) == 100
    # Idempotency
    resp2 = client.post('/wallet/deposit', json={"amount": 100, "reference_id": "dep-1", "description": "Test deposit"}, headers={"Authorization": "Bearer testtoken"})
    assert resp2.status_code == 201
    assert resp2.get_json()["id"] == data["id"]

def test_withdraw(client):
    client.post('/wallet/account', headers={"Authorization": "Bearer testtoken"})
    client.post('/wallet/deposit', json={"amount": 200, "reference_id": "dep-2", "description": "Deposit for withdraw"}, headers={"Authorization": "Bearer testtoken"})
    resp = client.post('/wallet/withdraw', json={"amount": 50, "reference_id": "wd-1", "description": "Withdraw"}, headers={"Authorization": "Bearer testtoken"})
    if resp.status_code != 201:
        print('withdraw:', resp.get_json())
    assert resp.status_code == 201
    data = resp.get_json()
    assert float(data["amount"]) == 50
    # Insufficient funds
    resp2 = client.post('/wallet/withdraw', json={"amount": 1000, "reference_id": "wd-2", "description": "Too much"}, headers={"Authorization": "Bearer testtoken"})
    assert resp2.status_code == 400
    # Negative amount
    resp3 = client.post('/wallet/withdraw', json={"amount": -10, "reference_id": "wd-3", "description": "Negative"}, headers={"Authorization": "Bearer testtoken"})
    assert resp3.status_code == 400

def test_transfer(client):
    # Add another user and account
    session = db.connection.session
    user2 = User(
        id=2,
        first_name="Other",
        last_name="User",
        email="other@example.com",
        phone_number="0987654321",
        encrypted_pwd="dummy",
        ref_code="ref2",
        sponsor_code=None,
        role="USER",
        country="US",
        blocked=False,
        deleted=False
    )
    session.add(user2)
    session.commit()
    # Create account for user2
    from service import create_account
    create_account(user2.id, session)
    client.post('/wallet/account', headers={"Authorization": "Bearer testtoken"})
    client.post('/wallet/deposit', json={"amount": 300, "reference_id": "dep-3", "description": "Deposit for transfer"}, headers={"Authorization": "Bearer testtoken"})
    # Transfer
    resp = client.post('/wallet/transfer', json={"to": 2, "amount": 100, "reference_id": "tr-1", "description": "Transfer"}, headers={"Authorization": "Bearer testtoken"})
    if resp.status_code != 201:
        print('transfer:', resp.get_json())
    assert resp.status_code == 201
    data = resp.get_json()
    assert isinstance(data, list) and len(data) == 2
    # Insufficient funds
    resp2 = client.post('/wallet/transfer', json={"to": 2, "amount": 1000, "reference_id": "tr-2", "description": "Too much"}, headers={"Authorization": "Bearer testtoken"})
    assert resp2.status_code == 400
    # Negative amount
    resp3 = client.post('/wallet/transfer', json={"to": 2, "amount": -10, "reference_id": "tr-3", "description": "Negative"}, headers={"Authorization": "Bearer testtoken"})
    assert resp3.status_code == 400
    # Self-transfer
    resp4 = client.post('/wallet/transfer', json={"to": 1, "amount": 10, "reference_id": "tr-4", "description": "Self"}, headers={"Authorization": "Bearer testtoken"})
    assert resp4.status_code == 400

def test_transaction_history(client):
    client.post('/wallet/account', headers={"Authorization": "Bearer testtoken"})
    client.post('/wallet/deposit', json={"amount": 100, "reference_id": "dep-4", "description": "Deposit for history"}, headers={"Authorization": "Bearer testtoken"})
    resp = client.get('/wallet/transactions', headers={"Authorization": "Bearer testtoken"})
    if resp.status_code != 200:
        print('transactions:', resp.get_json())
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert any(tx["reference_id"] == "dep-4" for tx in data) 