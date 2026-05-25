"""Map LLM walking_tolerance to Layer 4 transport_modes."""

from typing import List

from app.schemas.trip import LLMDataContract


def transport_modes_from_contract(contract: LLMDataContract) -> List[str]:
    """Primary mode first — L4 uses transport_modes[0] for OSRM matrix."""
    tolerance = (contract.walking_tolerance or "medium").lower()
    if tolerance == "low":
        return ["taxi"]
    if tolerance == "high":
        return ["walking", "taxi"]
    return ["taxi", "walking"]
