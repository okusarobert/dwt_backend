import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db import Base, User
from db.wallet import Account, Transaction
from service import create_account, get_balance, deposit, withdraw, transfer

@pytest.fixture(scope="module")
def engine():
    return create_engine("sqlite:///:memory:")

@pytest.fixture(scope="module")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def db_session(engine, tables):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    # Add a test user with all required fields
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
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_user_id():
    return 1

@pytest.fixture
def other_user_id(db_session):
    user = User(
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
    db_session.add(user)
    db_session.commit()
    return 2

def test_create_account(db_session, test_user_id):
    account = create_account(test_user_id, db_session)
    assert isinstance(account, Account)
    assert account.user_id == test_user_id
    # Should not allow duplicate account
    with pytest.raises(ValueError):
        create_account(test_user_id, db_session)

def test_get_balance(db_session, test_user_id):
    create_account(test_user_id, db_session)
    balance = get_balance(test_user_id, db_session)
    assert balance["balance"] == 0
    assert balance["available_balance"] == 0

def test_deposit_and_idempotency(db_session, test_user_id):
    create_account(test_user_id, db_session)
    ref_id = "dep-1"
    tx1 = deposit(test_user_id, 100, ref_id, "First deposit", db_session)
    assert tx1.amount == 100
    # Idempotency: same reference_id returns same transaction
    tx2 = deposit(test_user_id, 100, ref_id, "First deposit", db_session)
    assert tx1.id == tx2.id
    # Balance should be updated only once
    balance = get_balance(test_user_id, db_session)
    assert balance["balance"] == 100

def test_withdraw_and_idempotency(db_session, test_user_id):
    create_account(test_user_id, db_session)
    deposit(test_user_id, 200, "dep-2", "Deposit for withdraw", db_session)
    ref_id = "wd-1"
    tx1 = withdraw(test_user_id, 50, ref_id, "Withdraw", db_session)
    assert tx1.amount == 50
    # Idempotency: same reference_id returns same transaction
    tx2 = withdraw(test_user_id, 50, ref_id, "Withdraw", db_session)
    assert tx1.id == tx2.id
    # Balance should be updated only once
    balance = get_balance(test_user_id, db_session)
    assert balance["balance"] == 150
    # Insufficient funds
    with pytest.raises(ValueError):
        withdraw(test_user_id, 1000, "wd-2", "Too much", db_session)
    # Negative amount
    with pytest.raises(ValueError):
        withdraw(test_user_id, -10, "wd-3", "Negative", db_session)

def test_transfer_and_idempotency(db_session, test_user_id, other_user_id):
    create_account(test_user_id, db_session)
    create_account(other_user_id, db_session)
    deposit(test_user_id, 300, "dep-3", "Deposit for transfer", db_session)
    ref_id = "tr-1"
    txs1 = transfer(test_user_id, other_user_id, 100, ref_id, "Transfer", db_session)
    assert len(txs1) == 2
    # Idempotency: same reference_id returns same transactions
    txs2 = transfer(test_user_id, other_user_id, 100, ref_id, "Transfer", db_session)
    assert txs1[0].id == txs2[0].id and txs1[1].id == txs2[1].id
    # Balances
    bal1 = get_balance(test_user_id, db_session)
    bal2 = get_balance(other_user_id, db_session)
    assert bal1["balance"] == 200
    assert bal2["balance"] == 100
    # Insufficient funds
    with pytest.raises(ValueError):
        transfer(test_user_id, other_user_id, 1000, "tr-2", "Too much", db_session)
    # Negative amount
    with pytest.raises(ValueError):
        transfer(test_user_id, other_user_id, -10, "tr-3", "Negative", db_session)
    # Self-transfer
    with pytest.raises(ValueError):
        transfer(test_user_id, test_user_id, 10, "tr-4", "Self", db_session)

@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    from db.base import Base
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_deposit_idempotency(session):
    user_id = 1
    create_account(user_id, session)
    tx1 = deposit(user_id, 100, "ref-abc", "desc", session)
    tx2 = deposit(user_id, 100, "ref-abc", "desc", session)
    account = session.query(Account).filter_by(user_id=user_id).first()
    assert tx1.id == tx2.id
    assert account.balance == 100

def test_withdraw_idempotency(session):
    user_id = 2
    create_account(user_id, session)
    deposit(user_id, 100, "ref-dep", "desc", session)
    tx1 = withdraw(user_id, 50, "ref-wd", "desc", session)
    tx2 = withdraw(user_id, 50, "ref-wd", "desc", session)
    account = session.query(Account).filter_by(user_id=user_id).first()
    assert tx1.id == tx2.id
    assert account.balance == 50

def test_transfer_idempotency(session):
    from_user = 3
    to_user = 4
    create_account(from_user, session)
    create_account(to_user, session)
    deposit(from_user, 200, "ref-dep", "desc", session)
    txs1 = transfer(from_user, to_user, 75, "ref-xfer", "desc", session)
    txs2 = transfer(from_user, to_user, 75, "ref-xfer", "desc", session)
    from_acc = session.query(Account).filter_by(user_id=from_user).first()
    to_acc = session.query(Account).filter_by(user_id=to_user).first()
    assert txs1[0].id == txs2[0].id
    assert txs1[1].id == txs2[1].id
    assert from_acc.balance == 125
    assert to_acc.balance == 75 