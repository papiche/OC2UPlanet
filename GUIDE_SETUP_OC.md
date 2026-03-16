# Guide : Configurer OpenCollective pour une nouvelle UPlanet ẐEN

Ce guide explique pas à pas comment créer et configurer un collectif OpenCollective
pour alimenter l'économie ẐEN d'une station UPlanet.

## Vue d'ensemble

```
Contributeur € ──→ OpenCollective ──→ oc2uplanet.sh ──→ UPLANET.official.sh ──→ Ğ1 blockchain
                    (collecte €)      (pont OC→ẐEN)      (émission ẐEN)          (transferts)
```

L'économie ẐEN est un système de tokens d'usage adossé à la Ğ1 (Monnaie Libre Duniter) :
- **1€ = 1Ẑ = 0.1Ğ1**
- Les € collectés via OC financent l'infrastructure réelle
- Les Ẑ sont émis comme tokens d'usage sur la blockchain Ğ1

---

## Étape 1 : Créer le collectif OpenCollective

### 1.1 Créer un compte fiscal

Rendez-vous sur [opencollective.com](https://opencollective.com) et créez un collectif.

Le collectif doit être hébergé par une entité fiscale (Fiscal Host) compatible :
- **Open Collective Europe** (ASBL belge) — recommandé pour la France/UE
- Ou votre propre structure (association, SCIC, coopérative)

### 1.2 Créer un projet "CoeurBox" (ou équivalent)

Dans votre collectif, créez un **projet** qui recevra les cotisations infrastructure.
Exemple : `monnaie-libre/projects/coeurbox`

### 1.3 Créer les 4 tiers de contribution

Depuis l'admin du projet (`/admin/tiers`), créez exactement ces 4 tiers :

#### Tier 1 : Satellite (sociétaire)
- **Nom** : Parrainage Infrastructure Extension 128 Go
- **Slug** : `parrainage-infrastructure-extension-128-go`
- **Type** : Contribution récurrente
- **Montant** : 50€/an (ou ~1€/sem)
- **Description** : Parrainage d'une extension de stockage 128 Go sur une station UPlanet.
  Le contributeur devient sociétaire de la SCIC et reçoit une ZEN Card.

#### Tier 2 : Constellation (sociétaire)
- **Nom** : Parrainage Infrastructure Module GPU
- **Slug** : `parrainage-infrastructure-module-gpu-1-24`
- **Type** : Contribution récurrente
- **Montant** : 540€ / 3ans
- **Description** : Parrainage d'un module GPU sur une constellation UPlanet.
  Le contributeur devient sociétaire de la SCIC et reçoit une ZEN Card.

#### Tier 3 : Cloud Usage (locataire)
- **Nom** : Cotisation Services Cloud Usage
- **Slug** : `cotisation-services-cloud-usage`
- **Type** : Contribution ponctuelle ou récurrente
- **Montant** : Flexible (le contributeur choisit)
- **Description** : Cotisation pour l'usage des services cloud UPlanet.
  Le montant est converti en ẐEN d'usage sur le MULTIPASS du contributeur (1€ = 1Ẑ).

#### Tier 4 : Membre résident (locataire)
- **Nom** : Membre Résident Soutien Mensuel
- **Slug** : `membre-resident-soutien-mensuel`
- **Type** : Contribution récurrente mensuelle
- **Montant** : Flexible (le contributeur choisit)
- **Description** : Soutien mensuel d'un membre résident.
  Le montant est converti en ẐEN d'usage sur le MULTIPASS (1€ = 1Ẑ), cycle mensuel.

> **Important** : Les slugs doivent contenir les mots-clés exacts (`128-go`, `gpu`,
> `cotisation`, `cloud`, `membre-resident`, `soutien-mensuel`) car le dispatch
> dans `oc2uplanet.sh` utilise du pattern matching sur ces slugs.

---

## Étape 2 : Générer le Personal Token API

1. Allez dans l'admin de votre collectif :
   `https://opencollective.com/dashboard/{votre-slug}/for-developers/personal-tokens/`

2. Créez un nouveau Personal Token avec les scopes :
   - `account` (lecture des emails backers)
   - `transactions` (lecture des transactions)

3. Copiez le token généré

### Mode ORIGIN (staging/dev)

Si vous êtes en mode développement (swarm key tout-zéros dans `~/.ipfs/swarm.key`),
utilisez l'API staging :

1. Créez un compte sur [staging.opencollective.com](https://staging.opencollective.com)
2. Recréez les mêmes tiers sur le staging
3. Générez un Personal Token staging
4. Le script détecte automatiquement le mode ORIGIN et bascule sur l'API staging

---

## Étape 3 : Configurer la station Astroport

### 3.1 Cloner OC2UPlanet

```bash
cd ~/.zen/workspace
git clone https://github.com/papiche/OC2UPlanet.git
cd OC2UPlanet
```

> Note : `20h12.process.sh` fait automatiquement le `git clone` si le dossier n'existe pas.

### 3.2 Créer le fichier `.env`

```bash
cp .env.example .env
nano .env
```

Contenu :
```bash
OCAPIKEY="votre_personal_token_ici"
OCSLUG="votre-slug-collectif"
```

### 3.3 Rendre exécutable

```bash
chmod +x oc2uplanet.sh
```

### 3.4 Test manuel

```bash
./oc2uplanet.sh
```

Vérifiez :
- `data/backers.json` contient les backers
- `data/tx.json` contient les transactions avec les tiers
- `data/current_month.credit.json` filtre correctement le mois en cours
- `data/emission.log` trace les émissions effectuées

---

## Étape 4 : Configurer le webhook (optionnel)

Pour les recharges immédiates (sans attendre le cycle mensuel) :

### 4.1 URL du webhook

L'endpoint est disponible sur l'API UPassport de la station :
```
https://votre-domaine:54321/oc_webhook
```

### 4.2 Configurer dans OC

1. Admin du collectif → Webhooks
2. Ajouter un webhook :
   - **URL** : `https://votre-domaine:54321/oc_webhook`
   - **Événement** : `collective.transaction.created`

### 4.3 Fonctionnement du webhook

Le webhook reçoit un payload minimal (sans email ni tier). Il résout ces informations
via une requête GraphQL supplémentaire en utilisant le slug du contributeur :

```
Webhook payload (slug, amount) → GraphQL (email + tier) → UPLANET.official.sh
```

Le tier est résolu en interrogeant les 5 dernières transactions du contributeur
et en matchant le montant avec la transaction du webhook.

---

## Étape 5 : Vérification du fonctionnement

### Cycle mensuel (automatique)

Le script `20h12.process.sh` (cron quotidien Astroport) exécute `oc2uplanet.sh`
**une fois par mois** (marqueur `~/.zen/game/.oc2uplanet_monthly.done`).

Pour forcer une ré-exécution :
```bash
rm ~/.zen/game/.oc2uplanet_monthly.done
```

### Vérifier les émissions

```bash
# Transactions du mois
cat ~/.zen/workspace/OC2UPlanet/data/current_month.credit.json | jq .

# Log d'émission
cat ~/.zen/workspace/OC2UPlanet/data/emission.log

# Log webhook
cat ~/.zen/tmp/oc_webhook_processed.log
```

### Vérifier les soldes ẐEN

```bash
# Balance MULTIPASS d'un utilisateur
~/.zen/Astroport.ONE/tools/G1check.sh $(cat ~/.zen/game/nostr/user@example.com/G1PUBNOSTR)

# Balance ZEN Card (si sociétaire avec ZenCard)
~/.zen/Astroport.ONE/tools/G1check.sh $(cat ~/.zen/game/players/user@example.com/.g1pub)
```

---

## Architecture des portefeuilles

```
UPLANETNAME_G1 (source primale)
    │
    ├── process_locataire ──→ UPLANETNAME ──→ MULTIPASS (usage)
    │   (cloud-usage, membre-resident)
    │
    └── process_societaire ──→ UPLANETNAME_SOCIETY ──→ ZEN Card
        (satellite, constellation)                        │
                                                    ┌─────┼─────┐
                                                    │     │     │
                                                  1/3   1/3   1/3
                                                 CASH   RnD  ASSETS
```

Le MULTIPASS reçoit son crédit initial (PRIMO TX 1Ğ1 = 10Ẑ) lors de la création
via `make_NOSTRCARD.sh`. Les sociétaires ne rechargent pas le MULTIPASS — leurs
contributions alimentent la coopérative via la ZEN Card.

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `ERROR 0 missing .env` | Fichier `.env` absent | Créer à partir de `.env.example` |
| `⚠ No email for slug=xxx` | Backer sans email visible | Vérifier les permissions du Personal Token |
| `⚠ No MULTIPASS for xxx` | Utilisateur pas encore inscrit | L'utilisateur doit créer son MULTIPASS via Ẑinkgo ou le terminal |
| `⏭ Already processed` | Transaction déjà traitée | Normal — idempotence. Supprimer la ligne dans `emission.log` pour forcer |
| API staging au lieu de prod | Mode ORIGIN détecté | Vérifier `~/.ipfs/swarm.key` (ne doit pas être tout-zéros en production) |
| Webhook retourne `no_email` | GraphQL ne résout pas le slug | Vérifier que le Personal Token a le scope `account` |

---

## Références

- [ZEN.ECONOMY.readme.md](../Astroport.ONE/docs/ZEN.ECONOMY.readme.md) — Modèle économique complet
- [UPLANET.official.sh](../Astroport.ONE/UPLANET.official.sh) — Script d'émission ẐEN
- [OpenCollective GraphQL API](https://graphql-docs-v2.opencollective.com) — Documentation API
- [OpenCollective.md](OpenCollective.md) — Exemples de requêtes GraphQL
