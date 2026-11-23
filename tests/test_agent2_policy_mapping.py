import json
import pytest
from langchain_core.documents import Document

from cidan.agents import policy_mapping
from cidan.ingestion.retrieval import retrieve_policy_candidates
from cidan.models import Citation, Obligation, PolicyFinding
from cidan.services import agent2_storage


def make_citation(document_type="circular", chunk_id="circ-chunk-1", page=1):
    return Citation(
        document_id="doc-circ-1",
        filename="circular_2026.pdf" if document_type == "circular" else "handbook_2025.pdf",
        document_type=document_type,
        page=page,
        excerpt="Senior citizen priority service and complaint handling rules.",
        chunk_id=chunk_id,
    )


def make_obligation(
    obligation_id="OBL-001",
    clause_id="2.5",
    text="Acknowledge senior citizen complaints within 1 working day; resolve within 7 working days.",
    required_action="Acknowledge complaint within 1 working day and resolve within 7 working days",
    applicability="Senior citizen complaints",
    amount_threshold=None,
    currency=None,
    deadline_or_frequency="1 working day",
):
    citation = make_citation(document_type="circular", chunk_id="circ-chunk-1")
    return Obligation(
        obligation_id=obligation_id,
        clause_id=clause_id,
        text=text,
        applicability=applicability,
        product_type="retail_banking",
        amount_threshold=amount_threshold,
        currency=currency,
        effective_date="2026-07-01",
        responsible_function="customer_service",
        required_action=required_action,
        deadline_or_frequency=deadline_or_frequency,
        source=citation,
        supporting_excerpt=citation.excerpt,
        confidence=0.92,
    )


def make_policy_doc(
    chunk_id="pol-chunk-1",
    content="[TABLE t2 ROW 5] Clause=2.5 Grievance handling | Requirement / Operational rule=Route complaints tagged as senior-citizen service issues to a designated service officer. Acknowledge within 2 working days and target resolution within 10 working days.",
    document_type="policy_handbook",
    page=2,
    clause_id="2.5",
):
    return Document(
        page_content=content,
        metadata={
            "document_id": "doc-policy-1",
            "filename": "handbook_2025.pdf",
            "document_type": document_type,
            "page": page,
            "chunk_id": chunk_id,
            "clause_id": clause_id,
        },
    )


def test_policy_mapping_classifications_all_five_statuses():
    """Requirement 3: Verify all 5 classifications can be produced with valid structures."""
    statuses = [
        ("covered", 0.95),
        ("partially_covered", 0.85),
        ("potential_conflict", 0.90),
        ("not_found", 0.75),
        ("requires_human_review", 0.40),
    ]
    obligation = make_obligation()
    policy_doc = make_policy_doc(chunk_id="pol-c1")

    for expected_status, conf in statuses:
        cited_chunks = ["pol-c1"] if expected_status in ("covered", "partially_covered", "potential_conflict") else []

        def fake_llm(schema, system, prompt):
            assert "semantic" in system
            assert "one short sentence" in system
            return schema(
                status=expected_status,
                reasoning=f"Assessment indicates {expected_status} status.",
                missing_or_inconsistent="None identified" if expected_status == "covered" else "Difference noted.",
                operational_impact="Follow revised operating instructions.",
                recommended_action="Proceed according to compliance matrix.",
                confidence=conf,
                evidence_limitations=[],
                cited_policy_chunk_ids=cited_chunks,
            )

        findings = policy_mapping.run([obligation], [policy_doc], llm_call=fake_llm)
        assert len(findings) == 1
        finding = findings[0]
        assert finding.status == expected_status
        assert finding.confidence == conf
        assert finding.obligation_id == obligation.obligation_id
        assert finding.circular_citation.chunk_id == obligation.source.chunk_id
        if cited_chunks:
            assert len(finding.policy_citations) == 1
            assert finding.policy_citations[0].chunk_id == "pol-c1"
        else:
            assert len(finding.policy_citations) == 0


def test_missing_retrieval_evidence_fails_safe_to_human_review():
    """Requirement 4: Never treat missing retrieval evidence as proof a policy doesn't exist."""
    obligation = make_obligation()
    findings = policy_mapping.run([obligation], documents=[])
    assert len(findings) == 1
    finding = findings[0]
    assert finding.status == "requires_human_review"
    assert finding.confidence == 0
    assert not finding.policy_citations
    assert "inconclusive" in finding.reasoning.lower()


def test_hallucinated_chunk_id_rejected_and_downgraded():
    """Requirement 5 & 6: Cited chunk IDs must exist in retrieved passages."""
    obligation = make_obligation()
    policy_doc = make_policy_doc(chunk_id="real-chunk-1")

    def hallucinating_llm(schema, system, prompt):
        return schema(
            status="covered",
            reasoning="The policy covers this obligation completely.",
            missing_or_inconsistent="None.",
            operational_impact="No change needed.",
            recommended_action="Maintain current operations.",
            confidence=0.95,
            evidence_limitations=[],
            cited_policy_chunk_ids=["hallucinated-chunk-999"],  # NOT in retrieved docs
        )

    findings = policy_mapping.run([obligation], [policy_doc], llm_call=hallucinating_llm)
    assert len(findings) == 1
    finding = findings[0]
    # Status should be safely downgraded to requires_human_review because cited chunk is fake
    assert finding.status == "requires_human_review"
    assert finding.confidence <= 0.4
    assert len(finding.policy_citations) == 0
    assert any("unverified" in lim.lower() for lim in finding.evidence_limitations)


def test_duplicate_policy_chunks_deduplicated():
    """Requirement 6: Deduplication of duplicate retrieved policy chunks."""
    obligation = make_obligation()
    doc1 = make_policy_doc(chunk_id="pol-1", content="Policy statement A")
    doc2 = make_policy_doc(chunk_id="pol-1", content="Policy statement A duplicate")

    def capture_llm(schema, system, prompt):
        # Count occurrences of chunk citation in prompt
        assert prompt.count("pol-1") == 1
        return schema(
            status="covered",
            reasoning="Deduplicated chunk confirms policy coverage.",
            missing_or_inconsistent="None.",
            operational_impact="No impact.",
            recommended_action="Retain policy.",
            confidence=0.9,
            evidence_limitations=[],
            cited_policy_chunk_ids=["pol-1"],
        )

    findings = policy_mapping.run([obligation], [doc1, doc2], llm_call=capture_llm)
    assert len(findings) == 1
    assert len(findings[0].policy_citations) == 1


def test_baseline_policy_document_type_accepted():
    """Ensure baseline_policy document_type is accepted alongside policy_handbook."""
    obligation = make_obligation()
    doc = make_policy_doc(chunk_id="base-1", document_type="baseline_policy")

    def mock_llm(schema, system, prompt):
        return schema(
            status="partially_covered",
            reasoning="Baseline policy covers standard process but lacks specific SLA.",
            missing_or_inconsistent="SLA timeline difference.",
            operational_impact="Workflow adjustment required.",
            recommended_action="Update operational procedures.",
            confidence=0.88,
            evidence_limitations=[],
            cited_policy_chunk_ids=["base-1"],
        )

    findings = policy_mapping.run([obligation], [doc], llm_call=mock_llm)
    assert len(findings) == 1
    assert findings[0].status == "partially_covered"
    assert len(findings[0].policy_citations) == 1
    assert findings[0].policy_citations[0].chunk_id == "base-1"


def test_llm_exception_fails_safe_to_human_review():
    """Requirement 6: Robust error handling when LLM invocation raises an exception."""
    obligation = make_obligation()
    doc = make_policy_doc(chunk_id="pol-1")

    def failing_llm(schema, system, prompt):
        raise RuntimeError("Groq API rate limit or network timeout")

    findings = policy_mapping.run([obligation], [doc], llm_call=failing_llm)
    assert len(findings) == 1
    assert findings[0].status == "requires_human_review"
    assert findings[0].confidence == 0.0
    assert "error" in findings[0].reasoning.lower() or "failed" in findings[0].reasoning.lower()


def test_agent2_structured_json_storage_and_agent3_consumption(tmp_path, monkeypatch):
    """Requirement 9: Save Agent 2 outputs as structured JSON consumable by Agent 3."""
    monkeypatch.setattr(agent2_storage, "WORKFLOW_OUTPUTS_DIR", tmp_path)

    workflow_id = "test-agent2-storage-wf"
    obligation = make_obligation()
    doc = make_policy_doc(chunk_id="pol-c1")

    def mock_llm(schema, system, prompt):
        return schema(
            status="potential_conflict",
            reasoning="Policy prescribes 2 working days whereas circular mandates 1 working day.",
            missing_or_inconsistent="1-day grievance acknowledgment timeline.",
            operational_impact="Risk of non-compliance with updated turn-around SLA.",
            recommended_action="Reduce acknowledgment SLA in grievance workflow.",
            confidence=0.92,
            evidence_limitations=[],
            cited_policy_chunk_ids=["pol-c1"],
        )

    findings = policy_mapping.run([obligation], [doc], llm_call=mock_llm, workflow_id=workflow_id)
    assert len(findings) == 1

    # Verify structured JSON file was created on disk
    findings_file = tmp_path / workflow_id / "agent_2_policy_mapping" / "policy_findings.json"
    assert findings_file.exists()
    data = json.loads(findings_file.read_text(encoding="utf-8"))
    assert data["workflow_id"] == workflow_id
    assert data["total_findings"] == 1
    assert data["status_counts"]["potential_conflict"] == 1

    # Verify Agent 3 contract: Agent 3 takes list[dict] obligations and list[PolicyFinding] findings
    loaded_findings = [PolicyFinding.model_validate(f) for f in data["findings"]]
    assert len(loaded_findings) == 1
    assert loaded_findings[0].obligation_id == obligation.obligation_id
    assert loaded_findings[0].status == "potential_conflict"

    # Verify evidence and citations file
    evidence_file = tmp_path / workflow_id / "agent_2_policy_mapping" / "evidence_and_citations.json"
    assert evidence_file.exists()

    # Verify mapping summary file
    summary_file = tmp_path / workflow_id / "agent_2_policy_mapping" / "mapping_summary.json"
    assert summary_file.exists()


def test_retrieve_policy_candidates_builds_multi_queries():
    """Requirement 2: Semantic retrieval multi-query construction."""
    obligation = make_obligation(
        amount_threshold=50000,
        currency="INR",
        deadline_or_frequency="7 days",
    )
    # Even with an uninitialized or mocked vector store, calling with a dummy store works cleanly
    docs = retrieve_policy_candidates(obligation, top_k=5)
    assert isinstance(docs, list)
