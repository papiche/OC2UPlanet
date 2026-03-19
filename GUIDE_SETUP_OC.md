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

## Étape 2 : Authentification API — Personal Token ou OAuth ?

> ⚠️ **Clarification importante** : OC propose deux mécanismes d'authentification distincts.
> Les scripts `oc2uplanet.sh` et l'endpoint `/oc_webhook` de UPassport utilisent **uniquement**
> le **Personal Token**. L'OAuth App (ZEN0) est un mécanisme séparé, optionnel.

### 2.1 Personal Token (requis pour les scripts)

Le Personal Token est un jeton d'accès direct lié à **votre compte utilisateur OC personnel**
(pas au dashboard du collectif). Il permet aux scripts bash de faire des appels GraphQL
en votre nom, sans interaction utilisateur.

> ⚠️ **Si vous ne trouvez pas l'option** : c'est parce que vous cherchez dans le dashboard
> du *collectif* (`monnaie-libre`). La section Personal Token est sous **votre profil personnel**.

**URL exacte :**
```
https://opencollective.com/dashboard/[VOTRE-LOGIN-PERSONNEL]/for-developers/personal-tokens/
```
Remplacer `[VOTRE-LOGIN-PERSONNEL]` par votre propre slug de profil OC (ex: `fred-kaminski`, `papa-astro`…).
Ce n'est PAS le slug du collectif.

1. Créez un nouveau Personal Token en cochant **exactement ces scopes** :

   | Scope OC | Pourquoi requis |
   |---|---|
   | ✅ `account` | Lire les emails des backers (`members { emails }`) |
   | ✅ `transactions` | Lire les transactions CREDIT avec le tier (`order { tier { slug } }`) |
   | ✅ `expenses` | Surveiller les notes de frais RESTITUTION (`oc_expense_monitor.sh`) |

   > ⚠️ Sans le scope `account`, les emails des backers ne seront pas accessibles → aucun virement possible.

2. **Cochez READ uniquement** — les scripts n'écrivent jamais sur OC (les virements ẐEN se font via la blockchain Ğ1, pas via l'API OC).

3. Copiez le token généré → c'est votre **`OCAPIKEY`** dans le fichier `.env`

4. Vous devez être **administrateur** du collectif `OCSLUG` pour que le token donne accès aux emails des backers.

### 2.2 OAuth App ZEN0 (optionnel — identification web des membres)

L'application OAuth (ZEN0 avec son `client_id` et `client_secret`) sert à un usage **différent** :
permettre à un membre OC de s'authentifier depuis l'interface web UPassport en cliquant
"Se connecter avec OpenCollective". C'est le **flux OAuth standard** (authorization code flow).

| | Personal Token | OAuth App ZEN0 |
|---|---|---|
| **Usage** | Scripts serveur automatisés | Interface web membre |
| **Nécessaire pour `oc2uplanet.sh`** | ✅ Oui | ❌ Non |
| **Nécessaire pour `/oc_webhook`** | ✅ Oui (résolution GraphQL) | ❌ Non |
| **URL de callback** | Aucune | `https://votre-domaine:54321/oc_oauth_callback` |
| **Où le stocker** | `.env` → `OCAPIKEY` | `.env` → `OC_CLIENT_ID` / `OC_CLIENT_SECRET` |

#### Où inscrire l'URL de callback OAuth ?

Si vous souhaitez activer l'identification OC des membres depuis UPassport, renseignez
dans l'admin de l'app ZEN0 (`for-developers/oauth/`) :

```
URL de rappel : https://votre-domaine:54321/oc_oauth_callback
```

> Cette fonctionnalité n'est **pas encore implémentée** dans UPassport. Les scripts
> fonctionnent sans elle. Laissez l'URL de callback vide pour l'instant ou mettez
> `https://localhost:54321/oc_oauth_callback` pour le développement.

#### Stocker les credentials OAuth dans `.env`

```bash
# Personal Token (obligatoire pour les scripts)
OCAPIKEY="votre_personal_token_ici"
OCSLUG="votre-slug-collectif"

# OAuth App ZEN0 (optionnel — futur usage web)
OC_CLIENT_ID="68133e7a2ba37db06bbf"
OC_CLIENT_SECRET="8e1f490036c81f09f7a8039bc2c..."
```

### 2.3 Mode ORIGIN (staging/dev)

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

### 3.2 Configurer l'OCAPIKEY — deux méthodes

#### Méthode A (recommandée) : DID NOSTR coopératif — configuration partagée swarm

> ✅ **À faire une seule fois** sur la station Capitaine. Toutes les autres stations
> du même essaim (même `swarm.key`) récupèrent automatiquement l'`OCAPIKEY` déchiffré.

L'`OCAPIKEY` est stocké **chiffré** dans un événement NOSTR kind 30800
(`d-tag: cooperative-config`) via [`cooperative_config.sh`](../Astroport.ONE/tools/cooperative_config.sh) :

```bash
# Sur la station Capitaine (une seule fois) :
source ~/.zen/Astroport.ONE/tools/cooperative_config.sh
coop_config_set OCAPIKEY "votre_personal_token_ici"
coop_config_set OCSLUG "monnaie-libre"
coop_config_set OC_API "https://api.opencollective.com/graphql/v2"
```

Le chiffrement utilise `$UPLANETNAME` (clé privée de l'essaim) → seules les stations
avec la même `swarm.key` peuvent déchiffrer. L'`oc2uplanet.sh` et l'endpoint `/oc_webhook`
de UPassport lisent automatiquement ce DID si le `.env` local est absent ou incomplet.

#### Méthode B (fallback) : fichier `.env` local

```bash
cp .env.example .env
nano .env
```

Contenu minimal en production :
```bash
# — Personal Token de votre profil OC personnel
OCAPIKEY="votre_personal_token_ici"

# — Slug du collectif OC
OCSLUG="monnaie-libre"

# — Forcer l'API production quelle que soit la swarm.key
OC_API="https://api.opencollective.com/graphql/v2"
```

> **Priorité de chargement** (dans `oc2uplanet.sh` et `finance.py`) :
> 1. `.env` local → 2. DID NOSTR coopératif → 3. variables d'environnement
>
> Le `.env` local peut rester vide ou absent si le DID NOSTR est configuré.

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

## Étape 4 : Configurer le webhook (recommandé)

Pour les recharges **immédiates** (sans attendre le cycle mensuel cron) :

### 4.1 URL du webhook

L'endpoint `/oc_webhook` est implémenté dans UPassport ([`routers/finance.py`](../UPassport/routers/finance.py)).

> ⚠️ UPassport écoute en HTTPS sur le port **443** (via reverse proxy) ou **54321** en direct.
> Pour une station exposée sous un domaine, utiliser le port 443 sans numéro explicite.

Exemples :
```
# Via reverse proxy HTTPS (recommandé)
https://u.copylaradio.com/oc_webhook

# Direct (si port 54321 exposé)
https://votre-domaine:54321/oc_webhook
```

### 4.2 Configurer dans OC

1. Admin du collectif OC → section **Webhooks**
2. Cliquer **Ajouter un webhook** :
   - **URL** : `https://u.copylaradio.com/oc_webhook`  *(adapté à votre domaine)*
   - **Événement** : laisser sur **"tous les événements"** ou sélectionner `collective.transaction.created`
3. Enregistrer — OC enverra un ping de test immédiatement

> ✅ **Déjà configuré** pour `G1FabLab #monnaie-libre` sur `https://u.copylaradio.com/oc_webhook`

### 4.3 Fonctionnement du webhook

Le webhook reçoit un payload minimal (sans email ni tier détaillé). Il résout ces informations
via une requête GraphQL supplémentaire utilisant le Personal Token (`OCAPIKEY`) :

```
Webhook payload (slug, amount) → GraphQL OCAPIKEY → email + tier → UPLANET.official.sh
```

Le tier est résolu en matchant le montant avec les 5 dernières transactions du contributeur.
Le Personal Token doit donc être valide et avoir le scope `account` + `transactions`.

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
