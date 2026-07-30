#!/bin/bash
########################################################################
# Version: 0.5
# License: AGPL-3.0 (https://choosealicense.com/licenses/agpl-3.0/)
########################################################################
## OC 2 UPlanet
########################################################################
## Regularly make OpenCollective GraphQL API calls
## to fill-up members ZenCard with their donation 1€=1Ẑ (-OC%)
########################################################################
## INIT
ASTROPORT="${HOME}/.zen/Astroport.ONE"
MY_PATH="$(cd "$(dirname "$0")" && pwd)"
EMISSION_LOG="${MY_PATH}/data/emission.log"
mkdir -p "${MY_PATH}/data"
touch "$EMISSION_LOG"

# NOTE: .env is NO LONGER loaded locally. We rely on NOSTR/DID or explicit exports.

#######################################################################
## UPLANET SECRETS & ORIGIN DETECTION
#######################################################################
export UPLANETNAME="$(cat ~/.ipfs/swarm.key 2>/dev/null | tail -n 1)"

##############################################################################
## FALLBACK : DID NOSTR coopératif (kind 30800, chiffré avec $UPLANETNAME)
##############################################################################
COOP_CONFIG="${ASTROPORT}/tools/cooperative_config.sh"
JSON_OUTPUT=false
# Preliminary check for --json to silence init messages
for arg in "$@"; do [[ "$arg" == "--json" ]] && JSON_OUTPUT=true; done

########################################################################
## Protection contre les exécutions concurrentes (pattern oc_expense_monitor.sh:16-18,
## RUNTIME/ZEN.INVOICE.sh) — absente jusqu'ici. Un --sync complet spawn de nombreux
## sous-process (curl OC, strfry scan par transaction du rattrapage 12 mois) ; deux
## invocations simultanées (cron + manuel, ou double-clic sur oc_admin.html) se
## ralentissent mutuellement au lieu de s'isoler, plutôt qu'une des deux attendant
## simplement son tour. Couvre toutes les commandes (lecture ET --run/--manual) : même
## les vues --status/--sync spawnent assez de sous-process pour se gêner entre elles.
exec 200>"/tmp/oc2uplanet.lock"
if ! flock -n 200; then
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo '{"error":"oc2uplanet.sh déjà en cours d'"'"'exécution — réessayer dans quelques secondes"}'
    else
        echo "⏳ oc2uplanet.sh déjà en cours d'exécution — réessayer dans quelques secondes"
    fi
    exit 1
fi

if [[ -z "${OCAPIKEY}" && -f "${COOP_CONFIG}" ]]; then
    source "${COOP_CONFIG}" 2>/dev/null
    _coop_ocapikey=$(coop_config_get "OCAPIKEY" 2>/dev/null)
    [[ -n "${_coop_ocapikey}" ]] && export OCAPIKEY="${_coop_ocapikey}"
    [[ "$JSON_OUTPUT" == "false" && -n "${OCAPIKEY}" ]] && echo "✅ OCAPIKEY chargé depuis le DID NOSTR coopératif"
    _coop_ocslug=$(coop_config_get "OCSLUG" 2>/dev/null)
    [[ -n "${_coop_ocslug}" && -z "${OCSLUG}" ]] && export OCSLUG="${_coop_ocslug}"
    _coop_oc_api=$(coop_config_get "OC_API" 2>/dev/null)
    [[ -n "${_coop_oc_api}" && -z "${OC_API}" ]] && export OC_API="${_coop_oc_api}"

    ## Motifs de routage par tier (satellite/constellation/labo/cloud), configurables
    ## via `cooperative_config.sh coop_config_set TIER_SLUG_XXX "*motif1*,*motif2*"`.
    [[ -z "${TIER_SLUG_SATELLITE}" ]] && TIER_SLUG_SATELLITE=$(coop_config_get "TIER_SLUG_SATELLITE" 2>/dev/null)
    [[ -z "${TIER_SLUG_CONSTELLATION}" ]] && TIER_SLUG_CONSTELLATION=$(coop_config_get "TIER_SLUG_CONSTELLATION" 2>/dev/null)
    [[ -z "${TIER_SLUG_LABO}" ]] && TIER_SLUG_LABO=$(coop_config_get "TIER_SLUG_LABO" 2>/dev/null)
    [[ -z "${TIER_SLUG_CLOUD}" ]] && TIER_SLUG_CLOUD=$(coop_config_get "TIER_SLUG_CLOUD" 2>/dev/null)

    ## URLs de contribution OC par tier — utilisées dans le lien "reprendre votre cotisation"
    ## de la relance envoyée aux abonnés arrêtés (cf. _send_renewal_reminder).
    [[ -z "${OC_URL_SATELLITE}" ]] && OC_URL_SATELLITE=$(coop_config_get "OC_URL_SATELLITE" 2>/dev/null)
    [[ -z "${OC_URL_CONSTELLATION}" ]] && OC_URL_CONSTELLATION=$(coop_config_get "OC_URL_CONSTELLATION" 2>/dev/null)
    [[ -z "${OC_URL_CLOUD}" ]] && OC_URL_CLOUD=$(coop_config_get "OC_URL_CLOUD" 2>/dev/null)
    [[ -z "${OC_URL_MEMBRE}" ]] && OC_URL_MEMBRE=$(coop_config_get "OC_URL_MEMBRE" 2>/dev/null)
fi
[[ -z "${OC_API}" ]] && OC_API="https://api.opencollective.com/graphql/v2"

## Repli sur les motifs historiques si la config coopérative n'expose pas encore ces clés
## Motifs SANS `*` = ancrés comme segment entier par _tier_matches (voir sa doc) ;
## seuls les motifs composés (deux mots-clés requis, ex. parrainage+128) gardent des
## `*` explicites, car ils ont besoin du wildcard au milieu.
[[ -z "${TIER_SLUG_SATELLITE}" ]] && TIER_SLUG_SATELLITE="*parrainage*128*,extension-128,satellite,*love-box*claude*"
[[ -z "${TIER_SLUG_CONSTELLATION}" ]] && TIER_SLUG_CONSTELLATION="*parrainage*gpu*,module-gpu,constellation,*love-box*deluxe*,*love-box*gpu*"
[[ -z "${TIER_SLUG_LABO}" ]] && TIER_SLUG_LABO="infrastructure,labo,genereux-donateur,r-d,recherche"
[[ -z "${TIER_SLUG_CLOUD}" ]] && TIER_SLUG_CLOUD="membre-resident,cloud-usage,adhesion"

[[ -z "${OC_URL_SATELLITE}" ]] && OC_URL_SATELLITE="https://opencollective.com/monnaie-libre/contribute/parrainage-infrastructure-extension-128-go-98386"
[[ -z "${OC_URL_CONSTELLATION}" ]] && OC_URL_CONSTELLATION="https://opencollective.com/monnaie-libre/contribute/parrainage-infrastructure-module-gpu-1-24-98385"
[[ -z "${OC_URL_CLOUD}" ]] && OC_URL_CLOUD="https://opencollective.com/monnaie-libre/projects/coeurbox/contribute/cotisation-services-cloud-usage-98388"
[[ -z "${OC_URL_MEMBRE}" ]] && OC_URL_MEMBRE="https://opencollective.com/monnaie-libre/projects/coeurbox/contribute/membre-resident-soutien-mensuel-98389"

## Teste si $1 (tier_slug) correspond à l'une des globs de la liste $2 (séparées par des virgules)
## Teste si $1 (tier_slug) correspond à l'une des entrées de la liste $2 (séparées
## par des virgules). Une entrée contenant un `*` est utilisée telle quelle (glob
## explicite, substring libre — pour les motifs composés type "*parrainage*128*").
## Une entrée SANS `*` est ancrée comme un segment entier délimité par des tirets
## (exactement le slug, ou en tête/fin/milieu entre deux tirets) — évite qu'un mot
## nu comme "labo" ou "r-d" ne matche par accident une sous-chaîne d'un autre mot
## (ex. "colLABOratif", "suppoRTer-Don" — vérifié empiriquement, cf. audit).
_tier_matches() {
    local slug="$1" patterns="$2" IFS="," p
    for p in $patterns; do
        if [[ "$p" == *'*'* ]]; then
            [[ "$slug" == $p ]] && return 0
        else
            [[ "$slug" == "$p" || "$slug" == "$p"-* || "$slug" == *-"$p" || "$slug" == *-"$p"-* ]] && return 0
        fi
    done
    return 1
}

## Solde Ẑen d'un wallet MULTIPASS (via G1check.sh, cache ~/.zen/tmp/coucou/*.COINS)
_zen_balance() {
    local g1pub="$1"
    [[ -z "$g1pub" || ! -x "${ASTROPORT}/tools/G1check.sh" ]] && return
    "${ASTROPORT}/tools/G1check.sh" "${g1pub}:ZEN" 2>/dev/null | tail -n 1
}

## Préchargement des preuves d'émission NOSTR (kind 30851, #t=oc-emission) — UN SEUL
## `strfry scan` au lieu d'un scan PAR transaction. C'était le principal goulot de perf
## de --sync/--run en pratique (~63 comptes × plusieurs sous-process chacun, dont ce scan) :
## recoupement en mémoire (bash associatif) plutôt qu'un aller-retour au relay par ligne.
## À appeler UNE FOIS avant toute boucle qui traite les transactions (_sync_rows, --run).
## Définies ICI (tout en haut du script) et non près de _check_emission_nostr plus bas :
## show_status/show_sync (qui appellent _sync_rows) sont dispatchées AVANT que le script
## n'atteigne la zone où vivait _check_emission_nostr — une définition plus bas serait
## encore non résolue au moment de l'appel (bash exécute top-to-bottom, une fonction
## n'existe qu'une fois la ligne `nom() { ... }` réellement atteinte).
declare -A EMITTED_STATUS=()
_prefetch_emission_status() {
    declare -gA EMITTED_STATUS=()
    [[ -x "$HOME/.zen/strfry/strfry" ]] || return 0
    local d s
    while IFS=$'\t' read -r d s; do
        [[ -n "$d" ]] && EMITTED_STATUS["$d"]="$s"
    done < <(cd "$HOME/.zen/strfry" && ./strfry scan '{"kinds":[30851],"#t":["oc-emission"]}' 2>/dev/null \
        | jq -r '[(.tags[]|select(.[0]=="d")|.[1]), ((.tags[]|select(.[0]=="s")|.[1])//"")] | @tsv' 2>/dev/null)
}

## Préchargement des chemins G1PUBNOSTR du swarm — UN SEUL `find` au lieu d'un `find`
## (parcours de tout l'arbre swarm) par transaction dont le MULTIPASS n'est pas local.
declare -A SWARM_G1PUBNOSTR=()
_prefetch_swarm_g1pubnostr() {
    declare -gA SWARM_G1PUBNOSTR=()
    local f email
    while IFS= read -r f; do
        email=$(basename "$(dirname "$f")")
        SWARM_G1PUBNOSTR["$email"]="$f"
    done < <(find ~/.zen/tmp/swarm -name "G1PUBNOSTR" 2>/dev/null)
}

## Station variables (CAPTAINEMAIL, uSPOT, myDOMAIN, myIPFS…)
[[ -z "$myDOMAIN" && -f "${ASTROPORT}/tools/my.sh" ]] && source "${ASTROPORT}/tools/my.sh" 2>/dev/null

INVITATION_LOG="${MY_PATH}/data/invitation.log"
touch "$INVITATION_LOG"
## Email du capitaine (destinataire des tiers labo/R&D)
CAPTAIN_TARGET="${CAPTAINEMAIL:-$(cat ~/.zen/game/players/.current/.player 2>/dev/null)}"

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Sans option : affiche une vue synthétique (comme --status). AUCUNE émission Ẑen."
    echo ""
    echo "Options en lecture seule (aucune émission Ẑen) :"
    echo "  --sync      Détail par compte (fenêtre de rattrapage 12 mois) : montant, tier, MULTIPASS, statut émission"
    echo "  --status    Résumé du mois courant + synchro OK/FAIL/pending sur 12 mois [= défaut]"
    echo "  --scan      List all backers and their contributions"
    echo "  --ranking   Rank backers by total contribution + active status"
    echo "  --alerts    Identify stopped or changed subscriptions"
    echo "  --history   Show the last processed transactions"
    echo ""
    echo "Options d'exécution (ÉMETTENT des Ẑen) :"
    echo "  --run       Traite la fenêtre de rattrapage (12 derniers mois) et émet les Ẑen (usage cron)"
    echo "  --manual    Comme --run, en mode interactif validation/édition transaction par transaction"
    echo ""
    echo "  --json      Modify output format to JSON (peut être placé n'importe où)"
    echo "  --help      Show this help message"
    echo ""
    echo "Rattrapage : --run/--sync/--status traitent les 12 derniers mois (pas seulement le mois"
    echo "courant), pour rattraper les dons dont le MULTIPASS n'a été créé que bien après"
    echo "l'inscription OC. L'idempotence (kind 30851 + emission.log) garantit qu'un don déjà"
    echo "émis n'est jamais rejoué. Pour les dons plus anciens qu'un an, traiter manuellement."
    echo ""
    echo "Exemples :"
    echo "  $0                     # vue synthétique, sans risque"
    echo "  $0 --sync              # voir où en est chaque compte (12 derniers mois)"
    echo "  $0 --json --sync       # idem, en JSON"
    echo "  $0 --run               # déclenche réellement l'émission Ẑen (12 derniers mois)"
    echo ""
}

show_history() {
    echo "=== Emission History (last 20 — kind 30851) ==="
    if [[ -x "$HOME/.zen/strfry/strfry" ]]; then
        (cd "$HOME/.zen/strfry" && ./strfry scan '{"kinds":[30851],"#t":["oc-emission"],"limit":20}' 2>/dev/null) \
        | jq -r '
            . as $e |
            ($e.tags | map(select(.[0]=="email"))  | first | .[1] // "?") as $email  |
            ($e.tags | map(select(.[0]=="amount"))  | first | .[1] // "?") as $amount |
            ($e.tags | map(select(.[0]=="tier"))    | first | .[1] // "?") as $tier   |
            ($e.tags | map(select(.[0]=="s"))       | first | .[1] // "?") as $status |
            "Email: \($email) | Amount: \($amount) | Tier: \($tier) | Status: \($status)"
        ' 2>/dev/null \
        || { echo "(strfry indisponible — fallback emission.log)"; tail -n 20 "$EMISSION_LOG" 2>/dev/null; }
    else
        [[ -f "$EMISSION_LOG" ]] && tail -n 20 "$EMISSION_LOG" || echo "No history found."
    fi
}

show_status() {
    fetch_oc_data || return 1
    local total_backers=$(jq -r ".data.account.members.totalCount // 0" ${MY_PATH}/data/backers.json 2>/dev/null)
    local count=$(jq -s "length" ${MY_PATH}/data/current_month.credit.json 2>/dev/null)
    local total_amount=$(jq -s "[.[] | .amount.value] | add // 0" ${MY_PATH}/data/current_month.credit.json 2>/dev/null)
    local processed=0
    if [[ -x "$HOME/.zen/strfry/strfry" ]]; then
        processed=$(cd "$HOME/.zen/strfry" && ./strfry scan '{"kinds":[30851],"#s":["OK"]}' 2>/dev/null | grep -c '"id"') || true
    fi
    if [[ "${processed:-0}" -eq 0 ]]; then
        processed=$(grep -c ":OK$" "$EMISSION_LOG" 2>/dev/null)
        processed="${processed:-0}"
    fi

    ## Synchro sur la fenêtre de rattrapage (catchup.credit.json, 12 derniers mois) : statut réel par compte
    ## (émission Ẑen + MULTIPASS), y compris les dons anciens en attente de rattrapage.
    local rows ok fail pending mp_missing pending_active pending_stopped blocked_no_email
    rows=$(_sync_rows | jq -s .)
    ok=$(echo "$rows" | jq '[.[] | select(.emission_status=="ok")] | length')
    fail=$(echo "$rows" | jq '[.[] | select(.emission_status=="fail")] | length')
    pending=$(echo "$rows" | jq '[.[] | select(.emission_status=="pending")] | length')
    mp_missing=$(echo "$rows" | jq '[.[] | select(.multipass_status!="local" and .multipass_status!="swarm")] | length')
    pending_active=$(echo "$rows" | jq '[.[] | select(.emission_status=="pending" and .subscriber_status=="active")] | length')
    pending_stopped=$(echo "$rows" | jq '[.[] | select(.emission_status=="pending" and .subscriber_status=="stopped")] | length')
    blocked_no_email=$(echo "$rows" | jq '[.[] | select(.multipass_status=="blocked")] | length')

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        jq -n --arg tb "$total_backers" --arg cnt "$count" --arg ta "$total_amount" --arg pr "$processed" \
            --arg ok "$ok" --arg fail "$fail" --arg pending "$pending" --arg mp_missing "$mp_missing" \
            --arg pa "$pending_active" --arg ps "$pending_stopped" --arg bne "$blocked_no_email" \
            '{total_backers: $tb, current_month_tx: $cnt, current_month_total: $ta, processed_ok: $pr,
              sync_status: {ok: $ok, fail: $fail, pending: $pending, multipass_missing: $mp_missing,
                            pending_active_subscribers: $pa, pending_stopped_subscribers: $ps,
                            blocked_no_email: $bne}}'
    else
        echo "=== Current Status ==="
        echo "Total Backers: $total_backers"
        echo "Current Month Transactions: $count"
        echo "Current Month Total: $total_amount EUR"
        echo "Total Transactions Processed (OK): $processed"
        echo "--- Synchro €→Ẑen (rattrapage 12 derniers mois) ---"
        echo "✅ Émis: $ok | ❌ Échec: $fail | ⏳ En attente: $pending | MULTIPASS manquant: $mp_missing"
        echo "   dont en attente : 🟢 $pending_active abonné(s) actif(s) ce mois-ci | 🔴 $pending_stopped abonné(s) arrêté(s)"
        [[ "$blocked_no_email" -gt 0 ]] && echo "🚫 $blocked_no_email don(s) sans email exploitable — jamais traités par --run, à vérifier manuellement (--sync)"
        [[ "$pending" -gt 0 || "$fail" -gt 0 || "$mp_missing" -gt 0 ]] && echo "→ Détail : ./oc2uplanet.sh --sync"
    fi
}

fetch_oc_data() {
    [[ -z "${OCAPIKEY}" ]] && echo "ERROR 0 : OCAPIKEY manquant" && return 1
    [[ "$JSON_OUTPUT" == "false" ]] && echo "Fetching data from OpenCollective for slug: ${OCSLUG}..."
    
    # Backers list — --max-time : sans lui un OC API lent/rate-limité bloque tout
    # invocateur (cron mensuel, appel manuel, route UPassport /api/oc_admin/contributions)
    # indéfiniment, sans aucun message d'erreur pour l'expliquer.
    curl -sX POST --max-time 30 -H "Content-Type: application/json" -H "Personal-Token: ${OCAPIKEY}" \
        -d "{\"query\": \"query account(\$slug: String) { account(slug: \$slug) { name slug members(role: BACKER, limit: 200) { totalCount nodes { account { name slug emails } } } } }\", \"variables\": {\"slug\": \"${OCSLUG}\"}}" \
        "${OC_API}" > ${MY_PATH}/data/backers.json

    # Slug email map
    jq -r '.data.account.members.nodes[] | "\(.account.slug):\(.account.emails[0])"' ${MY_PATH}/data/backers.json > ${MY_PATH}/data/slugemail.list
    cat ${MY_PATH}/data/slugemail.list | awk -F: '{print "{\"" $1 "\": \"" $2 "\"}"}' | jq -s 'add' > ${MY_PATH}/data/slug_email_map.json

    # Transactions (last 1000) — includeChildrenTransactions: true est INDISPENSABLE
    # pour voir les contributions aux Projects enfants (ex: atom4love, coeurbox, stiits
    # sous monnaie-libre) : sans ce flag, Account.transactions ne retourne QUE les
    # transactions dont toAccount == ce slug précis, jamais celles des projets enfants
    # (vérifié empiriquement : 480 tx sans le flag, 484 avec — 4 tx enfants invisibles).
    curl -sX POST --max-time 30 -H "Content-Type: application/json" -H "Personal-Token: ${OCAPIKEY}" \
        -d "{\"query\": \"query (\$slug: String) { account(slug: \$slug) { name slug transactions(limit: 1000, type: CREDIT, includeChildrenTransactions: true) { totalCount nodes { type fromAccount { name slug emails } toAccount { slug name } amount { value currency } order { tier { slug name } } createdAt } } } }\", \"variables\": {\"slug\": \"${OCSLUG}\"}}" \
        "${OC_API}" > ${MY_PATH}/data/tx.json

    ## Vérifie que l'API a bien répondu (pas une erreur GraphQL / réponse vide / API
    ## down) — sinon un `--run` planifié peut "réussir" (exit 0, marqueur mensuel posé
    ## par 20h12.process.sh) sans avoir traité la moindre transaction, silencieusement.
    if ! jq -e '.data.account' "${MY_PATH}/data/tx.json" >/dev/null 2>&1; then
        local _api_err
        _api_err=$(jq -r '.errors[0].message // "réponse illisible"' "${MY_PATH}/data/tx.json" 2>/dev/null)
        echo "ERROR 1 : réponse OpenCollective invalide — ${_api_err}" >&2
        return 1
    fi

    # Time splits
    local start_of_month=$(date -d "$(date +%Y-%m-01)" +"%Y-%m-%d")
    local start_of_last_month=$(date -d "$(date +%Y-%m-01) -1 month" +"%Y-%m-%d")
    local end_of_last_month=$(date -d "$(date +%Y-%m-01) -1 day" +"%Y-%m-%d")
    local start_of_catchup=$(date -d "1 year ago" +"%Y-%m-%d")

    jq -c --arg som "$start_of_month" '.data.account.transactions.nodes[] | select(.type == "CREDIT" and .createdAt >= $som)' ${MY_PATH}/data/tx.json > ${MY_PATH}/data/current_month.credit.json
    jq -c --arg solm "$start_of_last_month" --arg eolm "$end_of_last_month" '.data.account.transactions.nodes[] | select(.type == "CREDIT" and (.createdAt >= $solm and .createdAt <= $eolm))' ${MY_PATH}/data/tx.json > ${MY_PATH}/data/last_month.credit.json

    ## Fenêtre de rattrapage (12 derniers mois, PAS tout l'historique) — sert au
    ## traitement/synchro réels. Contrairement à current_month.credit.json (info
    ## mensuelle), ce fichier permet de rattraper les dons dont le MULTIPASS n'a été
    ## créé que bien après l'inscription OC : l'idempotence (_check_emission_nostr /
    ## kind 30851) garantit qu'un don déjà émis n'est jamais rejoué. La fenêtre est
    ## volontairement bornée à 1 an (et non tout l'historique depuis la création du
    ## collectif) pour laisser un contrôle humain sur les dons plus anciens, dont le
    ## traitement éventuel (hors pipeline) ne peut pas être vérifié automatiquement.
    jq -c --arg soc "$start_of_catchup" '.data.account.transactions.nodes[] | select(.type == "CREDIT" and .createdAt >= $soc)' ${MY_PATH}/data/tx.json > ${MY_PATH}/data/catchup.credit.json
}

show_scan() {
    fetch_oc_data || return 1
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        # Join with email map in JSON
        jq --slurpfile map ${MY_PATH}/data/slug_email_map.json '
            .data.account.transactions.nodes | map(. + {email: ($map[0][.fromAccount.slug] // .fromAccount.emails[0] // "-")})
        ' ${MY_PATH}/data/tx.json
    else
        echo ""
        echo "=== OpenCollective Scan : ${OCSLUG} (+ projets enfants) ==="
        printf "%-20s | %-15s | %-25s | %-10s | %-15s | %-12s | %s\n" "Name" "Slug" "Email" "Amount" "Tier" "Project" "Date"
        echo "----------------------------------------------------------------------------------------------------------------------------------------"
        jq -r '.data.account.transactions.nodes[] | "\(.fromAccount.name // "-"):\(.fromAccount.slug):\(.fromAccount.emails[0] // "-"):\(.amount.value) \(.amount.currency):\(.order.tier.name // "-"):\(.toAccount.slug // "-"):\(.createdAt)"' ${MY_PATH}/data/tx.json | while IFS=: read -r name slug email amount tier project date; do
            [[ "$email" == "-" ]] && email=$(jq -r --arg s "$slug" '.[$s] // "-"' ${MY_PATH}/data/slug_email_map.json 2>/dev/null)
            printf "%-20.20s | %-15.15s | %-25.25s | %-10s | %-15.15s | %-12.12s | %s\n" "$name" "$slug" "$email" "$amount" "$tier" "$project" "$date"
        done
    fi
}

show_ranking() {
    fetch_oc_data || return 1
    # Identify slugs that paid this month
    local active_slugs=$(jq -r '.fromAccount.slug' ${MY_PATH}/data/current_month.credit.json | sort -u)
    
    local rank_cmd='
        .data.account.transactions.nodes 
        | group_by(.fromAccount.slug) 
        | map({
            slug: .[0].fromAccount.slug, 
            name: (.[0].fromAccount.name // .[0].fromAccount.slug), 
            total: (map(.amount.value) | add), 
            count: length, 
            currency: .[0].amount.currency,
            email: ""
          }) 
        | sort_by(-.total)'

    local result_json=$(jq "$rank_cmd" ${MY_PATH}/data/tx.json)
    
    # Enrich with email and active status
    local enriched=$(echo "$result_json" | jq --argjson active "$(echo "$active_slugs" | jq -R . | jq -s .)" --slurpfile map ${MY_PATH}/data/slug_email_map.json '
        map(. + {
            email: ($map[0][.slug] // "-"),
            status: (if (.slug as $s | $active | index($s)) then "ACTIVE" else "INACTIVE" end)
        })
    ')

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo "$enriched"
    else
        echo "=== Backers Ranking (based on last 100 transactions) ==="
        printf "%-25s | %-25s | %-10s | %-8s | %-8s\n" "Backer Name" "Email" "Total" "Status" "Count"
        echo "---------------------------------------------------------------------------------------------------"
        echo "$enriched" | jq -r '.[] | "\(.name):\(.email):\(.total) \(.currency):\(.status):\(.count)"' | while IFS=: read -r name email total status count; do
            printf "%-25.25s | %-25.25s | %-10s | %-8s | %-8s\n" "$name" "$email" "$total" "$status" "$count"
        done
    fi
}

show_alerts() {
    fetch_oc_data || return 1
    local slugs_last=$(jq -r '.fromAccount.slug' ${MY_PATH}/data/last_month.credit.json | sort -u)
    local slugs_curr=$(jq -r '.fromAccount.slug' ${MY_PATH}/data/current_month.credit.json | sort -u)
    
    if [[ "$JSON_OUTPUT" == "true" ]]; then
        local stopped=$(comm -23 <(echo "$slugs_last") <(echo "$slugs_curr") | while read s; do
            jq -n --arg slug "$s" --arg email "$(jq -r --arg s "$s" '.[$s] // "-"' ${MY_PATH}/data/slug_email_map.json)" \
                  --arg name "$(jq -r --arg s "$s" 'select(.fromAccount.slug == $s).fromAccount.name' ${MY_PATH}/data/last_month.credit.json | head -1)" \
                  '{slug: $slug, name: $name, email: $email, status: "STOPPED"}'
        done | jq -s .)
        
        local common=$(comm -12 <(echo "$slugs_last") <(echo "$slugs_curr"))
        local changed="[]"
        for s in $common; do
            local val_last=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" ${MY_PATH}/data/last_month.credit.json)
            local val_curr=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" ${MY_PATH}/data/current_month.credit.json)
            if (( $(echo "$val_last != $val_curr" | bc -l) )); then
                changed=$(echo "$changed" | jq --arg slug "$s" --arg last "$val_last" --arg curr "$val_curr" \
                    --arg email "$(jq -r --arg s "$s" '.[$s] // "-"' ${MY_PATH}/data/slug_email_map.json)" \
                    '. += [{slug: $slug, email: $email, last_month: $last, current_month: $curr, status: "CHANGED"}]')
            fi
        done
        jq -n --argjson s "$stopped" --argjson c "$changed" '{stopped: $s, changed: $c}'
    else
        echo "=== Subscription Alerts (Current Month vs Last Month) ==="
        echo "--- STOPPED (Paid last month, not yet this month) ---"
        comm -23 <(echo "$slugs_last") <(echo "$slugs_curr") | while read s; do
            local name=$(jq -r --arg s "$s" 'select(.fromAccount.slug == $s).fromAccount.name' ${MY_PATH}/data/last_month.credit.json | head -1)
            local email=$(jq -r --arg s "$s" '.[$s] // "-"' ${MY_PATH}/data/slug_email_map.json)
            echo "❌ $s ($name) - Email: $email"
        done
        echo ""
        echo "--- CHANGED (Amount differs from last month) ---"
        local common=$(comm -12 <(echo "$slugs_last") <(echo "$slugs_curr"))
        for s in $common; do
            local val_last=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" ${MY_PATH}/data/last_month.credit.json)
            local val_curr=$(jq -s "map(select(.fromAccount.slug == \"$s\").amount.value) | add" ${MY_PATH}/data/current_month.credit.json)
            if (( $(echo "$val_last != $val_curr" | bc -l) )); then
                local name=$(jq -r --arg s "$s" 'select(.fromAccount.slug == $s).fromAccount.name' ${MY_PATH}/data/current_month.credit.json | head -1)
                local email=$(jq -r --arg s "$s" '.[$s] // "-"' ${MY_PATH}/data/slug_email_map.json)
                echo "⚠️  $s ($name): ${val_last}€ -> ${val_curr}€ - Email: $email"
            fi
        done
    fi
}

## Croise catchup.credit.json (rattrapage 12 derniers mois) avec l'état réel de
## chaque compte : présence MULTIPASS (local/swarm/invité/absent) + statut émission
## Ẑen (OK/FAIL/pending). Émet un objet JSON par ligne (à consommer avec `jq -s .`).
_sync_rows() {
    ## Extraction via tx_fields.py (NUL-separe) plutot que jq @tsv + `read` :
    ## bash `read` avec IFS=tab collabe silencieusement les champs vides consecutifs
    ## (ex: email manquant pour un compte OC anonyme), decalant tous les champs
    ## suivants -- verifie empiriquement sur les comptes "incognito-*" et les
    ## transactions de projets enfants (emails: null). NUL ne peut jamais apparaitre
    ## dans une chaine JSON, donc `readarray -d ''` est fiable a 100%.
    local -a _fields
    readarray -d '' -t _fields < <(python3 "${MY_PATH}/tx_fields.py" "${MY_PATH}/data/catchup.credit.json" 2>/dev/null)

    ## Préchargement (1 seul scan/find pour TOUTES les lignes, cf. définitions ci-dessus) —
    ## remplace ce qui était, avant correctif, un `strfry scan` + un `find` PAR ligne.
    _prefetch_emission_status
    _prefetch_swarm_g1pubnostr

    ## Comptes ayant contribué CE mois-ci (cotisation en cours) — sert à distinguer
    ## les dons en attente d'un abonné toujours actif de ceux d'un abonné qui a arrêté.
    local -A _active_slugs=()
    local _s
    while IFS= read -r _s; do
        [[ -n "$_s" ]] && _active_slugs["$_s"]=1
    done < <(jq -r '.fromAccount.slug' "${MY_PATH}/data/current_month.credit.json" 2>/dev/null | sort -u)

    local _i
    for ((_i = 0; _i < ${#_fields[@]}; _i += 6)); do
        local slug="${_fields[_i]}" raw_email="${_fields[_i+1]}" amount="${_fields[_i+2]}" \
              created_at="${_fields[_i+3]}" tier_slug="${_fields[_i+4]}"
        local sub_status="stopped" sub_label="🔴 arrêté"
        [[ -n "${_active_slugs[$slug]:-}" ]] && sub_status="active" && sub_label="🟢 actif"
        ## Résolution de l'email : si introuvable (compte OC anonyme, projet enfant,
        ## absent de slug_email_map.json), le don est structurellement bloqué — aucun
        ## moyen de contacter ou créditer qui que ce soit. On le marque distinctement
        ## (mp_status="blocked") plutôt que de fabriquer un faux email=$slug qui le
        ## ferait ressembler à un "en attente" ordinaire (cf. audit : ces dons étaient
        ## silencieusement abandonnés par la boucle --run sans jamais être signalés ici).
        local email="$raw_email" no_email=false
        [[ -z "$email" || "$email" == "null" ]] && email=$(jq -r --arg s "$slug" '.[$s] // empty' "${MY_PATH}/data/slug_email_map.json" 2>/dev/null)
        if [[ -z "$email" || "$email" == "null" ]]; then
            no_email=true
            email="$slug"
        fi

        local _effective_email="$email"
        local mp_status mp_label mp_g1pub_file=""
        if [[ "$no_email" == "true" ]]; then
            mp_status="blocked"; mp_label="🚫 email introuvable"
        else
            _tier_matches "$tier_slug" "$TIER_SLUG_LABO" && _effective_email="${CAPTAIN_TARGET:-support@qo-op.com}"

            mp_status="not_invited"; mp_label="❌ non invité"
            if [[ -f "$HOME/.zen/game/nostr/${_effective_email}/G1PUBNOSTR" ]]; then
                mp_status="local"; mp_label="✅ local"
                mp_g1pub_file="$HOME/.zen/game/nostr/${_effective_email}/G1PUBNOSTR"
            else
                local _swarm_hit="${SWARM_G1PUBNOSTR[$_effective_email]:-}"
                if [[ -n "$_swarm_hit" ]]; then
                    mp_status="swarm"; mp_label="✅ swarm"
                    mp_g1pub_file="$_swarm_hit"
                else
                    local last_invite
                    last_invite=$(grep -F "${_effective_email}:" "$INVITATION_LOG" 2>/dev/null | grep ":INVITED:" | tail -1 | awk -F: '{print $NF}')
                    if [[ -n "$last_invite" ]]; then
                        mp_status="invited"; mp_label="📧 invité $(date -d "@$last_invite" +%d/%m 2>/dev/null)"
                    fi
                fi
            fi
        fi

        local wallet_zen=""
        if [[ -n "$mp_g1pub_file" ]]; then
            local _g1pub
            _g1pub=$(cat "$mp_g1pub_file" 2>/dev/null)
            [[ -n "$_g1pub" ]] && wallet_zen=$(_zen_balance "$_g1pub")
        fi

        local tx_id="${raw_email}:${amount}:${created_at}"
        local _rec_s="${EMITTED_STATUS[oc-emission-${tx_id}]:-}"
        [[ -z "$_rec_s" ]] && _rec_s=$(grep -F "$tx_id" "$EMISSION_LOG" 2>/dev/null | tail -1 | awk -F: '{print $NF}')
        local emis_status="pending" emis_label="⏳ en attente"
        case "$_rec_s" in
            OK) emis_status="ok"; emis_label="✅ OK" ;;
            FAIL) emis_status="fail"; emis_label="❌ FAIL" ;;
        esac

        jq -cn --arg email "$email" --arg amount "$amount" --arg tier "${tier_slug:-standard}" \
            --arg mp_status "$mp_status" --arg mp_label "$mp_label" \
            --arg emis_status "$emis_status" --arg emis_label "$emis_label" \
            --arg wallet_zen "$wallet_zen" \
            --arg sub_status "$sub_status" --arg sub_label "$sub_label" \
            '{email:$email, amount:($amount|tonumber), tier:$tier,
              multipass_status:$mp_status, multipass_label:$mp_label,
              wallet_zen:(if $wallet_zen == "" then null else ($wallet_zen|tonumber) end),
              subscriber_status:$sub_status, subscriber_label:$sub_label,
              emission_status:$emis_status, emission_label:$emis_label}'
    done
}

show_sync() {
    fetch_oc_data || return 1
    local rows
    rows=$(_sync_rows | jq -s .)

    if [[ "$JSON_OUTPUT" == "true" ]]; then
        echo "$rows"
        return 0
    fi

    echo ""
    echo "=== Synchro €→Ẑen : ${OCSLUG} (rattrapage 12 derniers mois) ==="
    printf "%-25s | %-10s | %-25s | %-10s | %-14s | %-10s | %s\n" "Email" "Montant" "Tier" "Abonnement" "MULTIPASS" "Solde Ẑen" "Émission"
    echo "----------------------------------------------------------------------------------------------------------------------------"
    ## Seules les lignes non soldées sont affichées (pending/fail) — les dons déjà émis
    ## (✅ OK) sont comptabilisés dans le total mais masqués pour éviter un mur de lignes.
    echo "$rows" | jq -r '.[] | select(.emission_status != "ok") | "\(.email):\(.amount)€:\(.tier):\(.subscriber_label):\(.multipass_label):\(.wallet_zen // "-"):\(.emission_label)"' | while IFS=: read -r email amount tier sub mp zen emis; do
        printf "%-25.25s | %-10s | %-25.25s | %-10s | %-14s | %-10s | %s\n" "$email" "$amount" "$tier" "$sub" "$mp" "$zen" "$emis"
    done
    echo ""
    local total ok fail pending pending_active pending_stopped blocked_no_email
    total=$(echo "$rows" | jq 'length')
    ok=$(echo "$rows" | jq '[.[] | select(.emission_status=="ok")] | length')
    fail=$(echo "$rows" | jq '[.[] | select(.emission_status=="fail")] | length')
    pending=$(echo "$rows" | jq '[.[] | select(.emission_status=="pending")] | length')
    pending_active=$(echo "$rows" | jq '[.[] | select(.emission_status=="pending" and .subscriber_status=="active")] | length')
    pending_stopped=$(echo "$rows" | jq '[.[] | select(.emission_status=="pending" and .subscriber_status=="stopped")] | length')
    blocked_no_email=$(echo "$rows" | jq '[.[] | select(.multipass_status=="blocked")] | length')
    echo "Total: $total | ✅ Émis: $ok (masqués ci-dessus) | ❌ Échec: $fail | ⏳ En attente: $pending (🟢 actifs: $pending_active | 🔴 arrêtés: $pending_stopped)"
    [[ "$blocked_no_email" -gt 0 ]] && echo "🚫 Bloqués (email introuvable, jamais traités par --run) : $blocked_no_email — vérifier data/slug_email_map.json"
}

## Argument parsing
ACTION=""
RUN_MODE=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --manual) MANUAL_MODE=true; RUN_MODE=true ;;
        --run) RUN_MODE=true ;;
        --scan) ACTION="scan" ;;
        --ranking) ACTION="ranking" ;;
        --alerts) ACTION="alerts" ;;
        --status) ACTION="status" ;;
        --sync) ACTION="sync" ;;
        --history) ACTION="history" ;;
        --json) JSON_OUTPUT=true ;;
        --help) show_help; exit 0 ;;
        *) [[ "$JSON_OUTPUT" == "false" ]] && echo "Unknown parameter: $1" && show_help; exit 1 ;;
    esac
    shift
done

if [[ -n "$ACTION" ]]; then
    case "$ACTION" in
        scan) show_scan ;;
        ranking) show_ranking ;;
        alerts) show_alerts ;;
        status) show_status ;;
        sync) show_sync ;;
        history) show_history ;;
    esac
    exit 0
fi

## Sans --run (ni --manual) : vue synthétique par défaut, aucune émission Ẑen déclenchée.
if [[ "$RUN_MODE" != "true" ]]; then
    show_status
    [[ "$JSON_OUTPUT" == "false" ]] && echo "" && echo "→ Pour émettre réellement les Ẑen de ce mois : ./oc2uplanet.sh --run"
    exit 0
fi

[[ "$JSON_OUTPUT" == "false" ]] && echo "MONITORING ${OCSLUG} | Station: ${UPLANETNAME:0:8}..."

#######################################################################
## CHECKS
#######################################################################
[[ -z $UPLANETNAME ]] && echo "MISSING PRIVATE SWARM ACTIVATED ASTROPORT STATION" && exit 1
[[ "${PAF}" == "0" ]] && echo "PAF=0 — station sandbox, émission ẐEN désactivée." && exit 0
find ./data -mtime +1 -type f -exec rm '{}' \; 2>/dev/null
## Échec explicite (exit 1) si la récupération des données échoue — sans ça, un
## `--run` planifié peut se déclarer "réussi" et poser le marqueur mensuel de
## 20h12.process.sh sans avoir traité la moindre transaction.
if [[ ! -s ${MY_PATH}/data/catchup.credit.json ]]; then
    fetch_oc_data || { echo "❌ Échec de récupération OpenCollective — abandon, aucune émission tentée." >&2; exit 1; }
fi

########################################################################
## EMISSION ẐEN
########################################################################
if [[ -f "$EMISSION_LOG" ]]; then
    cutoff_ts=$(date -d "90 days ago" +%s 2>/dev/null)
    if [[ -n "$cutoff_ts" ]]; then
        grep -E ':[0-9]{10}:(OK|FAIL)$' "$EMISSION_LOG" \
        | awk -F: -v cut="$cutoff_ts" '$(NF-1)+0 >= cut' \
        > "${EMISSION_LOG}.tmp" && mv "${EMISSION_LOG}.tmp" "$EMISSION_LOG"
    fi
fi

########################################################################
## NOSTR kind 30851 — Preuve de paiement ẐEN (source de vérité)
########################################################################

## Chargement lazy de la clé NOSTR du Capitaine
CAPTAIN_NOSTR_KEYFILE=""
trap '[[ -n "$CAPTAIN_NOSTR_KEYFILE" ]] && rm -f "$CAPTAIN_NOSTR_KEYFILE"' EXIT INT TERM

_init_captain_nostr_key() {
    [[ -n "$CAPTAIN_NOSTR_KEYFILE" ]] && return 0
    local _secret="$HOME/.zen/game/nostr/${CAPTAIN_TARGET}/.secret.nostr"
    [[ ! -s "$_secret" ]] && return 1
    local _raw _nsec
    _raw=$(cat "$_secret" 2>/dev/null)
    _nsec=$(echo "$_raw" | grep -oP 'NSEC=\K[^;]+' || true)
    [[ -z "$_nsec" || "$_nsec" != nsec1* ]] && _nsec=$(echo "$_raw" | grep -oP 'nsec1[a-z0-9]+' || true)
    [[ "$_nsec" != nsec1* ]] && return 1
    CAPTAIN_NOSTR_KEYFILE=$(mktemp /tmp/oc_nostr_key_XXXXXX)
    echo "NSEC=$_nsec;" > "$CAPTAIN_NOSTR_KEYFILE"
}

## Vérification idempotence via relay local (kind 30851) avec fallback emission.log.
## Chemin rapide : consulte EMITTED_STATUS (préchargé par _prefetch_emission_status) —
## O(1), pas de sous-process. Repli sur un scan ciblé si le préchargement n'a pas eu
## lieu (appel isolé de cette fonction hors _sync_rows()/--run), pour rester utilisable
## seule sans régression de comportement.
_check_emission_nostr() {
    local tx_d="oc-emission-${1}"
    [[ -n "${EMITTED_STATUS[$tx_d]+_}" ]] && return 0
    local found=0
    if [[ -x "$HOME/.zen/strfry/strfry" ]]; then
        found=$(cd "$HOME/.zen/strfry" && \
            ./strfry scan "{\"kinds\":[30851],\"#d\":[\"${tx_d}\"]}" 2>/dev/null \
            | grep -c '"id"') || found=0
    fi
    [[ "${found:-0}" -gt 0 ]] && return 0
    grep -qF "$1" "$EMISSION_LOG" 2>/dev/null
}

## Publication preuve de paiement (kind 30851) + écriture audit trail emission.log
_publish_emission_proof() {
    local email="$1" amount="$2" tier_slug="$3" raw_email="${4:-$1}" created_at="$5" status="${6:-OK}"
    local tx_d="oc-emission-${raw_email}:${amount}:${created_at}"

    ## Écriture audit trail local (fallback + migration)
    echo "${raw_email}:${amount}:${created_at}:${amount}:${tier_slug:-unknown}:$(date +%s):${status}" >> "$EMISSION_LOG"

    _init_captain_nostr_key || return 1
    [[ -z "${UPLANETG1PUB:-}" ]] && return 1

    local content_json
    content_json=$(jq -cn \
        --arg email "$email" \
        --arg raw_email "$raw_email" \
        --arg amount "$amount" \
        --arg tier_slug "${tier_slug:-unknown}" \
        --arg oc_created_at "$created_at" \
        --arg status "$status" \
        --arg generated_at "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
        --arg uplanet "${UPLANETG1PUB}" \
        '{email:$email,raw_email:$raw_email,amount:$amount,tier_slug:$tier_slug,
          oc_created_at:$oc_created_at,status:$status,generated_at:$generated_at,
          uplanet:$uplanet}') || return 1

    local tags_json
    tags_json=$(jq -cn \
        --arg d "$tx_d" \
        --arg email "$email" \
        --arg amount "$amount" \
        --arg tier "${tier_slug:-unknown}" \
        --arg s "$status" \
        --arg constellation "${UPLANETG1PUB}" \
        '[["d",$d],["t","uplanet"],["t","oc-emission"],["s",$s],
          ["email",$email],["amount",$amount],["tier",$tier],
          ["constellation",$constellation]]') || return 1

    python3 "${ASTROPORT}/tools/nostr_send_note.py" \
        --keyfile "$CAPTAIN_NOSTR_KEYFILE" \
        --kind 30851 \
        --content "$(echo "$content_json" | jq -c .)" \
        --tags "$tags_json" \
        --relay "ws://127.0.0.1:7777" 2>/dev/null
    local rc=$?
    [[ $rc -eq 0 ]] && [[ "$JSON_OUTPUT" == "false" ]] && \
        echo "✅ Preuve 30851 publiée : ${email} ${amount}Ẑ [${status}]"
    return $rc
}

dispatch_zen_emission() {
    local email="$1" amount="$2" tier_slug="$3"
    local zen_amount=$(echo "scale=2; $amount * 1" | bc)
    if _tier_matches "$tier_slug" "$TIER_SLUG_SATELLITE"; then
        ${ASTROPORT}/UPLANET.official.sh -s "${email}" -t satellite -m "${zen_amount}"
        return $?
    elif _tier_matches "$tier_slug" "$TIER_SLUG_CONSTELLATION"; then
        ${ASTROPORT}/UPLANET.official.sh -s "${email}" -t constellation -m "${zen_amount}"
        return $?
    elif _tier_matches "$tier_slug" "$TIER_SLUG_LABO"; then
        ## Dons fléchés vers le MULTIPASS du Capitaine (labo / R&D qo-op)
        local cap="${CAPTAIN_TARGET:-support@qo-op.com}"
        [[ "$JSON_OUTPUT" == "false" ]] && echo "→ Tier labo/R&D : routage vers MULTIPASS capitaine ${cap}"
        ${ASTROPORT}/UPLANET.official.sh -l "${cap}" -m "${zen_amount}"
        return $?
    else
        ${ASTROPORT}/UPLANET.official.sh -l "${email}" -m "${zen_amount}"
        return $?
    fi
}

_build_station_card_html() {
    ## Génère un bloc HTML présentant les capacités de cette station Astroport.
    ## Injecté dans les emails d'invitation via {{STATION_CARD}}.
    local _hb_json
    if [[ -n "$IPFSNODEID" ]]; then
        _hb_json="${HOME}/.zen/tmp/${IPFSNODEID}/heartbox_analysis.json"
    else
        _hb_json=$(find "${HOME}/.zen/tmp" -maxdepth 2 -name "heartbox_analysis.json" 2>/dev/null | head -1)
    fi
    [[ ! -s "$_hb_json" ]] && return 0

    local hostname cpu_model cpu_cores ram_gb
    local power_score provider_tier gpu_detected gpu_vram gpu_name
    local disk_write disk_read crypto_score crypto_ms
    local zencard_slots nostr_slots
    local ollama_active ollama_models nextcloud_active
    local ipfs_active ipfs_peers nostr_relay_active nostr_engine

    hostname=$(jq -r '.node_info.hostname // "Station UPlanet"' "$_hb_json" 2>/dev/null | sed 's/&/\&amp;/g; s/</\&lt;/g')
    cpu_model=$(jq -r '.system.cpu.model // "Unknown"' "$_hb_json" 2>/dev/null | sed 's/&/\&amp;/g; s/</\&lt;/g')
    cpu_cores=$(jq -r '.system.cpu.cores // 0' "$_hb_json" 2>/dev/null)
    ram_gb=$(jq -r '.system.memory.total_gb // 0' "$_hb_json" 2>/dev/null)
    power_score=$(jq -r '.capacities.power_score // 0' "$_hb_json" 2>/dev/null)
    provider_tier=$(jq -r '.capacities.provider_tier // "light"' "$_hb_json" 2>/dev/null)
    gpu_detected=$(jq -r '.capacities.gpu.detected // false' "$_hb_json" 2>/dev/null)
    gpu_vram=$(jq -r '.capacities.gpu.vram_gb // 0' "$_hb_json" 2>/dev/null)
    gpu_name=$(jq -r '.capacities.gpu.name // ""' "$_hb_json" 2>/dev/null | sed 's/&/\&amp;/g; s/</\&lt;/g')
    disk_write=$(jq -r '.capacities.disk_io.write_mbps // 0' "$_hb_json" 2>/dev/null)
    disk_read=$(jq -r '.capacities.disk_io.read_mbps // 0' "$_hb_json" 2>/dev/null)
    crypto_score=$(jq -r '.capacities.crypto_score // 0' "$_hb_json" 2>/dev/null)
    crypto_ms=$(jq -r '.capacities.crypto_ms // 0' "$_hb_json" 2>/dev/null)
    zencard_slots=$(jq -r '.capacities.zencard_slots // 0' "$_hb_json" 2>/dev/null)
    nostr_slots=$(jq -r '.capacities.nostr_slots // 0' "$_hb_json" 2>/dev/null)
    ollama_active=$(jq -r '.services.ai_company.ollama.active // false' "$_hb_json" 2>/dev/null)
    ollama_models=$(jq -r '(.services.ai_company.ollama.models // []) | map(split(":")[0]) | join(", ")' "$_hb_json" 2>/dev/null)
    nextcloud_active=$(jq -r '.services.nextcloud.cloud_apache.active // false' "$_hb_json" 2>/dev/null)
    ipfs_active=$(jq -r '.services.ipfs.active // false' "$_hb_json" 2>/dev/null)
    ipfs_peers=$(jq -r '.services.ipfs.peers_connected // 0' "$_hb_json" 2>/dev/null)
    nostr_relay_active=$(jq -r '.services.nostr_relay.active // false' "$_hb_json" 2>/dev/null)
    nostr_engine=$(jq -r '.services.nostr_relay.engine // "strfry"' "$_hb_json" 2>/dev/null)

    local tier_badge tier_color
    case "$provider_tier" in
        brain-gpu)  tier_badge="🔥 BRAIN-GPU"  ; tier_color="#ff6b35" ;;
        brain-cpu)  tier_badge="🔥 BRAIN-CPU"  ; tier_color="#ff9500" ;;
        standard)   tier_badge="⚡ STANDARD"   ; tier_color="#e8d44d" ;;
        *)          tier_badge="🌿 LIGHT"       ; tier_color="#00ff88" ;;
    esac

    local svc_badges=""
    [[ "$ipfs_active" == "true" ]] && \
        svc_badges+="<span style=\"display:inline-block;background:rgba(0,245,255,0.1);border:1px solid rgba(0,245,255,0.2);border-radius:3px;padding:2px 8px;font-size:0.72rem;color:#00f5ff;margin:2px 2px 2px 0;\">🌐&nbsp;IPFS&nbsp;(${ipfs_peers})</span>"
    [[ "$nostr_relay_active" == "true" ]] && \
        svc_badges+="<span style=\"display:inline-block;background:rgba(0,245,255,0.08);border:1px solid rgba(0,245,255,0.18);border-radius:3px;padding:2px 8px;font-size:0.72rem;color:#00f5ff;margin:2px 2px 2px 0;\">⚡&nbsp;NOSTR&nbsp;(${nostr_engine})</span>"
    [[ "$nextcloud_active" == "true" ]] && \
        svc_badges+="<span style=\"display:inline-block;background:rgba(0,255,136,0.08);border:1px solid rgba(0,255,136,0.2);border-radius:3px;padding:2px 8px;font-size:0.72rem;color:#00ff88;margin:2px 2px 2px 0;\">☁️&nbsp;NextCloud</span>"
    [[ "$ollama_active" == "true" ]] && \
        svc_badges+="<span style=\"display:inline-block;background:rgba(195,155,211,0.1);border:1px solid rgba(195,155,211,0.2);border-radius:3px;padding:2px 8px;font-size:0.72rem;color:#c39bd3;margin:2px 2px 2px 0;\">🤖&nbsp;Ollama&nbsp;LLM</span>"

    local gpu_row=""
    [[ "$gpu_detected" == "true" && "${gpu_vram:-0}" -gt 0 ]] && \
        gpu_row="<tr><td style=\"padding:3px 8px;color:rgba(255,255,255,0.45);\">GPU</td><td style=\"padding:3px 8px;color:#c39bd3;\">${gpu_name}&nbsp;·&nbsp;${gpu_vram}&nbsp;Go VRAM</td></tr>"

    local models_row=""
    [[ "$ollama_active" == "true" && -n "$ollama_models" && "$ollama_models" != "null" && "$ollama_models" != "" ]] && \
        models_row="<tr><td style=\"padding:3px 8px;color:rgba(255,255,255,0.45);\">Modèles&nbsp;IA</td><td style=\"padding:3px 8px;color:#c39bd3;font-size:0.78rem;\">${ollama_models}</td></tr>"

    local crypto_info="${crypto_score}/10"
    [[ "${crypto_ms:-0}" -gt 0 ]] && crypto_info="${crypto_score}/10&nbsp;(${crypto_ms}&nbsp;ms)"

    cat << STATION_HTML

  <!-- FICHE STATION ASTROPORT -->
  <div style="background:rgba(0,0,0,0.3);border:1px solid rgba(0,245,255,0.15);padding:18px 20px;margin-bottom:20px;border-radius:4px;">
    <div style="font-family:'Courier New',monospace;font-size:0.62rem;color:#00f5ff;letter-spacing:4px;margin-bottom:12px;">// STATION ASTROPORT · SOURCE DE CE MESSAGE</div>
    <table style="width:100%;margin-bottom:14px;"><tr>
      <td style="vertical-align:top;">
        <strong style="font-family:'Courier New',monospace;color:#00f5ff;font-size:0.95rem;">${hostname}</strong><br>
        <span style="font-family:'Courier New',monospace;font-size:0.68rem;color:rgba(255,255,255,0.3);">${UPLANETNAME:0:8}</span>
      </td>
      <td style="text-align:right;vertical-align:top;">
        <span style="display:inline-block;background:rgba(0,245,255,0.06);border:1px solid rgba(0,245,255,0.22);border-radius:3px;padding:4px 12px;font-family:'Courier New',monospace;font-size:0.75rem;color:${tier_color};">${tier_badge}&nbsp;·&nbsp;Score&nbsp;${power_score}</span>
      </td>
    </tr></table>
    <table style="width:100%;border-collapse:collapse;font-size:0.82rem;margin-bottom:14px;">
      <tr>
        <td style="padding:3px 8px;color:rgba(255,255,255,0.45);width:30%;">CPU</td>
        <td style="padding:3px 8px;color:#e0f0ff;">${cpu_model}&nbsp;·&nbsp;${cpu_cores}&nbsp;cœurs</td>
      </tr>
      <tr>
        <td style="padding:3px 8px;color:rgba(255,255,255,0.45);">RAM</td>
        <td style="padding:3px 8px;color:#e0f0ff;">${ram_gb}&nbsp;Go</td>
      </tr>
      ${gpu_row}
      <tr>
        <td style="padding:3px 8px;color:rgba(255,255,255,0.45);">Disque</td>
        <td style="padding:3px 8px;color:#e0f0ff;">✍&nbsp;${disk_write}&nbsp;MB/s&nbsp;·&nbsp;📖&nbsp;${disk_read}&nbsp;MB/s</td>
      </tr>
      <tr>
        <td style="padding:3px 8px;color:rgba(255,255,255,0.45);">Crypto</td>
        <td style="padding:3px 8px;color:#e0f0ff;">${crypto_info}</td>
      </tr>
      <tr>
        <td style="padding:3px 8px;color:rgba(255,255,255,0.45);">Capacités</td>
        <td style="padding:3px 8px;color:#00ff88;">${zencard_slots}&nbsp;ZenCard&nbsp;·&nbsp;${nostr_slots}&nbsp;slots&nbsp;NOSTR</td>
      </tr>
      ${models_row}
    </table>
    <div style="margin-bottom:12px;">${svc_badges}</div>
    <p style="margin:0;font-size:0.72rem;color:rgba(255,255,255,0.3);">Capitaine&nbsp;:&nbsp;<a href="mailto:${CAPTAIN_TARGET:-support@qo-op.com}" style="color:rgba(0,245,255,0.5);">${CAPTAIN_TARGET:-support@qo-op.com}</a>&nbsp;·&nbsp;<a href="${station_url:-https://u.copylaradio.com}" style="color:rgba(0,245,255,0.4);">Station →</a>&nbsp;·&nbsp;<a href="https://ipfs.copylaradio.com/ipns/${IPFSNODEID}/status.html" style="color:rgba(0,245,255,0.4);">📊&nbsp;Status →</a></p>
  </div>

STATION_HTML
}

_send_multipass_invitation() {
    local email="$1" amount="$2" tier_slug="$3" donor_email="${4:-$1}" created_at="${5:-}"

    ## Opt-out Mailjet : vérifier ~/.zen/game/nostr/$email/.mailjet
    local mailjet_optout="${HOME}/.zen/game/nostr/${email}/.mailjet"
    if [[ -f "$mailjet_optout" ]]; then
        local _ch
        _ch=$(jq -r '.channels[]?' "$mailjet_optout" 2>/dev/null)
        if echo "$_ch" | grep -qE '^(email|all)$'; then
            [[ "$JSON_OUTPUT" == "false" ]] && echo "⛔ ${email} a demandé l'opt-out (mailjet)"
            return 0
        fi
    fi

    ## Seule la station primaire (tête de liste dans A_boostrap_nodes.txt) envoie les invitations
    local is_primary=false
    local strapfile="${HOME}/.zen/game/MY_boostrap_nodes.txt"
    [[ ! -f "$strapfile" ]] && strapfile="${HOME}/.zen/Astroport.ONE/A_boostrap_nodes.txt"
    if [[ -f "$strapfile" ]]; then
        local primary_strap
        primary_strap=$(grep -Ev '#' "$strapfile" | rev | cut -d '/' -f 1 | rev | grep -v '^[[:space:]]*$' | head -n 1)
        [[ "$IPFSNODEID" == "$primary_strap" ]] && is_primary=true
    fi
    if [[ "$is_primary" == "false" ]]; then
        [[ "$JSON_OUTPUT" == "false" ]] && echo "ℹ️  Station non-primaire — délégation de l'invitation à la station principale"
        return 0
    fi

    ## Idempotence : renvoi toutes les 72h si MULTIPASS non détecté
    local now
    now=$(date +%s)
    local last_ts
    last_ts=$(grep -F "${email}:" "$INVITATION_LOG" | grep ":INVITED:" | grep -oE ':[0-9]{10}$' | tail -1 | tr -d ':')
    if [[ -n "$last_ts" ]] && (( now - last_ts < 259200 )); then
        return 0
    fi

    local captain_npub=""
    [[ -n "$CAPTAIN_TARGET" ]] && captain_npub=$(cat ~/.zen/game/nostr/${CAPTAIN_TARGET}/NPUB 2>/dev/null)

    ## URL publique de la station
    local station_url
    if [[ -n "$uSPOT" ]]; then
        station_url="$uSPOT"
    else
        station_url="https://u.copylaradio.com"
    fi

    ## Profil NOSTR du capitaine (viewer public sur la station ou Coracle)
    local profile_url
    if [[ -n "$captain_npub" ]]; then
        profile_url="${station_url}/earth/nostr_profile_viewer.html?npub=${captain_npub}"
    else
        profile_url="https://coracle.copylaradio.com"
    fi

    ## Sélection du template et objet selon le tier
    local template_file subject
    if _tier_matches "$tier_slug" "$TIER_SLUG_SATELLITE"; then
        template_file="${MY_PATH}/templates/invitation_satellite.html"
        subject="🌟 Bienvenue Parrain Satellite UPlanet — créez votre MULTIPASS"
    elif _tier_matches "$tier_slug" "$TIER_SLUG_CONSTELLATION"; then
        template_file="${MY_PATH}/templates/invitation_constellation.html"
        subject="✨ Bienvenue Parrain Constellation UPlanet — accès GPU & #BRO"
    elif _tier_matches "$tier_slug" "$TIER_SLUG_LABO"; then
        template_file="${MY_PATH}/templates/notification_labo.html"
        subject="🔬 Contribution Labo/R&D reçue — UPlanet"
    elif _tier_matches "$tier_slug" "$TIER_SLUG_CLOUD"; then
        template_file="${MY_PATH}/templates/invitation_locataire.html"
        subject="🎫 Votre adhésion UPlanet — créez votre MULTIPASS"
    else
        template_file="${MY_PATH}/templates/invitation_multipass.html"
        subject="Votre contribution UPlanet — créez votre MULTIPASS"
    fi
    [[ ! -f "$template_file" ]] && template_file="${MY_PATH}/templates/invitation_multipass.html"

    local tmp_html
    tmp_html=$(mktemp /tmp/oc_invitation_XXXXXX.html)

    ## Date lisible du don (peut dater de plusieurs mois — fenêtre de rattrapage 12 mois)
    local human_date
    human_date=$(date -d "$created_at" +"%d/%m/%Y" 2>/dev/null)
    [[ -z "$human_date" ]] && human_date="récemment"

    if [[ -f "$template_file" ]]; then
        sed \
            -e "s|{{EMAIL}}|${email}|g" \
            -e "s|{{DONOR_EMAIL}}|${donor_email}|g" \
            -e "s|{{AMOUNT}}|${amount}|g" \
            -e "s|{{TIER_SLUG}}|${tier_slug:-standard}|g" \
            -e "s|{{DATE}}|${human_date}|g" \
            -e "s|{{STATION_URL}}|${station_url}|g" \
            -e "s|{{PROFILE_URL}}|${profile_url}|g" \
            -e "s|{{CAPTAIN_EMAIL}}|${CAPTAIN_TARGET:-support@qo-op.com}|g" \
            -e "s|{{UPLANETNAME}}|${UPLANETNAME:0:8}|g" \
            -e "s|{{UNSUB_URL}}|${station_url}|g" \
            "$template_file" > "$tmp_html"
    else
        cat > "$tmp_html" << HTMLEOF
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#222">
  <h2>🌍 Votre contribution sur UPlanet</h2>
  <p>Contribution de <strong>${amount}&nbsp;€</strong> (${tier_slug:-standard}) reçue — merci !</p>
  <p>Créez votre MULTIPASS avec l'email <code>${donor_email}</code> sur
     <a href="${station_url}">${station_url}</a> ou via
     <code>bash &lt;(curl -sL https://install.astroport.com)</code>.</p>
</div>
HTMLEOF
    fi

    ## Injecter la fiche station (substitution multi-ligne via Python). Note : cette
    ## invitation ne s'adresse qu'à des comptes SANS MULTIPASS — pas de "reprenez votre
    ## cotisation" ici, ce message n'a de sens que dans _send_renewal_reminder (comptes
    ## qui ONT déjà un MULTIPASS et une vraie interruption de cotisation).
    local _card_tmpfile
    _card_tmpfile=$(mktemp /tmp/station_card_XXXXXX.html)
    _build_station_card_html > "$_card_tmpfile"
    python3 - "$_card_tmpfile" "$tmp_html" << 'PYEOF' 2>/dev/null || \
        sed -i 's/{{STATION_CARD}}//' "$tmp_html"
import sys
with open(sys.argv[1], encoding='utf-8') as f: card = f.read()
with open(sys.argv[2], encoding='utf-8') as f: html = f.read()
with open(sys.argv[2], 'w', encoding='utf-8') as f: f.write(html.replace('{{STATION_CARD}}', card))
PYEOF
    rm -f "$_card_tmpfile"

    if [[ -x "${ASTROPORT}/tools/mailjet.sh" ]]; then
        "${ASTROPORT}/tools/mailjet.sh" \
            --template "$0" \
            --expire 7d \
            "${email}" \
            "${tmp_html}" \
            "${subject}"
        local rc=$?
        rm -f "$tmp_html"
        if [[ $rc -eq 0 ]]; then
            echo "${email}:${amount}:INVITED:$(date +%s)" >> "$INVITATION_LOG"
            [[ "$JSON_OUTPUT" == "false" ]] && echo "📧 Invitation envoyée à ${email} (${amount} €)"
        else
            [[ "$JSON_OUTPUT" == "false" ]] && echo "⚠️  Échec envoi invitation à ${email} (mailjet rc=$rc)"
        fi
    else
        rm -f "$tmp_html"
        [[ "$JSON_OUTPUT" == "false" ]] && echo "⚠️  mailjet.sh introuvable — invitation non envoyée pour ${email}"
    fi
}

## Relance dédiée aux abonnés dont le MULTIPASS existe déjà mais qui ne cotisent plus
## ce mois-ci (cf. subscriber_status "stopped") — distinct de _send_multipass_invitation
## (qui s'adresse à ceux qui n'ont pas encore de MULTIPASS).
_send_renewal_reminder() {
    local email="$1" tier_slug="$2" last_amount="$3" last_created_at="$4"

    local mailjet_optout="${HOME}/.zen/game/nostr/${email}/.mailjet"
    if [[ -f "$mailjet_optout" ]]; then
        local _ch
        _ch=$(jq -r '.channels[]?' "$mailjet_optout" 2>/dev/null)
        if echo "$_ch" | grep -qE '^(email|all)$'; then
            return 0
        fi
    fi

    local is_primary=false
    local strapfile="${HOME}/.zen/game/MY_boostrap_nodes.txt"
    [[ ! -f "$strapfile" ]] && strapfile="${HOME}/.zen/Astroport.ONE/A_boostrap_nodes.txt"
    if [[ -f "$strapfile" ]]; then
        local primary_strap
        primary_strap=$(grep -Ev '#' "$strapfile" | rev | cut -d '/' -f 1 | rev | grep -v '^[[:space:]]*$' | head -n 1)
        [[ "$IPFSNODEID" == "$primary_strap" ]] && is_primary=true
    fi
    [[ "$is_primary" == "false" ]] && return 0

    ## Idempotence : une relance au plus tous les 30 jours (abonnement mensuel — pas
    ## besoin d'insister comme pour l'invitation MULTIPASS, marqueur distinct "REMINDED"
    ## dans le même log pour réutiliser l'infrastructure existante).
    local now last_ts
    now=$(date +%s)
    last_ts=$(grep -F "${email}:" "$INVITATION_LOG" | grep ":REMINDED:" | grep -oE ':[0-9]{10}$' | tail -1 | tr -d ':')
    if [[ -n "$last_ts" ]] && (( now - last_ts < 2592000 )); then
        return 0
    fi

    ## TIER_SLUG_CLOUD regroupe deux offres OC distinctes (cloud-usage et
    ## membre-resident), chacune avec sa propre page de cotisation — on vérifie
    ## "membre-resident" spécifiquement avant de retomber sur le lien CLOUD générique,
    ## sinon un membre résident recevait le lien de la cotisation cloud-usage par erreur.
    local resume_url="https://opencollective.com/monnaie-libre/contribute"
    if _tier_matches "$tier_slug" "$TIER_SLUG_SATELLITE"; then
        resume_url="${OC_URL_SATELLITE:-$resume_url}"
    elif _tier_matches "$tier_slug" "$TIER_SLUG_CONSTELLATION"; then
        resume_url="${OC_URL_CONSTELLATION:-$resume_url}"
    elif _tier_matches "$tier_slug" "membre-resident"; then
        resume_url="${OC_URL_MEMBRE:-$resume_url}"
    elif _tier_matches "$tier_slug" "$TIER_SLUG_CLOUD"; then
        resume_url="${OC_URL_CLOUD:-$resume_url}"
    fi

    local human_date
    human_date=$(date -d "$last_created_at" +"%d/%m/%Y" 2>/dev/null)
    [[ -z "$human_date" ]] && human_date="récemment"

    local station_url
    if [[ -n "$uSPOT" ]]; then
        station_url="$uSPOT"
    else
        station_url="https://u.copylaradio.com"
    fi

    ## Code PASS (PIN 5 chiffres, créé par make_NOSTRCARD.sh) — permet de récupérer
    ## le MULTIPASS existant depuis Zelkova (email + PASS → UPassport /g1nostr) sans
    ## ressaisir de clés. N'existe que si le MULTIPASS est local (garanti par l'appelant :
    ## _send_renewal_reminder n'est invoqué qu'après confirmation que G1PUBNOSTR est local).
    local pass_code
    pass_code=$(cat "${HOME}/.zen/game/nostr/${email}/.pass" 2>/dev/null)

    local template_file="${MY_PATH}/templates/reminder_resume.html"
    local tmp_html
    tmp_html=$(mktemp /tmp/oc_reminder_XXXXXX.html)

    if [[ -f "$template_file" ]]; then
        sed \
            -e "s|{{EMAIL}}|${email}|g" \
            -e "s|{{AMOUNT}}|${last_amount}|g" \
            -e "s|{{TIER_SLUG}}|${tier_slug:-standard}|g" \
            -e "s|{{DATE}}|${human_date}|g" \
            -e "s|{{RESUME_URL}}|${resume_url}|g" \
            -e "s|{{STATION_URL}}|${station_url}|g" \
            -e "s|{{UNSUB_URL}}|${station_url}|g" \
            -e "s|{{PASS_CODE}}|${pass_code:-????}|g" \
            -e "s|{{CAPTAIN_EMAIL}}|${CAPTAIN_TARGET:-support@qo-op.com}|g" \
            -e "s|{{UPLANETNAME}}|${UPLANETNAME:0:8}|g" \
            "$template_file" > "$tmp_html"
    else
        rm -f "$tmp_html"
        return 1
    fi

    if [[ -x "${ASTROPORT}/tools/mailjet.sh" ]]; then
        "${ASTROPORT}/tools/mailjet.sh" \
            --template "$0" \
            --expire 7d \
            "${email}" \
            "${tmp_html}" \
            "🔄 Votre cotisation UPlanet s'est arrêtée — la reprendre ?"
        local rc=$?
        rm -f "$tmp_html"
        if [[ $rc -eq 0 ]]; then
            echo "${email}:${last_amount}:REMINDED:$(date +%s)" >> "$INVITATION_LOG"
            [[ "$JSON_OUTPUT" == "false" ]] && echo "📧 Relance abonnement envoyée à ${email}"
        else
            [[ "$JSON_OUTPUT" == "false" ]] && echo "⚠️  Échec envoi relance à ${email} (mailjet rc=$rc)"
        fi
    else
        rm -f "$tmp_html"
    fi
}

[[ "$JSON_OUTPUT" == "false" ]] && echo "=== Processing 12-month catch-up window (MULTIPASS tardifs inclus) ==="
## Extraction via tx_fields.py (NUL-séparé) — voir _sync_rows() pour le détail du bug
## `read`+IFS=tab évité (champs vides d'un compte OC anonyme décalant toute la ligne).
declare -a _fields
readarray -d '' -t _fields < <(python3 "${MY_PATH}/tx_fields.py" "${MY_PATH}/data/catchup.credit.json" 2>/dev/null)

## Préchargement (1 seul scan/find pour TOUTES les lignes) — voir _sync_rows() pour le détail.
_prefetch_emission_status
_prefetch_swarm_g1pubnostr

## Comptes ayant contribué CE mois-ci — voir _sync_rows() pour le détail.
declare -A _active_slugs=()
while IFS= read -r _s; do
    [[ -n "$_s" ]] && _active_slugs["$_s"]=1
done < <(jq -r '.fromAccount.slug' "${MY_PATH}/data/current_month.credit.json" 2>/dev/null | sort -u)

for ((_i = 0; _i < ${#_fields[@]}; _i += 6)); do
    slug="${_fields[_i]}"; raw_email="${_fields[_i+1]}"; amount="${_fields[_i+2]}"
    created_at="${_fields[_i+3]}"; tier_slug="${_fields[_i+4]}"; to_project="${_fields[_i+5]}"
    sub_status="stopped"
    [[ -n "${_active_slugs[$slug]:-}" ]] && sub_status="active"

    email="$raw_email"
    [[ -z "$email" || "$email" == "null" ]] && email=$(jq -r --arg s "$slug" '.[$s] // empty' "${MY_PATH}/data/slug_email_map.json" 2>/dev/null)
    if [[ -z "$email" || "$email" == "null" ]]; then
        ## Don structurellement bloqué (pas d'email exploitable) : rien n'est tenté ni
        ## journalisé, donc rien ne le distinguera d'un don "en attente" ordinaire dans
        ## --sync sauf le statut dédié "blocked" (🚫). Signalé ici pour que ce ne soit
        ## pas silencieux côté --run aussi.
        [[ "$JSON_OUTPUT" == "false" ]] && echo "🚫 Don bloqué (aucun email exploitable, slug='${slug}', ${amount}€) — voir --sync"
        continue
    fi

    tx_id="${raw_email}:${amount}:${created_at}"
    _check_emission_nostr "$tx_id" && continue

    [[ "$JSON_OUTPUT" == "false" && -n "$to_project" && "$to_project" != "$OCSLUG" ]] && \
        echo "🌱 Contribution au projet enfant '${to_project}' (tier: ${tier_slug:-?}) — ${email} : ${amount}€"

    ## Routage des tiers labo/R&D : l'email cible est le Capitaine, pas le donateur
    _effective_email="$email"
    _tier_matches "$tier_slug" "$TIER_SLUG_LABO" && _effective_email="${CAPTAIN_TARGET:-support@qo-op.com}"

    ## Vérification MULTIPASS : local d'abord, puis swarm
    if [[ ! -f "$HOME/.zen/game/nostr/${_effective_email}/G1PUBNOSTR" ]]; then
        _swarm_hit="${SWARM_G1PUBNOSTR[$_effective_email]:-}"
        if [[ -z "$_swarm_hit" ]]; then
            [[ "$JSON_OUTPUT" == "false" ]] && echo "⚠️  MULTIPASS introuvable pour ${_effective_email} — invitation en cours"
            _send_multipass_invitation "${_effective_email}" "${amount}" "${tier_slug}" "${email}" "${created_at}"
        else
            [[ "$JSON_OUTPUT" == "false" ]] && echo "ℹ️  MULTIPASS de ${_effective_email} présent dans le swarm (${_swarm_hit})"
        fi
        continue
    fi

    ## MULTIPASS déjà créé mais abonnement arrêté (ne cotise plus ce mois-ci) : relance
    ## dédiée, distincte de l'invitation MULTIPASS ci-dessus. Ne concerne pas les tiers
    ## labo/R&D (redirigés vers le Capitaine — la notion d'abonnement ne s'y applique pas).
    if [[ "$sub_status" == "stopped" ]] && ! _tier_matches "$tier_slug" "$TIER_SLUG_LABO"; then
        _send_renewal_reminder "${_effective_email}" "${tier_slug}" "${amount}" "${created_at}"
    fi

    if [[ "$MANUAL_MODE" == "true" ]]; then
        echo "------------------------------------------------"
        echo "Transaction: $email | Amount: $amount EUR | Tier: ${tier_slug:-standard}"
        ## Tiers labo/R&D : le don ne recharge PAS le wallet du donateur mais celui du
        ## Capitaine (cf. dispatch_zen_emission) — le préciser pour éviter toute confusion
        ## avec un donateur dont le MULTIPASS personnel n'existe pas encore.
        [[ "$_effective_email" != "$email" ]] && \
            echo "   → Tier labo/R&D : redirigé vers le MULTIPASS Capitaine (${_effective_email})"
        read -p "Process? [Y/n/edit/skip/exit]: " choice
        case "${choice,,}" in
            y|yes|"") dispatch_zen_emission "${email}" "${amount}" "${tier_slug}" ;;
            edit)
                read -p "Amount: " amount
                echo "Tier: 1) Satellite 2) Constellation 3) Cloud 4) Membre"
                read -p "Choice: " tc
                case $tc in 1) ts="satellite" ;; 2) ts="constellation" ;; 3) ts="cotisation" ;; 4) ts="membre-resident" ;; *) ts="$tier_slug" ;; esac
                dispatch_zen_emission "${email}" "${amount}" "$ts" ;;
            skip|n|no) continue ;;
            exit) exit 0 ;;
            *) continue ;;
        esac
    else
        dispatch_zen_emission "${email}" "${amount}" "${tier_slug}"
    fi
    _dispatch_rc=$?
    _dispatch_status="FAIL"
    [[ $_dispatch_rc -eq 0 ]] && _dispatch_status="OK"
    _publish_emission_proof "$email" "$amount" "$tier_slug" "$raw_email" "$created_at" "$_dispatch_status"
done

[[ "$JSON_OUTPUT" == "false" ]] && echo "=== ẐEN emission complete ==="
[[ -x "$MY_PATH/oc_expense_monitor.sh" ]] && "$MY_PATH/oc_expense_monitor.sh" >/dev/null 2>&1 || true
