"""
Pydantic models for Investigation output per SPEC.md section 5.
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator


class ClaimType(str, Enum):
    EVENT_EXISTS = "EVENT_EXISTS"
    FIELD_VALUE = "FIELD_VALUE"
    ORDER = "ORDER"
    DEVICE_FAMILIARITY = "DEVICE_FAMILIARITY"
    CONTEXT_EXISTS = "CONTEXT_EXISTS"
    INTERPRETATION = "INTERPRETATION"
    HYPOTHESIS = "HYPOTHESIS"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"


class ConclusionLabel(str, Enum):
    NO_CONCERN = "no_concern"
    LIKELY_BENIGN = "likely_benign"
    UNEXPLAINED = "unexplained"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Claim(BaseModel):
    claim_id: str = Field(..., pattern=r"^C\d+$")
    text: str
    claim_type: ClaimType
    cited_event_ids: List[str] = Field(default_factory=list)
    cited_record_ids: List[str] = Field(default_factory=list)
    structured: Dict[str, Any] = Field(default_factory=dict)
    supports: List[str] = Field(default_factory=list)
    contradicts: List[str] = Field(default_factory=list)
    limitations: str = ""

    @field_validator("structured")
    @classmethod
    def validate_structured(cls, v, info):
        """Validate structured fields based on claim_type."""
        claim_type = info.data.get("claim_type")
        if not claim_type:
            return v

        if claim_type == ClaimType.EVENT_EXISTS:
            required = {"event_id"}
            if not required.issubset(v.keys()):
                raise ValueError(f"EVENT_EXISTS requires {required}")
        elif claim_type == ClaimType.FIELD_VALUE:
            required = {"event_id", "field", "value"}
            if not required.issubset(v.keys()):
                raise ValueError(f"FIELD_VALUE requires {required}")
            allowed_fields = {"user_id", "ts", "event_type", "device_id", "resource", "source_ip", "outcome"}
            if v.get("field") not in allowed_fields:
                raise ValueError(f"FIELD_VALUE field must be one of {allowed_fields}")
        elif claim_type == ClaimType.ORDER:
            required = {"first_event_id", "second_event_id"}
            if not required.issubset(v.keys()):
                raise ValueError(f"ORDER requires {required}")
        elif claim_type == ClaimType.DEVICE_FAMILIARITY:
            required = {"user_id", "device_id", "familiar"}
            if not required.issubset(v.keys()):
                raise ValueError(f"DEVICE_FAMILIARITY requires {required}")
            if not isinstance(v.get("familiar"), bool):
                raise ValueError("DEVICE_FAMILIARITY.familiar must be boolean")
        elif claim_type == ClaimType.CONTEXT_EXISTS:
            required = {"record_id"}
            if not required.issubset(v.keys()):
                raise ValueError(f"CONTEXT_EXISTS requires {required}")

        # For INTERPRETATION, HYPOTHESIS, MISSING_EVIDENCE - structured must be empty
        if claim_type in (ClaimType.INTERPRETATION, ClaimType.HYPOTHESIS, ClaimType.MISSING_EVIDENCE):
            if v:
                raise ValueError(f"{claim_type} must have empty structured fields")

        return v


class Hypothesis(BaseModel):
    hypothesis_id: str = Field(..., pattern=r"^H\d+$")
    description: str
    supporting_claim_ids: List[str] = Field(default_factory=list)
    contradicting_claim_ids: List[str] = Field(default_factory=list)


class Conclusion(BaseModel):
    label: ConclusionLabel
    rationale: str


class Investigation(BaseModel):
    question: str
    claims: List[Claim] = Field(default_factory=list)
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    conclusion: Conclusion

    @field_validator("claims")
    @classmethod
    def validate_claim_ids_sequential(cls, v):
        """Ensure claim_ids are sequential C1, C2, C3..."""
        for i, claim in enumerate(v, 1):
            expected = f"C{i}"
            if claim.claim_id != expected:
                raise ValueError(f"Claim IDs must be sequential (C1, C2, ...), got {claim.claim_id} at position {i}")
        return v

    @field_validator("hypotheses")
    @classmethod
    def validate_hypothesis_ids_sequential(cls, v):
        """Ensure hypothesis_ids are sequential H1, H2, H3..."""
        for i, hyp in enumerate(v, 1):
            expected = f"H{i}"
            if hyp.hypothesis_id != expected:
                raise ValueError(f"Hypothesis IDs must be sequential (H1, H2, ...), got {hyp.hypothesis_id} at position {i}")
        return v


class InvestigationResult(BaseModel):
    investigation: Optional[Investigation] = None
    status: Literal["success", "failed", "limit_reached", "validation_error"]
    audit_steps: List[Dict[str, Any]] = Field(default_factory=list)
    rounds_used: int = 0
    retrieved_event_ids: List[str] = Field(default_factory=list)
    retrieved_record_ids: List[str] = Field(default_factory=list)
    model_name: str = ""
    system_prompt_version: str = ""

    model_config = {"extra": "forbid"}


# JSON fallback mode types
class ToolAction(BaseModel):
    action: Literal["tool"]
    tool: str
    args: Dict[str, Any]


class FinalAction(BaseModel):
    action: Literal["final"]
    investigation: Investigation


Action = Union[ToolAction, FinalAction]