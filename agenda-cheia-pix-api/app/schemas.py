from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerInput(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    tax_id: str | None = Field(default=None, alias="taxID")
    address: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class ChargeCreateRequest(BaseModel):
    value: int = Field(gt=0, description="Charge value in cents.")
    expires_in: int = Field(default=3600, gt=0, alias="expiresIn")
    correlation_id: str | None = Field(default=None, alias="correlationID")
    comment: str | None = None
    customer: CustomerInput | None = None
    additional_info: list[dict[str, Any]] | None = Field(
        default=None, alias="additionalInfo"
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("correlation_id")
    @classmethod
    def empty_correlation_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def to_woovi_payload(self) -> dict[str, Any]:
        payload = self.model_dump(by_alias=True, exclude_none=True)
        payload["correlationID"] = self.correlation_id or str(uuid4())
        return payload


class ChargeResponse(BaseModel):
    correlation_id: str | None = Field(default=None, alias="correlationID")
    value: int | None = None
    status: str | None = None
    expires_in: int | None = Field(default=None, alias="expiresIn")
    expires_date: str | None = Field(default=None, alias="expiresDate")
    br_code: str | None = Field(default=None, alias="brCode")
    qr_code_image: str | None = Field(default=None, alias="qrCodeImage")
    payment_link_url: str | None = Field(default=None, alias="paymentLinkUrl")
    provider_charge_id: str | None = Field(default=None, alias="providerChargeID")
    raw: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)


class ChargeRecord(BaseModel):
    correlation_id: str = Field(alias="correlationID")
    value: int | None = None
    status: str | None = None
    expires_in: int | None = Field(default=None, alias="expiresIn")
    expires_date: str | None = Field(default=None, alias="expiresDate")
    br_code: str | None = Field(default=None, alias="brCode")
    qr_code_image: str | None = Field(default=None, alias="qrCodeImage")
    payment_link_url: str | None = Field(default=None, alias="paymentLinkUrl")
    provider_charge_id: str | None = Field(default=None, alias="providerChargeID")
    payment_link_id: str | None = Field(default=None, alias="paymentLinkID")
    paid_at: str | None = Field(default=None, alias="paidAt")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class WebhookCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    event: str = Field(default="OPENPIX:CHARGE_COMPLETED", min_length=1)
    url: str = Field(min_length=1)
    authorization: str | None = None
    is_active: bool = Field(default=True, alias="isActive")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    @field_validator("authorization")
    @classmethod
    def empty_authorization_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def to_woovi_payload(
        self, *, default_authorization: str | None = None
    ) -> dict[str, Any]:
        webhook = self.model_dump(by_alias=True, exclude_none=True)
        if "authorization" not in webhook and default_authorization:
            webhook["authorization"] = default_authorization
        return {"webhook": webhook}


class WebhookRegistrationResponse(BaseModel):
    id: str | None = None
    name: str | None = None
    event: str | None = None
    url: str | None = None
    is_active: bool | None = Field(default=None, alias="isActive")
    raw: dict[str, Any]

    model_config = ConfigDict(populate_by_name=True)
