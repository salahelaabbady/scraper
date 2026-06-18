import os, json

CONFIG_PATH = "/tmp/bot_config.json"


def get_default_config() -> dict:
    return {
        "target_url": "",
        "form_types": ["contact", "devis", "inscription", "login", "all"],
        "backend_type": "none",       # none | netlify | supabase | firebase | confirmation_page
        "netlify_token": "",
        "netlify_site_id": "",
        "netlify_form_name": "contact",
        "supabase_url": "",
        "supabase_key": "",
        "supabase_table": "leads",
        "firebase_project": "",
        "firebase_collection": "leads",
        "interval_hours": 6,
        "auto_run": False,
        "test_data": {
            "first_name": ["Jean", "Michel", "Pierre", "Marie", "Sophie", "André"],
            "last_name":  ["Martin", "Dubois", "Bernard", "Moreau", "Simon"],
            "email":      ["test{n}@example.com"],
            "phone":      ["0612345678", "0698765432", "0634567890"],
            "zip":        ["75001", "69001", "13001", "31000", "33000"],
            "message":    ["Test académique — bot automatique"],
        },
        "export_filename": "leads",
        "project_name": "Mon Projet",
    }


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            saved = json.load(f)
        # Merge with defaults so new keys always exist
        defaults = get_default_config()
        defaults.update(saved)
        return defaults
    return get_default_config()


def save_config(data: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)
