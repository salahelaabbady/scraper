import asyncio, random, logging
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

log = logging.getLogger(__name__)

# Keywords used to score candidate pages
FORM_PAGE_KEYWORDS = [
    "contact", "devis", "formulaire", "form", "demande", "inscription",
    "register", "signup", "sign-up", "login", "connexion", "mutuelle",
    "assurance", "sante", "santé", "quote", "request", "apply", "subscribe"
]

# Field mapping: logical name → patterns to match name/id/placeholder
FIELD_MAP = {
    "first_name": ["prenom", "firstname", "first_name", "prénom", "given", "fname", "forename"],
    "last_name":  ["nom", "lastname", "last_name", "family", "surname", "lname"],
    "email":      ["email", "mail", "courriel", "e-mail"],
    "phone":      ["tel", "phone", "telephone", "mobile", "portable", "gsm"],
    "zip":        ["cp", "code_postal", "codepostal", "zip", "postal", "postcode"],
    "name":       ["name", "fullname", "full_name", "nom_complet", "votre_nom"],
    "message":    ["message", "msg", "texte", "commentaire", "comment", "description", "sujet"],
    "subject":    ["subject", "sujet", "objet", "titre"],
    "company":    ["company", "entreprise", "societe", "société", "org"],
    "city":       ["ville", "city", "town", "localite"],
    "age":        ["age", "âge", "dob", "birth"],
    "insurance":  ["assurance", "type", "produit", "mutuelle", "garantie", "formule"],
}

# Forms to skip (login/payment — safety)
SKIP_KEYWORDS = ["password", "mot_de_passe", "mdp", "credit_card", "carte", "iban", "stripe"]


def _get_test_value(field_key: str, cfg: dict, n: int = 0) -> str:
    td = cfg.get("test_data", {})
    pool = td.get(field_key, [])
    if not pool:
        return f"test_{field_key}"
    val = random.choice(pool)
    return val.replace("{n}", str(random.randint(100, 999)))


async def _crawl_form_pages(page, base_url: str) -> list[str]:
    """Return list of page URLs that likely contain forms, scored by relevance."""
    try:
        await page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        log.error(f"Cannot load {base_url}: {e}")
        return [base_url]

    links = await page.eval_on_selector_all(
        "a[href]",
        "els => els.map(e => ({ text: e.innerText.toLowerCase().trim(), href: e.href }))"
    )

    scored = {}
    for link in links:
        href = link["href"]
        text = link["text"]
        if not href.startswith(base_url) and not href.startswith("/"):
            continue
        if any(x in href for x in ["#", "javascript:", "mailto:", "tel:"]):
            continue
        score = sum(1 for kw in FORM_PAGE_KEYWORDS if kw in href.lower() or kw in text)
        if score > 0:
            scored[href] = score

    # Always include base_url
    scored[base_url] = scored.get(base_url, 0) + 1

    return sorted(scored, key=lambda x: scored[x], reverse=True)[:8]


async def _extract_forms(page) -> list[dict]:
    """Extract all forms from the current page with their fields."""
    forms_data = await page.evaluate("""
        () => {
            const forms = Array.from(document.querySelectorAll('form'));
            return forms.map((form, fi) => {
                const fields = Array.from(form.querySelectorAll('input, textarea, select'))
                    .filter(el => !['hidden','submit','button','reset','file','image'].includes(el.type))
                    .map(el => ({
                        tag:         el.tagName.toLowerCase(),
                        type:        el.type || '',
                        name:        el.name || '',
                        id:          el.id || '',
                        placeholder: el.placeholder || '',
                        options:     el.tagName === 'SELECT'
                            ? Array.from(el.options).map(o => ({ value: o.value, text: o.text }))
                            : []
                    }));
                return {
                    index:  fi,
                    action: form.action || '',
                    method: form.method || 'get',
                    fields: fields,
                    hasSubmit: !!form.querySelector('[type=submit], button:not([type=button])')
                };
            });
        }
    """)
    return forms_data


def _should_skip_form(form: dict) -> bool:
    """Skip forms that contain sensitive fields."""
    for field in form.get("fields", []):
        combined = (field["name"] + field["id"] + field["placeholder"]).lower()
        if any(kw in combined for kw in SKIP_KEYWORDS):
            return True
    return False


def _match_field(field: dict, logical_key: str) -> bool:
    patterns = FIELD_MAP.get(logical_key, [])
    combined = (field["name"] + " " + field["id"] + " " + field["placeholder"]).lower()
    return any(p in combined for p in patterns)


async def _fill_and_submit_form(page, form: dict, cfg: dict) -> bool:
    """Fill all detected fields and submit the form."""
    fields_filled = 0

    for field in form.get("fields", []):
        # Find which logical key matches this field
        matched_key = next(
            (key for key in FIELD_MAP if _match_field(field, key)), None
        )

        value = _get_test_value(matched_key or "message", cfg)

        try:
            # Build selector
            if field["id"]:
                sel = f'#{field["id"]}'
            elif field["name"]:
                sel = f'[name="{field["name"]}"]'
            else:
                continue

            el = await page.query_selector(sel)
            if not el:
                continue

            if field["tag"] == "select" and field["options"]:
                # Pick first non-empty option
                opts = [o["value"] for o in field["options"] if o["value"]]
                if opts:
                    await el.select_option(value=opts[0])
                    fields_filled += 1
            elif field["type"] in ("checkbox", "radio"):
                await el.check()
                fields_filled += 1
            else:
                await el.click()
                await el.fill(value)
                fields_filled += 1

            await asyncio.sleep(random.uniform(0.1, 0.3))

        except Exception as e:
            log.debug(f"Could not fill field {field.get('name')}: {e}")

    if fields_filled == 0:
        log.warning("No fields filled — skipping form submission")
        return False

    log.info(f"Filled {fields_filled} fields")

    # Submit
    submit_selectors = [
        '[type="submit"]',
        'button:not([type="button"])',
        'button:has-text("Envoyer")',
        'button:has-text("Valider")',
        'button:has-text("Submit")',
        'button:has-text("Send")',
        'button:has-text("Confirmer")',
    ]
    for sel in submit_selectors:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(2)
                log.info(f"Submitted via: {sel}")
                return True
        except Exception:
            continue

    # Fallback
    try:
        await page.evaluate(f"document.querySelectorAll('form')[{form['index']}].submit()")
        await asyncio.sleep(2)
        return True
    except Exception as e:
        log.warning(f"Fallback submit failed: {e}")
        return False


async def run_scraper(cfg: dict) -> dict:
    base_url = cfg.get("target_url", "").rstrip("/")
    if not base_url:
        raise ValueError("target_url is not configured")

    results = {"forms_found": 0, "forms_submitted": 0, "pages_scanned": 0, "details": []}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            locale="fr-FR",
        )
        page = await context.new_page()

        # Discover pages with forms
        candidate_pages = await _crawl_form_pages(page, base_url)
        log.info(f"Scanning {len(candidate_pages)} candidate pages...")

        visited = set()
        for url in candidate_pages:
            if url in visited:
                continue
            visited.add(url)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(0.5)
                results["pages_scanned"] += 1

                forms = await _extract_forms(page)
                submittable = [f for f in forms if f["fields"] and f["hasSubmit"] and not _should_skip_form(f)]

                if not submittable:
                    continue

                log.info(f"{url} — {len(submittable)} form(s) found")
                results["forms_found"] += len(submittable)

                for form in submittable:
                    try:
                        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        await asyncio.sleep(0.5)
                        submitted = await _fill_and_submit_form(page, form, cfg)
                        if submitted:
                            results["forms_submitted"] += 1
                        results["details"].append({
                            "url": url,
                            "fields": len(form["fields"]),
                            "submitted": submitted,
                        })
                        await asyncio.sleep(random.uniform(1, 2))
                    except Exception as e:
                        log.warning(f"Form submission failed on {url}: {e}")

            except Exception as e:
                log.warning(f"Could not scan {url}: {e}")

        await browser.close()

    log.info(f"Scraper done: {results['forms_found']} forms found, {results['forms_submitted']} submitted")
    return results
