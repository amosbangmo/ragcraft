"""Small helpers for evaluation UI inputs (no Streamlit / app imports)."""


def parse_evaluation_csv_list(raw_value: str) -> list[str]:
    if not raw_value.strip():
        return []

    values: list[str] = []
    seen: set[str] = set()

    for part in raw_value.split(","):
        cleaned = part.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        values.append(cleaned)

    return values
