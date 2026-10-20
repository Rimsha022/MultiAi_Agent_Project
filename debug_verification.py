
from dotenv import load_dotenv
from groq import Groq

from pipeline import (
    extract_claims,
    verify_external_evidence,
)

load_dotenv()

client = Groq()

question = "What is the smallest country in the world by area?"

answer = """
Vatican City is the smallest country in the world by area.
It is located entirely within Rome, Italy.
Its area is approximately 0.49 square kilometres.
It is an independent sovereign state.
"""

print("Question:", question)
print("\nExtracting claims...")

claims = extract_claims(
    client=client,
    question=question,
    answer=answer,
)

print("\nExtracted claims:", len(claims))

for i, claim in enumerate(claims, start=1):
    print(f"{i}. {claim}")

print("\nRunning evidence verification...")

results = verify_external_evidence(claims)

print("\nFINAL DEBUG SUMMARY")
print("=" * 45)
print("Input claims:", len(claims))
print("Results returned:", len(results))

for i, item in enumerate(results, start=1):
    print(f"\nClaim {i}: {item.get('claim')}")
    print("Status:", item.get("status"))
    print("Reason:", item.get("reason"))

from collections import Counter

print("\nStatus totals:")
print(Counter(item.get("status") for item in results))
