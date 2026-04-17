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

**Note :** Les sociétaires (Satellite/Constellation) ne rechargent pas le MULTIPASS.
Le MULTIPASS reçoit son crédit initial à la création (`make_NOSTRCARD.sh` → PRIMO TX 1Ğ1).

## Structure du projet

```
OC2UPlanet/
├── oc2uplanet.sh          ← Script principal (GraphQL OC → émission ẐEN)
├── oc_expense_monitor.sh  ← Monitoring dépenses OC (flux REJECTED → REFUND)
├── microledger.me.sh      ← Publication IPFS + git du microledger
├── data/                  ← Données runtime (NON versionné)
│   ├── backers.json           ← Cache liste des membres OC
│   ├── tx.json                ← Transactions récupérées
│   ├── current_month.credit.json  ← Crédits du mois courant
│   ├── last_month.credit.json     ← Crédits du mois précédent
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
OC_API="https://api.opencollective.com/graphql/v2"  # auto-détecté (staging vs prod)
```

**Détection ORIGIN** : `cat ~/.ipfs/swarm.key | tail -n 1`
- Vide → API production
- Présent → API staging

## Déclenchement

**Automatique** : `20h12.process.sh` d'Astroport.ONE l'exécute **une fois par mois**.
Marqueur d'idempotence mensuel : `~/.zen/game/.oc2uplanet_monthly.done`

**Manuel** :
```bash
cd ~/.zen/workspace/OC2UPlanet
./oc2uplanet.sh                # Traitement du mois courant
./oc2uplanet.sh --scan         # Lister tous les backers et contributions
./oc2uplanet.sh --ranking      # Classement par contribution + statut actif
./oc2uplanet.sh --alerts       # Abonnements arrêtés ou modifiés
./oc2uplanet.sh --status       # Résumé du mois courant
./oc2uplanet.sh --history      # 20 dernières transactions traitées
./oc2uplanet.sh --manual       # Mode interactif validation/édition
./oc2uplanet.sh --json         # Sortie JSON machine-readable
```

## Idempotence

Chaque transaction est enregistrée dans `data/emission.log` au format :
```
email:montant:tier:timestamp:status
```
`status` = `OK` si émis, évite les doubles émissions en cas de re-run.

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
