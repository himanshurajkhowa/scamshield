"""Offline URL inspection. No network operations or destination reputation claims."""

import ipaddress
import re
import unicodedata
from collections.abc import Callable
from urllib.parse import SplitResult, unquote, urlsplit

from .contracts import Signal, URLAnalysis, URLLink

MAX_URLS = 20
AddFinding = Callable[[str, str, str, int], None]

# Exact reference hosts, not ownership or destination-content verification.
# eChallan: CERT-In CICA-2026-3492 and MoRTH NextGen (21 Nov 2026).
CHALLAN_HOSTS = frozenset(
    ("echallan.parivahan.gov.in", "echallan.parivahan.nic.in")
)
REFERENCE_HOSTS = frozenset((
    *CHALLAN_HOSTS, "parivahan.gov.in", "sbi.co.in", "hdfcbank.com",
    "icicibank.com", "rbi.org.in", "npci.org.in", "uidai.gov.in",
    "indiapost.gov.in",
))
TOKENS = (
    "parivahan", "echallan", "challan", "hdfcbank", "icicibank",
    "indiapost", "uidai", "npci", "sbi", "rbi",
)
SCHEME = (
    r"(?:[a-z][a-z0-9+.-]*://|"
    r"(?:javascript|data|file|vbscript|intent|market):|//)"
)
BARE = (
    r'(?:www\.)?(?:[\w\-]+\.)+(?:[a-z\u0080-\uffff]{2,63})(?::\d+)?'
    r'(?:[/\?#][^\s<>"\x27]*)?|(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?'
    r'(?:/[^\s<>"\x27]*)?'
)
URL_RE = re.compile(
    r'(?<![\w@])(?:' + SCHEME + r'[^\s<>"\x27]+|' + BARE + r')', re.I
)
CLAIM_RE = re.compile(
    r"\b(?:e[\s-]?challan|challan|parivahan|rto|"
    r"traffic\s+(?:police|fine)|morth)\b", re.I,
)
CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    "і": "i", "ј": "j", "ӏ": "l", "ν": "v", "ɑ": "a", "0": "o", "1": "i",
})


def extract_urls(text: str) -> list[tuple[str, int, int]]:
    """Return link text and offsets without resolving any destination."""
    found = []
    for match in URL_RE.finditer(text):
        value = match.group().rstrip(".,;!?")
        while value.endswith(")") and value.count(")") > value.count("("):
            value = value[:-1]
        found.append((value, match.start(), match.start() + len(value)))
    return found


def is_standalone_url(text: str) -> bool:
    """Check whether one extracted link occupies the submitted text."""
    stripped = text.strip()
    found = extract_urls(stripped)
    return (
        len(found) == 1
        and found[0][1] == 0
        and found[0][2] == len(stripped.rstrip(".,;!?"))
    )


def near(a: str, b: str) -> bool:
    """Check the original bounded edit distance for longer service names."""
    if len(b) < 5 or abs(len(a) - len(b)) > 1:
        return False
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (x != y),
            ))
        previous = current
    return 0 < previous[-1] <= 1


def _parse_link(normalized: str) -> SplitResult:
    """Normalize link syntax and supply the original implicit HTTPS scheme."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", normalized, re.I):
        return urlsplit(normalized)
    if normalized.startswith("//"):
        return urlsplit("https:" + normalized)
    return urlsplit("https://" + normalized)


def _is_ip_host(host: str, ascii_host: str) -> bool:
    """Validate a named hostname or recognize an IPv4/IPv6 literal."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        if not all(
            re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", part)
            for part in ascii_host.split(".")
        ):
            raise ValueError("invalid hostname")
        return False


def _check_service_host(host: str, ascii_host: str, add: AddFinding) -> None:
    """Apply existing lookalike, government, shortener and suffix rules."""
    skeleton = host.translate(CONFUSABLES)
    labels = re.split(r"[.\-]", skeleton)
    deceptive = any(
        domain + "." in ascii_host or ascii_host.endswith("." + domain)
        for domain in REFERENCE_HOSTS
    )
    if deceptive:
        add(
            "url_deceptive", "Official-looking text is not the reference host",
            f"The actual host is {ascii_host}. An official name embedded in "
            "another host does not make it official.", 3,
        )
    named = any(token in skeleton for token in TOKENS if len(token) >= 5) or any(
        label in ("sbi", "rbi", "rto") for label in labels
    )
    lookalike = any(near(label, token) for label in labels for token in TOKENS)
    if named or lookalike:
        add(
            "impersonation", "Service name in an unverified hostname",
            f"The actual host is {ascii_host}, outside the small reference list. "
            "It contains a familiar service name or close spelling; confirm "
            "through the official service.",
            1 if ascii_host.endswith((".gov.in", ".nic.in")) else 3,
        )
    if (
        re.search(r"(?:^|[.\-])gov(?:[.\-]|$)", ascii_host)
        and not ascii_host.endswith((".gov.in", ".nic.in"))
    ):
        add(
            "url_government", "Government-looking hostname",
            f"The actual host {ascii_host} uses government-looking labels "
            "outside .gov.in or .nic.in.", 3,
        )
    if ascii_host in ("bit.ly", "tinyurl.com", "t.co"):
        add(
            "url_shortener", "Short link hides the destination",
            "The final destination is not visible. The short link was not followed.",
            1,
        )
    if ascii_host.endswith((".xyz", ".top", ".click")):
        add(
            "url", "Link needs independent verification",
            "This domain suffix warrants another check. "
            "A suffix alone does not prove fraud.", 1,
        )


def _check_transport(
    parsed: SplitResult, scheme: str, ascii_host: str,
    is_ip: bool, port: int | None, add: AddFinding,
) -> None:
    """Emit existing IP, userinfo, encryption, port and IDN warnings in order."""
    if is_ip:
        add(
            "url_ip", "Link points to an IP address",
            f"The actual host is {ascii_host}, not a named service. "
            "Verify independently before using it.", 2,
        )
    if parsed.username is not None or parsed.password is not None:
        add(
            "url_userinfo", "Displayed service may hide the real host",
            f"Text before @ is not the destination. "
            f"The actual host is {ascii_host}.", 3,
        )
    if scheme == "http":
        add(
            "url_http", "Link is not encrypted",
            "This link uses HTTP. Verify the service independently before "
            "entering information.", 1,
        )
    if port not in (None, 80, 443):
        add(
            "url_port", "Link uses an unusual port",
            f"The destination uses port {port}; verify independently.", 1,
        )
    if any(part.startswith("xn--") for part in ascii_host.split(".")):
        add(
            "url_idn", "Internationalized hostname",
            "The link contains an encoded international hostname. Check its "
            "spelling carefully; this alone does not prove fraud.", 1,
        )


def _inspect_link(
    raw: str, add: AddFinding, hosts: list[str], links: list[URLLink]
) -> None:
    """Append one parsed link, keeping original checks and finding order."""
    item: URLLink = dict(
        host=None, scheme=None, reference_match=False, challan_reference=False
    )
    try:
        # Normalization occurred before ambiguity checks in the original policy.
        normalized = unicodedata.normalize("NFKC", raw)
        if "\\" in raw or any(ord(char) < 32 for char in raw):
            add(
                "url_ambiguous", "Ambiguous link syntax",
                "Backslashes or control characters can make browsers interpret "
                "a link differently. Do not use this link.", 3,
            )
        parsed = _parse_link(normalized)
        scheme = parsed.scheme.casefold()
        item["scheme"] = scheme
        if scheme not in ("http", "https"):
            add(
                "url_scheme", "Link uses a non-web scheme",
                f"The {scheme} scheme can launch an app, access a file or run "
                "content. It was not executed.", 3,
            )
        host = (parsed.hostname or "").rstrip(".").casefold()
        if not host:
            if scheme in ("http", "https"):
                raise ValueError("missing hostname")
            links.append(item)
            return
        if "%" in host or any(char.isspace() for char in host):
            raise ValueError("encoded or invalid hostname")
        ascii_host = host.encode("idna").decode("ascii")
        port = parsed.port  # Validate numeric range/syntax before storing the host.
        is_ip = _is_ip_host(host, ascii_host)
        hosts.append(ascii_host)
        item["host"] = ascii_host
        item["reference_match"] = ascii_host in REFERENCE_HOSTS
        item["challan_reference"] = ascii_host in CHALLAN_HOSTS
        _check_transport(parsed, scheme, ascii_host, is_ip, port, add)
        if not item["reference_match"]:
            _check_service_host(host, ascii_host, add)
        if unquote(parsed.path).casefold().endswith(".apk"):
            add(
                "url_apk", "Link offers an Android installer",
                "An APK from a message can install software with sensitive "
                "permissions. This file was not downloaded.", 3,
            )
        links.append(item)
    except (ValueError, UnicodeError):
        add(
            "url", "Malformed link",
            "The hostname or URL syntax could not be parsed safely. "
            "Do not rely on its displayed name.", 2,
        )
        links.append(item)


def _check_challan_claim(text: str, links: list[URLLink], add: AddFinding) -> None:
    """Compare the claimed service with parsed hosts using existing severity."""
    challan_claim = bool(CLAIM_RE.search(text))
    nonofficial = [link for link in links if not link["challan_reference"]]
    payment = bool(re.search(
        r"\b(?:pay|payment|fine|penalty|dues|pending|settle|challan)\b", text, re.I
    ))
    if challan_claim and nonofficial:
        weight = 3 if payment and any(
            not (link.get("host") or "").endswith((".gov.in", ".nic.in"))
            for link in nonofficial
        ) else 1
        add(
            "challan_mismatch", "e-Challan service and link do not match",
            "This message mentions RTO/e-Challan but links outside the two "
            "checked e-Challan hostnames. Independently use "
            "echallan.parivahan.gov.in or your verified state traffic-police "
            "portal; this list does not cover every legitimate state service.",
            weight,
        )


def inspect_urls(text: str) -> URLAnalysis:
    """Inspect bounded links offline; preserve first-finding deduplication."""
    findings: dict[str, Signal] = {}
    hosts: list[str] = []
    links: list[URLLink] = []

    def add(code: str, title: str, detail: str, weight: int) -> None:
        # Do not fix the known shared 'url' code collision in this parity pass.
        findings.setdefault(code, dict(
            code=code, title=title, detail=detail, weight=weight
        ))

    matches = extract_urls(text)
    if len(matches) > MAX_URLS:
        add(
            "url_limit", "More links than checked",
            "Only the first 20 links were inspected. "
            "Check the remaining links independently.", 1,
        )
    for raw, _, _ in matches[:MAX_URLS]:
        _inspect_link(raw, add, hosts, links)
    _check_challan_claim(text, links, add)
    return dict(
        signals=list(findings.values()), hosts=list(dict.fromkeys(hosts)),
        links=links, standalone=is_standalone_url(text),
    )
