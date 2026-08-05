import requests

API_KEY = "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"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": "llama-3.1-8b-instant",
    "messages": [
        {
            "role": "user",
            "content": "Hello"
        }
    ]
}

response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers=headers,
    json=payload,
)

print("Status Code:", response.status_code)
print("Response:")
print(response.text)