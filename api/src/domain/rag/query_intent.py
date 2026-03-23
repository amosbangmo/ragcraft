from enum import Enum


class QueryIntent(str, Enum):
    """
    Coarse query intents for retrieval and QA shaping.

    TABLE marks questions that target tabular structure (metrics, rows/columns, comparisons over values).
    """

    FACTUAL = "factual"
    EXPLORATORY = "exploratory"
    TABLE = "table"
    IMAGE = "image"
    COMPARISON = "comparison"
    UNKNOWN = "unknown"
