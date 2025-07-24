#!/bin/bash
########################################################################
# G1FabLab & CopyLaRadio Presentation Campaign
# Version: 1.0
# License: AGPL-3.0
########################################################################
## Envoie des messages de présentation via Cesium/jaklis
## aux prospects Ğ1 pour présenter G1FabLab et CopyLaRadio
########################################################################

set -euo pipefail

source ~/.zen/Astroport.ONE/tools/my.sh

# Configuration
PROSPECT_FILE="$HOME/.zen/game/g1prospect.json"
BACKUP_FILE="$PROSPECT_FILE.backup.$(date +%Y%m%d_%H%M%S)"
TEST_PUBKEY="DsEx1pS33vzYZg4MroyBV9hCw98j1gtHEhwiZ5tK7ech"

# Templates de messages
SUBJECT_TEMPLATE="Découvrez G1FabLab & CopyLaRadio - Votre souveraineté numérique"
MESSAGE_TEMPLATE="Bonjour,

Je me permets de vous contacter car vous faites partie de la communauté Ğ1.

Nous développons un écosystème complet pour votre souveraineté numérique :

🏗️ G1FabLab (https://g1sms.fr) :
- Services informatiques pour la communauté Ğ1
- Dégooglisation de smartphones
- Installation Linux avec assistance RustDesk
- Développement d'applications communautaires
- Collecte d'idées pour orienter les logiciels libres

🌐 CopyLaRadio (https://copylaradio.com) :
- Coopérative d'auto-hébergeurs en toile de confiance
- NextCloud, IA et Blockchain
- Transformez votre ordinateur en 'Ambassade Diplomatique Web3'
- Co-hébergement de données chez vous ou un membre de confiance

🚀 UPlanet ORIGIN :
Rejoignez notre 'Internet des Gens' décentralisé !
- Sélectionnez votre localisation
- Indiquez votre email
- Obtenez votre MULTIPASS pour naviguer sur UPlanet

Inscription : https://qo-op.com

Nous organisons des ateliers et formations. Souhaitez-vous en savoir plus ?

Cordialement,
L'équipe G1FabLab & CopyLaRadio"

# Fonctions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

check_dependencies() {
    if [[ ! -f "$HOME/.zen/Astroport.ONE/tools/jaklis/jaklis.py" ]]; then
        log "ERROR: jaklis.py not found at $HOME/.zen/Astroport.ONE/tools/jaklis/jaklis.py"
        exit 1
    fi
    
    if [[ -z "$CAPTAINEMAIL" ]]; then
        log "ERROR: CAPTAINEMAIL environment variable not set"
        exit 1
    fi
    
    if [[ -z "$contactG1PUB" ]]; then
        log "ERROR: contactG1PUB environment variable not set"
        exit 1
    fi
    
    if [[ ! -f "$PROSPECT_FILE" ]]; then
        log "ERROR: Prospect file not found: $PROSPECT_FILE"
        log "Please run g1prospect_final.sh first"
        exit 1
    fi
}

send_message() {
    local pubkey="$1"
    local uid="$2"
    
    log "Sending message to $uid ($pubkey)"
    
    # Load Cesium nodes from .env if available
    local cesium_node=""
    if [[ -f ".env" ]]; then
        cesium_node=$(grep "^CESIUM_PRIMARY_NODE=" .env | cut -d'=' -f2)
        if [[ -n "$cesium_node" ]]; then
            log "Using Cesium node from .env: $cesium_node"
        fi
    fi
    
    # Try to send message with Cesium node if available
    if [[ -n "$cesium_node" ]]; then
        python3 "$HOME/.zen/Astroport.ONE/tools/jaklis/jaklis.py" \
            -k "$HOME/.zen/game/nostr/$CAPTAINEMAIL/.secret.dunikey" \
            -n "$cesium_node" \
            send \
            -d "$pubkey" \
            -t "$SUBJECT_TEMPLATE" \
            -m "$MESSAGE_TEMPLATE"
    else
        # Fallback to default jaklis behavior
        python3 "$HOME/.zen/Astroport.ONE/tools/jaklis/jaklis.py" \
            -k "$HOME/.zen/game/nostr/$CAPTAINEMAIL/.secret.dunikey" \
            send \
            -d "$pubkey" \
            -t "$SUBJECT_TEMPLATE" \
            -m "$MESSAGE_TEMPLATE"
    fi
    
    if [[ $? -eq 0 ]]; then
        log "SUCCESS: Message sent to $uid"
        echo "$pubkey,$uid,$(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "sent_messages_$(date +%Y%m%d).csv"
        return 0
    else
        log "ERROR: Failed to send message to $uid"
        echo "$pubkey,$uid,$(date -u +"%Y-%m-%dT%H:%M:%SZ"),FAILED" >> "failed_messages_$(date +%Y%m%d).csv"
        return 1
    fi
}

update_prospect_file() {
    local pubkey="$1"
    local uid="$2"
    local success="$3"
    
    log "Updating prospect file for $uid"
    
    # Créer un backup avant modification
    if [[ ! -f "$BACKUP_FILE" ]]; then
        cp "$PROSPECT_FILE" "$BACKUP_FILE"
        log "Backup created: $BACKUP_FILE"
    fi
    
    # Ajouter le champ message_sent au membre
    local current_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    if [[ "$success" == "true" ]]; then
        # Message envoyé avec succès
        jq --arg pubkey "$pubkey" \
           --arg sent_date "$current_date" \
           --arg subject "$SUBJECT_TEMPLATE" \
           '.members |= map(if .pubkey == $pubkey then . + {"message_sent": {"date": $sent_date, "subject": $subject, "status": "success"}} else . end)' \
           "$PROSPECT_FILE" > "${PROSPECT_FILE}.tmp" && mv "${PROSPECT_FILE}.tmp" "$PROSPECT_FILE"
    else
        # Échec de l'envoi
        jq --arg pubkey "$pubkey" \
           --arg sent_date "$current_date" \
           --arg subject "$SUBJECT_TEMPLATE" \
           '.members |= map(if .pubkey == $pubkey then . + {"message_sent": {"date": $sent_date, "subject": $subject, "status": "failed"}} else . end)' \
           "$PROSPECT_FILE" > "${PROSPECT_FILE}.tmp" && mv "${PROSPECT_FILE}.tmp" "$PROSPECT_FILE"
    fi
    
    log "Prospect file updated for $uid"
}

main() {
    log "Starting G1FabLab & CopyLaRadio presentation campaign"
    
    # Vérifications
    check_dependencies
    
    # Statistiques
    total_members=$(jq '.members | length' "$PROSPECT_FILE")
    log "Found $total_members members in prospect database"
    
    # Demander confirmation
    if [[ "${TEST_MODE:-}" == "1" ]]; then
        echo ""
        echo "MODE TEST: Vous allez envoyer un message à la clé de test"
        echo "Clé de test: $TEST_PUBKEY"
        echo "Sujet: $SUBJECT_TEMPLATE"
        echo ""
        read -p "Voulez-vous continuer ? (y/N): " -n 1 -r
        echo ""
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Test cancelled by user"
            exit 0
        fi
        
        local max_messages=1
    else
        echo ""
        echo "Vous êtes sur le point d'envoyer des messages à $total_members membres Ğ1"
        echo "Sujet: $SUBJECT_TEMPLATE"
        echo ""
        read -p "Voulez-vous continuer ? (y/N): " -n 1 -r
        echo ""
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Campaign cancelled by user"
            exit 0
        fi
        
        # Demander nombre de messages à envoyer
        echo ""
        read -p "Combien de messages voulez-vous envoyer ? (max $total_members, défaut: 10): " -n 3 -r
        echo ""
        
        local max_messages=${REPLY:-10}
        if [[ $max_messages -gt $total_members ]]; then
            max_messages=$total_members
        fi
    fi
    
    log "Sending $max_messages messages"
    
    # Créer les fichiers de suivi
    echo "pubkey,uid,sent_date" > "sent_messages_$(date +%Y%m%d).csv"
    echo "pubkey,uid,sent_date,error" > "failed_messages_$(date +%Y%m%d).csv"
    
    # Envoyer les messages
    local sent=0
    local failed=0
    
    if [[ "${TEST_MODE:-}" == "1" ]]; then
        # Mode test : envoyer uniquement à la clé de test
        log "TEST MODE: Sending message to test pubkey: $TEST_PUBKEY"
        
        if send_message "$TEST_PUBKEY" "TEST_USER"; then
            sent=1
            log "SUCCESS: Test message sent"
        else
            failed=1
            log "ERROR: Test message failed"
        fi
    else
        # Mode normal : boucle sur les prospects
        while IFS= read -r member && [[ $sent -lt $max_messages ]]; do
            local pubkey
            local uid
            
            pubkey=$(echo "$member" | jq -r '.pubkey')
            uid=$(echo "$member" | jq -r '.uid')
            
            # Vérifier si le message a déjà été envoyé (dans le fichier prospect)
            if jq -e --arg pubkey "$pubkey" '.members[] | select(.pubkey == $pubkey and .message_sent)' "$PROSPECT_FILE" >/dev/null 2>&1; then
                log "SKIP: Message already sent to $uid (found in prospect file)"
                continue
            fi
            
            # Vérifier si le message a déjà été envoyé aujourd'hui (fichier CSV)
            if grep -q "^$pubkey," "sent_messages_$(date +%Y%m%d).csv" 2>/dev/null; then
                log "SKIP: Message already sent to $uid today (found in CSV)"
                continue
            fi
            
            # Envoyer le message
            if send_message "$pubkey" "$uid"; then
                sent=$((sent + 1))
                # Mettre à jour le fichier prospect avec succès
                update_prospect_file "$pubkey" "$uid" "true"
            else
                failed=$((failed + 1))
                # Mettre à jour le fichier prospect avec échec
                update_prospect_file "$pubkey" "$uid" "false"
            fi
            
            # Pause aléatoire entre 5 et 15 secondes
            if [[ $sent -lt $max_messages ]]; then
                local delay=$((RANDOM % 11 + 5))
                log "Waiting $delay seconds before next message..."
                sleep $delay
            fi
            
        done < <(jq -c '.members[]' "$PROSPECT_FILE")
    fi
    
    # Résumé
    log "Campaign completed!"
    log "Messages sent: $sent"
    log "Messages failed: $failed"
    log "Log files:"
    log "  - sent_messages_$(date +%Y%m%d).csv"
    log "  - failed_messages_$(date +%Y%m%d).csv"
}

# Gestion des arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--help|--test|--dry-run]"
        echo ""
        echo "Options:"
        echo "  --help, -h     Show this help"
        echo "  --test         Test mode (send to first 3 members only)"
        echo "  --dry-run      Show what would be sent without actually sending"
        echo ""
        echo "Environment variables:"
        echo "  CAPTAINEMAIL   Your captain email for jaklis"
        echo "  contactG1PUB   Your G1 public key"
        exit 0
        ;;
    --test)
        log "TEST MODE: Will send to test pubkey only"
        export TEST_MODE=1
        ;;
    --dry-run)
        log "DRY RUN MODE: Will not send actual messages"
        export DRY_RUN=1
        ;;
esac

# Lancer le script principal
main "$@" 