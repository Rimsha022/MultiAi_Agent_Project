import json


def extract_claims(client, question, answer):

    prompt = f"""
You are a factual claim extraction agent.

Your job is to identify factual claims from an AI-generated
answer that could potentially be verified using external evidence.

User Question:
{question}

AI Answer:
{answer}

Instructions:

1. Extract only factual and externally verifiable claims.
2. Do not extract opinions.
3. Do not extract general advice.
4. Do not extract duplicate claims.
5. Keep each claim concise and self-contained.
6. Do not judge whether a claim is true or false.
7. Return at most 8 important claims.

Return ONLY valid JSON in exactly this format:

{{
    "claims": [
        "claim 1",
        "claim 2",
        "claim 3"
    ]
}}

Do not include markdown.
Do not include explanations outside the JSON.
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",

        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0,
        max_tokens=1000
    )

    raw_text = (
        response
        .choices[0]
        .message
        .content
        .strip()
    )

    # Remove possible markdown formatting
    if raw_text.startswith("```"):

        raw_text = raw_text.replace(
            "```json",
            ""
        )

        raw_text = raw_text.replace(
            "```",
            ""
        ).strip()

    result = json.loads(raw_text)

    claims = result.get(
        "claims",
        []
    )

    return claims