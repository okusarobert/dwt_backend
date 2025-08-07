from pydantic import BaseModel
from typing import Optional, Type, Dict

class RelworxMetadata(BaseModel):
    status: Optional[str]
    message: Optional[str]
    customer_reference: str
    internal_reference: str
    msisdn: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    provider: Optional[str]
    charge: Optional[float]
    completed_at: Optional[str]

class MpesaMetadata(BaseModel):
    transaction_id: str
    phone_number: str
    status: Optional[str]
    # Add more as needed

# Registry for provider metadata models
PROVIDER_METADATA_MODELS: Dict[str, Type[BaseModel]] = {
    "relworx": RelworxMetadata,
    "mpesa": MpesaMetadata,
    # Add more as needed
} 