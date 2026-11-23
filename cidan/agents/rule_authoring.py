import logging
from typing import Any, Callable
from pydantic import BaseModel, Field

from cidan.agents.base import invoke_structured
from cidan.models import Citation, PolicyFinding, RuleCondition, RuleProposal

logger = logging.getLogger(__name__)


class ProposalBatch(BaseModel):
    proposals: list[RuleProposal] = Field(default_factory=list)


SYSTEM = """Draft constrained declarative proposals only for evidence-supported
partially covered or conflicting findings. Use only allowlisted fields/operators.
Never emit executable code, shell, SQL, or arbitrary expressions. Every proposal starts
as draft and cites source evidence. The circular is synthetic, not legally binding.
Do not invent an effective date.

For sandbox validation, include both baseline_rule and sandbox_rule only when the cited
handbook and circular explicitly support deterministic conditions, product scope, and
outcomes. They must use the same rule_id and product_type, and different versions.
Set change_id to the ID of this proposed change and use it in sandbox_rule.change_id.
Use only fields present in the policy evidence and operators gt, gte, lt, lte, eq, ne,
or between. If the baseline cannot be deterministically represented, leave both rules
null and record the reason in unresolved_questions. Include unrelated_product_types
only when those products are evidenced by the supplied policy citations; do not invent
product categories. A rule without a complete baseline, proposed rule, and unrelated
product evidence must remain for manual review."""


def _create_human_review_proposal(
    item: dict,
    finding: PolicyFinding,
    reason: str = "Insufficient deterministic policy evidence; requires human compliance review before rule definition.",
) -> RuleProposal:
    source_citation = Citation.model_validate(item["source"])
    citations = [source_citation]
    if finding.policy_citations:
        citations.extend(finding.policy_citations[:2])

    clause = str(item.get("clause_id", finding.obligation_id)).replace(".", "-")
    rule_id = f"RULE-{clause}-REV"
    change_id = f"CHG-{clause}"
    provision = finding.matching_policy_provision or "None identified"

    return RuleProposal(
        rule_id=rule_id,
        version=1,
        change_id=change_id,
        business_purpose=f"Compliance review draft for {finding.obligation_id}: {finding.reasoning[:120]}",
        source_obligation_ids=[item["obligation_id"]],
        source_policy_references=[provision] if provision else [],
        description=f"Human review required: draft declarative rule for {item.get('required_action', finding.obligation_id)[:100]}. {finding.missing_or_inconsistent[:120]}",
        trigger_conditions=[RuleCondition(field="is_emergency", operator="eq", value=True)],
        required_inputs=["transaction_id", "is_emergency"],
        decision_outcomes=["flag_review"],
        validation_criteria=["Compliance manual review and rule specification approval."],
        rollback_considerations="Maintain existing manual compliance review controls.",
        supporting_citations=citations,
        baseline_rule=None,
        sandbox_rule=None,
        unrelated_product_types=[],
        action="flag_review",
        status="draft",
        risk_level="undetermined",
        unresolved_questions=[reason],
        review_reasons=[reason],
        existing_policy_provision=provision,
        proposed_rule=f"Flag for human review: {item.get('required_action', 'Compliance review')}",
        reason_for_change=finding.reasoning,
        operational_impact=finding.operational_impact,
        confidence=finding.confidence,
    )


def _save_outputs(
    workflow_id: str,
    proposals: list[RuleProposal],
    eligible: list[PolicyFinding],
    obligations: list[dict],
) -> None:
    from cidan.services import agent3_storage

    proposals_json = [p.model_dump(mode="json") for p in proposals]
    agent3_storage.save_rule_proposals(
        workflow_id=workflow_id,
        proposals=proposals_json,
        eligible_count=len(eligible),
    )

    evidence_records = []
    for proposal in proposals:
        ob_id = proposal.source_obligation_ids[0] if proposal.source_obligation_ids else ""
        for citation in proposal.supporting_citations:
            evidence_records.append({
                "rule_id": proposal.rule_id,
                "obligation_id": ob_id,
                "document_id": citation.document_id,
                "filename": citation.filename,
                "document_type": citation.document_type,
                "page": citation.page,
                "chunk_id": citation.chunk_id,
                "excerpt": citation.excerpt,
                "is_valid": bool(citation.chunk_id),
            })
    agent3_storage.save_evidence_and_citations(workflow_id, evidence_records)

    sandbox_ready = sum(1 for p in proposals if p.baseline_rule is not None and p.sandbox_rule is not None)
    human_review = sum(1 for p in proposals if p.action == "flag_review" or p.unresolved_questions or p.review_reasons)
    action_counts: dict[str, int] = {}
    risk_counts: dict[str, int] = {}
    for p in proposals:
        action_counts[p.action] = action_counts.get(p.action, 0) + 1
        risk_counts[p.risk_level] = risk_counts.get(p.risk_level, 0) + 1

    summary = {
        "workflow_id": workflow_id,
        "total_proposals": len(proposals),
        "eligible_findings": len(eligible),
        "draft_count": len(proposals),
        "sandbox_ready_count": sandbox_ready,
        "human_review_required_count": human_review,
        "status_counts": {"draft": len(proposals)},
        "action_counts": action_counts,
        "risk_counts": risk_counts,
    }
    agent3_storage.save_rule_summary(workflow_id, summary)
    agent3_storage.save_execution_metadata(workflow_id, {
        "status": "completed",
        "agent": "agent_3_rule_authoring",
        "total_proposals": len(proposals),
    })


def run(
    obligations: list[dict],
    findings: list[PolicyFinding],
    workflow_id: str | None = None,
    llm_call: Callable[..., Any] = invoke_structured,
) -> list[RuleProposal]:
    eligible = [
        finding for finding in findings
        if finding.status in {"partially_covered", "potential_conflict"}
    ]
    if not eligible:
        if workflow_id:
            _save_outputs(workflow_id, [], eligible, obligations)
        return []

    obligation_by_id = {item["obligation_id"]: item for item in obligations}
    proposals: list[RuleProposal] = []
    seen_obligations: set[str] = set()

    for finding in eligible:
        ob_id = finding.obligation_id
        if ob_id in seen_obligations:
            continue
        seen_obligations.add(ob_id)

        item = obligation_by_id.get(ob_id)
        if not item:
            continue

        compact_obligation = {
            "obligation_id": item["obligation_id"],
            "text": item["text"][:250],
            "amount_threshold": item.get("amount_threshold"),
            "currency": item.get("currency"),
            "effective_date": item.get("effective_date", "not_specified"),
            "required_action": item["required_action"][:160],
            "source": {
                key: item["source"][key]
                for key in ("document_id", "filename", "document_type", "page", "chunk_id")
            }
            | {"excerpt": item["source"]["excerpt"][:160]},
        }
        compact_finding = {
            "obligation_id": finding.obligation_id,
            "status": finding.status,
            "reasoning": finding.reasoning[:220],
            "missing_or_inconsistent": finding.missing_or_inconsistent[:180],
            "operational_impact": finding.operational_impact[:140],
            "recommended_action": finding.recommended_action[:140],
            "confidence": finding.confidence,
            "circular_citation": {
                **finding.circular_citation.model_dump(mode="json"),
                "excerpt": finding.circular_citation.excerpt[:160],
            },
            "policy_citations": [
                {
                    **citation.model_dump(mode="json"),
                    "excerpt": citation.excerpt[:160],
                }
                for citation in finding.policy_citations
            ],
        }

        try:
            batch = llm_call(
                ProposalBatch, SYSTEM,
                "Draft at most one proposal for this single eligible finding. Return no "
                "proposal if a safe declarative rule cannot be supported.\n"
                f"Obligation:\n{compact_obligation}\nFinding:\n{compact_finding}",
            )
        except Exception as exc:
            logger.warning(
                "LLM rule proposal generation failed for %s: %s; falling back to human review draft.",
                ob_id, exc,
            )
            batch = ProposalBatch(proposals=[
                _create_human_review_proposal(
                    item, finding,
                    reason=f"Automated rule authoring requires human review: {str(exc)[:150]}",
                )
            ])

        if not batch.proposals:
            batch = ProposalBatch(proposals=[
                _create_human_review_proposal(
                    item, finding,
                    reason="Insufficient deterministic policy evidence; requires human review before rule creation.",
                )
            ])

        if len(batch.proposals) > 1:
            raise ValueError("Rule authoring must return at most one proposal per finding.")

        for p in batch.proposals:
            # Populate required fields
            if not p.existing_policy_provision:
                p.existing_policy_provision = finding.matching_policy_provision or (
                    finding.policy_citations[0].excerpt if finding.policy_citations else "None identified"
                )
            if not p.proposed_rule:
                p.proposed_rule = p.description
            if not p.reason_for_change:
                p.reason_for_change = p.business_purpose or finding.reasoning
            if not p.operational_impact:
                p.operational_impact = finding.operational_impact
            if p.confidence is None or p.confidence == 0.85:
                p.confidence = finding.confidence
            if not p.source_policy_references and finding.matching_policy_provision:
                p.source_policy_references = [finding.matching_policy_provision]

            proposals.append(p)

    eligible_ids = {finding.obligation_id for finding in eligible}
    citations_by_obligation: dict[str, dict[tuple[str, str, str, int, str], str]] = {}
    for finding in eligible:
        source = Citation.model_validate(obligation_by_id[finding.obligation_id]["source"])
        citations = [source, finding.circular_citation, *finding.policy_citations]
        citations_by_obligation[finding.obligation_id] = {
            (
                citation.document_id,
                citation.filename,
                citation.document_type,
                citation.page,
                citation.chunk_id,
            ): citation.excerpt
            for citation in citations
        }

    seen_ids: set[str] = set()
    validated_proposals: list[RuleProposal] = []
    for proposal in proposals:
        proposal_obligations = set(proposal.source_obligation_ids)
        if not proposal_obligations or not proposal_obligations <= eligible_ids:
            raise ValueError("Proposal references an unsupported policy finding.")
        if len(proposal_obligations) != len(proposal.source_obligation_ids):
            raise ValueError("Proposal contains duplicate source obligation IDs.")
        if proposal.rule_id in seen_ids:
            raise ValueError("The rule authoring agent returned duplicate rule IDs.")
        seen_ids.add(proposal.rule_id)

        supported_citations = {
            key: excerpt
            for obligation_id in proposal.source_obligation_ids
            for key, excerpt in citations_by_obligation[obligation_id].items()
        }
        proposal_citation_keys = set()
        for citation in proposal.supporting_citations:
            citation_key = (
                citation.document_id,
                citation.filename,
                citation.document_type,
                citation.page,
                citation.chunk_id,
            )
            source_excerpt = supported_citations.get(citation_key)
            if not source_excerpt or citation.excerpt not in source_excerpt:
                raise ValueError("Rule proposal contains an unsupported source citation.")
            proposal_citation_keys.add(citation_key)

        for obligation_id in proposal.source_obligation_ids:
            obligation_source = Citation.model_validate(
                obligation_by_id[obligation_id]["source"]
            )
            source_key = (
                obligation_source.document_id,
                obligation_source.filename,
                obligation_source.document_type,
                obligation_source.page,
                obligation_source.chunk_id,
            )
            if source_key not in proposal_citation_keys:
                raise ValueError(
                    "Rule proposal must cite the circular source for each linked obligation."
                )

        # Enforce draft status until human approval gate
        proposal.status = "draft"
        validated_proposals.append(proposal)

    if workflow_id:
        _save_outputs(workflow_id, validated_proposals, eligible, obligations)

    return validated_proposals
