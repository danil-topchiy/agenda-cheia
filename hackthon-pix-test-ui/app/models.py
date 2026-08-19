from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChargeCreateInput(BaseModel):
    value: int = Field(gt=0)
    expires_in: int = Field(default=900, gt=0, alias="expiresIn")
    correlation_id: str = Field(min_length=1, alias="correlationID")
    comment: str | None = None
    customer_name: str | None = Field(default=None, alias="customerName")
    customer_email: str | None = Field(default=None, alias="customerEmail")
    customer_phone: str | None = Field(default=None, alias="customerPhone")

    model_config = ConfigDict(populate_by_name=True)

    def to_pix_api_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "value": self.value,
            "expiresIn": self.expires_in,
            "correlationID": self.correlation_id,
        }
        if self.comment:
            payload["comment"] = self.comment

        customer = {
            key: value
            for key, value in {
                "name": self.customer_name,
                "email": self.customer_email,
                "phone": self.customer_phone,
            }.items()
            if value
        }
        if customer:
            payload["customer"] = customer
        return payload


class SimulateWebhookInput(BaseModel):
    correlation_id: str = Field(min_length=1, alias="correlationID")
    value: int = Field(default=1, gt=0)
    status: str = Field(pattern="^(COMPLETED|EXPIRED)$")
    provider_charge_id: str | None = Field(default=None, alias="providerChargeID")
    payment_link_id: str | None = Field(default=None, alias="paymentLinkID")

    model_config = ConfigDict(populate_by_name=True)

