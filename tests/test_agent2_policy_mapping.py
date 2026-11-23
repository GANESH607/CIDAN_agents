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
        ("not_found", 0.70),
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
        assert finding.model_reported_confidence == conf
        assert finding.confidence <= conf
        assert finding.obligation_id == obligation.obligation_id
        assert finding.circular_citation.chunk_id == obligation.source.chunk_id
        if cited_chunks:
            assert len(finding.policy_citations) == 1
            assert finding.policy_citations[0].chunk_id == "pol-c1"
        else:
            assert len(finding.policy_citations) == 0


def test_retrieval_error_handling_and_incomplete_retrieval_safety(caplog):
    """Improvement 1: Retrieval failures are logged and incomplete retrieval is not mistaken for missing policy."""
    import logging
    from cidan.ingestion import retrieval

    obligation = make_obligation()

    # Simulate vector store with errors
    class BrokenVectorStore:
        def similarity_search(self, query, k=8, filter=None):
            raise ConnectionError("Vector store cluster unreachable")

    # When all retrieval fails due to error, retrieve_policy_candidates raises RuntimeError and logs error
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError) as exc_info:
            with pytest.MonkeyPatch.context() as mp:
                mp.setattr(retrieval, "create_vector_store", lambda: BrokenVectorStore())
                retrieval.retrieve_policy_candidates(obligation)
        assert "Vector store cluster unreachable" in str(exc_info.value)
        assert any("Error during policy similarity search" in r.message for r in caplog.records)

    # When partial retrieval succeeds but is incomplete, policy_mapping ensures it's not mistaken for not_found
    doc = make_policy_doc(chunk_id="pol-partial")
    doc.metadata["retrieval_incomplete"] = True
    doc.metadata["retrieval_errors"] = ["partial error"]

    def model_claiming_not_found(schema, system, prompt):
        return schema(
            status="not_found",
            reasoning="No provision was found in retrieved text.",
            missing_or_inconsistent="Not present.",
            operational_impact="Verify manually.",
            recommended_action="Manual review.",
            confidence=0.85,
            evidence_limitations=[],
            cited_policy_chunk_ids=[],
        )

    findings = policy_mapping.run([obligation], [doc], llm_call=model_claiming_not_found)
    assert len(findings) == 1
    # not_found MUST be converted to requires_human_review when retrieval was incomplete!
    assert findings[0].status == "requires_human_review"
    assert any("incomplete retrieval" in lim.lower() for lim in findings[0].evidence_limitations)


def test_citation_improvements_up_to_five_and_strict_validation():
    """Improvement 2: Support up to 5 citations and strictly validate each against retrieved chunks."""
    obligation = make_obligation()
    docs = [
        make_policy_doc(chunk_id=f"pol-{i}", page=i, clause_id=f"2.{i}")
        for i in range(1, 6)
    ]

    def five_citation_llm(schema, system, prompt):
        assert "five citation chunk IDs" in system
        return schema(
            status="covered",
            reasoning="Coverage supported across 5 separate policy clauses.",
            missing_or_inconsistent="None.",
            operational_impact="Operations aligned.",
            recommended_action="Monitor SLA compliance.",
            confidence=0.95,
            evidence_limitations=[],
            cited_policy_chunk_ids=["pol-1", "pol-2", "pol-3", "pol-4", "pol-5"],
        )

    findings = policy_mapping.run([obligation], docs, llm_call=five_citation_llm)
    assert len(findings) == 1
    assert len(findings[0].policy_citations) == 5
    assert [c.chunk_id for c in findings[0].policy_citations] == [f"pol-{i}" for i in range(1, 6)]

    # Test with a mix of valid and invalid chunk IDs
    def mixed_citation_llm(schema, system, prompt):
        return schema(
            status="covered",
            reasoning="Coverage claim.",
            missing_or_inconsistent="None.",
            operational_impact="None.",
            recommended_action="None.",
            confidence=0.90,
            evidence_limitations=[],
            cited_policy_chunk_ids=["pol-1", "fake-chunk-99"],
        )

    findings_mixed = policy_mapping.run([obligation], docs, llm_call=mixed_citation_llm)
    assert len(findings_mixed[0].policy_citations) == 1
    assert findings_mixed[0].policy_citations[0].chunk_id == "pol-1"
    assert any("unverified citations" in lim.lower() for lim in findings_mixed[0].evidence_limitations)


def test_confidence_distinguishes_model_confidence_from_evidence_quality():
    """Improvement 3: Model-reported confidence is distinct from evidence quality and cannot inflate confidence."""
    obligation = make_obligation()
    doc = make_policy_doc(chunk_id="pol-1")

    # High model confidence (0.99) but invalid citation -> evidence quality is 0.0, confidence must not be 0.99
    def overconfident_llm(schema, system, prompt):
        return schema(
            status="covered",
            reasoning="I am absolutely 100% confident this is covered.",
            missing_or_inconsistent="None.",
            operational_impact="None.",
            recommended_action="None.",
            confidence=0.99,
            evidence_limitations=[],
            cited_policy_chunk_ids=["non-existent-chunk"],
        )

    findings = policy_mapping.run([obligation], [doc], llm_call=overconfident_llm)
    finding = findings[0]
    assert finding.model_reported_confidence == 0.99
    assert finding.evidence_confidence == 0.0
    assert finding.confidence <= 0.40  # Capped and grounded in evidence quality
    assert finding.status == "requires_human_review"


def test_matching_policy_provision_identifies_most_relevant_clause():
    """Improvement 4: matching_policy_provision identifies the most relevant clause, not just the first cited chunk."""
    obligation = make_obligation(
        clause_id="2.5",
        text="Acknowledge senior citizen complaints within 1 working day.",
        required_action="Acknowledge senior citizen complaints within 1 working day",
    )

    # Chunk 1: Preamble / General definitions (Clause 1.1)
    doc_preamble = make_policy_doc(
        chunk_id="pol-preamble",
        content="Clause 1.1 General Scope: This policy applies to all branch banking operations.",
        clause_id="1.1",
        page=1,
    )
    # Chunk 2: Exactly matches obligation clause 2.5 and required action
    doc_target = make_policy_doc(
        chunk_id="pol-grievance",
        content="Clause 2.5 Grievance handling | Senior citizen complaints must be acknowledged within 2 working days.",
        clause_id="2.5",
        page=3,
    )

    # LLM happens to cite the preamble first, then the grievance clause second
    def llm_citing_preamble_first(schema, system, prompt):
        return schema(
            status="potential_conflict",
            reasoning="Timeline conflict between 1 day requirement and 2 day policy.",
            missing_or_inconsistent="Acknowledgment SLA.",
            operational_impact="Operational backlog.",
            recommended_action="Align policy SLA.",
            confidence=0.90,
            evidence_limitations=[],
            cited_policy_chunk_ids=["pol-preamble", "pol-grievance"],
        )

    findings = policy_mapping.run([obligation], [doc_preamble, doc_target], llm_call=llm_citing_preamble_first)
    finding = findings[0]
    # Despite pol-preamble being cited first, matching_policy_provision should correctly select Clause 2.5!
    assert "2.5" in finding.matching_policy_provision
    assert "Clause 2.5" in finding.matching_policy_provision


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


def test_retrieve_policy_candidates_builds_multi_queries(monkeypatch):
    """Requirement 2: Semantic retrieval multi-query construction."""
    from cidan.ingestion import retrieval

    obligation = make_obligation(
        amount_threshold=50000,
        currency="INR",
        deadline_or_frequency="7 days",
    )
    captured_queries = []

    class MockStore:
        def similarity_search(self, query, k=8, filter=None):
            captured_queries.append((query, filter))
            return [
                Document(
                    page_content="Policy clause content",
                    metadata={"chunk_id": f"chunk-{len(captured_queries)}", "document_type": "policy_handbook"},
                )
            ]

    monkeypatch.setattr(retrieval, "create_vector_store", lambda: MockStore())
    docs = retrieval.retrieve_policy_candidates(obligation, top_k=5)
    assert isinstance(docs, list)
    assert len(captured_queries) >= 3
    # Check query diversity across multi-queries
    query_texts = [q[0] for q in captured_queries]
    assert any("50000" in q for q in query_texts)  # Numerical specifics query
    assert any("7 days" in q for q in query_texts)  # SLA / operational query
