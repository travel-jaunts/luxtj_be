from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowDefinition:
    key: str
    label: str


_REGISTRY: dict[str, WorkflowDefinition] = {
    "kyc_approval": WorkflowDefinition(key="kyc_approval", label="KYC Approvals"),
    "content_review": WorkflowDefinition(key="content_review", label="Content Reviews"),
}


def get_registered_workflows() -> list[WorkflowDefinition]:
    return list(_REGISTRY.values())


def get_workflow(key: str) -> WorkflowDefinition | None:
    return _REGISTRY.get(key)


def is_registered(key: str) -> bool:
    return key in _REGISTRY
