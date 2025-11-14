# Edge services
from .domain_resolver import domain_resolver, DomainResolver
from .decision import decision_service, DecisionService

__all__ = [
    'domain_resolver',
    'DomainResolver',
    'decision_service',
    'DecisionService',
]
