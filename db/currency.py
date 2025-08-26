from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Currency(Base):
    __tablename__ = 'admin_currencies'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    is_multi_network = Column(Boolean, default=False, nullable=False)
    contract_address = Column(String(255), nullable=True)
    decimals = Column(Integer, default=18, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship to networks
    networks = relationship("CurrencyNetwork", back_populates="currency", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name': self.name,
            'is_enabled': self.is_enabled,
            'is_multi_network': self.is_multi_network,
            'contract_address': self.contract_address,
            'decimals': self.decimals,
            'networks': [network.to_dict() for network in self.networks],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class CurrencyNetwork(Base):
    __tablename__ = 'admin_currency_networks'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    currency_id = Column(String(36), ForeignKey('admin_currencies.id'), nullable=False)
    network_type = Column(String(50), nullable=False)
    network_name = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    contract_address = Column(String(255), nullable=True)
    confirmation_blocks = Column(Integer, default=12, nullable=False)
    explorer_url = Column(String(255), nullable=False)
    is_testnet = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship back to currency
    currency = relationship("Currency", back_populates="networks")
    
    def to_dict(self):
        return {
            'id': self.id,
            'currency_id': self.currency_id,
            'network_type': self.network_type,
            'network_name': self.network_name,
            'display_name': self.display_name,
            'is_enabled': self.is_enabled,
            'contract_address': self.contract_address,
            'confirmation_blocks': self.confirmation_blocks,
            'explorer_url': self.explorer_url,
            'is_testnet': self.is_testnet,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
