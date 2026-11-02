"""
chargement_sql.py
Rôle : range les ressources d'un Bundle FHIR dans une base SQLite
       (trois tables : patients, observations, conditions).
Pourquoi : FHIR est un format d'échange (JSON imbriqué) ; pour compter,
           regrouper et croiser, une base relationnelle est plus pratique.
Utilisé par : scripts/lancer_pipeline.py, requetes_sql.py, tests/
"""

import sqlite3

# Schéma des trois tables. Les clés étrangères relient mesures et diagnostics au patient.
SCHEMA = """
CREATE TABLE patients (
    id TEXT PRIMARY KEY,
    prenom TEXT NOT NULL,
    nom TEXT NOT NULL,
    sexe TEXT NOT NULL,
    date_naissance TEXT NOT NULL
);
CREATE TABLE observations (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patients(id),
    code_loinc TEXT NOT NULL,
    libelle TEXT NOT NULL,
    valeur REAL NOT NULL,
    unite TEXT NOT NULL,
    date_mesure TEXT NOT NULL
);
CREATE TABLE conditions (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patients(id),
    code_cim10 TEXT NOT NULL,
    libelle TEXT NOT NULL,
    date_debut TEXT NOT NULL
);
"""


def creer_base(chemin: str = ":memory:") -> sqlite3.Connection:
    """
    Crée une base SQLite vide avec les trois tables.

    Paramètres :
        chemin (str) : fichier de la base, ou ":memory:" pour une base
            temporaire en mémoire (pratique pour les tests).

    Retourne :
        sqlite3.Connection : la connexion ouverte, tables créées.
    """
    connexion = sqlite3.connect(chemin)
    connexion.execute("PRAGMA foreign_keys = ON")
    connexion.executescript(SCHEMA)
    return connexion


def _ligne_patient(ressource: dict) -> tuple:
    """Extrait d'une ressource Patient les valeurs de la table patients."""
    nom = ressource["name"][0]
    return (ressource["id"], nom["given"][0], nom["family"],
            ressource["gender"], ressource["birthDate"])


def _ligne_observation(ressource: dict) -> tuple:
    """Extrait d'une ressource Observation les valeurs de la table observations."""
    codage = ressource["code"]["coding"][0]
    quantite = ressource["valueQuantity"]
    patient_id = ressource["subject"]["reference"].removeprefix("Patient/")
    return (ressource["id"], patient_id, codage["code"], codage["display"],
            quantite["value"], quantite["unit"], ressource["effectiveDateTime"])


def _ligne_condition(ressource: dict) -> tuple:
    """Extrait d'une ressource Condition les valeurs de la table conditions."""
    codage = ressource["code"]["coding"][0]
    patient_id = ressource["subject"]["reference"].removeprefix("Patient/")
    return (ressource["id"], patient_id, codage["code"], codage["display"],
            ressource["onsetDateTime"])


def charger_bundle(connexion: sqlite3.Connection, bundle: dict) -> dict:
    """
    Insère toutes les ressources du Bundle dans la base.

    Les requêtes sont paramétrées (les "?") : les valeurs ne sont jamais
    collées dans le texte SQL, ce qui évite les injections SQL.

    Paramètres :
        connexion (sqlite3.Connection) : base créée par creer_base().
        bundle (dict) : Bundle FHIR déjà validé.

    Retourne :
        dict : nombre de lignes insérées par table.
    """
    lignes = {"patients": [], "observations": [], "conditions": []}
    convertisseurs = {
        "Patient": ("patients", _ligne_patient),
        "Observation": ("observations", _ligne_observation),
        "Condition": ("conditions", _ligne_condition),
    }
    for entree in bundle["entry"]:
        ressource = entree["resource"]
        table, convertir = convertisseurs[ressource["resourceType"]]
        lignes[table].append(convertir(ressource))

    # Les patients d'abord, pour respecter les clés étrangères
    for table, nb_colonnes in (("patients", 5), ("observations", 7), ("conditions", 5)):
        marques = ", ".join("?" * nb_colonnes)
        connexion.executemany(f"INSERT INTO {table} VALUES ({marques})", lignes[table])
    connexion.commit()
    return {table: len(valeurs) for table, valeurs in lignes.items()}
