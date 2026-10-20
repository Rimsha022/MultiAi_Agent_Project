
import json
import re


def synthesize_verified_answer(
    client,
    question,
    selected_answer,
    evidence_results
):
    """
    Synthesize an answer using the available claim-verification
    results. Never silently treat invalid synthesis output as
    a successfully verified answer.
    """

    if not isinstance(evidence_results, (list, tuple)):
        raise ValueError(
            "evidence_results must be a list or tuple."
        )

    evidence_text = "\n".join(
        (
            f"Claim: {result.get('claim', '')}\n"
            f"Status: {result.get('status', '')}\n"
            f"Confidence: {result.get('confidence', 'N/A')}\n"
            f"Reason: {result.get('reason', '')}"
        )
        for result in evidence_results
        if isinstance(result, dict)
    )

    if not evidence_text.strip():
        evidence_text = "No claim-verification results were supplied."

    synthesis_prompt = f"""
You are the final answer synthesis agent in a multi-agent
AI verification system.

QUESTION:
{question}

ORIGINAL SELECTED ANSWER:
{selected_answer}

CLAIM-VERIFICATION RESULTS:
{evidence_text}

RULES:
1. Preserve claims supported by the evidence.
2. Correct contradicted claims only when the evidence establishes
   a reliable correction.
3. Do not state insufficiently supported claims as certain facts.
4. Do not invent factual claims, citations, or sources.
5. Keep the answer clear and relevant to the question.
6. Do not claim that every statement was verified unless the
   supplied verification results establish that.
7. Report corrections and removed uncertain claims accurately.

Return ONLY valid JSON with this structure:
{{
    "verified_answer": "Final answer",
    "corrections_made": [],
    "uncertain_claims_removed": []
}}
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": synthesis_prompt
            }
        ],
        temperature=0
    )

    message = response.choices[0].message.content

    if not message or not message.strip():
        raise ValueError(
            "Synthesis agent returned an empty response."
        )

    text = message.strip()

    if text.startswith("```"):
        text = re.sub(
            r"\A```(?:json)?\s*|\s*```\Z",
            "",
            text,
            flags=re.IGNORECASE
        ).strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Synthesis agent returned invalid JSON: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            "Synthesis response must be a JSON object."
        )

    answer = result.get("verified_answer")

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(
            "Synthesis response has no valid verified_answer."
        )

    for field in (
        "corrections_made",
        "uncertain_claims_removed"
    ):
        if not isinstance(result.get(field), list):
            raise ValueError(
                f"Synthesis field '{field}' must be a list."
            )

    result["verified_answer"] = answer.strip()

    return result
