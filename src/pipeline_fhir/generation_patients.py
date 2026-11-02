"""
generation_patients.py
Rôle : fabrique des patients entièrement fictifs (identité, mesures, maladies).
       Aucune donnée réelle : tout est tiré au hasard avec une graine fixe,
       donc le résultat est identique à chaque exécution.
Utilisé par : scripts/lancer_pipeline.py, tests/
"""

import random
from datetime import date, timedelta

# Date de référence du pipeline : les âges et les dates de mesure s'y rapportent
DATE_REFERENCE = date(2026, 1, 1)

# Listes de prénoms et de noms courants, sans lien avec de vraies personnes
PRENOMS = {
    "female": ["Alice", "Camille", "Chloé", "Emma", "Inès", "Jeanne", "Léa", "Manon"],
    "male": ["Adam", "Hugo", "Jules", "Louis", "Lucas", "Nathan", "Paul", "Théo"],
}
NOMS = ["Bernard", "Dubois", "Durand", "Lefebvre", "Martin", "Moreau", "Petit", "Roux"]

# Mesures simulées : code LOINC, libellé et unité (UCUM)
MESURES = {
    "poids": ("29463-7", "Poids corporel", "kg"),
    "taille": ("8302-2", "Taille", "cm"),
    "systolique": ("8480-6", "Pression artérielle systolique", "mm[Hg]"),
    "diastolique": ("8462-4", "Pression artérielle diastolique", "mm[Hg]"),
    "frequence": ("8867-4", "Fréquence cardiaque", "/min"),
}

# Maladies simulées : code CIM-10 et libellé
CONDITIONS = {
    "hypertension": ("I10", "Hypertension essentielle"),
    "diabete": ("E11", "Diabète de type 2"),
    "asthme": ("J45", "Asthme"),
}


def _tirer_mesures(hasard: random.Random, sexe: str, age: int) -> dict:
    """
    Tire les valeurs des cinq mesures d'un patient.

    La tension monte légèrement avec l'âge, comme dans la réalité, pour que
    les requêtes SQL aient une tendance à montrer. Les valeurs restent
    plausibles mais ne représentent aucune population réelle.

    Paramètres :
        hasard (Random) : générateur à graine fixe.
        sexe (str) : "female" ou "male".
        age (int) : âge en années à la date de référence.

    Retourne :
        dict : une valeur par clé de MESURES.
    """
    taille = hasard.gauss(163 if sexe == "female" else 176, 6)
    poids = hasard.gauss(65 if sexe == "female" else 78, 10)
    systolique = hasard.gauss(108 + 0.55 * (age - 18), 11)
    diastolique = 0.6 * systolique + hasard.gauss(2, 5)
    frequence = hasard.gauss(72, 8)
    return {
        "poids": round(poids, 1),
        "taille": round(taille),
        "systolique": round(systolique),
        "diastolique": round(diastolique),
        "frequence": round(frequence),
    }


def _tirer_conditions(hasard: random.Random, systolique: int) -> list[str]:
    """
    Décide quelles maladies le patient a reçues comme diagnostic.

    Un patient à forte tension a plus de chances d'avoir un diagnostic
    d'hypertension, mais pas toujours : certains cas ne sont volontairement
    pas diagnostiqués, ce qui permet de les retrouver avec une requête SQL.

    Paramètres :
        hasard (Random) : générateur à graine fixe.
        systolique (int) : pression systolique du patient, en mm[Hg].

    Retourne :
        list[str] : clés de CONDITIONS retenues.
    """
    retenues = []
    # Probabilité de diagnostic : élevée si la tension est forte, faible sinon
    chance_hypertension = 0.6 if systolique >= 140 else 0.04
    if hasard.random() < chance_hypertension:
        retenues.append("hypertension")
    if hasard.random() < 0.10:
        retenues.append("diabete")
    if hasard.random() < 0.08:
        retenues.append("asthme")
    return retenues


def generer_patients(nombre: int = 200, graine: int = 42) -> list[dict]:
    """
    Génère une liste de patients fictifs.

    Paramètres :
        nombre (int) : combien de patients fabriquer.
        graine (int) : graine du hasard. Même graine, mêmes patients.

    Retourne :
        list[dict] : un dictionnaire par patient, avec "id", "prenom", "nom",
        "sexe", "date_naissance", "observations" et "conditions".
    """
    hasard = random.Random(graine)
    patients = []

    for numero in range(1, nombre + 1):
        sexe = hasard.choice(["female", "male"])
        age = hasard.randint(18, 90)
        naissance = DATE_REFERENCE - timedelta(days=int(age * 365.25) + hasard.randint(0, 364))
        valeurs = _tirer_mesures(hasard, sexe, age)

        # Une observation FHIR par mesure, toutes prises à la date de référence
        observations = [
            {"code": code, "libelle": libelle, "valeur": valeurs[cle],
             "unite": unite, "date": DATE_REFERENCE.isoformat()}
            for cle, (code, libelle, unite) in MESURES.items()
        ]
        conditions = [
            {"code": CONDITIONS[cle][0], "libelle": CONDITIONS[cle][1],
             "date_debut": (DATE_REFERENCE - timedelta(days=hasard.randint(30, 3000))).isoformat()}
            for cle in _tirer_conditions(hasard, valeurs["systolique"])
        ]

        patients.append({
            "id": f"patient-{numero:03d}",
            "prenom": hasard.choice(PRENOMS[sexe]),
            "nom": hasard.choice(NOMS),
            "sexe": sexe,
            "date_naissance": naissance.isoformat(),
            "observations": observations,
            "conditions": conditions,
        })

    return patients
