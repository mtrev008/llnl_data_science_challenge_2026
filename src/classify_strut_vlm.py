#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import sys
from pathlib import Path
from typing import Any

from huggingface_hub import InferenceClient


CLASS_DEFINITIONS = """
You are classifying one expected lattice strut using cropped X-ray CT slices.

Classes:

MISSING:
The expected connection between two junctions is largely or completely absent.
Little or no material is visible along most of the expected strut path.
Small remnants near a junction may still be present.

BROKEN:
A substantial portion of the expected strut is present, but the material path
contains a localized internal discontinuity or gap. Material should generally
be visible on both sides of the break.

THIN:
The strut remains materially continuous between its junctions, but its visible
cross-section is substantially smaller than comparable normal struts.

NORMAL:
The expected strut is continuously present and has a thickness reasonably
consistent with nearby normal struts.

UNCERTAIN:
The evidence is insufficient, ambiguous, incorrectly cropped, or affected by
neighboring structures such that a reliable classification cannot be made.

Important rules:

1. Do not classify based on whether the strut is horizontal, vertical, or diagonal.
2. Treat orientation as irrelevant.
3. Inspect continuity, material presence, internal gaps, and relative thickness.
4. A strut must not be called missing merely because it is absent in one slice.
5. A broken strut should contain separated material portions with an internal gap.
6. A thin strut should remain continuous.
7. Use UNCERTAIN when the target strut is not clearly visible.
8. Base the decision only on the CT evidence supplied.
"""


def image_to_data_url(image_path: Path) -> str:
    """Encode a local image as a base64 data URL."""
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    mime_type, _ = mimetypes.guess_type(image_path.name)
    if mime_type is None:
        mime_type = "image/png"

    encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def image_part(image_path: Path) -> dict[str, Any]:
    """Create a Hugging Face/OpenAI-compatible image content part."""
    return {
        "type": "image_url",
        "image_url": {
            "url": image_to_data_url(image_path)
        },
    }


def text_part(text: str) -> dict[str, str]:
    return {
        "type": "text",
        "text": text,
    }


def locate_examples(
    examples_dir: Path,
    examples_per_class: int,
) -> dict[str, list[Path]]:
    """Find a fixed number of example images for each class."""
    class_names = ["missing", "broken", "thin", "normal"]
    valid_extensions = {".png", ".jpg", ".jpeg", ".webp"}

    selected: dict[str, list[Path]] = {}

    for class_name in class_names:
        class_dir = examples_dir / class_name

        if not class_dir.is_dir():
            raise FileNotFoundError(
                f"Missing example directory: {class_dir}"
            )

        images = sorted(
            path
            for path in class_dir.iterdir()
            if path.is_file() and path.suffix.lower() in valid_extensions
        )

        if len(images) < examples_per_class:
            raise ValueError(
                f"Class '{class_name}' contains {len(images)} images, "
                f"but {examples_per_class} are required."
            )

        selected[class_name] = images[:examples_per_class]

    return selected


def build_messages(
    examples: dict[str, list[Path]],
    target_path: Path,
) -> list[dict[str, Any]]:
    """
    Build a multimodal few-shot conversation.

    Each example is supplied as its own user/assistant demonstration:
    user: image + request
    assistant: correct label and explanation
    """
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": CLASS_DEFINITIONS,
        }
    ]

    example_reasoning = {
        "missing": (
            "The expected strut is largely absent across the supplied CT slices. "
            "There is insufficient continuous material connecting the expected "
            "junction locations."
        ),
        "broken": (
            "Material belonging to the expected strut is visible in separated "
            "portions, but a localized internal gap interrupts the connection."
        ),
        "thin": (
            "The strut remains continuous, but its cross-section is consistently "
            "smaller than the surrounding normal struts."
        ),
        "normal": (
            "The strut is continuously present and its apparent thickness is "
            "consistent with nearby intact struts."
        ),
    }

    example_number = 1

    for class_name in ["missing", "broken", "thin", "normal"]:
        for path in examples[class_name]:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        image_part(path),
                        text_part(
                            f"Few-shot example {example_number}. "
                            "Classify the highlighted or centered expected strut."
                        ),
                    ],
                }
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "class": class_name,
                            "reasoning": example_reasoning[class_name],
                        }
                    ),
                }
            )

            example_number += 1

    target_instruction = """
Now classify the target strut shown in the attached CT-slice image or montage.

Return exactly one JSON object with this schema:

{
  "class": "missing | broken | thin | normal | uncertain",
  "confidence": 0.0,
  "reasoning": "Concise explanation based on visible CT evidence.",
  "evidence": [
    "First visual observation",
    "Second visual observation"
  ],
  "alternative_class": "missing | broken | thin | normal | uncertain",
  "needs_review": true
}

Requirements:

- confidence must be between 0 and 1.
- needs_review must be true when confidence is below 0.70.
- Do not use orientation as evidence.
- Do not infer information that is not visible.
- Return JSON only, with no Markdown code fence.
"""

    messages.append(
        {
            "role": "user",
            "content": [
                image_part(target_path),
                text_part(target_instruction),
            ],
        }
    )

    return messages


def extract_json(response_text: str) -> dict[str, Any]:
    """Extract and validate a JSON object from the model response."""
    cleaned = response_text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    ).strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match is None:
            raise ValueError(
                f"Model did not return a JSON object:\n{response_text}"
            )

        result = json.loads(match.group(0))

    allowed_classes = {
        "missing",
        "broken",
        "thin",
        "normal",
        "uncertain",
    }

    predicted_class = str(result.get("class", "")).lower()

    if predicted_class not in allowed_classes:
        raise ValueError(
            f"Invalid predicted class: {result.get('class')}"
        )

    try:
        confidence = float(result.get("confidence"))
    except (TypeError, ValueError) as exc:
        raise ValueError("Response has an invalid confidence value.") from exc

    if not 0.0 <= confidence <= 1.0:
        raise ValueError("Confidence must be between 0 and 1.")

    result["class"] = predicted_class
    result["confidence"] = confidence
    result["needs_review"] = bool(
        result.get("needs_review", confidence < 0.70)
    )

    if confidence < 0.70:
        result["needs_review"] = True

    return result


def classify(
    model: str,
    provider: str,
    examples_dir: Path,
    target_path: Path,
    examples_per_class: int,
    max_tokens: int,
) -> dict[str, Any]:
    token = os.environ.get("HF_TOKEN")

    if not token:
        raise EnvironmentError(
            "HF_TOKEN is not set. Run:\n"
            'export HF_TOKEN="your_huggingface_token"'
        )

    examples = locate_examples(
        examples_dir=examples_dir,
        examples_per_class=examples_per_class,
    )

    messages = build_messages(
        examples=examples,
        target_path=target_path,
    )

    client = InferenceClient(
        provider=provider,
        api_key=token,
    )

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.0,
    )

    response_text = response.choices[0].message.content

    if not isinstance(response_text, str):
        raise ValueError("The model returned an empty or unsupported response.")

    return extract_json(response_text)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Classify a lattice strut from CT slices using a Hugging Face VLM "
            "and multimodal few-shot in-context examples."
        )
    )

    parser.add_argument(
        "--model",
        required=True,
        help=(
            "Hugging Face model ID, for example a conversational VLM "
            "supported by your selected inference provider."
        ),
    )

    parser.add_argument(
        "--provider",
        default="auto",
        help=(
            "Inference provider name. Default: auto. The selected provider "
            "must support the chosen VLM."
        ),
    )

    parser.add_argument(
        "--examples-dir",
        type=Path,
        required=True,
        help="Directory containing missing/, broken/, thin/, and normal/.",
    )

    parser.add_argument(
        "--target",
        type=Path,
        required=True,
        help="Target CT crop or slice-montage image.",
    )

    parser.add_argument(
        "--examples-per-class",
        type=int,
        default=2,
        help="Number of few-shot images to use from each class. Default: 2.",
    )

    parser.add_argument(
        "--max-tokens",
        type=int,
        default=600,
        help="Maximum output tokens. Default: 600.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("strut_classification.json"),
        help="Output JSON path.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = classify(
            model=args.model,
            provider=args.provider,
            examples_dir=args.examples_dir,
            target_path=args.target,
            examples_per_class=args.examples_per_class,
            max_tokens=args.max_tokens,
        )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2),
            encoding="utf-8",
        )

        print(json.dumps(result, indent=2))
        print(f"\nSaved result to: {args.output}")
        return 0

    except Exception as exc:
        print(f"Classification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())