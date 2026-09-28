"""Debtor record + two-check validation (truncation + blank-line tolerant)."""
from dataclasses import dataclass
import re


@dataclass
class Debtor:
    """Full debtor record. Blank string means field absent (skipped in document check)."""
    no: str = ""
    first_name: str = ""
    last_name: str = ""
    company: str = ""
    street: str = ""
    zip_code: str = ""
    city: str = ""
    country: str = ""


def norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\.+$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def prefix_ok(visible: str, full: str) -> bool:
    """Visible cell (dots stripped) is a prefix of the full value, either direction."""
    v, f = norm(visible), norm(full)
    if not v and not f:
        return True
    if not v or not f:
        return False
    return f.startswith(v) or v.startswith(f)


def _tokens(s: str) -> list:
    return [t for t in norm(s).split(" ") if t]


def _company_hit(blob_tokens: list, company: str) -> bool:
    """Truncated cells ('Northstar Off.') still match ('Northstar Office GmbH')."""
    want = _tokens(company)
    if not want:
        return True
    if not any(prefix_ok(b, want[0]) for b in blob_tokens):
        return False
    if len(want) == 1:
        return True
    return any(prefix_ok(b, want[1]) for b in blob_tokens)


def row_matches(row: dict, debtor: Debtor) -> bool:
    """Check 1, before clicking. Company-led, truncation tolerant.

    Strict path compares column by column. Fallback path ignores column
    borders (OCR shifts them on wrapped rows) and requires the company plus
    one more non-blank field to appear without spaces inside the whole row.
    """
    pairs = [
        (row.get("No.", ""), debtor.no),
        (row.get("First Name", ""), debtor.first_name),
        (row.get("Name", ""), debtor.last_name),
        (row.get("Company", ""), debtor.company),
        (row.get("ZIP", ""), debtor.zip_code),
        (row.get("City", ""), debtor.city),
    ]
    strict = True
    for visible, full in pairs:
        if not norm(full):
            continue
        if not norm(visible) or not prefix_ok(visible, full):
            strict = False
            break
    else:
        if norm(debtor.company) and not prefix_ok(row.get("Company", ""), debtor.company):
            strict = False
    if strict:
        return True
    blob_tokens = _tokens(" ".join(str(row.get(k, "")) for k in
                                   ("No.", "First Name", "Name", "Company", "ZIP", "City")))
    if norm(debtor.company) and not _company_hit(blob_tokens, debtor.company):
        return False
    extras = [debtor.no, debtor.first_name, debtor.last_name, debtor.zip_code, debtor.city]
    return any(norm(e) and any(prefix_ok(b, norm(e)) for b in blob_tokens) for e in extras)


def expected_doc_lines(debtor: Debtor) -> list:
    """Document order: company / first+last / street / zip+city / country. Blanks dropped."""
    lines = []
    if norm(debtor.company):
        lines.append(norm(debtor.company))
    names = " ".join(p for p in [norm(debtor.first_name), norm(debtor.last_name)] if p)
    if names:
        lines.append(names)
    if norm(debtor.street):
        lines.append(norm(debtor.street))
    zc = " ".join(p for p in [norm(debtor.zip_code), norm(debtor.city)] if p)
    if zc:
        lines.append(zc)
    if norm(debtor.country):
        lines.append(norm(debtor.country))
    return lines


def doc_lines(address_text: str) -> list:
    lines = []
    for raw in (address_text or "").replace("\r", "\n").split("\n"):
        t = norm(raw.split("|")[0] if "|" in raw else raw)
        t = re.sub(r"^[a-z]{2}-", "", t).strip()
        if t:
            lines.append(t)
    return lines


def doc_matches(address_text: str, debtor: Debtor) -> tuple:
    """Check 2, after clicking. Subsequence over non-empty lines. Returns (ok, detail)."""
    exp = expected_doc_lines(debtor)
    got = doc_lines(address_text)
    pos = 0
    for want in exp:
        found = -1
        for j in range(pos, len(got)):
            if prefix_ok(got[j], want):
                found = j
                break
        if found == -1:
            return (False, f"missing {want!r} in {got}")
        pos = found + 1
    return (True, "")
