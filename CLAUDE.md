# CLAUDE.md — OC2UPlanet

Pont automatique entre les cotisations OpenCollective et l'économie ẐEN d'une station UPlanet.
Synchronise les contributions mensuelles OC → ZenCards des membres.
Author: Fred (support@qo-op.com). License: AGPL-3.0. Version: 0.5.

## Principe

Chaque versement CREDIT sur OpenCollective déclenche l'émission de ẐEN équivalents
(1€ = 1Ẑ = 0.1Ğ1) vers les portefeuilles appropriés via `UPLANET.official.sh` d'Astroport.ONE.

## Flux par type de contribution

| Tier OC | Slug | Action | Destination |
|---------|------|--------|-------------|
| Satellite (50€/an) | `parrainage-infrastructure-extension-128-go` | `process_societaire` | ZEN Card → répartition SCIC 33/33/33/1 |
| Constellation (540€/an) | `parrainage-infrastructure-module-gpu-1-24` | `process_societaire` | ZEN Card → répartition SCIC 33/33/33/1 |
| Cloud usage | `cotisation-services-cloud-usage` | `process_locataire` | Recharge MULTIPASS immédiate |
| Membre résident | `membre-resident-soutien-mensuel` | `process_locataire` | Recharge MULTIPASS mensuelle |
| Labo / R&D | `infrastructure,labo,genereux-donateur,r-d,recherche` | `PAYforSURE.sh` direct | **Wallet coopératif `UPLANETNAME_RND`** (jamais le MULTIPASS personnel du Capitaine) |

**Note :** Les sociétaires (Satellite/Constellation) ne rechargent pas le MULTIPASS.
Le MULTIPASS reçoit son crédit initial à la création (`make_NOSTRCARD.sh` → PRIMO TX 1Ğ1).

**Tier labo/R&D — conformité** : ces dons sont versés directement au portefeuille coopératif
`UPLANETNAME_RND` (`~/.zen/game/uplanet.G1.dunikey` → `UPLANETNAME_RND`, cf. `dispatch_zen_emission()`
dans `oc2uplanet.sh`), et non au MULTIPASS personnel du Capitaine (`CAPTAINEMAIL`) — même schéma
que l'allocation 1/3 R&D de `RUNTIME/ZEN.COOPERATIVE.3x1-3.sh` d'Astroport.ONE. Aucune vérification
MULTIPASS/invitation ne s'applique à ce tier : le wallet R&D est toujours disponible (dérivé de la
clé swarm), sans notion d'abonné.

**Routage configurable** : le slug ci-dessus n'est qu'un exemple par défaut. La correspondance
slug → catégorie (satellite/constellation/labo/cloud) est pilotée par les clés
`TIER_SLUG_SATELLITE` / `TIER_SLUG_CONSTELLATION` / `TIER_SLUG_LABO` / `TIER_SLUG_CLOUD` de
`cooperative_config.sh` (listes de globs séparées par des virgules, ex. `*satellite*,*love-box*claude*`).
Si ces clés sont absentes de la config coopérative, `oc2uplanet.sh` retombe sur les motifs
historiques codés en dur (`_tier_matches()` dans le script).

## Structure du projet

```
OC2UPlanet/
├── oc2uplanet.sh          ← Script principal (GraphQL OC → émission ẐEN)
├── tx_fields.py           ← Extraction NUL-séparée des transactions (voir note bash `read` ci-dessous)
├── oc_expense_monitor.sh  ← Monitoring dépenses OC (flux REJECTED → REFUND)
├── microledger.me.sh      ← Publication IPFS + git du microledger
├── data/                  ← Données runtime (NON versionné)
│   ├── backers.json           ← Cache liste des membres OC
│   ├── tx.json                ← Transactions récupérées (GraphQL, jusqu'à 1000)
│   ├── current_month.credit.json  ← Crédits du mois courant (info/alerts/ranking)
│   ├── last_month.credit.json     ← Crédits du mois précédent (info/alerts)
│   ├── catchup.credit.json        ← Crédits des 12 derniers mois (source réelle de --sync/--status/--run)
│   ├── yesterday.credit.json      ← Crédits du jour précédent
│   ├── emission.log               ← Journal d'idempotence (format: email:montant:tier:ts:status)
│   ├── expenses.json              ← Dépenses OC
│   ├── restitution_pending.json   ← Restitutions en attente
│   ├── restitution.log            ← Journal restitutions
│   ├── refund.log                 ← Journal remboursements
│   ├── slug_email_map.json        ← Mapping slug → email
│   └── slugemail.list             ← Liste slug/email
├── AstroBot/              ← Automation IA (optionnel)
├── more/                  ← Scripts supplémentaires
└── GUIDE_SETUP_OC.md      ← Guide configuration OpenCollective
```

## Configuration

Les secrets ne sont **plus** dans `.env` local. Ils sont chargés depuis le DID NOSTR coopératif
(kind 30800, chiffré avec `$UPLANETNAME`) via `cooperative_config.sh` d'Astroport.ONE :

```bash
OCAPIKEY="votre_personal_token_OC"
OCSLUG="votre-slug-collectif"
OC_API="https://api.opencollective.com/graphql/v2"  # toujours l'API de production
```

Pas de bascule staging : ce collectif OpenCollective n'a pas d'API staging configurée.
UPlanet ORIGIN reste un régime économique réel (1Ẑ=0.1Ğ1), pas un sandbox — `oc2uplanet.sh`
et `oc_expense_monitor.sh` ciblent toujours l'API de production, avec ou sans `~/.ipfs/swarm.key`.

## Déclenchement

**Automatique** : `20h12.process.sh` d'Astroport.ONE l'exécute **une fois par mois**.
Marqueur d'idempotence mensuel : `~/.zen/game/.oc2uplanet_monthly.done`

**Manuel** :
```bash
cd ~/.zen/workspace/OC2UPlanet
./oc2uplanet.sh                # Vue synthétique (= --status), AUCUNE émission Ẑen
./oc2uplanet.sh --sync         # Détail par compte (rattrapage 12 mois) : montant, tier, MULTIPASS, statut émission
./oc2uplanet.sh --status       # Résumé du mois courant + synchro OK/FAIL/pending (12 mois)
./oc2uplanet.sh --scan         # Lister tous les backers et contributions
./oc2uplanet.sh --ranking      # Classement par contribution + statut actif
./oc2uplanet.sh --parrain-ranking  # Classement des parrains sociétaires (tiers Satellite/Constellation),
                                    # pseudonymisé (sans email) — alimente /api/parrains_ranking (public)
./oc2uplanet.sh --alerts       # Abonnements arrêtés ou modifiés
./oc2uplanet.sh --history      # 20 dernières transactions traitées
./oc2uplanet.sh --json         # Sortie JSON machine-readable (combinable avec les options ci-dessus)

./oc2uplanet.sh --run          # Traite le rattrapage 12 mois et ÉMET les Ẑen (usage cron)
./oc2uplanet.sh --manual       # Comme --run, en mode interactif validation/édition
```

## Rattrapage des MULTIPASS créés tardivement

`--sync`/`--status`/`--run` traitent désormais `data/catchup.credit.json` (12 derniers
mois, pas seulement le mois courant) : un don OC dont le MULTIPASS n'a été créé que des
semaines après l'inscription est ainsi automatiquement rattrapé au run suivant, sans
jamais rejouer un don déjà émis (idempotence). La fenêtre est volontairement bornée à un
an : au-delà, le traitement d'un don ancien doit être validé manuellement, car son
éventuelle compensation par un autre canal (hors pipeline) ne peut pas être vérifiée
automatiquement.

## Idempotence

Chaque transaction traitée publie une preuve NOSTR **kind 30851** (d-tag
`oc-emission-<email>:<montant>:<created_at>`) et une ligne dans `data/emission.log` :
```
email:montant:tier:timestamp:status
```
`status` = `OK` si émis. `_check_emission_nostr()` vérifie kind 30851 (source de vérité,
persistant) puis `emission.log` (fallback local, purgé après 90 jours) avant tout
traitement — évite les doubles émissions en cas de re-run.

**Extraction des champs (`tx_fields.py`)** : les transactions sont parsées en Python
(séparateur NUL) plutôt qu'en `jq @tsv` + `read` bash. Raison : `IFS=$'\t'` fait
collapser silencieusement les champs vides consécutifs par le `read` de bash (tabulation
= caractère "whitespace" pour bash), ce qui décale tous les champs suivants dès qu'une
transaction n'a pas d'email visible (compte OC anonyme "incognito-*", transaction de
projet enfant). NUL ne pouvant jamais apparaître dans une chaîne JSON, `readarray -d ''`
est fiable à 100 % — vérifié empiriquement sur l'historique réel du collectif.

## Webhook temps réel (optionnel)

Pour les recharges immédiates (cotisation cloud-usage), l'API UPassport expose :
```
POST https://votre-station:54321/oc_webhook
```
Configuré côté OpenCollective dans les Webhooks du collectif.

## Monitoring des dépenses

`oc_expense_monitor.sh` surveille les dépenses OC :
- Statut REJECTED → déclenchement flux REFUND
- Données dans `data/expenses.json`, `data/restitution_pending.json`
- Journaux : `data/refund.log`, `data/restitution.log`

## Dépendances

- **Astroport.ONE** installé (accès à `UPLANET.official.sh`, `cooperative_config.sh`)
- `jq`, `curl` (pour les appels GraphQL OC)
- Compte Capitaine actif (wallet G1 pour émission ẐEN)
- Personal Token API OpenCollective (`OCAPIKEY`)

## GraphQL OC

Requêtes principales :
- `account.members` → liste des backers avec tier, montant, email
- `transactions(type: CREDIT)` → crédits du mois courant
- `expenses` → dépenses soumises/validées/rejetées
