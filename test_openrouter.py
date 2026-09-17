import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

# --- Test 1: Laguna S 2.1 (coding specialist) ---
laguna_response = client.chat.completions.create(
    model="poolside/laguna-s-2.1:free",
    messages=[
        {"role": "user", "content": "Write a Python function that checks if a string is a palindrome."}
    ],
)
print("=== Laguna S 2.1 ===")
print(laguna_response.choices[0].message.content)
print(laguna_response.usage)

# --- Test 2: Nemotron 3 Ultra (reasoning/orchestration) ---
nemotron_response = client.chat.completions.create(
    model="nvidia/nemotron-3-ultra-550b-a55b:free",
    messages=[
        {"role": "user", "content": "Outline a multi-step plan to migrate a monolith app to microservices."}
    ],
)
print("\n=== Nemotron 3 Ultra ===")
print(nemotron_response.choices[0].message.content)
print(nemotron_response.usage)
