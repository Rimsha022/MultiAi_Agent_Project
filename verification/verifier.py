import json
import re


def clean_json_response(text):
    """
    Cleans possible markdown/code fences or extra text
    returned by the verification model.
    """

    if not text:
        raise ValueError("Verifier returned an empty response.")

    text = text.strip()

    # Remove markdown code fences
    text = re.sub(r"^```json\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Extract JSON object if model added extra text
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(
            "Verifier response does not contain valid JSON."
        )

    return text[start:end + 1]


def verify_answer(client, question, answer):

    verification_prompt = f"""
You are an independent AI verification agent.

Your task is to evaluate the factual reliability of an AI-generated answer.

USER QUESTION:
{question}

AI ANSWER:
{answer}

Evaluate the answer using the following criteria:

1. Factual correctness
2. Internal consistency
3. Presence of unsupported or questionable factual claims
4. Overall reliability

Scoring instructions:

verification_score:
Give a score from 0 to 10.

0 = completely unreliable
5 = partially reliable
10 = highly reliable

confidence:
Give a percentage from 0 to 100 representing how confident
you are in your verification assessment.

supported_claims:
List important factual claims from the answer that appear
correct and well supported by established knowledge.

unsupported_claims:
List claims that appear incorrect, misleading, unverifiable,
overstated, or insufficiently supported.

If no unsupported claims are found, return an empty list.

reason:
Provide a short explanation summarizing why the answer
received its verification score.

Return ONLY valid JSON using exactly this structure:

{{
    "verification_score": 0,
    "confidence": 0,
    "supported_claims": [],
    "unsupported_claims": [],
    "reason": ""
}}

IMPORTANT:

- verification_score must be a number from 0 to 10.
- confidence must be a number from 0 to 100.
- supported_claims must be a JSON list.
- unsupported_claims must be a JSON list.
- reason must be a string.
- Do not include markdown.
- Do not include ```json.
- Do not include explanations outside the JSON.
"""

    response = client.chat.completions.create(

        model="openai/gpt-oss-120b",

        messages=[
            {
                "role": "user",
                "content": verification_prompt
            }
        ],

        temperature=0
    )

    # ------------------------------------------
    # Get model response
    # ------------------------------------------

    text = response.choices[0].message.content

    # ------------------------------------------
    # Clean JSON
    # ------------------------------------------

    cleaned_text = clean_json_response(text)

    try:
        result = json.loads(cleaned_text)

    except json.JSONDecodeError as e:

        raise ValueError(
            f"Verifier returned invalid JSON: {e}"
        )

    # ------------------------------------------
    # Validate required fields
    # ------------------------------------------

    required_fields = [
        "verification_score",
        "confidence",
        "supported_claims",
        "unsupported_claims",
        "reason"
    ]

    for field in required_fields:

        if field not in result:
            raise ValueError(
                f"Missing verifier field: {field}"
            )

    # ------------------------------------------
    # Convert scores safely
    # ------------------------------------------

    try:
        result["verification_score"] = float(
            result["verification_score"]
        )

        result["confidence"] = float(
            result["confidence"]
        )

    except (TypeError, ValueError):

        raise ValueError(
            "Verification score and confidence must be numeric."
        )

    # ------------------------------------------
    # Keep values inside valid ranges
    # ------------------------------------------

    result["verification_score"] = max(
        0,
        min(10, result["verification_score"])
    )

    result["confidence"] = max(
        0,
        min(100, result["confidence"])
    )

    # ------------------------------------------
    # Ensure claim fields are lists
    # ------------------------------------------

    if not isinstance(result["supported_claims"], list):
        result["supported_claims"] = []

    if not isinstance(result["unsupported_claims"], list):
        result["unsupported_claims"] = []

    # ------------------------------------------
    # Ensure reason is text
    # ------------------------------------------

    result["reason"] = str(
        result.get("reason", "")
    ).strip()

    return result