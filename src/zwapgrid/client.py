import uuid
from collections.abc import Iterator

import httpx

ZWAPGRID_BASE_URL = "https://apione.zwapgrid.com"


class ZwapgridError(Exception):
    def __init__(self, status_code: int, body: str):
        super().__init__(f"Zwapgrid API error [{status_code}]: {body}")
        self.status_code = status_code
        self.body = body


def invoice_date_param(value: str | None) -> str | None:
    """Fortnox rejects ISO datetimes on invoice filters; send yyyy-MM-dd."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:10]


class ZwapgridClient:
    def __init__(self, api_key: str, consent_id: str):
        self._api_key = api_key
        self._consent_id = consent_id

    @classmethod
    def from_env(cls) -> "ZwapgridClient":
        import os
        return cls(
            api_key=os.environ["ZWAPGRID_API_KEY"],
            consent_id=os.environ["ZWAPGRID_CONSENT_ID"],
        )

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "x-correlation-id": str(uuid.uuid4()),
            "Accept": "application/json",
        }

    def _consent_path(self, resource: str, *, version: str = "v1") -> str:
        return f"/accounting/api/{version}/consents/{self._consent_id}/{resource}"

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        response = httpx.request(
            method,
            ZWAPGRID_BASE_URL + path,
            headers=self._headers(),
            timeout=30,
            **kwargs,
        )
        if not response.is_success:
            raise ZwapgridError(response.status_code, response.text)
        return response

    def _get(self, resource: str, *, version: str = "v1", **query) -> dict:
        params = {key: value for key, value in query.items() if value is not None}
        return self._request(
            "GET",
            self._consent_path(resource, version=version),
            params=params or None,
        ).json()

    def _iter_pages(
        self,
        resource: str,
        *,
        count: int = 100,
        extra: dict | None = None,
    ) -> tuple[list, dict]:
        page = 1
        items: list = []
        last_meta: dict = {}
        pages_fetched = 0
        extra = extra or {}
        while True:
            result = self._get(
                resource,
                Count=count,
                CurrentPage=page,
                **extra,
            )
            pages_fetched += 1
            data = result.get("data") or []
            meta = result.get("meta") or {}
            last_meta = meta
            items.extend(data)
            current = meta.get("currentPage") or page
            total_pages = meta.get("totalPages") or 1
            if current >= total_pages or not data:
                break
            page += 1
        last_meta = {
            **last_meta,
            "pagesFetched": pages_fetched,
            "complete": (last_meta.get("totalPages") or 1) <= pages_fetched,
        }
        return items, last_meta

    def get_company_information(self) -> dict:
        return self._get("companyinformation")

    def get_income_statement(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        level: int | None = None,
    ) -> dict:
        return self._get(
            "incomestatement",
            StartDate=invoice_date_param(start_date) or start_date,
            EndDate=invoice_date_param(end_date) or end_date,
            Level=level,
        )

    def get_balance_sheet(
        self,
        *,
        end_date: str | None = None,
        level: int | None = None,
    ) -> dict:
        return self._get(
            "balancesheet",
            EndDate=invoice_date_param(end_date) or end_date,
            Level=level,
        )

    def get_trial_balances(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        level: int | None = None,
    ) -> dict:
        return self._get(
            "trialbalances",
            version="v2",
            StartDate=invoice_date_param(start_date),
            EndDate=invoice_date_param(end_date),
            Level=level,
        )

    def list_sales_invoices(
        self,
        *,
        count: int | None = None,
        current_page: int | None = None,
        from_invoice_date: str | None = None,
        to_invoice_date: str | None = None,
        status: str | None = None,
        order_by: str | None = None,
        include: str | None = None,
    ) -> dict:
        return self._get(
            "salesinvoices",
            Count=count,
            CurrentPage=current_page,
            FromInvoiceDate=invoice_date_param(from_invoice_date),
            ToInvoiceDate=invoice_date_param(to_invoice_date),
            Status=status,
            OrderBy=order_by,
            Include=include,
        )

    def iter_sales_invoices(
        self,
        *,
        from_invoice_date: str | None = None,
        to_invoice_date: str | None = None,
        status: str | None = None,
        include: str = "paymentStatus",
        count: int = 100,
    ) -> tuple[list, dict]:
        return self._iter_pages(
            "salesinvoices",
            count=count,
            extra={
                "FromInvoiceDate": invoice_date_param(from_invoice_date),
                "ToInvoiceDate": invoice_date_param(to_invoice_date),
                "Status": status,
                "Include": include,
            },
        )

    def get_sales_invoice(
        self,
        sales_invoice_id: str,
        *,
        include: str | None = None,
    ) -> dict:
        return self._get(f"salesinvoices/{sales_invoice_id}", Include=include)

    def list_sales_invoice_payments(self) -> dict:
        return self._get("salesinvoices/payments")

    def list_sales_invoice_payments_for_invoice(self, sales_invoice_id: str) -> dict:
        return self._get(f"salesinvoices/{sales_invoice_id}/payments")

    def iter_sales_invoice_payments_for_invoice(
        self,
        sales_invoice_id: str,
        *,
        count: int = 100,
    ) -> tuple[list, dict]:
        return self._iter_pages(
            f"salesinvoices/{sales_invoice_id}/payments",
            count=count,
        )

    def list_supplier_invoices(
        self,
        *,
        count: int | None = None,
        current_page: int | None = None,
        from_invoice_date: str | None = None,
        to_invoice_date: str | None = None,
        status: str | None = None,
        order_by: str | None = None,
        include: str | None = None,
    ) -> dict:
        # Fortnox returns HTTP 501 if OrderBy is sent on supplier invoices.
        del order_by
        return self._get(
            "supplierinvoices",
            Count=count,
            CurrentPage=current_page,
            FromInvoiceDate=invoice_date_param(from_invoice_date),
            ToInvoiceDate=invoice_date_param(to_invoice_date),
            Status=status,
            Include=include,
        )

    def iter_supplier_invoices(
        self,
        *,
        from_invoice_date: str | None = None,
        to_invoice_date: str | None = None,
        status: str | None = None,
        include: str = "paymentStatus",
        count: int = 100,
    ) -> tuple[list, dict]:
        return self._iter_pages(
            "supplierinvoices",
            count=count,
            extra={
                "FromInvoiceDate": invoice_date_param(from_invoice_date),
                "ToInvoiceDate": invoice_date_param(to_invoice_date),
                "Status": status,
                "Include": include,
            },
        )

    def get_supplier_invoice(
        self,
        supplier_invoice_id: str,
        *,
        include: str | None = None,
    ) -> dict:
        return self._get(f"supplierinvoices/{supplier_invoice_id}", Include=include)

    def list_supplier_invoice_payments(self) -> dict:
        return self._get("supplierinvoices/payments")

    def list_supplier_invoice_payments_for_invoice(self, supplier_invoice_id: str) -> dict:
        return self._get(f"supplierinvoices/{supplier_invoice_id}/payments")

    def iter_supplier_invoice_payments_for_invoice(
        self,
        supplier_invoice_id: str,
        *,
        count: int = 100,
    ) -> tuple[list, dict]:
        return self._iter_pages(
            f"supplierinvoices/{supplier_invoice_id}/payments",
            count=count,
        )

    def iter_pages(self, resource: str, **kwargs) -> Iterator[dict]:
        items, _meta = self._iter_pages(resource, **kwargs)
        yield from items
