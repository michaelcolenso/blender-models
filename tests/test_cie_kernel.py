from src.cie.ids import semantic_id
from src.cie.model import Claim, Confidence, Element, Evidence, ProjectState, Status
from src.cie.validate import validate_project_state


def test_semantic_id_is_readable_and_stable():
    assert semantic_id("Meydenbauer B", "Pipe", "B-104", "W-004", "017") == "meydenbauer-b:pipe:b-104:w-004:017"


def test_confirmed_claim_requires_evidence():
    element = Element(id="p:pipe:1", kind="pipe", name="P1", project_id="p")
    claim = Claim(id="p:claim:1", subject_id=element.id, predicate="diameter", value=4, status=Status.CONFIRMED, confidence=Confidence.HIGH)
    state = ProjectState(schema_version="0.1.0", project_id="p", name="P", elements=[element], claims=[claim])
    assert "confirmed claim p:claim:1 has no evidence" in validate_project_state(state)


def test_valid_evidence_backed_claim_passes():
    evidence = Evidence(id="p:evidence:p102", kind="drawing", source="P1.02")
    element = Element(id="p:pipe:1", kind="pipe", name="P1", project_id="p", source_ids=(evidence.id,), status=Status.PROVISIONAL)
    claim = Claim(id="p:claim:1", subject_id=element.id, predicate="diameter", value=4, evidence_ids=(evidence.id,), status=Status.PROVISIONAL, confidence=Confidence.MEDIUM)
    state = ProjectState(schema_version="0.1.0", project_id="p", name="P", evidence=[evidence], elements=[element], claims=[claim])
    assert validate_project_state(state) == []
