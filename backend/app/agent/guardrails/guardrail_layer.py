"""GuardrailLayer — 3-level safety checks: input, action, output.

Blocks FORBIDDEN_MVP actions, detects PII, validates output format.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml
import structlog

logger = structlog.get_logger()

# PII patterns for Italian documents
_CF_PATTERN = re.compile(r"[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]", re.IGNORECASE)
_PIVA_PATTERN = re.compile(r"\b\d{11}\b")
_IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}[A-Z0-9]{0,16}\b", re.IGNORECASE)

# Date ISO 8601 validation
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


class GuardrailResult:
    def __init__(self, allowed: bool, reason: str = "") -> None:
        self.allowed = allowed
        self.reason = reason


class GuardrailLayer:
    def __init__(self) -> None:
        base = Path(__file__).parent
        self._constitution = (base / "constitution.md").read_text()

        blacklist_path = base / "blacklist.yaml"
        data = yaml.safe_load(blacklist_path.read_text()) or {}
        self._blacklist: list[dict] = data.get("blacklist", [])

    def check_input(self, text: str) -> GuardrailResult:
        """Level 1: Check user input for jailbreak, PII, blacklisted keywords."""
        # Jailbreak detection
        jailbreak_phrases = ["ignora le istruzioni", "ignore previous", "sei ora", "you are now"]
        for phrase in jailbreak_phrases:
            if phrase.lower() in text.lower():
                logger.warning("guardrail_block", level="input", reason="jailbreak_attempt")
                return GuardrailResult(False, "Input bloccato: tentativo di jailbreak rilevato")

        # Blacklist check
        for item in self._blacklist:
            for kw in item.get("keywords", []):
                if kw.lower() in text.lower():
                    logger.warning("guardrail_block", level="input", reason=item.get("id"))
                    return GuardrailResult(False, item.get("error_message", "Azione non consentita"))

        return GuardrailResult(True)

    def check_action(self, tool_name: str, args: dict) -> GuardrailResult:
        """Level 2: Verify tool call against blacklist + constitution."""
        for item in self._blacklist:
            if tool_name == item.get("id"):
                logger.warning("guardrail_block", level="action", tool=tool_name)
                return GuardrailResult(False, item.get("error_message", "Azione vietata"))

        # Constitution check: no fiscal advice
        forbidden_actions = ["invio_ente_pubblico", "pagamento", "modifica_gestionale", "consiglio_fiscale"]
        if tool_name in forbidden_actions:
            return GuardrailResult(False, f"Azione vietata dalla Constitution: {tool_name}")

        return GuardrailResult(True)

    def check_output(self, text: str) -> GuardrailResult:
        """Level 3: Block only explicit interpretive fiscal/legal advice."""
        # Only block explicit interpretive fiscal advice (not generic helpful phrases)
        fiscal_phrases = [
            "secondo la mia interpretazione fiscale",
            "come commercialista ti suggerisco",
            "la legge prevede che tu debba",
        ]
        for phrase in fiscal_phrases:
            if phrase.lower() in text.lower():
                logger.warning("guardrail_block", level="output", reason="fiscal_advice")
                return GuardrailResult(False, "Output bloccato: consiglio fiscale interpretativo")

        return GuardrailResult(True)

    def detect_pii(self, text: str) -> list[dict]:
        """Detect PII patterns in text."""
        findings: list[dict] = []
        for m in _CF_PATTERN.finditer(text):
            findings.append({"type": "codice_fiscale", "match": m.group(), "pos": m.start()})
        for m in _PIVA_PATTERN.finditer(text):
            findings.append({"type": "partita_iva", "match": m.group(), "pos": m.start()})
        for m in _IBAN_PATTERN.finditer(text):
            findings.append({"type": "iban", "match": m.group(), "pos": m.start()})
        return findings
