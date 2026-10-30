"""
Pydantic schemas for Investigation output (SPEC.md section 5).
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Literal
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
    claims: List[Claim]
    hypotheses: List[Hypothesis]
    missing_evidence: List[str]
    next_steps: List[str]
    conclusion: Conclusion

    @field_validator("claims")
    @classmethod
    def validate_claim_ids(cls, v: List[Claim]) -> List[Claim]:
        seen = set()
        for claim in v:
            if claim.claim_id in seen:
                raise ValueError(f"Duplicate claim_id: {claim.claim_id}")
            seen.add(claim.claim_id)
        return v

    @field_validator("hypotheses")
    @classmethod
    def validate_hypothesis_ids(cls, v: List[Hypothesis]) -> List[Hypothesis]:
        seen = set()
        for h in v:
            if h.hypothesis_id in seen:
                raise ValueError(f"Duplicate hypothesis_id: {h.hypothesis_id}")
            seen.add(h.hypothesis_id)
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

    class Config:
        extra = "forbid"


if __name__ == "__main__":
    # Quick validation test
    inv = Investigation(
        question="Test",
        claims=[
            Claim(claim_id="C1", text="User logged in", claim_type=ClaimType.EVENT_EXISTS, cited_event_ids=["EVT-001"])
        ],
        hypotheses=[
            Hypothesis(hypothesis_id="H1", description="Normal login")
        ],
        missing_evidence=[],
        next_steps=["Review"],
        conclusion=Conclusion(label=ConclusionLabel.NO_CONCERN, rationale="Normal")
    )
    print(inv.model_dump_json(indent=2))