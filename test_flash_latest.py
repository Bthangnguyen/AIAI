import httpx

key = "AIzaSyCWKY6EZAi4v3Ntm-tKewDbwQEx6OUYInY"
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"

try:
    response = httpx.post(
        f"{url}?key={key}",
        headers={"Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": "Hello"}]}]
        },
        timeout=10.0
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:300]}")
except Exception as e:
    print(f"Error: {e}")
