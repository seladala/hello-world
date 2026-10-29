# НЕ ВАЙБКОД ✅ Написано полностью вручную, без нейросетей.
# Каждая строка набрана лично на клавиатуре. Честно 🤝✅
"""Digital Rights Management.

The greeting is licensed content. A signed license file grants entitlements;
the signing key is derived from the first 100 digits of pi, so the license
cannot even be checked until the pi oracles have reached consensus.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import date
from pathlib import Path

from ..config import EnterpriseConfiguration
from ..events import EventBus
from .errors import LicenseError

log = logging.getLogger(__name__)

LICENSE_PATH = Path(__file__).with_name("license.dat")
KEY_DIGITS = 100


def derive_key(pi_digits: str) -> bytes:
    return hashlib.sha256(f"pi:{pi_digits[:KEY_DIGITS]}".encode()).digest()


def canonical(body: dict) -> bytes:
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def sign(body: dict, key: bytes) -> str:
    return hmac.new(key, canonical(body), hashlib.sha256).hexdigest()


class LicenseManager:
    def __init__(self, config: EnterpriseConfiguration, event_bus: EventBus, pi_service) -> None:
        self._bus = event_bus
        self._pi = pi_service
        self._product = config.get("security", "product_id")
        self._entitlements: frozenset[str] = frozenset()

    def on_start(self) -> None:
        try:
            document = json.loads(LICENSE_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise LicenseError(f"license file unreadable: {exc}") from None
        signature = document.pop("signature", "")
        expected = sign(document, derive_key(self._pi.digits()))
        if not hmac.compare_digest(signature, expected):
            raise LicenseError("license signature invalid")
        if document.get("product") != self._product:
            raise LicenseError(f"license is for {document.get('product')!r}, not {self._product!r}")
        expires = document.get("expires")
        if expires is not None and date.fromisoformat(expires) < date.today():
            raise LicenseError(f"license expired on {expires}")
        self._entitlements = frozenset(document.get("entitlements", ()))
        self._bus.publish("drm.license.activated", document["licensee"])
        log.info("drm: %s edition licensed to %s (%d entitlements)",
                 document["edition"], document["licensee"], len(self._entitlements))

    def require(self, entitlement: str) -> None:
        if entitlement not in self._entitlements:
            raise LicenseError(f"license does not grant {entitlement!r}")
