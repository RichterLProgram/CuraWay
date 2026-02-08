import os

from src.supply.fallback_parse import parse_supply_fallback
from src.intelligence.facility_answer import answer_facility
from src.validation.anomaly_agent import validate_supply


def test_eval_harness(capsys):
    os.environ["LLM_DISABLED"] = "true"
    text = "Facility offers CT scan and oncology services."
    supply = parse_supply_fallback(text, source_doc_id="eval-doc")
    expected = {"IMAGING_CT", "ONC_GENERAL"}
    extracted = set(supply.canonical_capabilities or [])

    true_positive = len(expected & extracted)
    precision = true_positive / max(len(extracted), 1)
    recall = true_positive / max(len(expected), 1)

    answer = answer_facility(
        {
            "facility_id": supply.facility_id,
            "required_capability_codes": list(expected),
            "facility": supply.model_dump(),
        },
        trace_id="eval-trace",
    )

    validation = validate_supply(supply.model_dump())
    output = (
        f"precision={precision:.2f}, recall={recall:.2f}, "
        f"answer={answer['answer']}, verdict={validation.verdict}"
    )
    print(output)
    captured = capsys.readouterr()
    assert "precision" in captured.out
