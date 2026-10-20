import os

from dotenv import load_dotenv
from groq import Groq

from retrieval.evidence_retriever import retrieve_evidence
from retrieval.evidence_verifier import verify_claim_with_evidence


# =========================================================
# 1. LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")


# =========================================================
# 2. CHECK API KEY
# =========================================================

if not groq_api_key:
    raise ValueError(
        "GROQ_API_KEY is missing from the .env file."
    )


# =========================================================
# 3. CREATE GROQ CLIENT
# =========================================================

client = Groq(
    api_key=groq_api_key
)


# =========================================================
# 4. TEST CLAIM
# =========================================================

claim = (
    "IBM Deep Blue defeated world chess "
    "champion Garry Kasparov in 1997."
)


print("\nCLAIM")
print("-" * 60)

print(claim)


# =========================================================
# 5. RETRIEVE EXTERNAL EVIDENCE
# =========================================================

print("\nRetrieving external evidence...")


evidence = retrieve_evidence(
    claim,
    max_results=3
)


print(
    f"\nRetrieved {len(evidence)} evidence sources."
)


# =========================================================
# 6. DISPLAY RETRIEVED EVIDENCE
# =========================================================

for number, item in enumerate(
    evidence,
    start=1
):

    print("\n" + "=" * 60)

    print(
        f"SOURCE {number}"
    )

    print(
        "Title:",
        item.get("title", "Unknown")
    )

    print(
        "URL:",
        item.get("url", "Unknown")
    )

    print("\nContent:")

    content = item.get(
        "content",
        ""
    )

    print(
        content[:500]
    )


# =========================================================
# 7. VERIFY CLAIM AGAINST EVIDENCE
# =========================================================

print("\n" + "=" * 60)

print(
    "\nVerifying claim against retrieved evidence..."
)


verification = verify_claim_with_evidence(

    client=client,

    claim=claim,

    evidence=evidence
)


# =========================================================
# 8. DISPLAY VERIFICATION RESULT
# =========================================================

print("\nEVIDENCE VERIFICATION")

print("-" * 60)


print(
    "Status:",
    verification.get(
        "status",
        "UNKNOWN"
    )
)


print(
    "Confidence:",
    f"{verification.get('confidence', 0):.2f}%"
)


print(
    "Reason:",
    verification.get(
        "reason",
        "No explanation available."
    )
)


print("-" * 60)