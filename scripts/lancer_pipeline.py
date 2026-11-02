"""
lancer_pipeline.py
Rôle : exécute le pipeline de bout en bout.
       patients fictifs -> Bundle FHIR -> validation -> base SQLite -> rapport HTML
Usage : python scripts/lancer_pipeline.py
Sortie : dossier sortie/ (bundle.json, base.sqlite, rapport.html), ignoré par Git.
"""

import json
import sys
from pathlib import Path

# Ajoute src/ au chemin de recherche pour pouvoir importer le paquet
RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "src"))

from pipeline_fhir import requetes_sql  # noqa: E402
from pipeline_fhir.chargement_sql import charger_bundle, creer_base  # noqa: E402
from pipeline_fhir.conversion_fhir import construire_bundle  # noqa: E402
from pipeline_fhir.generation_patients import generer_patients  # noqa: E402
from pipeline_fhir.rapport_html import generer_rapport  # noqa: E402
from pipeline_fhir.validation_fhir import verifier_bundle  # noqa: E402


def main() -> int:
    """
    Enchaîne les étapes du pipeline et écrit les fichiers de sortie.

    Retourne :
        int : 0 si tout s'est bien passé, 1 si la validation a échoué.
    """
    dossier = RACINE / "sortie"
    dossier.mkdir(exist_ok=True)

    patients = generer_patients()
    bundle = construire_bundle(patients)

    # On s'arrête avant le chargement si le Bundle est mal formé
    erreurs = verifier_bundle(bundle)
    if erreurs:
        print(f"Validation échouée ({len(erreurs)} erreurs) :", *erreurs[:10], sep="\n  ")
        return 1
    (dossier / "bundle.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2),
                                         encoding="utf-8")

    chemin_base = dossier / "base.sqlite"
    chemin_base.unlink(missing_ok=True)
    connexion = creer_base(str(chemin_base))
    comptes = charger_bundle(connexion, bundle)

    resultats = {
        "sexe": requetes_sql.repartition_sexe(connexion),
        "tension": requetes_sql.tension_par_tranche_age(connexion),
        "conditions": requetes_sql.prevalence_conditions(connexion),
        "hypertension": requetes_sql.hypertension_non_diagnostiquee(connexion),
    }
    connexion.close()

    (dossier / "rapport.html").write_text(generer_rapport(comptes, resultats), encoding="utf-8")
    print(f"Pipeline terminé : {comptes}. Fichiers dans {dossier}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
