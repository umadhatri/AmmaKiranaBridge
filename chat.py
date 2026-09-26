import os
from pathlib import Path

from sarvamai import SarvamAI


for line in Path(".env").read_text().splitlines():
    key, _, value = line.partition("=")
    if key == "SARVAM_API_KEY" and value:
        os.environ[key] = value

if not os.getenv("SARVAM_API_KEY"):
    raise RuntimeError("Set SARVAM_API_KEY in .env before running this script.")

client = SarvamAI(api_subscription_key=os.environ["SARVAM_API_KEY"])
response = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
