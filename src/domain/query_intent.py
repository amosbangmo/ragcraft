from enum import Enum


class QueryIntent(str, Enum):
    FACTUAL = "factual"
    EXPLORATORY = "exploratory"
    TABLE = "table"
    IMAGE = "image"
    COMPARISON = "comparison"
    UNKNOWN = "unknown"
