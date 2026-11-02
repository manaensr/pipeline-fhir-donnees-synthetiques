"""
rapport_html.py
Rôle : produit un rapport HTML statique (un seul fichier, sans JavaScript)
       à partir des résultats des requêtes SQL.
Sécurité : tout texte est passé par html.escape avant d'être inséré dans la page.
Utilisé par : scripts/lancer_pipeline.py, tests/
"""

from html import escape


def _tableau(titre: str, colonnes: list[str], lignes: list[tuple]) -> str:
    """
    Construit un tableau HTML avec son titre.

    Paramètres :
        titre (str) : titre de la section.
        colonnes (list[str]) : en-têtes de colonnes.
        lignes (list[tuple]) : données, une ligne par tuple.

    Retourne :
        str : le bloc HTML de la section.
    """
    entetes = "".join(f"<th>{escape(c)}</th>" for c in colonnes)
    corps = "".join(
        "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in ligne) + "</tr>"
        for ligne in lignes
    )
    return (f"<h2>{escape(titre)}</h2>"
            f"<table><thead><tr>{entetes}</tr></thead><tbody>{corps}</tbody></table>")


def generer_rapport(comptes: dict, resultats: dict) -> str:
    """
    Assemble la page HTML complète.

    Paramètres :
        comptes (dict) : nombre de lignes par table (retour de charger_bundle).
        resultats (dict) : résultats des requêtes, avec les clés "sexe",
            "tension", "conditions" et "hypertension".

    Retourne :
        str : le document HTML.
    """
    resume = ", ".join(f"{nombre} {table}" for table, nombre in comptes.items())
    sections = [
        _tableau("Répartition par sexe", ["Sexe", "Patients"], resultats["sexe"]),
        _tableau("Pression systolique moyenne par tranche d'âge",
                 ["Tranche (début)", "Patients", "Moyenne (mm[Hg])"], resultats["tension"]),
        _tableau("Maladies enregistrées",
                 ["Maladie", "Patients", "%"], resultats["conditions"]),
        _tableau("Pression ≥ 140 sans diagnostic d'hypertension",
                 ["Patient", "Nom", "Systolique"], resultats["hypertension"]),
    ]
    style = ("body{font-family:sans-serif;max-width:48rem;margin:2rem auto;padding:0 1rem}"
             "table{border-collapse:collapse;width:100%}"
             "th,td{border:1px solid #ccc;padding:.3rem .6rem;text-align:left}"
             "th{background:#f0f0f0}")
    return (f"<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
            f"<title>Rapport du pipeline FHIR</title><style>{style}</style></head><body>"
            f"<h1>Rapport du pipeline FHIR</h1>"
            f"<p>Données entièrement synthétiques. Chargées : {escape(resume)}.</p>"
            f"{''.join(sections)}</body></html>")
