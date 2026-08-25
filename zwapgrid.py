import os
import uuid
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ZWAPGRID_API_KEY")
CONSENT_ID = os.getenv("ZWAPGRID_CONSENT_ID")

print("API key loaded:", API_KEY is not None)
print("Consent ID loaded:", CONSENT_ID is not None)

headers = {
    "x-api-key": API_KEY,
    "x-correlation-id": str(uuid.uuid4()),
    "Accept": "application/json"
}

url = (
    f"https://apione.zwapgrid.com/accounting/api/v1/"
    f"consents/{CONSENT_ID}/companyinformation"
)

print("Calling:", url)

try:
    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    print("Status:", response.status_code)

    if response.ok:
        print("SUCCESS!")
        print(json.dumps(response.json(), indent=2))
    else:
        print("ERROR:")
        print(response.text)

except requests.exceptions.RequestException as e:
    print("REQUEST FAILED:")
    print(e)