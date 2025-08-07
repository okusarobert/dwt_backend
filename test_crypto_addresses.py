#!/usr/bin/env python3
import requests
import json

# Test the crypto address creation endpoint
url = "http://localhost:3030/wallet/admin/create-crypto-addresses/13"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer test"  # You'll need a real admin token
}

try:
    response = requests.post(url, headers=headers)
    print("Status Code: {}".format(response.status_code))
    print("Response: {}".format(response.text))
except Exception as e:
    print("Error: {}".format(e)) 