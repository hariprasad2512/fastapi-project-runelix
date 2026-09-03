from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupplierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(ge=0)
    quantity: Decimal = Field(ge=0)
    supplier_name: str = Field(min_length=1, max_length=255)
    supplier_email: EmailStr


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=255)
    price: Decimal | None = Field(default=None, ge=0)
    quantity: Decimal | None = Field(default=None, ge=0)
    supplier_name: str | None = Field(default=None, min_length=1, max_length=255)
    supplier_email: EmailStr | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    price: Decimal
    quantity: Decimal
    supplier: SupplierResponse
