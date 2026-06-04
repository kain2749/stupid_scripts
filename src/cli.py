from __future__ import annotations

import argparse
import html
import json
import socket
import ssl
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup


DEFAULT_TIMEOUT_SECONDS = 12
CERT_EXPIRY_WARNING_DAYS = 30
ERROR_LEVEL_CHECKS = frozenset({"dns", "http_status", "configured_paths"})

CHECK_LABELS: dict[str, str] = {
  "dns": "Domain resolves",
  "https_certificate": "SSL certificate",
  "http_to_https": "HTTP redirects to HTTPS",
  "http_status": "Site responds",
  "response_time_ms": "Response time",
  "title": "Page title",
  "meta_description": "Meta description",
  "og_title": "Social share title",
  "og_description": "Social share description",
  "json_ld": "Structured data",
  "noindex": "Visible to search engines",
  "nofollow": "Links followed by search engines",
  "robots_blocks_all": "Crawling allowed",
  "contact_path": "Contact information",
  "required_text": "Required page text",
  "required_links": "Required links",
  "configured_paths": "All pages respond",
  "internal_links": "Internal links",
}

CHECK_GROUPS: list[tuple[str, list[str]]] = [
  ("Availability", ["dns", "https_certificate", "http_to_https", "http_status", "response_time_ms"]),
  ("Search visibility", ["noindex", "nofollow", "robots_blocks_all"]),
  ("Page content", ["title", "meta_description", "og_title", "og_description", "json_ld"]),
  ("Contact and content", ["contact_path", "required_text", "required_links"]),
  ("Pages and links", ["configured_paths", "internal_links"]),
]

_REPORT_CSS = """
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 15px;
  line-height: 1.6;
  background: #fbfaf6;
  color: #17211d;
}
a { color: inherit; }
header {
  background: #17211d;
  color: #fff;
  padding: 18px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.brand { font-weight: 800; font-size: 1.05rem; letter-spacing: -0.01em; }
.report-meta { color: rgba(255,255,255,0.6); font-size: 0.88rem; }
main { max-width: 820px; margin: 0 auto; padding: 32px 24px 64px; }
.client {
  background: #fff;
  border: 1px solid #d8ddd5;
  border-radius: 8px;
  padding: 28px;
  margin-bottom: 28px;
  box-shadow: 0 1px 3px rgba(23,33,29,0.06);
}
.client-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}
.client-header h2 { margin: 0 0 3px; font-size: 1.25rem; }
.domain { color: #5b6861; font-size: 0.88rem; text-decoration: none; }
.domain:hover { text-decoration: underline; }
.badge {
  display: inline-block;
  padding: 5px 13px;
  border-radius: 999px;
  color: #fff;
  font-size: 0.8rem;
  font-weight: 700;
  white-space: nowrap;
  flex-shrink: 0;
}
.badge-healthy { background: #315f4b; }
.badge-warning { background: #b87c1a; }
.badge-error { background: #a02020; }
.issues {
  background: #fff8f0;
  border: 1px solid #e8c98a;
  border-radius: 6px;
  padding: 13px 16px;
  margin-bottom: 20px;
  font-size: 0.9rem;
}
.issues-error {
  background: #fff4f4;
  border-color: #e8aaaa;
}
.issues strong { display: block; margin-bottom: 4px; }
.issues ul { margin: 0; padding-left: 18px; }
.issues li { margin-top: 2px; }
.group { margin-top: 22px; }
.group-label {
  margin: 0 0 8px;
  font-size: 0.73rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #5b6861;
}
.checks { list-style: none; margin: 0; padding: 0; display: grid; gap: 5px; }
.check {
  display: flex;
  align-items: baseline;
  gap: 9px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.9rem;
}
.check-pass { background: #f3faf5; }
.check-fail { background: #fdf4f4; }
.check-icon { font-weight: 900; width: 14px; flex-shrink: 0; font-style: normal; }
.check-pass .check-icon { color: #315f4b; }
.check-fail .check-icon { color: #a02020; }
.check-label { font-weight: 700; flex-shrink: 0; }
.check-detail { color: #5b6861; margin-left: 2px; word-break: break-word; }
footer {
  text-align: center;
  padding: 20px;
  color: #5b6861;
  font-size: 0.85rem;
  border-top: 1px solid #d8ddd5;
}
@media (max-width: 600px) {
  header { padding: 14px 18px; }
  main { padding: 20px 16px 48px; }
  .client { padding: 20px; }
  .client-header { flex-direction: column; }
}
"""


@dataclass
class CheckResult:
  ok: bool
  value: Any = None
  note: str | None = None

  def to_json(self) -> dict[str, Any]:
    result: dict[str, Any] = {"ok": self.ok}
    if self.value is not None:
      result["value"] = self.value
    if self.note:
      result["note"] = self.note
    return result


def load_clients(path: Path) -> list[dict[str, Any]]:
  with path.open("r", encoding="utf-8") as handle:
    data = yaml.safe_load(handle) or {}

  clients = data.get("clients")
  if not isinstance(clients, list):
    raise ValueError(f"{path} must contain a top-level 'clients' list")

  return clients


def fetch_url(session: requests.Session, url: str, timeout: int) -> tuple[requests.Response | None, float | None, str | None]:
  started = time.perf_counter()
  try:
    response = session.get(url, timeout=timeout, allow_redirects=True)
  except requests.RequestException as exc:
    return None, None, str(exc)

  elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
  return response, elapsed_ms, None


def check_dns(domain: str) -> CheckResult:
  try:
    addresses = sorted({info[4][0] for info in socket.getaddrinfo(domain, 443, type=socket.SOCK_STREAM)})
  except socket.gaierror as exc:
    return CheckResult(False, note=f"DNS lookup failed: {exc}")

  return CheckResult(bool(addresses), addresses)


def check_https_certificate(domain: str) -> CheckResult:
  context = ssl.create_default_context()
  try:
    with socket.create_connection((domain, 443), timeout=DEFAULT_TIMEOUT_SECONDS) as sock:
      with context.wrap_socket(sock, server_hostname=domain) as tls:
        cert = tls.getpeercert()
  except (OSError, ssl.SSLError) as exc:
    return CheckResult(False, note=f"TLS certificate check failed: {exc}")

  not_after = cert.get("notAfter")
  if not not_after:
    return CheckResult(False, note="TLS certificate did not include an expiration date")

  expires_at = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
  days_remaining = (expires_at - datetime.now(timezone.utc)).days
  ok = days_remaining >= CERT_EXPIRY_WARNING_DAYS
  return CheckResult(ok, {"expires_at": expires_at.isoformat(), "days_remaining": days_remaining})


def check_http_to_https(session: requests.Session, domain: str, canonical_url: str, timeout: int) -> CheckResult:
  http_url = f"http://{domain}"
  response, _, error = fetch_url(session, http_url, timeout)
  if error or response is None:
    return CheckResult(False, note=f"HTTP redirect check failed: {error}")

  final_url = response.url.rstrip("/")
  expected = canonical_url.rstrip("/")
  ok = final_url == expected or final_url.startswith("https://")
  return CheckResult(ok, {"from": http_url, "to": response.url, "status": response.status_code})


def check_page_metadata(soup: BeautifulSoup) -> dict[str, CheckResult]:
  title = soup.find("title")
  description = soup.find("meta", attrs={"name": "description"})
  og_title = soup.find("meta", attrs={"property": "og:title"})
  og_description = soup.find("meta", attrs={"property": "og:description"})
  json_ld = soup.find("script", attrs={"type": "application/ld+json"})

  return {
    "title": CheckResult(bool(title and title.get_text(strip=True)), title.get_text(strip=True) if title else None),
    "meta_description": CheckResult(bool(description and description.get("content")), description.get("content") if description else None),
    "og_title": CheckResult(bool(og_title and og_title.get("content")), og_title.get("content") if og_title else None),
    "og_description": CheckResult(bool(og_description and og_description.get("content")), og_description.get("content") if og_description else None),
    "json_ld": CheckResult(bool(json_ld)),
  }


def check_indexing(soup: BeautifulSoup, robots_text: str | None, launched: bool) -> dict[str, CheckResult]:
  robots_meta = soup.find("meta", attrs={"name": "robots"})
  robots_content = (robots_meta.get("content", "") if robots_meta else "").lower()
  found_noindex = "noindex" in robots_content
  found_nofollow = "nofollow" in robots_content
  robots_blocks_all = False

  if robots_text:
    normalized = [line.strip().lower().replace(" ", "") for line in robots_text.splitlines()]
    robots_blocks_all = "user-agent:*" in normalized and "disallow:/" in normalized

  return {
    "noindex": CheckResult(not (launched and found_noindex), found_noindex, "noindex is acceptable before launch" if found_noindex and not launched else None),
    "nofollow": CheckResult(not (launched and found_nofollow), found_nofollow, "nofollow is acceptable before launch" if found_nofollow and not launched else None),
    "robots_blocks_all": CheckResult(not (launched and robots_blocks_all), robots_blocks_all, "robots.txt blocks all crawling before launch" if robots_blocks_all and not launched else None),
  }


def normalize_phone(text: str) -> str:
  return "".join(char for char in text if char.isdigit())


def check_contact_path(client: dict[str, Any], soup: BeautifulSoup, page_text: str) -> CheckResult:
  hrefs = [tag.get("href", "") for tag in soup.find_all("a")]
  expected_emails = client.get("expected_email") or []
  expected_phones = client.get("expected_phone") or []

  email_ok = not expected_emails or any(
    email.lower() in page_text.lower() or f"mailto:{email.lower()}" in [href.lower() for href in hrefs]
    for email in expected_emails
  )
  phone_digits = normalize_phone(page_text + " " + " ".join(hrefs))
  phone_ok = not expected_phones or any(normalize_phone(phone) in phone_digits for phone in expected_phones)

  return CheckResult(email_ok and phone_ok, {"email": email_ok, "phone": phone_ok})


def check_required_text(required_text: list[str], page_text: str) -> CheckResult:
  missing = [text for text in required_text if text.lower() not in page_text.lower()]
  return CheckResult(not missing, {"missing": missing, "checked": len(required_text)})


def check_required_links(required_links: list[str], soup: BeautifulSoup) -> CheckResult:
  hrefs = [tag.get("href", "") for tag in soup.find_all("a")]
  missing = [link for link in required_links if not any(link in href for href in hrefs)]
  return CheckResult(not missing, {"missing": missing, "checked": len(required_links)})


def check_paths(session: requests.Session, canonical_url: str, paths: list[str], timeout: int) -> CheckResult:
  results = []
  ok = True
  for path in paths:
    url = urljoin(canonical_url.rstrip("/") + "/", path.lstrip("/"))
    response, elapsed_ms, error = fetch_url(session, url, timeout)
    if error or response is None:
      ok = False
      results.append({"path": path, "ok": False, "error": error})
      continue

    path_ok = 200 <= response.status_code < 400
    ok = ok and path_ok
    results.append({"path": path, "ok": path_ok, "status": response.status_code, "response_time_ms": elapsed_ms})

  return CheckResult(ok, results)


def check_internal_links(session: requests.Session, canonical_url: str, soup: BeautifulSoup, timeout: int) -> CheckResult:
  canonical = urlparse(canonical_url)
  seen: set[str] = set()
  results = []
  ok = True

  for tag in soup.find_all("a"):
    href = tag.get("href")
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
      continue

    url = urljoin(canonical_url, href)
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != canonical.netloc:
      continue
    if url in seen:
      continue
    seen.add(url)

    response, _, error = fetch_url(session, url, timeout)
    if error or response is None:
      ok = False
      results.append({"url": url, "ok": False, "error": error})
      continue

    link_ok = 200 <= response.status_code < 400
    ok = ok and link_ok
    if not link_ok:
      results.append({"url": url, "ok": False, "status": response.status_code})

  return CheckResult(ok, {"checked": len(seen), "problems": results})


def fetch_robots(session: requests.Session, canonical_url: str, timeout: int) -> str | None:
  robots_url = urljoin(canonical_url.rstrip("/") + "/", "robots.txt")
  response, _, error = fetch_url(session, robots_url, timeout)
  if error or response is None or response.status_code >= 400:
    return None
  return response.text


def check_client(client: dict[str, Any], timeout: int) -> dict[str, Any]:
  domain = client["domain"]
  canonical_url = client["canonical_url"]
  launched = bool(client.get("launched", True))

  with requests.Session() as session:
    session.headers.update({"User-Agent": "PlainWebWorksHealthcheck/0.1"})

    checks: dict[str, CheckResult] = {
      "dns": check_dns(domain),
      "https_certificate": check_https_certificate(domain),
      "http_to_https": check_http_to_https(session, domain, canonical_url, timeout),
    }

    response, elapsed_ms, error = fetch_url(session, canonical_url, timeout)
    if error or response is None:
      checks["http_status"] = CheckResult(False, note=error)
      checks["response_time_ms"] = CheckResult(False)
      return build_client_result(client, checks)

    checks["http_status"] = CheckResult(response.status_code == 200, response.status_code)
    checks["response_time_ms"] = CheckResult(elapsed_ms is not None and elapsed_ms < 3000, elapsed_ms)

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)
    robots_text = fetch_robots(session, canonical_url, timeout)

    checks.update(check_page_metadata(soup))
    checks.update(check_indexing(soup, robots_text, launched))
    checks["contact_path"] = check_contact_path(client, soup, page_text)
    checks["required_text"] = check_required_text(client.get("required_text") or [], page_text)
    checks["required_links"] = check_required_links(client.get("required_links") or [], soup)
    checks["configured_paths"] = check_paths(session, canonical_url, client.get("check_paths") or ["/"], timeout)
    checks["internal_links"] = check_internal_links(session, canonical_url, soup, timeout)

    return build_client_result(client, checks)


def build_client_result(client: dict[str, Any], checks: dict[str, CheckResult]) -> dict[str, Any]:
  failed = [name for name, result in checks.items() if not result.ok]
  notes = [f"{name}: {result.note}" for name, result in checks.items() if result.note]

  if any(name in ERROR_LEVEL_CHECKS for name in failed):
    status = "error"
  elif failed:
    status = "warning"
  else:
    status = "healthy"

  return {
    "date": date.today().isoformat(),
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "client": client["name"],
    "domain": client["domain"],
    "canonical_url": client["canonical_url"],
    "launched": bool(client.get("launched", True)),
    "status": status,
    "checks": {name: result.to_json() for name, result in checks.items()},
    "failed_checks": failed,
    "notes": notes,
  }


def write_results(results: list[dict[str, Any]], output_dir: Path) -> Path:
  output_dir.mkdir(parents=True, exist_ok=True)
  path = output_dir / f"{date.today().isoformat()}.json"
  statuses = {result["status"] for result in results}
  overall = "error" if "error" in statuses else ("warning" if "warning" in statuses else "healthy")
  payload = {
    "date": date.today().isoformat(),
    "status": overall,
    "results": results,
  }
  path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
  return path


def _check_detail(name: str, check: dict[str, Any]) -> str:
  ok = check.get("ok", False)
  v = check.get("value")
  note = check.get("note") or ""

  if name == "dns":
    if ok and isinstance(v, list):
      return "Resolves to: " + ", ".join(str(a) for a in v)
    return note or "Lookup failed"
  if name == "https_certificate":
    if isinstance(v, dict):
      days = v.get("days_remaining", "?")
      expires = (v.get("expires_at") or "")[:10]
      return f"Expires {expires} · {days} days remaining"
    return note or ("Valid" if ok else "Check failed")
  if name == "http_to_https":
    if isinstance(v, dict):
      return f"{v.get('from', '')} → {v.get('to', '')}"
    return note or ""
  if name == "http_status":
    return f"HTTP {v}" if v is not None else note or ""
  if name == "response_time_ms":
    return f"{v} ms" if v is not None else ""
  if name == "noindex":
    return "Visible to search engines" if not v else "Hidden from search engines"
  if name == "nofollow":
    return "Links are followed" if not v else "Links marked nofollow"
  if name == "robots_blocks_all":
    return "Crawling permitted" if not v else "robots.txt is blocking all crawlers"
  if name == "contact_path":
    if isinstance(v, dict):
      parts = [
        "Email found" if v.get("email") else "Email not found",
        "Phone found" if v.get("phone") else "Phone not found",
      ]
      return " · ".join(parts)
    return ""
  if name == "required_text":
    if isinstance(v, dict):
      missing = v.get("missing", [])
      checked = v.get("checked", 0)
      return ("Missing: " + ", ".join(missing)) if missing else f"{checked} item(s) present"
    return ""
  if name == "required_links":
    if isinstance(v, dict):
      missing = v.get("missing", [])
      checked = v.get("checked", 0)
      return ("Missing: " + ", ".join(missing)) if missing else f"{checked} link(s) present"
    return ""
  if name == "configured_paths":
    if isinstance(v, list):
      problems = [p["path"] for p in v if not p.get("ok")]
      return ("Problems: " + ", ".join(problems)) if problems else f"{len(v)} path(s) responding"
    return ""
  if name == "internal_links":
    if isinstance(v, dict):
      problems = v.get("problems", [])
      checked = v.get("checked", 0)
      if problems:
        urls = [p.get("url", "") for p in problems]
        return f"{len(problems)} broken: " + ", ".join(urls)
      return f"{checked} link(s) checked"
    return ""
  if name in ("title", "meta_description", "og_title", "og_description"):
    return str(v) if v else ""
  if name == "json_ld":
    return "Present" if ok else "Not found"
  return note or ""


def _build_html_report(date_str: str, results: list[dict[str, Any]]) -> str:
  try:
    display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
  except ValueError:
    display_date = date_str

  status_labels = {"healthy": "All clear", "warning": "Issues found", "error": "Critical issues"}

  client_blocks: list[str] = []
  for result in results:
    client_name = html.escape(result.get("client", ""))
    domain = html.escape(result.get("domain", ""))
    canonical_url = html.escape(result.get("canonical_url", ""))
    status = result.get("status", "healthy")
    failed = result.get("failed_checks", [])
    checks = result.get("checks", {})

    badge_label = status_labels.get(status, status)
    badge_class = f"badge-{status}"

    issues_html = ""
    if failed:
      items = "".join(f"<li>{html.escape(CHECK_LABELS.get(f, f))}</li>" for f in failed)
      box_class = "issues issues-error" if status == "error" else "issues"
      noun = "Critical issue" if status == "error" else "Issue"
      plural = "s" if len(failed) > 1 else ""
      issues_html = f'<div class="{box_class}"><strong>{noun}{plural} found:</strong><ul>{items}</ul></div>'

    groups_html: list[str] = []
    for group_name, check_names in CHECK_GROUPS:
      rows: list[str] = []
      for name in check_names:
        if name not in checks:
          continue
        check = checks[name]
        ok = check.get("ok", False)
        label = html.escape(CHECK_LABELS.get(name, name))
        detail = _check_detail(name, check)
        icon = "✓" if ok else "✗"
        row_class = "check check-pass" if ok else "check check-fail"
        detail_html = f'<span class="check-detail">{html.escape(detail)}</span>' if detail else ""
        rows.append(f'<li class="{row_class}"><span class="check-icon">{icon}</span><span class="check-label">{label}</span>{detail_html}</li>')
      if rows:
        groups_html.append(
          f'<div class="group"><p class="group-label">{html.escape(group_name)}</p>'
          f'<ul class="checks">{"".join(rows)}</ul></div>'
        )

    client_blocks.append(
      f'<section class="client">'
      f'<div class="client-header"><div><h2>{client_name}</h2>'
      f'<a class="domain" href="{canonical_url}" target="_blank" rel="noopener">{domain}</a></div>'
      f'<span class="badge {badge_class}">{badge_label}</span></div>'
      f'{issues_html}{"".join(groups_html)}</section>'
    )

  return (
    f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
    f'<meta charset="utf-8">\n'
    f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    f'<title>Site Health Report — {html.escape(display_date)}</title>\n'
    f'<style>{_REPORT_CSS}</style>\n'
    f'</head>\n<body>\n'
    f'<header>'
    f'<span class="brand">Plain Web Works</span>'
    f'<span class="report-meta">Site Health Report &middot; {html.escape(display_date)}</span>'
    f'</header>\n'
    f'<main>{"".join(client_blocks)}</main>\n'
    f'<footer>Prepared by <a href="https://plainwebworks.co">Plain Web Works</a> &middot; {html.escape(display_date)}</footer>\n'
    f'</body>\n</html>\n'
  )


def write_report_html(results: list[dict[str, Any]], output_dir: Path) -> Path:
  output_dir.mkdir(parents=True, exist_ok=True)
  path = output_dir / f"{date.today().isoformat()}.html"
  path.write_text(_build_html_report(date.today().isoformat(), results), encoding="utf-8")
  return path


def print_summary(results: list[dict[str, Any]]) -> None:
  for result in results:
    failed = ", ".join(result["failed_checks"]) if result["failed_checks"] else "none"
    print(f"{result['client']}: {result['status']} (failed: {failed})")
    for note in result["notes"]:
      print(f"  note: {note}")


def parse_args(argv: list[str]) -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Run Plain Web Works public-surface health checks.")
  parser.add_argument("--clients", type=Path, default=Path("clients.yml"), help="Path to clients.yml")
  parser.add_argument("--output-dir", type=Path, default=Path("reports/daily"), help="Directory for daily JSON results")
  parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="HTTP timeout in seconds")
  parser.add_argument("--no-write", action="store_true", help="Print summary without writing a report file")
  return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
  args = parse_args(argv or sys.argv[1:])
  clients = load_clients(args.clients)
  results = [check_client(client, args.timeout) for client in clients]
  print_summary(results)

  if not args.no_write:
    json_path = write_results(results, args.output_dir)
    html_path = write_report_html(results, args.output_dir)
    print(f"Wrote {json_path}")
    print(f"Wrote {html_path}")

  return 0 if all(result["status"] == "healthy" for result in results) else 1


if __name__ == "__main__":
  raise SystemExit(main())
