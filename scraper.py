import json
import os
import urllib.request
from playwright.sync_api import sync_playwright

URL_CIBLE = "https://www.ceiaube.fr/catalogue-plateforme-reemploi"
FICHIER_MEMOIRE = "memoire_catalogue.json"

def recuperer_annonces():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL_CIBLE, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)

        cartes = page.locator("main li, main [role='listitem']").all()
        resultats = []

        if cartes:
            for item in cartes:
                texte = item.inner_text().strip()
                if texte and len(texte) > 5:
                    resultats.append(texte)
        else:
            texte_global = page.locator("main").inner_text().strip()
            lignes = [l.strip() for l in texte_global.split("\n") if len(l.strip()) > 3]
            resultats = list(dict.fromkeys(lignes))

        browser.close()
        return resultats

def creer_issue_github(nouveautes):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("Variables d'environnement GitHub manquantes.")
        return

    url = f"https://api.github.com/repos/{repo}/issues"
    corps_texte = "### Nouveaux matériaux détectés :\n\n"
    for n in nouveautes:
        corps_texte += f"- {n}\n\n"
    corps_texte += f"\n[Accéder au catalogue]({URL_CIBLE})"

    data = json.dumps({
        "title": f"🚨 Alerte réemploi : {len(nouveautes)} nouveau(x) matériau(x)",
        "body": corps_texte
    }).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req) as resp:
            print("Issue GitHub créée avec succès (e-mail envoyé) !")
    except Exception as e:
        print(f"Erreur lors de la création de l'Issue : {e}")

def main():
    actuels = recuperer_annonces()
    print(f"{len(actuels)} éléments relevés sur la page.")

    anciens = []
    if os.path.exists(FICHIER_MEMOIRE):
        with open(FICHIER_MEMOIRE, "r", encoding="utf-8") as f:
            anciens = json.load(f)

    # Détection des nouveaux ajouts
    anciens_set = set(anciens)
    nouveautes = [item for item in actuels if item not in anciens_set]

    if not os.path.exists(FICHIER_MEMOIRE):
        print("Premier passage : initialisation de la base.")
    elif nouveautes:
        print(f"{len(nouveautes)} nouveauté(s) trouvée(s) !")
        creer_issue_github(nouveautes)
    else:
        print("Aucun changement détecté.")

    with open(FICHIER_MEMOIRE, "w", encoding="utf-8") as f:
        json.dump(actuels, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
