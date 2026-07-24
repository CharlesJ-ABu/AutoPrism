from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason_code: str
    message: str
    requires_human_action: bool = False


def evaluate_static_policy(
    url: str,
    *,
    enabled: bool,
    requires_auth: bool,
    credential_available: bool,
    blocked_domains: set[str] | None = None,
) -> PolicyDecision:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return PolicyDecision(False, "INVALID_URL", "Only HTTP(S) sources are allowed")
    if not enabled:
        return PolicyDecision(False, "SOURCE_DISABLED", "Source is disabled")
    if blocked_domains and parsed.hostname.lower() in blocked_domains:
        return PolicyDecision(False, "DOMAIN_BLOCKED", "Domain is blocked by policy")
    if requires_auth and not credential_available:
        return PolicyDecision(
            False,
            "CREDENTIAL_REQUIRED",
            "User-provided source credentials are required",
            True,
        )
    return PolicyDecision(True, "ALLOWED", "Static policy checks passed")


def evaluate_robots(
    robots_text: str,
    *,
    robots_url: str,
    target_url: str,
    user_agent: str,
) -> PolicyDecision:
    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(robots_text.splitlines())
    if parser.can_fetch(user_agent, target_url):
        return PolicyDecision(True, "ROBOTS_ALLOWED", "robots policy allows access")
    return PolicyDecision(
        False,
        "ROBOTS_BLOCKED",
        "robots policy disallows automated access",
        True,
    )
