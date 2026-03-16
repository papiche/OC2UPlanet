# OC2UPlanet — OpenCollective → ẐEN Economy Bridge

Pont automatique entre les cotisations OpenCollective et l'économie ẐEN d'une station UPlanet.

## Principe

Chaque versement CREDIT constaté sur le collectif OpenCollective déclenche l'émission
de ẐEN équivalents (1€ = 1Ẑ = 0.1Ğ1) vers les portefeuilles appropriés via `UPLANET.official.sh`.

### Flux par type de contribution

| Tier OpenCollective | Slug OC | Action | Destination |
|---|---|---|---|
| Satellite (50€/an) | `parrainage-infrastructure-extension-128-go` | `process_societaire` | ZEN Card → SCIC 33/33/33/1 |
| Constellation (540€/an) | `parrainage-infrastructure-module-gpu-1-24` | `process_societaire` | ZEN Card → SCIC 33/33/33/1 |
| Cloud usage | `cotisation-services-cloud-usage` | `process_locataire` | Recharge MULTIPASS immédiate |
| Membre résident | `membre-resident-soutien-mensuel` | `process_locataire` | Recharge MULTIPASS mensuelle |

**Note :** Les sociétaires (Satellite/Constellation) ne rechargent pas le MULTIPASS.
Le MULTIPASS reçoit son crédit initial lors de la création (`make_NOSTRCARD.sh` → PRIMO TX 1Ğ1).
Le montant offert est paramétré dans le DID Zen Economy de l'essaim.

## Prérequis

1. [Astroport.ONE](https://github.com/papiche/Astroport.ONE) installé avec un compte Capitaine
2. Un collectif OpenCollective configuré (voir [GUIDE_SETUP_OC.md](GUIDE_SETUP_OC.md))
3. Un Personal Token API OC

## Configuration

### `.env`

```bash
OCAPIKEY="votre_personal_token"
OCSLUG="votre-slug-collectif"
```

Le mode ORIGIN (dev/staging) est **auto-détecté** via `~/.ipfs/swarm.key` :
- Clé tout-zéros → API staging (`api-staging.opencollective.com`)
- Clé réelle → API production (`api.opencollective.com`)

### Lancement

Le script est exécuté **automatiquement une fois par mois** par `20h12.process.sh`
(le processus cron quotidien d'Astroport). Le marqueur `~/.zen/game/.oc2uplanet_monthly.done`
empêche les exécutions multiples dans le même mois.

Lancement manuel :
```bash
cd ~/.zen/workspace/OC2UPlanet
./oc2uplanet.sh
```

### Webhook temps réel (optionnel)

Pour les recharges immédiates (cotisation cloud-usage), un endpoint webhook est disponible
sur l'API UPassport :

```
POST https://votre-station:54321/oc_webhook
```

Configurez l'URL webhook dans l'admin OC du collectif pour l'événement
`collective.transaction.created`.

## Fonctionnement

1. **Récupération des backers** — Requête GraphQL `members(role: BACKER)` → `data/backers.json`
2. **Mapping slug→email** — Extraction des correspondances → `data/slug_email_map.json`
3. **Récupération des transactions** — `transactions(type: CREDIT)` avec `order { tier { slug } }` → `data/tx.json`
4. **Filtrage temporel** — Extraction des crédits du mois en cours → `data/current_month.credit.json`
5. **Dispatch par tier** — Chaque transaction est routée via `dispatch_zen_emission()` :
   - Identification du tier slug depuis la réponse GraphQL
   - Vérification que le MULTIPASS existe (`~/.zen/game/nostr/{email}/G1PUBNOSTR`)
   - Contrôle d'idempotence via `data/emission.log`
   - Appel `UPLANET.official.sh` avec les bons flags (`-s` sociétaire ou `-l` locataire)

### Requête GraphQL transactions (avec tier)

```graphql
query ($slug: String) {
  account(slug: $slug) {
    name slug
    transactions(limit: 100, type: CREDIT) {
      totalCount
      nodes {
        type
        fromAccount { name slug emails }
        amount { value currency }
        order { tier { slug name } }
        createdAt
      }
    }
  }
}
```

### Structure des données

```
data/
├── backers.json                  # Liste des backers (emails)
├── slugemail.list                # Correspondances slug:email
├── slug_email_map.json           # Map JSON {slug: email}
├── tx.json                       # Transactions CREDIT brutes
├── current_month.credit.json     # Crédits du mois en cours
├── last_month.credit.json        # Crédits du mois précédent
├── yesterday.credit.json         # Crédits d'hier
├── emission.log                  # Log d'idempotence (tx traitées)
├── expenses.json                 # Expenses OC (PENDING/REJECTED/PAID)
├── restitution_pending.json      # TX RESTITUTION reçues par uplanet.G1
├── restitution.log               # Expenses PAID (finalisées)
└── refund.log                    # Expenses REJECTED (remboursées)
```

### Rétroaction : surveillance des indemnisations (oc_expense_monitor.sh)

Lorsqu'un membre restitue des crédits ẐEN via Ẑinkgo (TX `RESTITUTION:INDEMNISATION`
vers `uplanet.G1.dunikey`), il dépose ensuite une note de frais sur OpenCollective.

Le script `oc_expense_monitor.sh` (appelé automatiquement par `oc2uplanet.sh`) surveille
le statut de ces expenses :

| Statut OC | Action |
|---|---|
| **PENDING** | En attente de validation — aucune action |
| **APPROVED** | Validée, en cours de paiement — aucune action |
| **PAID** | Payée → marquer comme finalisée dans `restitution.log` |
| **REJECTED** | Refusée → **reverser les ẐEN** au MULTIPASS du membre |

#### Flux de rétroaction (expense REJECTED)

```
1. Membre restitue 30 ẐEN → uplanet.G1.dunikey (TX: RESTITUTION:INDEMNISATION)
2. Membre dépose note de frais 30€ sur OpenCollective
3. Admin OC refuse la note de frais (REJECTED)
4. oc_expense_monitor.sh détecte le REJECTED
5. PAYforSURE.sh envoie 3 Ğ1 (= 30 ẐEN) depuis uplanet.G1.dunikey → MULTIPASS
   Comment: REFUND:REJECTED:{expense_id}
6. Logged dans refund.log (idempotent)
```

#### Lancement manuel

```bash
cd ~/.zen/workspace/OC2UPlanet
./oc_expense_monitor.sh
```

### Exemple transaction CREDIT

```json
{
  "type": "CREDIT",
  "fromAccount": {
    "name": "Alice",
    "slug": "alice-doe",
    "emails": ["alice@example.com"]
  },
  "amount": { "value": 50.00, "currency": "EUR" },
  "order": {
    "tier": {
      "slug": "parrainage-infrastructure-extension-128-go",
      "name": "Satellite 128 Go"
    }
  },
  "createdAt": "2026-03-01T10:15:28.042Z"
}
```

---

Voir [GUIDE_SETUP_OC.md](GUIDE_SETUP_OC.md) pour la configuration complète d'OpenCollective
pour une nouvelle UPlanet ẐEN.
