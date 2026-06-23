from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from opcua import Client

logger = logging.getLogger(__name__)


class OPCErrorCodes:
    INVALID_ENDPOINT = "OPC_INVALID_ENDPOINT"
    CONNECT_TIMEOUT = "OPC_CONNECT_TIMEOUT"
    AUTH_FAILED = "OPC_AUTH_FAILED"
    SECURITY_UNSUPPORTED = "OPC_SECURITY_UNSUPPORTED"
    CERT_INVALID = "OPC_CERT_INVALID"
    CONNECT_FAILED = "OPC_CONNECT_FAILED"
    BROWSE_FAILED = "OPC_BROWSE_FAILED"
    READ_FAILED = "OPC_READ_FAILED"


@dataclass
class OPCError(Exception):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details or {},
        }


def _resolve_security_mode(mode: str):
    from opcua import ua

    mapping = {
        "None": ua.MessageSecurityMode.None_,
        "Sign": ua.MessageSecurityMode.Sign,
        "SignAndEncrypt": ua.MessageSecurityMode.SignAndEncrypt,
    }
    if mode not in mapping:
        raise OPCError(
            OPCErrorCodes.SECURITY_UNSUPPORTED,
            f"Invalid security_mode: {mode}. Must be one of: {', '.join(mapping)}",
        )
    return mapping[mode]


def _resolve_security_policy(policy: str):
    from opcua import ua

    mapping = {
        "Basic256Sha256": ua.SecurityPolicyType.Basic256Sha256,
        "Basic256": ua.SecurityPolicyType.Basic256,
        "None": ua.SecurityPolicyType.NoSecurity,
    }
    if policy not in mapping:
        raise OPCError(
            OPCErrorCodes.SECURITY_UNSUPPORTED,
            f"Invalid security_policy: {policy}. Must be one of: {', '.join(mapping)}",
        )
    return mapping[policy]


def _username_endpoint_supported(endpoints) -> tuple[bool, Optional[str], Optional[str]]:
    from opcua import ua

    for ep in endpoints:
        for token in ep.UserIdentityTokens:
            if token.TokenType == ua.UserTokenType.UserName:
                mode_str = str(ep.SecurityMode)
                # ← Fix: read the TOKEN's security policy, not the endpoint's
                token_policy_uri = token.SecurityPolicyUri or ""
                return True, mode_str, token_policy_uri
    return False, None, None




def create_opcua_client(
    *,
    endpoint_url: str,
    timeout_seconds: int = 10,
    security_policy: Optional[str] = None,
    security_mode: Optional[str] = None,
    auth_type: str = "username",
    username: str = "admin",
    password: str = "123456",
    client_cert_path: Optional[str] = None,
    client_key_path: Optional[str] = None,
    server_cert_path: Optional[str] = None,
) -> Client:
    if not endpoint_url or not isinstance(endpoint_url, str):
        raise OPCError(OPCErrorCodes.INVALID_ENDPOINT, "endpoint_url is required")

    try:
        client = Client(endpoint_url, timeout=timeout_seconds)

        # ── 1. Transport security ─────────────────────────────────────────
        if security_policy and security_mode:
            try:
                policy_cls = _resolve_security_policy(security_policy)
                mode_val   = _resolve_security_mode(security_mode)

                if not client_cert_path or not client_key_path:
                    raise OPCError(
                        code=OPCErrorCodes.CERT_INVALID,
                        message=(
                            "client_cert_path and client_key_path are required "
                            "when security_policy and security_mode are set."
                        ),
                        details={},
                    )

                client.set_security(
                    policy_cls,
                    client_cert_path,
                    client_key_path,
                    server_cert_path,
                    mode_val,
                )
            except OPCError:
                raise
            except Exception as e:
                raise OPCError(
                    OPCErrorCodes.SECURITY_UNSUPPORTED,
                    "Failed to apply OPC UA security settings",
                    {"error": str(e)},
                )

        # ── 2. Authentication ─────────────────────────────────────────────
        if auth_type == "username":
            if not username or not password:
                raise OPCError(
                    OPCErrorCodes.AUTH_FAILED,
                    "username and password are required when auth_type='username'",
                )
            client.set_user(username)
            client.set_password(password)

        # No pre-discovery probe. Probing via connect_and_get_server_endpoints()
        # on a server that enforces UserName-only auth (patched activate_session)
        # causes the probe's anonymous token to be rejected, surfacing as
        # BadUserAccessDenied / "Bad Request" before the real connect even runs.

        return client

    except OPCError:
        raise
    except Exception as e:
        raise OPCError(
            OPCErrorCodes.CONNECT_FAILED,
            "Failed to create OPC UA client",
            {"error": str(e)},
        )