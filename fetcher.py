import os, logging, requests
from datetime import datetime

log = logging.getLogger(__name__)

NETLIFY_API  = "https://api.netlify.com/api/v1"


def fetch_leads(cfg: dict) -> list[dict]:
    backend = cfg.get("backend_type", "none")

    if backend == "netlify":
        return _fetch_netlify(cfg)
    elif backend == "supabase":
        return _fetch_supabase(cfg)
    elif backend == "firebase":
        return _fetch_firebase(cfg)
    elif backend == "confirmation_page":
        return _fetch_confirmation_page(cfg)
    else:
        log.info("No backend configured — returning empty leads")
        return []


# ─── Netlify Forms ─────────────────────────────────────────────────────────────

def _fetch_netlify(cfg: dict) -> list[dict]:
    token   = cfg.get("netlify_token") or os.getenv("NETLIFY_TOKEN")
    site_id = cfg.get("netlify_site_id") or os.getenv("NETLIFY_SITE_ID")
    form_id = cfg.get("netlify_form_id") or os.getenv("NETLIFY_FORM_ID")
    form_name = cfg.get("netlify_form_name", "contact")

    if not token:
        raise EnvironmentError("netlify_token is required for Netlify backend")

    headers = {"Authorization": f"Bearer {token}"}

    if not form_id:
        resp = requests.get(f"{NETLIFY_API}/sites/{site_id}/forms", headers=headers, timeout=15)
        resp.raise_for_status()
        forms = resp.json()
        match = next((f for f in forms if form_name.lower() in f.get("name", "").lower()), None)
        form_id = (match or forms[0])["id"] if forms else None
        if not form_id:
            raise RuntimeError("No forms found on Netlify site")
        log.info(f"Netlify form ID: {form_id}")

    all_leads, page = [], 1
    while True:
        resp = requests.get(
            f"{NETLIFY_API}/forms/{form_id}/submissions",
            headers=headers,
            params={"page": page, "per_page": 100},
            timeout=15,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        all_leads.extend(_normalize_netlify(s) for s in batch)
        if len(batch) < 100:
            break
        page += 1

    log.info(f"Netlify: {len(all_leads)} leads")
    return all_leads


def _normalize_netlify(s: dict) -> dict:
    d = s.get("data", {})
    return {
        "id":    s.get("id", ""),
        "date":  s.get("created_at", "")[:19].replace("T", " "),
        "source": "netlify",
        "nom":         d.get("nom") or d.get("last_name") or d.get("name", ""),
        "prenom":      d.get("prenom") or d.get("first_name", ""),
        "email":       d.get("email") or d.get("mail", ""),
        "telephone":   d.get("telephone") or d.get("tel") or d.get("phone", ""),
        "code_postal": d.get("code_postal") or d.get("cp") or d.get("zip", ""),
        "message":     d.get("message") or d.get("msg", ""),
        "assurance":   d.get("assurance") or d.get("type") or d.get("produit", ""),
        "raw": str(d),
    }


# ─── Supabase ──────────────────────────────────────────────────────────────────

def _fetch_supabase(cfg: dict) -> list[dict]:
    url   = cfg.get("supabase_url", "").rstrip("/")
    key   = cfg.get("supabase_key", "")
    table = cfg.get("supabase_table", "leads")

    if not url or not key:
        raise EnvironmentError("supabase_url and supabase_key are required")

    resp = requests.get(
        f"{url}/rest/v1/{table}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Range": "0-499",
        },
        params={"order": "created_at.desc"},
        timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json()
    log.info(f"Supabase: {len(rows)} rows from '{table}'")
    return [_normalize_generic(r, "supabase") for r in rows]


# ─── Firebase Firestore (REST) ─────────────────────────────────────────────────

def _fetch_firebase(cfg: dict) -> list[dict]:
    project    = cfg.get("firebase_project", "")
    collection = cfg.get("firebase_collection", "leads")
    api_key    = cfg.get("firebase_api_key", "")

    if not project:
        raise EnvironmentError("firebase_project is required")

    url = f"https://firestore.googleapis.com/v1/projects/{project}/databases/(default)/documents/{collection}"
    params = {}
    if api_key:
        params["key"] = api_key

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    docs = data.get("documents", [])
    leads = []
    for doc in docs:
        fields = doc.get("fields", {})
        flat = {k: list(v.values())[0] for k, v in fields.items()}
        leads.append(_normalize_generic(flat, "firebase"))

    log.info(f"Firebase: {len(leads)} documents from '{collection}'")
    return leads


# ─── Confirmation page scraping ────────────────────────────────────────────────

def _fetch_confirmation_page(cfg: dict) -> list[dict]:
    """
    When there's no backend API, scrape visible data from confirmation/thank-you pages.
    Returns whatever text is visible after form submission.
    """
    import re
    confirmation_url = cfg.get("confirmation_url") or cfg.get("target_url", "")
    if not confirmation_url:
        return []

    resp = requests.get(confirmation_url, timeout=15)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove nav, footer, scripts
    for tag in soup(["nav", "footer", "script", "style", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    # Try to extract structured data (emails, phones)
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", text)
    phones = re.findall(r"(?:0|\+33)[1-9][\s.\-]?(?:\d{2}[\s.\-]?){4}", text)
    zips   = re.findall(r"\b\d{5}\b", text)

    lead = {
        "id":          f"page_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "date":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source":      "confirmation_page",
        "email":       emails[0] if emails else "",
        "telephone":   phones[0] if phones else "",
        "code_postal": zips[0] if zips else "",
        "nom":         "",
        "prenom":      "",
        "message":     text[:500].strip(),
        "assurance":   "",
        "raw":         text[:1000],
    }
    return [lead]


# ─── Generic normalizer ────────────────────────────────────────────────────────

def _normalize_generic(row: dict, source: str) -> dict:
    def pick(*keys):
        for k in keys:
            v = row.get(k) or row.get(k.upper()) or row.get(k.capitalize())
            if v:
                return str(v)
        return ""

    return {
        "id":          pick("id", "_id", "uuid"),
        "date":        pick("created_at", "date", "timestamp", "submitted_at"),
        "source":      source,
        "nom":         pick("nom", "last_name", "name", "full_name"),
        "prenom":      pick("prenom", "first_name", "fname"),
        "email":       pick("email", "mail"),
        "telephone":   pick("telephone", "tel", "phone", "mobile"),
        "code_postal": pick("code_postal", "cp", "zip", "postal_code"),
        "message":     pick("message", "msg", "comment", "description"),
        "assurance":   pick("assurance", "type", "produit", "insurance"),
        "raw":         str(row),
    }
