#!/usr/bin/env python3
"""Generate a weekly dinner menu using Anthropic API and create a Google Tasks list."""

import json
import os
import sys
from datetime import datetime, timedelta

import anthropic
import requests


def get_current_season() -> str:
    month = datetime.now().month
    if month in (12, 1, 2):
        return "hiver"
    elif month in (3, 4, 5):
        return "printemps"
    elif month in (6, 7, 8):
        return "été"
    else:
        return "automne"


def next_monday(from_date: datetime) -> datetime:
    days_ahead = 7 - from_date.weekday()  # Monday is 0
    if days_ahead == 7:
        days_ahead = 0  # already Monday
    elif days_ahead > 7:
        days_ahead -= 7
    return from_date + timedelta(days=days_ahead)


def generate_menu() -> dict:
    """Call the Anthropic API and return parsed menu JSON."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    season = get_current_season()

    prompt = f"""Tu es un chef cuisinier bienveillant. Génère un menu de 7 dîners pour la semaine prochaine avec la liste de courses correspondante.

Contraintes strictes :
- Saison : {season} — utilise UNIQUEMENT des ingrédients de saison en France
- Convives : 2 adultes + 1 bébé de 15 mois
- Bébé : pas de sel ajouté, textures douces (tout écrasé/haché finement si nécessaire)
- ALLERGIE adulte : poissons, volailles (poulet, dinde, canard…), crustacés et fruits de mer sont STRICTEMENT INTERDITS
- Recettes simples (≤ 45 min), goûteuses, variées — pas forcément françaises
- Tout le texte en français

Réponds UNIQUEMENT avec un objet JSON valide, sans markdown, sans commentaire, respectant exactement ce schéma :
{{
  "semaine": "du JJ/MM au JJ/MM/AAAA",
  "menu": [
    {{
      "jour": "Lundi",
      "plat": "Nom du plat",
      "description": "Courte description (1 phrase)",
      "notes_bebe": "Adaptation pour le bébé"
    }}
  ],
  "liste_courses": {{
    "légumes_et_fruits": ["..."],
    "féculents_et_céréales": ["..."],
    "viandes": ["..."],
    "produits_laitiers_et_œufs": ["..."],
    "épicerie_sèche": ["..."],
    "autres": ["..."]
  }}
}}"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip potential markdown code fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)


def get_google_access_token() -> str:
    """Exchange the refresh token for a short-lived access token."""
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def create_tasks_list(access_token: str, menu: dict) -> tuple[str, str]:
    """Create a new Google Tasks list and populate it. Returns (list_id, list_title)."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    base_url = "https://tasks.googleapis.com/tasks/v1"

    monday = next_monday(datetime.now())
    sunday = monday + timedelta(days=6)
    list_title = f"Menu {monday.strftime('%d/%m')} – {sunday.strftime('%d/%m/%Y')}"

    # 1. Create the task list
    r = requests.post(
        f"{base_url}/users/@me/lists",
        headers=headers,
        json={"title": list_title},
        timeout=15,
    )
    r.raise_for_status()
    list_id = r.json()["id"]

    # 2. One task per dinner
    for item in menu["menu"]:
        notes = f"{item['description']}\n👶 Bébé : {item['notes_bebe']}"
        r = requests.post(
            f"{base_url}/lists/{list_id}/tasks",
            headers=headers,
            json={"title": f"🍽 {item['jour']} — {item['plat']}", "notes": notes},
            timeout=15,
        )
        r.raise_for_status()

    # 3. Shopping list — one task per category
    shopping = menu["liste_courses"]
    category_labels = {
        "légumes_et_fruits": "🥦 Légumes & fruits",
        "féculents_et_céréales": "🌾 Féculents & céréales",
        "viandes": "🥩 Viandes",
        "produits_laitiers_et_œufs": "🥚 Produits laitiers & œufs",
        "épicerie_sèche": "🫙 Épicerie sèche",
        "autres": "🛒 Autres",
    }
    for key, label in category_labels.items():
        items = shopping.get(key, [])
        if not items:
            continue
        notes = "\n".join(f"• {i}" for i in items)
        r = requests.post(
            f"{base_url}/lists/{list_id}/tasks",
            headers=headers,
            json={"title": label, "notes": notes},
            timeout=15,
        )
        r.raise_for_status()

    return list_id, list_title


def main(dry_run: bool = False) -> None:
    print("[1/3] Génération du menu via Anthropic…")
    menu = generate_menu()
    print(json.dumps(menu, ensure_ascii=False, indent=2))

    if dry_run:
        print("\n[dry-run] Étape Google Tasks ignorée.")
        return

    print("\n[2/3] Obtention du jeton Google…")
    token = get_google_access_token()

    print("[3/3] Création de la liste Google Tasks…")
    list_id, list_title = create_tasks_list(token, menu)
    print(f"\n✅ Liste créée : '{list_title}' (id={list_id})")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
