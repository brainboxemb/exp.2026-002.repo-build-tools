"""Minimal Pants target type used only by this make/buy experiment."""

from pants.engine.target import COMMON_TARGET_FIELDS, Dependencies, MultipleSourcesField, Target


class RepositoryCapabilitySourcesField(MultipleSourcesField):
    alias = "sources"
    help = "Repository paths whose change directly impacts this logical capability."


class RepositoryCapabilityTarget(Target):
    alias = "repo_capability"
    core_fields = (
        *COMMON_TARGET_FIELDS,
        Dependencies,
        RepositoryCapabilitySourcesField,
    )
    help = (
        "A logical repository capability used by the repository-impact experiment. "
        "It has no execution semantics."
    )
