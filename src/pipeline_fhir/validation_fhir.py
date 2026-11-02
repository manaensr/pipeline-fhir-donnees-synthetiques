"""
validation_fhir.py
Rôle : contrôle simplifié d'un Bundle FHIR avant son chargement en base.
Limite : ce n'est PAS le validateur officiel de HL7 (qui vérifie les profils
         et les terminologies). Il vérifie seulement la structure de base,
         ce qui suffit à repérer une ressource mal formée dans ce projet.
Utilisé par : scripts/lancer_pipeline.py, tests/
"""

import re

GENRES_VALIDES = {"male", "female", "other", "unknown"}
MODELE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _verifier_patient(ressource: dict) -> list[str]:
    """
    Contrôle une ressource Patient.

    Paramètres :
        ressource (dict) : la ressource à vérifier.

    Retourne :
        list[str] : les erreurs trouvées (liste vide si tout va bien).
    """
    erreurs = []
    if ressource.get("gender") not in GENRES_VALIDES:
        erreurs.append(f"{ressource.get('id')} : genre invalide")
    if not MODELE_DATE.match(str(ressource.get("birthDate", ""))):
        erreurs.append(f"{ressource.get('id')} : date de naissance invalide")
    return erreurs


def _verifier_observation(ressource: dict, patients: set[str]) -> list[str]:
    """
    Contrôle une ressource Observation : statut, code, valeur et patient existant.

    Paramètres :
        ressource (dict) : la ressource à vérifier.
        patients (set[str]) : identifiants des patients présents dans le Bundle.

    Retourne :
        list[str] : les erreurs trouvées.
    """
    erreurs = []
    identifiant = ressource.get("id")
    if ressource.get("status") != "final":
        erreurs.append(f"{identifiant} : statut absent ou inattendu")
    if not ressource.get("code", {}).get("coding"):
        erreurs.append(f"{identifiant} : code absent")
    if not isinstance(ressource.get("valueQuantity", {}).get("value"), (int, float)):
        erreurs.append(f"{identifiant} : valeur numérique absente")
    if ressource.get("subject", {}).get("reference", "").removeprefix("Patient/") not in patients:
        erreurs.append(f"{identifiant} : patient inconnu")
    return erreurs


def _verifier_condition(ressource: dict, patients: set[str]) -> list[str]:
    """
    Contrôle une ressource Condition : code et patient existant.

    Paramètres :
        ressource (dict) : la ressource à vérifier.
        patients (set[str]) : identifiants des patients présents dans le Bundle.

    Retourne :
        list[str] : les erreurs trouvées.
    """
    erreurs = []
    identifiant = ressource.get("id")
    if not ressource.get("code", {}).get("coding"):
        erreurs.append(f"{identifiant} : code absent")
    if ressource.get("subject", {}).get("reference", "").removeprefix("Patient/") not in patients:
        erreurs.append(f"{identifiant} : patient inconnu")
    return erreurs


def verifier_bundle(bundle: dict) -> list[str]:
    """
    Contrôle un Bundle complet : structure, identifiants uniques, ressources.

    Paramètres :
        bundle (dict) : le Bundle FHIR à vérifier.

    Retourne :
        list[str] : toutes les erreurs trouvées. Une liste vide veut dire
        que le Bundle passe ce contrôle simplifié.
    """
    if bundle.get("resourceType") != "Bundle":
        return ["la racine n'est pas un Bundle"]

    ressources = [entree["resource"] for entree in bundle.get("entry", [])]
    erreurs = []

    # Chaque couple (type, identifiant) doit être unique dans le Bundle
    vus = set()
    for ressource in ressources:
        cle = (ressource.get("resourceType"), ressource.get("id"))
        if cle in vus:
            erreurs.append(f"identifiant en double : {cle[1]}")
        vus.add(cle)

    # Les patients sont lus d'abord : les autres ressources s'y rattachent
    patients = {r["id"] for r in ressources if r.get("resourceType") == "Patient"}

    for ressource in ressources:
        type_ressource = ressource.get("resourceType")
        if type_ressource == "Patient":
            erreurs += _verifier_patient(ressource)
        elif type_ressource == "Observation":
            erreurs += _verifier_observation(ressource, patients)
        elif type_ressource == "Condition":
            erreurs += _verifier_condition(ressource, patients)
        else:
            erreurs.append(f"type de ressource non géré : {type_ressource}")
    return erreurs
