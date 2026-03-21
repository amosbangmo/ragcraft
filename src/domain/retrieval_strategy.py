from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalStrategy:
    k: int
    use_hybrid: bool
    apply_filters: bool

    def to_dict(self) -> dict:
        return {
            "k": self.k,
            "use_hybrid": self.use_hybrid,
            "apply_filters": self.apply_filters,
        }
