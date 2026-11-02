"""
requetes_sql.py
Rôle : requêtes SQL d'analyse sur la base remplie par chargement_sql.py.
Utilisé par : scripts/lancer_pipeline.py, rapport_html.py, tests/
"""

import sqlite3

from pipeline_fhir.generation_patients import DATE_REFERENCE

# Âge en années entières à la date de référence (calculé en SQL)
AGE_SQL = "CAST((julianday(?) - julianday(p.date_naissance)) / 365.25 AS INTEGER)"


def repartition_sexe(connexion: sqlite3.Connection) -> list[tuple]:
    """
    Compte les patients par sexe.

    Paramètres :
        connexion (sqlite3.Connection) : base remplie.

    Retourne :
        list[tuple] : couples (sexe, nombre).
    """
    return connexion.execute(
        "SELECT sexe, COUNT(*) FROM patients GROUP BY sexe ORDER BY sexe"
    ).fetchall()


def tension_par_tranche_age(connexion: sqlite3.Connection) -> list[tuple]:
    """
    Calcule la pression systolique moyenne par tranche d'âge de dix ans.

    Paramètres :
        connexion (sqlite3.Connection) : base remplie.

    Retourne :
        list[tuple] : triplets (début de tranche, nombre de patients, moyenne).
    """
    requete = f"""
        SELECT ({AGE_SQL} / 10) * 10 AS tranche, COUNT(*), ROUND(AVG(o.valeur), 1)
        FROM patients p JOIN observations o ON o.patient_id = p.id
        WHERE o.code_loinc = '8480-6'
        GROUP BY tranche ORDER BY tranche
    """
    return connexion.execute(requete, (DATE_REFERENCE.isoformat(),)).fetchall()


def prevalence_conditions(connexion: sqlite3.Connection) -> list[tuple]:
    """
    Calcule, pour chaque maladie, le nombre de patients et le pourcentage.

    Paramètres :
        connexion (sqlite3.Connection) : base remplie.

    Retourne :
        list[tuple] : triplets (libellé, nombre de patients, pourcentage).
    """
    requete = """
        SELECT libelle, COUNT(DISTINCT patient_id),
               ROUND(100.0 * COUNT(DISTINCT patient_id) / (SELECT COUNT(*) FROM patients), 1)
        FROM conditions GROUP BY libelle ORDER BY 2 DESC
    """
    return connexion.execute(requete).fetchall()


def hypertension_non_diagnostiquee(connexion: sqlite3.Connection) -> list[tuple]:
    """
    Repère les patients dont la pression systolique atteint 140 mm[Hg] ou plus
    sans diagnostic d'hypertension (code CIM-10 I10) enregistré.

    Paramètres :
        connexion (sqlite3.Connection) : base remplie.

    Retourne :
        list[tuple] : triplets (id du patient, nom complet, pression systolique).
    """
    requete = """
        SELECT p.id, p.prenom || ' ' || p.nom, o.valeur
        FROM patients p JOIN observations o ON o.patient_id = p.id
        WHERE o.code_loinc = '8480-6' AND o.valeur >= 140
          AND NOT EXISTS (SELECT 1 FROM conditions c
                          WHERE c.patient_id = p.id AND c.code_cim10 = 'I10')
        ORDER BY o.valeur DESC
    """
    return connexion.execute(requete).fetchall()
