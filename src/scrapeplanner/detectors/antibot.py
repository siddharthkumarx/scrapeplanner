"""Name the anti-bot vendor in front of a site, and recognise block pages.

Detection only. The signals below are public, documented artefacts (header
names, cookie names, script hosts, the titles of block pages). This module
never tries to avoid them, and nothing in this project does (D-007).

Two levels per vendor:

* ``present``: a header, cookie or script shows the vendor in front of the
  site, but the page was served;
* ``challenge``: the response is a block or interstitial page from the vendor.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from scrapeplanner.models import AntiBotReport, VendorHit, VendorName

Kind = Literal["header", "header_value", "challenge_header", "cookie", "marker", "challenge"]


@dataclass(frozen=True)
class Signal:
    vendor: VendorName
    kind: Kind
    pattern: str
    """header: header name; header_value / challenge_header: ``name=regex`` on the
    header value; cookie: regex on cookie names; marker / challenge: regex
    searched in the body (a challenge marker counts only on an interstitial)."""
    label: str


SIGNALS: tuple[Signal, ...] = (
    # Cloudflare. As a CDN it is everywhere; that alone is "present".
    Signal("cloudflare", "header", "cf-ray", "header cf-ray"),
    Signal("cloudflare", "header_value", r"server=^cloudflare", "header server: cloudflare"),
    Signal("cloudflare", "cookie", r"^__cf_bm$", "cookie __cf_bm (bot management)"),
    Signal("cloudflare", "cookie", r"^cf_clearance$", "cookie cf_clearance"),
    Signal(
        "cloudflare",
        "challenge_header",
        r"cf-mitigated=challenge",
        "header cf-mitigated: challenge",
    ),
    Signal(
        "cloudflare",
        "challenge",
        r"<title>\s*Just a moment\.\.\.\s*</title>",
        "'Just a moment...' interstitial",
    ),
    Signal("cloudflare", "challenge", r"window\._cf_chl_opt", "challenge script _cf_chl_opt"),
    Signal(
        "cloudflare",
        "challenge",
        r"Attention Required! \| Cloudflare",
        "'Attention Required' block page",
    ),
    Signal(
        "cloudflare", "challenge", r"Sorry, you have been blocked", "'you have been blocked' page"
    ),
    # Akamai
    Signal("akamai", "header_value", r"server=^AkamaiGHost", "header server: AkamaiGHost"),
    Signal("akamai", "header", "akamai-grn", "header akamai-grn"),
    Signal("akamai", "header", "x-akamai-transformed", "header x-akamai-transformed"),
    Signal("akamai", "cookie", r"^_abck$", "cookie _abck (Bot Manager)"),
    Signal("akamai", "cookie", r"^bm_sz$", "cookie bm_sz (Bot Manager)"),
    Signal("akamai", "cookie", r"^ak_bmsc$", "cookie ak_bmsc (Bot Manager)"),
    Signal("akamai", "cookie", r"^bm_sv$", "cookie bm_sv (Bot Manager)"),
    Signal("akamai", "challenge", r"errors\.edgesuite\.net", "Akamai 'Access Denied' reference"),
    Signal(
        "akamai",
        "challenge",
        r"sec-if-cpt-container|/_sec/cp_challenge/",
        "Akamai sec-cpt challenge",
    ),
    # DataDome
    Signal("datadome", "header", "x-datadome", "header x-datadome"),
    Signal("datadome", "header", "x-datadome-cid", "header x-datadome-cid"),
    Signal("datadome", "header", "x-dd-b", "header x-dd-b"),
    Signal("datadome", "cookie", r"^datadome$", "cookie datadome"),
    Signal("datadome", "marker", r"js\.datadome\.co|datadome\.co/tags\.js", "DataDome tag script"),
    Signal("datadome", "challenge", r"captcha-delivery\.com", "DataDome captcha-delivery page"),
    # HUMAN (PerimeterX)
    Signal("human", "cookie", r"^_px(3|2|hd|vid|de)$", "cookie _px* (HUMAN)"),
    Signal("human", "cookie", r"^pxcts$", "cookie pxcts (HUMAN)"),
    Signal(
        "human",
        "marker",
        r"client\.perimeterx\.net|client\.px-cloud\.net|px-cdn\.net",
        "HUMAN sensor script",
    ),
    Signal("human", "marker", r"window\._pxAppId", "HUMAN _pxAppId"),
    Signal("human", "challenge", r"px-captcha|captcha\.px-cdn\.net", "HUMAN px-captcha block page"),
    # Imperva (Incapsula)
    Signal("imperva", "header", "x-iinfo", "header x-iinfo"),
    Signal("imperva", "header_value", r"x-cdn=(?i:imperva|incapsula)", "header x-cdn: Imperva"),
    Signal(
        "imperva", "cookie", r"^(visid_incap_|incap_ses_|nlbi_)", "cookie visid_incap_/incap_ses_"
    ),
    Signal("imperva", "cookie", r"^reese84$", "cookie reese84 (Imperva ABP)"),
    Signal(
        "imperva", "challenge", r"_Incapsula_Resource|Incapsula incident ID", "Incapsula block page"
    ),
    # Kasada
    Signal("kasada", "header", "x-kpsdk-ct", "header x-kpsdk-ct"),
    Signal("kasada", "header", "x-kpsdk-cd", "header x-kpsdk-cd"),
    Signal("kasada", "header", "x-kpsdk-r", "header x-kpsdk-r"),
    Signal("kasada", "marker", r"\bKPSDK\b", "Kasada KPSDK script"),
    Signal("kasada", "challenge", r"\bKPSDK\b", "Kasada interstitial"),
    # AWS WAF (Bot Control). Not one of the big six, but common enough to name.
    Signal("aws_waf", "cookie", r"^aws-waf-token$", "cookie aws-waf-token"),
    Signal(
        "aws_waf",
        "challenge_header",
        r"x-amzn-waf-action=challenge|captcha",
        "header x-amzn-waf-action",
    ),
    Signal(
        "aws_waf",
        "challenge",
        r"awsWafCookieDomainList|AwsWafIntegration",
        "AWS WAF challenge page",
    ),
)

CDN_ONLY_EVIDENCE = frozenset(
    {
        "header cf-ray",
        "header server: cloudflare",
        "header server: AkamaiGHost",
        "header akamai-grn",
        "header x-akamai-transformed",
    }
)
"""Signals that show a CDN in front of the site, not its bot management."""
INTERSTITIAL_MAX_CHARS = 30_000
"""Challenge markers in a large 2xx page are an embedded script, not a block."""
BLOCK_STATUSES = frozenset({401, 403, 429, 503})

_COMPILED: dict[str, re.Pattern[str]] = {}


def _regex(pattern: str) -> re.Pattern[str]:
    compiled = _COMPILED.get(pattern)
    if compiled is None:
        compiled = re.compile(pattern, re.IGNORECASE)
        _COMPILED[pattern] = compiled
    return compiled


def detect(
    status: int,
    headers: Mapping[str, str],
    cookie_names: Sequence[str],
    text: str,
) -> list[VendorHit]:
    """Vendors seen in one response."""
    lowered = {key.lower(): value for key, value in headers.items()}
    interstitial = status >= 400 or len(text) <= INTERSTITIAL_MAX_CHARS
    hits: dict[str, VendorHit] = {}
    for signal in SIGNALS:
        fired = False
        challenge = False
        if signal.kind == "header":
            fired = signal.pattern in lowered
        elif signal.kind in ("header_value", "challenge_header"):
            name, _, value_pattern = signal.pattern.partition("=")
            value = lowered.get(name)
            fired = value is not None and bool(_regex(value_pattern).search(value))
            challenge = fired and signal.kind == "challenge_header"
        elif signal.kind == "cookie":
            fired = any(_regex(signal.pattern).search(name) for name in cookie_names)
        elif signal.kind == "marker":
            fired = bool(_regex(signal.pattern).search(text))
        else:  # challenge marker
            fired = bool(_regex(signal.pattern).search(text))
            challenge = fired and interstitial
        if not fired:
            continue
        hit = hits.setdefault(signal.vendor, VendorHit(vendor=signal.vendor, status="present"))
        if signal.label not in hit.evidence:
            hit.evidence.append(signal.label)
        if challenge:
            hit.status = "challenge"
    if status == 429 and "kasada" in hits:
        hits["kasada"].status = "challenge"
    for hit in hits.values():
        hit.bot_management = _managed(hit)
    return list(hits.values())


def _managed(hit: VendorHit) -> bool:
    if hit.status == "challenge":
        return True
    return not set(hit.evidence) <= CDN_ONLY_EVIDENCE


def classify_block(
    status: int, headers: Mapping[str, str], cookie_names: Sequence[str], text: str
) -> tuple[Literal["blocked", "challenge", "rate_limited"], str] | None:
    """Should the run stop after this response? Returns (reason, detail) or None."""
    hits = detect(status, headers, cookie_names, text)
    for hit in hits:
        if hit.status == "challenge":
            return "challenge", f"{hit.vendor} challenge page (HTTP {status}: {hit.evidence[-1]})"
    if status == 429:
        return "rate_limited", "HTTP 429 Too Many Requests"
    if status in BLOCK_STATUSES:
        vendors = ", ".join(hit.vendor for hit in hits)
        suffix = f"; {vendors} in front of the site" if vendors else ""
        return "blocked", f"HTTP {status}{suffix}"
    return None


def merge(responses: Iterable[tuple[str, list[VendorHit]]]) -> AntiBotReport:
    """Combine per-response hits (``(url, hits)``) into one report."""
    report = AntiBotReport()
    by_vendor: dict[str, VendorHit] = {}
    for url, hits in responses:
        for hit in hits:
            merged = by_vendor.get(hit.vendor)
            if merged is None:
                merged = VendorHit(vendor=hit.vendor, status="present")
                by_vendor[hit.vendor] = merged
                report.vendors.append(merged)
            for item in hit.evidence:
                if item not in merged.evidence:
                    merged.evidence.append(item)
            if hit.status == "challenge":
                merged.status = "challenge"
                if not report.challenged:
                    report.challenged = True
                    report.challenge_url = url
            merged.bot_management = _managed(merged)
    return report
