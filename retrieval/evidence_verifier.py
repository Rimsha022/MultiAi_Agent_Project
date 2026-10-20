
import json
import re


VALID_STATUSES = {
    "SUPPORTED",
    "CONTRADICTED",
    "INSUFFICIENT_EVIDENCE",
}


def verify_claim_with_evidence(client, claim, evidence):
    """
    Verify one factual claim against retrieved evidence.

    Returns a validated status, confidence score, and reason.
    Invalid model output raises an exception so that the caller
    can handle the failure without inventing a classification.
    """

    if not isinstance(claim, str) or not claim.strip():
        raise ValueError("Claim must be a non-empty string.")

    if not isinstance(evidence, (list, tuple)):
        raise ValueError("Evidence must be a list or tuple.")

    evidence_sections = []

    for i, item in enumerate(evidence, start=1):
        if not isinstance(item, dict):
            continue

        evidence_sections.append(
            f"""
SOURCE {i}
Title: {item.get("title", "")}
Content: {item.get("content", "")}
URL: {item.get("url", "")}
"""
        )

    evidence_text = (
        "\n".join(evidence_sections)
        if evidence_sections
        else "No usable external evidence was retrieved."
    )

    prompt = f"""
You are an independent factual evidence verification agent.

Evaluate ONLY the supplied evidence. Do not rely on unsupported
assumptions or outside knowledge.

CLAIM:
{claim}

RETRIEVED EVIDENCE:
{evidence_text}

Choose exactly one status:

SUPPORTED:
The evidence clearly supports the claim.

CONTRADICTED:
The evidence clearly conflicts with the claim.

INSUFFICIENT_EVIDENCE:
The evidence is missing, irrelevant, ambiguous, or inadequate
to confidently support or contradict the claim.

Return confidence as a number between 0 and 100.
If there is no usable evidence, use INSUFFICIENT_EVIDENCE.

Return ONLY valid JSON with these keys:
{{
    "status": "SUPPORTED",
    "confidence": 95,
    "reason": "Explanation based only on the retrieved evidence."
}}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0,
    )

    text = response.choices[0].message.content

    if not text or not text.strip():
        raise ValueError("The verification model returned an empty response.")

    text = text.strip()

    # Remove optional Markdown code fences.
    if text.startswith("```"):
        text = re.sub(
            r"\A```(?:json)?\s*|\s*```\Z",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

    # Parse JSON without silently guessing a classification.
    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON returned by verification model: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise ValueError("Verification response must be a JSON object.")

    status = result.get("status")

    if not isinstance(status, str):
        raise ValueError("Verification response has no valid status.")

    status = status.strip().upper()

    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid verification status: {status}")

    try:
        confidence = float(result["confidence"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Confidence must be a number between 0 and 100.") from exc

    if not 0 <= confidence <= 100:
        raise ValueError("Confidence must be between 0 and 100.")

    reason = result.get("reason", "")

    if not isinstance(reason, str):
        raise ValueError("Verification reason must be a string.")

    return {
        "status": status,
        "confidence": confidence,
        "reason": reason.strip(),
    }
