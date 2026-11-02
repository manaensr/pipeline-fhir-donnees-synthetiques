"""
test_pipeline.py
Rôle : tests automatiques du pipeline (génération, FHIR, validation, SQL, rapport).
Lancer : pytest
"""

import copy

import pytest

from pipeline_fhir import requetes_sql
from pipeline_fhir.chargement_sql import charger_bundle, creer_base
from pipeline_fhir.conversion_fhir import construire_bundle
from pipeline_fhir.generation_patients import generer_patients
from pipeline_fhir.rapport_html import generer_rapport
from pipeline_fhir.validation_fhir import verifier_bundle


@pytest.fixture(scope="module")
def patients():
    """Fournit 100 patients fictifs, identiques à chaque exécution."""
    return generer_patients(nombre=100, graine=1)


@pytest.fixture(scope="module")
def bundle(patients):
    """Fournit le Bundle FHIR construit à partir des patients."""
    return construire_bundle(patients)


@pytest.fixture()
def base(bundle):
    """Fournit une base SQLite en mémoire déjà remplie."""
    connexion = creer_base()
    charger_bundle(connexion, bundle)
    yield connexion
    connexion.close()


def test_generation_reproductible():
    """Deux générations avec la même graine donnent les mêmes patients."""
    assert generer_patients(10, graine=7) == generer_patients(10, graine=7)


def test_generation_nombre_et_mesures(patients):
    """Chaque patient a cinq mesures et un identifiant unique."""
    assert len(patients) == 100
    assert len({p["id"] for p in patients}) == 100
    assert all(len(p["observations"]) == 5 for p in patients)


def test_bundle_valide(bundle):
    """Le Bundle généré passe la validation sans erreur."""
    assert verifier_bundle(bundle) == []


def test_codes_loinc_et_cim10(bundle):
    """Les codes standards attendus sont bien présents dans le Bundle."""
    codes = {e["resource"]["code"]["coding"][0]["code"]
             for e in bundle["entry"] if "code" in e["resource"]}
    assert {"8480-6", "8462-4", "29463-7", "8302-2", "8867-4"} <= codes


def test_validation_detecte_patient_inconnu(bundle):
    """Une observation rattachée à un patient absent est signalée."""
    mauvais = copy.deepcopy(bundle)
    for entree in mauvais["entry"]:
        if entree["resource"]["resourceType"] == "Observation":
            entree["resource"]["subject"]["reference"] = "Patient/inexistant"
            break
    assert any("patient inconnu" in erreur for erreur in verifier_bundle(mauvais))


def test_validation_detecte_doublon(bundle):
    """Un identifiant en double est signalé."""
    mauvais = copy.deepcopy(bundle)
    mauvais["entry"].append(mauvais["entry"][0])
    assert any("double" in erreur for erreur in verifier_bundle(mauvais))


def test_chargement_compte_les_lignes(patients, base):
    """La base contient autant de patients et de mesures que prévu."""
    assert base.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 100
    assert base.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 500


def test_repartition_sexe_somme(base):
    """La somme des effectifs par sexe égale le nombre de patients."""
    assert sum(n for _, n in requetes_sql.repartition_sexe(base)) == 100


def test_tension_monte_avec_age(base):
    """La tension moyenne de la tranche la plus âgée dépasse celle des plus jeunes."""
    tranches = requetes_sql.tension_par_tranche_age(base)
    assert tranches[-1][2] > tranches[0][2]


def test_hypertension_non_diagnostiquee(base):
    """Les cas repérés ont bien une pression d'au moins 140 et aucun code I10."""
    for patient_id, _, valeur in requetes_sql.hypertension_non_diagnostiquee(base):
        assert valeur >= 140
        nb = base.execute("SELECT COUNT(*) FROM conditions WHERE patient_id=? AND code_cim10='I10'",
                          (patient_id,)).fetchone()[0]
        assert nb == 0


def test_rapport_echappe_le_html():
    """Un texte contenant des balises est neutralisé dans le rapport."""
    resultats = {"sexe": [("<script>", 1)], "tension": [], "conditions": [], "hypertension": []}
    page = generer_rapport({"patients": 1}, resultats)
    assert "<script>" not in page and "&lt;script&gt;" in page
