# Pipeline FHIR sur données synthétiques

Projet personnel d'apprentissage : je construis une chaîne complète qui part de
patients **entièrement fictifs**, les convertit en ressources **HL7 FHIR R4**,
les valide, les charge dans une base **SQLite**, les interroge en **SQL** et
produit un rapport HTML.

> Aucune donnée réelle n'est utilisée. Les patients sont tirés au hasard avec
> une graine fixe : le résultat est identique à chaque exécution.

## Ce que fait le pipeline

1. **Génération** (`generation_patients.py`) : 200 patients fictifs, 5 mesures chacun, diagnostics éventuels.
2. **Conversion** (`conversion_fhir.py`) : ressources `Patient`, `Observation`, `Condition` réunies dans un `Bundle`.
3. **Validation** (`validation_fhir.py`) : contrôle de structure simplifié (voir limites).
4. **Chargement** (`chargement_sql.py`) : trois tables SQLite, requêtes paramétrées.
5. **Analyse** (`requetes_sql.py`) : répartition par sexe, tension par tranche d'âge, maladies, hypertension non diagnostiquée.
6. **Rapport** (`rapport_html.py`) : page HTML statique.

## Codes utilisés

| Donnée | Système | Code |
|---|---|---|
| Poids / Taille | LOINC | 29463-7 / 8302-2 |
| Pression systolique / diastolique | LOINC | 8480-6 / 8462-4 |
| Fréquence cardiaque | LOINC | 8867-4 |
| Hypertension / Diabète type 2 / Asthme | CIM-10 | I10 / E11 / J45 |
| Unités | UCUM | kg, cm, mm[Hg], /min |

## Lancer le projet

```bash
pip install -r requirements-dev.txt   # installe pytest
pytest                                # 11 tests
python scripts/lancer_pipeline.py     # écrit sortie/bundle.json, base.sqlite, rapport.html
```

Seule la bibliothèque standard de Python (3.11 ou plus) est utilisée par le pipeline.

## Exemple de résultat (graine 42, 200 patients)

- Hypertension enregistrée chez 33 patients (16,5 %), diabète chez 29 (14,5 %), asthme chez 12 (6 %).
- La pression systolique moyenne passe d'environ 105 mm[Hg] (18-19 ans) à plus de 140 après 80 ans.
- 20 patients ont une pression systolique ≥ 140 sans diagnostic d'hypertension.

Ces chiffres viennent de la façon dont j'ai programmé le générateur ; ils ne
décrivent aucune population réelle et n'ont aucune valeur médicale.

## Limites

- La validation est **simplifiée** : ce n'est pas le validateur officiel de HL7, qui contrôle aussi les profils et les terminologies.
- Les données sont simulées : le pipeline n'a pas été testé sur de vrais dossiers de santé.
- Le Bundle est de type `collection` (pas de serveur FHIR ni d'API REST).

## Structure

```
src/pipeline_fhir/   code du pipeline (une responsabilité par fichier)
scripts/             point d'entrée
tests/               tests pytest
.github/workflows/   tests automatiques à chaque envoi
```

## Licence

MIT, voir [LICENSE](LICENSE).
