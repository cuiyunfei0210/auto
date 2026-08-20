"""Form parsing for the RANDOM.ORG client app. No GUI imports."""

from __future__ import annotations

from random_org import RandomOrgError, validate_range


class FormError(ValueError):
    """Invalid values typed into the form."""


def zh_error(exc: Exception) -> str:
    text = str(exc)
    mapping = {
        "num must be between 1 and 10000": "个数必须在 1 到 10000 之间。",
        "min must be between -1000000000 and 1000000000": "最小值超出允许范围。",
        "max must be between -1000000000 and 1000000000": "最大值超出允许范围。",
        "min must be less than or equal to max": "最小值不能大于最大值。",
        "cannot pick": "不重复时，个数不能超过可选范围。",
        "unique mode requires": "不重复模式下，最大值减最小值再加一不能超过 10000。",
        "quota is exhausted": "RANDOM.ORG 额度已用完，请稍后再试。",
        "network error": "网络连接失败，请检查能否访问 random.org。",
    }
    for key, value in mapping.items():
        if key in text:
            return value
    return text


def parse_inputs(
    num_text: str,
    min_text: str,
    max_text: str,
    *,
    unique: bool = False,
) -> tuple[int, int, int]:
    try:
        num = int(num_text.strip(), 10)
        minimum = int(min_text.strip(), 10)
        maximum = int(max_text.strip(), 10)
    except ValueError as exc:
        raise FormError("个数、最小值、最大值都必须是整数。") from exc
    try:
        validate_range(num, minimum, maximum, unique=unique)
    except RandomOrgError as exc:
        raise FormError(zh_error(exc)) from exc
    return num, minimum, maximum
