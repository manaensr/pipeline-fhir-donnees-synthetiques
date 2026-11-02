"""
conversion_fhir.py
Rôle : convertit les patients fictifs en ressources FHIR R4 (JSON) :
       Patient, Observation et Condition, réunies dans un Bundle.
Norme : HL7 FHIR R4 (hl7.org/fhir/R4). Les codes viennent de LOINC (mesures),
        de la CIM-10 (maladies) et d'UCUM (unités).
Utilisé par : scripts/lancer_pipeline.py, validation_fhir.py, tests/
"""

# Adresses (URI) qui identifient les systèmes de codes dans FHIR
SYSTEME_LOINC = "http://loinc.org"
SYSTEME_CIM10 = "http://hl7.org/fhir/sid/icd-10"
SYSTEME_UCUM = "http://unitsofmeasure.org"
SYSTEME_STATUT_CLINIQUE = "http://terminology.hl7.org/CodeSystem/condition-clinical"


def patient_vers_fhir(patient: dict) -> dict:
    """
    Convertit un patient en ressource FHIR Patient.

    Paramètres :
        patient (dict) : un patient issu de generer_patients().

    Retourne :
        dict : la ressource Patient (nom, genre, date de naissance).
    """
    return {
        "resourceType": "Patient",
        "id": patient["id"],
        "name": [{"family": patient["nom"], "given": [patient["prenom"]]}],
        "gender": patient["sexe"],
        "birthDate": patient["date_naissance"],
    }


def observation_vers_fhir(patient_id: str, numero: int, observation: dict) -> dict:
    """
    Convertit une mesure en ressource FHIR Observation.

    Paramètres :
        patient_id (str) : identifiant du patient concerné.
        numero (int) : rang de la mesure pour ce patient (sert à l'identifiant).
        observation (dict) : une mesure (code, libellé, valeur, unité, date).

    Retourne :
        dict : la ressource Observation, reliée au patient par "subject".
    """
    return {
        "resourceType": "Observation",
        "id": f"{patient_id}-obs-{numero}",
        "status": "final",
        "code": {"coding": [{"system": SYSTEME_LOINC, "code": observation["code"],
                             "display": observation["libelle"]}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": observation["date"],
        "valueQuantity": {"value": observation["valeur"], "unit": observation["unite"],
                          "system": SYSTEME_UCUM, "code": observation["unite"]},
    }


def condition_vers_fhir(patient_id: str, numero: int, condition: dict) -> dict:
    """
    Convertit un diagnostic en ressource FHIR Condition.

    Paramètres :
        patient_id (str) : identifiant du patient concerné.
        numero (int) : rang du diagnostic pour ce patient.
        condition (dict) : un diagnostic (code CIM-10, libellé, date de début).

    Retourne :
        dict : la ressource Condition, active, reliée au patient.
    """
    return {
        "resourceType": "Condition",
        "id": f"{patient_id}-cond-{numero}",
        "clinicalStatus": {"coding": [{"system": SYSTEME_STATUT_CLINIQUE, "code": "active"}]},
        "code": {"coding": [{"system": SYSTEME_CIM10, "code": condition["code"],
                             "display": condition["libelle"]}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "onsetDateTime": condition["date_debut"],
    }


def construire_bundle(patients: list[dict]) -> dict:
    """
    Rassemble toutes les ressources dans un Bundle FHIR de type "collection".

    Paramètres :
        patients (list[dict]) : les patients fictifs.

    Retourne :
        dict : le Bundle, prêt à être écrit en JSON.
    """
    ressources = []
    for patient in patients:
        ressources.append(patient_vers_fhir(patient))
        for numero, obs in enumerate(patient["observations"], start=1):
            ressources.append(observation_vers_fhir(patient["id"], numero, obs))
        for numero, cond in enumerate(patient["conditions"], start=1):
            ressources.append(condition_vers_fhir(patient["id"], numero, cond))

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [{"resource": ressource} for ressource in ressources],
    }
