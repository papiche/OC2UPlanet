# OC2UPlanet

Ce script Bash est conçu pour automatiser certaines tâches liées à la gestion des membres
et des transactions d'un compte sur OpenCollective.


## PREREQUIS

1. Créez un compte sur [Open Collective](https://opencollective.com)

`USLUG=$slug`

2. Créez un "token API" developpeur : xxxxxxxxxxxxxxxxxxxx

https://opencollective.com/dashboard/`$USLUG`/for-developers/personal-tokens/

3. Devenez administrateur "OCSLUG" : yyyyyyyyyy

Entité juridique qui possède le portefeuille "UNL"
qui pour tout CREDIT envoye une quantité équivalente de "Ẑen".

4. Installez [Astroport.ONE](https://github.com/papiche/Astroport.ONE) créez votre compte "Capitaine"


5. ForkUPlanetZERO depuis au moins 3 Stations


## CREATE `.env`


```
#######################################################################
## Open Collective API KEY
## https://docs.opencollective.com/help/contributing/development/api
#######################################################################
OCAPIKEY="xxxxxxxxxxxxxxxxxxxx"
OCSLUG="yyyyyyyyyy"
```

## RUN `./run.sh`


```
./run.sh
```

---


le principe de ce programme est de contrôler les versements constatés sur le collectif https://opencollective.com/made-in-zen
et de maintenir une équivalence en nombre de "tokens" Ẑen transférés entre le portefeuille maitre d'une instance UPlanet
 et les portefeuilles des membres ayant abondé à l'émission du "stable coin" du collectif

Ce script Bash est conçu pour automatiser certaines tâches liées à la gestion des membres et des transactions d'un compte sur OpenCollective. Voici une explication détaillée de chaque section du script :

### Initialisation

```bash
[[ ! -s .env ]] && echo "ERROR 0 missing .env" && exit 1
export $(xargs <.env)
mkdir -p ./data
```

- Vérifie si le fichier `.env` existe et n'est pas vide. Si ce n'est pas le cas, affiche une erreur et quitte le script.
- Charge les variables d'environnement depuis le fichier `.env`.
- Crée le répertoire `./data` s'il n'existe pas déjà.

### Nettoyage des anciennes données

```bash
find ./data -mtime +1 -type f -exec rm '{}' \;
```

- Supprime les fichiers dans le répertoire `./data` qui ont plus d'un jour.

### Définition des dates

```bash
today=$(date +"%Y-%m-%d")
yesterday=$(date -d 'yesterday' +'%Y-%m-%d')
start_of_week=$(date -d "last monday" +"%Y-%m-%d")
start_of_month=$(date -d "$(date +%Y-%m-01)" +"%Y-%m-%d")
start_of_year=$(date -d "$(date +%Y-01-01)" +"%Y-%m-%d")
```

- Définit les variables pour la date d'aujourd'hui, d'hier, le début de la semaine, du mois et de l'année.

### Récupération des emails des backers

```bash
[[ ! -s data/backers.json ]] \
&& curl -sX POST \
  -H "Content-Type: application/json" \
  -H "Personal-Token: ${OCAPIKEY}" \
  -d '{
    "query": "query account($slug: String) {
      account(slug: $slug) {
        name
        slug
        members(role: BACKER, limit: 100) {
          totalCount
          nodes {
            account {
              name
              slug
              emails
            }
          }
        }
      }
    }",
    "variables": {
      "slug": "'${OCSLUG}'"
    }
  }' \
  https://api.opencollective.com/graphql/v2 > data/backers.json
```

- Si le fichier `data/backers.json` n'existe pas ou est vide, envoie une requête POST à l'API GraphQL d'OpenCollective pour récupérer les informations des backers.
- Sauvegarde la réponse dans `data/backers.json`.

### Extraction des slugs et des emails

```bash
cat data/backers.json \
| jq -r '.data.account.members.nodes[] | "\(.account.slug):\(.account.emails[0])"' > data/slugemail.list
```

- Utilise `jq` pour extraire les slugs et les emails des backers depuis `data/backers.json` et les sauvegarde dans `data/slugemail.list`.

### Recherche des crédits d'hier

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Personal-Token: ${OCAPIKEY}" \
  -d '{
    "query": "query ($slug: String) {
      account(slug: $slug) {
        name
        slug
        transactions(limit: 10, type: CREDIT) {
          totalCount
          nodes {
            type
            fromAccount {
              name
              slug
              emails
            }
            amount {
              value
              currency
            }
            createdAt
          }
        }
      }
    }",
    "variables": {
      "slug": "'${OCSLUG}'"
    }
  }' \
  https://api.opencollective.com/graphql/v2 > data/tx.json
```

- Envoie une requête POST à l'API GraphQL d'OpenCollective pour récupérer les transactions de type "CREDIT" du compte spécifié.
- Sauvegarde la réponse dans `data/tx.json`.

### Filtrage des crédits d'hier

```bash
cat data/tx.json | jq --arg yesterday "$yesterday" '.data.account.transactions.nodes[] | select(.type == "CREDIT" and (.createdAt | startswith($yesterday)))' \
    > data/yesterday.credit.json
```

- Utilise `jq` pour filtrer les transactions de type "CREDIT" qui ont été créées hier et les sauvegarde dans `data/yesterday.credit.json`.

### Exemple de données de crédit d'hier

```json
{
  "type": "CREDIT",
  "fromAccount": {
    "name": "Astroport",
    "slug": "monnaie-libre",
    "emails": null
  },
  "amount": {
    "value": 259.53,
    "currency": "EUR"
  },
  "createdAt": "2023-02-06T10:15:28.042Z"
}
```

- Exemple de structure JSON pour une transaction de crédit d'hier.

### Affichage des crédits d'hier

```bash
cat data/yesterday.credit.json | jq -r
```

- Affiche le contenu de `data/yesterday.credit.json` de manière lisible.

### Commentaires supplémentaires

- Le script mentionne également la recherche d'un compte "UPlanet" par email et l'envoi de Zen en conséquence, mais cette partie n'est pas implémentée dans le code fourni.
- Il y a aussi une mention de contrôle de la concordance des transactions du portefeuille primal, mais cela n'est pas détaillé dans le script.

Ce script est utile pour automatiser la gestion des membres et des transactions sur OpenCollective, en particulier pour les tâches récurrentes comme la récupération des emails des backers et la vérification des transactions de crédit.

---
