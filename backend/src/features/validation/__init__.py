# Validation: Suspicious / conflict detection
from features.validation.anomaly_validator import (
    detect_suspicious_claims,
    is_negated,
    suspicious_for_capability,
)

__all__ = ["detect_suspicious_claims", "is_negated", "suspicious_for_capability"]
