from .base_agent import Agent
import json
import os
import subprocess
import time
import tempfile
from datetime import datetime

class OperatorAgent(Agent):
    """
    L'agent Opérateur est un dispatcher multicanal intelligent. Il exécute la campagne,
    informe l'utilisateur sur le processus, et ajoute une option de désinscription.
    """
    def _prepare_message(self, template: str, target: dict) -> str:
        """
        Prépare le message final et personnalisé en remplaçant toutes les variables.
        """
        # Récupérer les variables depuis la config
        url_oc = self.shared_state['config']['URL_OPEN_COLLECTIVE']
        opt_out_message = "\n\n---\n fred@g1sms.fr Pour ne plus recevoir de messages, répondez simplement 'STOP'."
        
        # Remplacer les placeholders
        message = template.replace("{{uid}}", target.get('uid', ''))
        message = message.replace("[URL_OPEN_COLLECTIVE]", url_oc)
        
        # Ajouter l'opt-out
        message += opt_out_message
        
        return message

    def run(self):
        """Menu principal de l'Agent Opérateur"""
        while True:
            print("\n" + "="*50)
            print("           🤖 AGENT OPÉRATEUR")
            print("="*50)
            print("1. 📤 ENVOYER - Lancer la campagne")
            print("2. 📥 RECEVOIR - Consulter la messagerie")
            print("3. 📊 État des interactions")
            print("4. Retour au menu principal")
            
            try:
                choice = input("\n> ")
            except KeyboardInterrupt:
                print("\nRetour au menu principal...")
                break
            
            if choice == "1":
                self._run_send_campaign()
            elif choice == "2":
                self._run_receive_messages()
            elif choice == "3":
                self._show_interaction_status()
            elif choice == "4":
                break
            else:
                print("❌ Choix invalide")

    def _run_send_campaign(self):
        """Lance l'envoi de la campagne"""
        self.logger.info("🤖 Agent Opérateur : Lancement de la campagne.")
        self.shared_state['status']['OperatorAgent'] = "Envoi en cours."

        # --- 1. Vérifier les prérequis ---
        workspace = self.shared_state['config']['workspace']
        targets_file = os.path.join(workspace, 'todays_targets.json')
        message_file = os.path.join(workspace, 'message_to_send.txt')

        if not os.path.exists(targets_file) or not os.path.exists(message_file):
            self.logger.error("❌ Fichiers de cibles ou de message manquants.")
            print("❌ Fichiers de cibles ou de message manquants.")
            self.shared_state['status']['OperatorAgent'] = "Échec : Prérequis manquants."
            return

        # --- 2. Charger les données ---
        try:
            with open(targets_file, 'r') as f: targets = json.load(f)
            with open(message_file, 'r') as f: message_template = f.read()
        except Exception as e:
            self.logger.error(f"❌ Erreur de lecture des fichiers : {e}")
            print(f"❌ Erreur de lecture des fichiers : {e}")
            self.shared_state['status']['OperatorAgent'] = "Échec : Fichiers corrompus."
            return

        if not targets:
            self.logger.warning("⚠️ Aucune cible sélectionnée.")
            print("⚠️ Aucune cible sélectionnée.")
            self.shared_state['status']['OperatorAgent'] = "Terminé : Aucune cible."
            return

        # --- 3. Sélection du canal ---
        print("\n📡 Choisissez le canal d'envoi :")
        print("1. Jaklis (Message privé Cesium+)")
        print("2. Mailjet (Email)")
        print("3. Nostr (DM pour les détenteurs de MULTIPASS)")
        try:
            channel_choice = input("> ")
        except KeyboardInterrupt:
            self.logger.info("🚫 Envoi annulé.")
            self.shared_state['status']['OperatorAgent'] = "Annulé par l'utilisateur."
            return

        # --- 4. Validation finale ---
        channel_name = {
            '1': 'Jaklis', '2': 'Mailjet', '3': 'Nostr (DM)'
        }.get(channel_choice, 'Inconnu')
        
        # Préparer un exemple de message pour l'aperçu
        example_target = targets[0] if targets else {"uid": "Exemple"}
        final_message_preview = self._prepare_message(message_template, example_target)

        print("\n" + "="*60)
        print("           📤 VALIDATION FINALE")
        print("="*60)
        print(f"📡 Canal : {channel_name}")
        print(f"🎯 Cibles : {len(targets)}")
        print(f"⏱️  Délai : {self.shared_state['config']['send_delay_seconds']} secondes")
        print("\n--- MESSAGE QUI SERA ENVOYÉ ---")
        print(final_message_preview)
        print("--- FIN DU MESSAGE ---")

        print("\n🚀 Lancer la campagne ? (oui/non) : ", end='', flush=True)
        try:
            confirm = input().lower().strip()
            if confirm not in ['o', 'oui', 'y', 'yes']:
                self.logger.info("🚫 Envoi annulé.")
                self.shared_state['status']['OperatorAgent'] = "Annulé par l'utilisateur."
                return
        except KeyboardInterrupt:
            self.logger.info("🚫 Envoi annulé.")
            self.shared_state['status']['OperatorAgent'] = "Annulé par l'utilisateur."
            return

        # Trouver un slot disponible
        available_slot = self._find_available_slot()
        if available_slot is None:
            self.logger.error("❌ Aucun slot disponible (tous les slots 0-11 sont utilisés)")
            print("❌ Aucun slot disponible. Veuillez nettoyer les anciennes campagnes.")
            self.shared_state['status']['OperatorAgent'] = "Échec : Aucun slot disponible."
            return
        
        # Sauvegarder les informations de la campagne
        self._save_campaign_info(available_slot, targets, message_template)
        
        # Démarrer la campagne pour de bon
        if channel_choice == '1':
            self.send_with_jaklis(targets, message_template, available_slot)
        elif channel_choice == '2':
            self.send_with_mailjet(targets, message_template, available_slot)
        elif channel_choice == '3':
            self.send_with_nostr(targets, message_template, available_slot)
        else:
            self.logger.error("Choix de canal invalide.")
            self.shared_state['status']['OperatorAgent'] = "Échec : Canal invalide."

    def _run_receive_messages(self):
        """Consulte la messagerie et gère les réponses automatiquement"""
        print("\n📥 CONSULTATION DE LA MESSAGERIE")
        print("="*50)
        
        try:
            # Utiliser Jaklis pour récupérer les nouveaux messages
            captain_email_file = os.path.expanduser("~/.zen/game/players/.current/.player")
            with open(captain_email_file, 'r') as f:
                captain_email = f.read().strip()
            
            secret_key_path = os.path.expanduser(f"~/.zen/game/nostr/{captain_email}/.secret.dunikey")
            cesium_node = self.shared_state['config']['cesium_node']
            jaklis_script = self.shared_state['config']['jaklis_script']
            
            print(f"🔍 Consultation de la messagerie Cesium+ pour {captain_email}...")
            
            # Récupérer les messages récents
            command = [
                'python3', jaklis_script,
                '-k', secret_key_path,
                '-n', cesium_node,
                'read',
                '-j'
            ]
            
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            messages_output = result.stdout
            
            # Analyser les messages pour identifier les réponses
            new_responses = self._parse_messages_for_responses(messages_output)
            
            if not new_responses:
                print("✅ Aucune nouvelle réponse détectée.")
                return
            
            print(f"📨 {len(new_responses)} nouvelle(s) réponse(s) détectée(s) :")
            
            for i, response in enumerate(new_responses, 1):
                print(f"\n--- Réponse {i}/{len(new_responses)} ---")
                print(f"De : {response['sender_uid']} ({response['sender_pubkey'][:10]}...)")
                print(f"Message : {response['content'][:100]}...")
                
                # Proposer de traiter automatiquement
                print("\nOptions :")
                print("1. Traiter automatiquement")
                print("2. Ignorer")
                print("3. Traiter manuellement")
                
                try:
                    choice = input("> ")
                    if choice == "1":
                        self._process_response_automatically(response)
                    elif choice == "3":
                        self._process_response_manually(response)
                    else:
                        print("⏭️ Réponse ignorée.")
                        
                except KeyboardInterrupt:
                    print("\n⏭️ Réponse ignorée.")
                    continue
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la consultation de la messagerie : {e}")
            print(f"❌ Erreur : {e}")

    def _parse_messages_for_responses(self, messages_output):
        """Parse la sortie JSON de Jaklis pour identifier les réponses"""
        responses = []
        
        try:
            # Parser le JSON de Jaklis
            messages = json.loads(messages_output)
            
            # Charger l'historique des interactions pour identifier les réponses
            memory_dir = self.setup_memory_system()
            sent_messages = set()
            
            # Récupérer tous les pubkeys à qui on a envoyé des messages
            for slot in range(12):
                slot_dir = os.path.join(memory_dir, f'slot_{slot}')
                if os.path.exists(slot_dir):
                    files = [f.replace('.json', '') for f in os.listdir(slot_dir) if f.endswith('.json')]
                    sent_messages.update(files)
            
            # Analyser chaque message
            for message in messages:
                if isinstance(message, dict):
                    sender_pubkey = message.get('pubkey', '')
                    content = message.get('content', '')
                    title = message.get('title', '')
                    date = message.get('date', 0)
                    
                    # Vérifier si c'est une réponse à nos messages
                    if sender_pubkey in sent_messages:
                        # C'est une réponse potentielle
                        responses.append({
                            'sender_pubkey': sender_pubkey,
                            'sender_uid': self._get_uid_from_pubkey(sender_pubkey),
                            'content': content,
                            'title': title,
                            'timestamp': self._format_timestamp(date),
                            'date_unix': date
                        })
            
            # Trier par date (plus récent en premier)
            responses.sort(key=lambda x: x['date_unix'], reverse=True)
            
            # Filtrer pour ne garder que les réponses récentes (dernières 24h)
            current_time = time.time()
            recent_responses = [
                r for r in responses 
                if (current_time - r['date_unix']) < 86400  # 24h en secondes
            ]
            
            return recent_responses
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur de parsing JSON : {e}")
            return []
        except Exception as e:
            self.logger.error(f"Erreur lors du parsing des messages : {e}")
            return []

    def _get_uid_from_pubkey(self, pubkey):
        """Récupère l'UID depuis la base de connaissance"""
        try:
            kb_file = self.shared_state['config']['enriched_prospects_file']
            if os.path.exists(kb_file):
                with open(kb_file, 'r') as f:
                    knowledge_base = json.load(f)
                
                if pubkey in knowledge_base:
                    profile = knowledge_base[pubkey].get('profile', {})
                    if profile and '_source' in profile:
                        return profile['_source'].get('uid', 'Unknown')
        except Exception as e:
            self.logger.debug(f"Erreur lors de la récupération de l'UID : {e}")
        
        return 'Unknown'

    def _format_timestamp(self, unix_timestamp):
        """Formate un timestamp Unix en format lisible"""
        try:
            dt = datetime.fromtimestamp(unix_timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "Date inconnue"

    def _process_response_automatically(self, response):
        """Traite automatiquement une réponse reçue"""
        try:
            print(f"🤖 Traitement automatique de la réponse de {response['sender_uid']}...")
            
            # Trouver le slot correspondant à cette interaction
            target_slot = self._find_slot_for_pubkey(response['sender_pubkey'])
            
            if target_slot is None:
                print("⚠️ Aucun historique d'interaction trouvé. Traitement manuel recommandé.")
                return
            
            print(f"📂 Slot identifié : {target_slot}")
            
            # Vérifier si c'est une réponse à un message envoyé
            history = self.get_interaction_history(response['sender_pubkey'], target_slot)
            
            if not history:
                print("⚠️ Aucun historique d'interaction trouvé dans ce slot.")
                return
            
            # Enregistrer la réponse reçue
            last_interaction = history[-1]
            self.record_interaction(
                response['sender_pubkey'],
                response['sender_uid'],
                last_interaction['message_sent'],
                response['content'],
                target_slot
            )
            
            # Traiter la réponse
            auto_response = self.process_incoming_response(
                response['sender_pubkey'],
                response['sender_uid'],
                response['content'],
                target_slot
            )
            
            if auto_response:
                print("✅ Réponse automatique générée et envoyée.")
                print(f"📝 Réponse : {auto_response[:100]}...")
            else:
                print("⚠️ Réponse nécessite une intervention manuelle.")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du traitement automatique : {e}")
            print(f"❌ Erreur : {e}")

    def _find_slot_for_pubkey(self, pubkey):
        """Trouve le slot correspondant à un pubkey"""
        memory_dir = self.setup_memory_system()
        
        for slot in range(12):
            slot_dir = os.path.join(memory_dir, f'slot_{slot}')
            if os.path.exists(slot_dir):
                slot_file = os.path.join(slot_dir, f'{pubkey}.json')
                if os.path.exists(slot_file):
                    return slot
        
        return None

    def _process_response_manually(self, response):
        """Traite manuellement une réponse reçue"""
        print(f"👤 Traitement manuel de la réponse de {response['sender_uid']}")
        print(f"Message complet : {response['content']}")
        
        # Permettre à l'utilisateur de choisir une banque de mémoire
        print("\nSélectionnez une banque de mémoire pour la réponse :")
        try:
            banks_config_file = os.path.join(self.shared_state['config']['workspace'], 'memory_banks_config.json')
            with open(banks_config_file, 'r') as f:
                banks_config = json.load(f)
            
            for slot, bank in banks_config.get('banks', {}).items():
                if bank.get('corpus'):
                    print(f"{slot}. {bank['name']} - {bank['archetype']}")
            
            choice = input("\nNuméro de la banque (ou Entrée pour automatique) : ")
            
            if choice.strip():
                # Utiliser la banque sélectionnée
                selected_bank = banks_config.get('banks', {}).get(choice)
                if selected_bank:
                    print(f"✅ Banque sélectionnée : {selected_bank['name']}")
                    # Ici on pourrait générer une réponse avec la banque spécifique
                else:
                    print("❌ Banque invalide.")
            else:
                print("🤖 Génération automatique...")
                self._process_response_automatically(response)
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du traitement manuel : {e}")
            print(f"❌ Erreur : {e}")

    def _show_interaction_status(self):
        """Affiche l'état détaillé des campagnes et interactions"""
        print("\n📊 ÉTAT DES CAMPAGNES ET INTERACTIONS")
        print("="*60)
        
        try:
            memory_dir = self.setup_memory_system()
            campaigns_file = os.path.join(memory_dir, 'campaigns.json')
            
            # Charger les informations des campagnes
            campaigns_info = {}
            if os.path.exists(campaigns_file):
                with open(campaigns_file, 'r') as f:
                    campaigns_info = json.load(f)
            
            # Analyser chaque slot
            active_campaigns = 0
            total_interactions = 0
            total_responses = 0
            
            for slot in range(12):  # Slots 0-11
                slot_dir = os.path.join(memory_dir, f'slot_{slot}')
                if os.path.exists(slot_dir):
                    slot_files = [f for f in os.listdir(slot_dir) if f.endswith('.json')]
                    
                    if slot_files:  # Slot actif
                        active_campaigns += 1
                        slot_interactions = 0
                        slot_responses = 0
                        slot_conversations = 0
                        
                        # Récupérer le nom de la campagne
                        campaign_name = campaigns_info.get(str(slot), {}).get('name', f'Campagne {slot}')
                        campaign_date = campaigns_info.get(str(slot), {}).get('date', 'Date inconnue')
                        campaign_targets = campaigns_info.get(str(slot), {}).get('targets', 0)
                        
                        print(f"\n🎯 SLOT {slot}: {campaign_name}")
                        print(f"   📅 Date: {campaign_date}")
                        print(f"   🎯 Cibles initiales: {campaign_targets}")
                        
                        # Analyser chaque profil
                        profiles_with_responses = []
                        
                        for file in slot_files:
                            try:
                                profile_pubkey = file.replace('.json', '')
                                with open(os.path.join(slot_dir, file), 'r') as f:
                                    history = json.load(f)
                                
                                profile_interactions = len(history)
                                profile_responses = sum(1 for interaction in history if interaction.get('response_received'))
                                
                                slot_interactions += profile_interactions
                                slot_responses += profile_responses
                                
                                if profile_responses > 0:
                                    slot_conversations += 1
                                    profiles_with_responses.append({
                                        'pubkey': profile_pubkey,
                                        'interactions': profile_interactions,
                                        'responses': profile_responses
                                    })
                                    
                            except Exception as e:
                                self.logger.error(f"Erreur lecture {file} : {e}")
                        
                        # Afficher les statistiques du slot
                        if slot_interactions > 0:
                            slot_response_rate = (slot_responses / slot_interactions) * 100
                            print(f"   📊 Interactions: {slot_interactions}")
                            print(f"   💬 Réponses: {slot_responses}")
                            print(f"   📈 Taux de réponse: {slot_response_rate:.1f}%")
                            print(f"   👥 Conversations actives: {slot_conversations}")
                            
                            total_interactions += slot_interactions
                            total_responses += slot_responses
                            
                            # Afficher les profils avec réponses
                            if profiles_with_responses:
                                print(f"   📋 Profils ayant répondu:")
                                for profile in profiles_with_responses[:5]:  # Limiter à 5
                                    print(f"      • {profile['pubkey'][:10]}... ({profile['responses']} réponses)")
                                if len(profiles_with_responses) > 5:
                                    print(f"      • ... et {len(profiles_with_responses) - 5} autres")
                        else:
                            print(f"   ⚠️ Aucune interaction enregistrée")
            
            # Résumé global
            print(f"\n" + "="*60)
            print(f"📈 RÉSUMÉ GLOBAL")
            print(f"   🎯 Campagnes actives: {active_campaigns}")
            print(f"   📊 Total interactions: {total_interactions}")
            print(f"   💬 Total réponses: {total_responses}")
            
            if total_interactions > 0:
                global_response_rate = (total_responses / total_interactions) * 100
                print(f"   📈 Taux de réponse global: {global_response_rate:.1f}%")
            
            # Options de consultation détaillée
            print(f"\n🔍 Options de consultation:")
            print(f"   1. Voir les détails d'une campagne spécifique")
            print(f"   2. Voir l'historique d'un profil spécifique")
            print(f"   3. Retour")
            
            try:
                choice = input("\n> ")
                if choice == "1":
                    self._show_campaign_details()
                elif choice == "2":
                    self._show_profile_history()
            except KeyboardInterrupt:
                print("\nRetour...")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'affichage du statut : {e}")
            print(f"❌ Erreur : {e}")

    def _create_campaign_name(self, targets, message_template):
        """Crée un nom automatique pour la campagne basé sur le contenu"""
        try:
            # Analyser les thèmes des cibles
            themes = set()
            languages = set()
            countries = set()
            
            for target in targets:
                metadata = target.get('metadata', {})
                themes.update(metadata.get('tags', []))
                languages.add(metadata.get('language', 'fr'))
                countries.add(metadata.get('country', ''))
            
            # Créer un nom descriptif
            theme_str = ', '.join(list(themes)[:3]) if themes else 'Général'
            lang_str = ', '.join(list(languages)[:2]) if languages else 'FR'
            country_str = ', '.join(list(countries)[:2]) if countries else 'International'
            
            # Analyser le message pour extraire le thème principal
            message_preview = message_template[:100].lower()
            if 'multipass' in message_preview:
                theme_str = 'MULTIPASS'
            elif 'opencollective' in message_preview or 'financement' in message_preview:
                theme_str = 'Financement'
            elif 'communauté' in message_preview or 'community' in message_preview:
                theme_str = 'Communauté'
            
            # Générer le nom final
            campaign_name = f"{theme_str} - {lang_str} - {country_str}"
            
            return campaign_name
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la création du nom de campagne : {e}")
            return f"Campagne {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    def _save_campaign_info(self, slot, targets, message_template):
        """Sauvegarde les informations de la campagne"""
        try:
            memory_dir = self.setup_memory_system()
            campaigns_file = os.path.join(memory_dir, 'campaigns.json')
            
            # Charger les campagnes existantes
            campaigns_info = {}
            if os.path.exists(campaigns_file):
                with open(campaigns_file, 'r') as f:
                    campaigns_info = json.load(f)
            
            # Créer les informations de la nouvelle campagne
            campaign_name = self._create_campaign_name(targets, message_template)
            
            campaigns_info[str(slot)] = {
                'name': campaign_name,
                'date': datetime.now().isoformat(),
                'targets': len(targets),
                'message_preview': message_template[:200] + "..." if len(message_template) > 200 else message_template,
                'themes': list(set([tag for target in targets for tag in target.get('metadata', {}).get('tags', [])]))[:5],
                'languages': list(set([target.get('metadata', {}).get('language', 'fr') for target in targets])),
                'countries': list(set([target.get('metadata', {}).get('country', '') for target in targets if target.get('metadata', {}).get('country')]))
            }
            
            # Sauvegarder
            with open(campaigns_file, 'w') as f:
                json.dump(campaigns_info, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ Informations de campagne sauvegardées pour le slot {slot}")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la sauvegarde des infos campagne : {e}")

    def _find_available_slot(self):
        """Trouve un slot disponible pour une nouvelle campagne"""
        try:
            memory_dir = self.setup_memory_system()
            
            for slot in range(12):  # Slots 0-11
                slot_dir = os.path.join(memory_dir, f'slot_{slot}')
                
                # Si le répertoire n'existe pas ou est vide, le slot est disponible
                if not os.path.exists(slot_dir) or not os.listdir(slot_dir):
                    return slot
            
            # Si tous les slots sont utilisés, retourner None
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la recherche de slot : {e}")
            return 0  # Fallback vers le slot 0

    def _show_campaign_details(self):
        """Affiche les détails d'une campagne spécifique"""
        print("\n🔍 DÉTAILS D'UNE CAMPAGNE")
        print("="*50)
        
        try:
            # Lister les campagnes disponibles
            memory_dir = self.setup_memory_system()
            campaigns_file = os.path.join(memory_dir, 'campaigns.json')
            
            if not os.path.exists(campaigns_file):
                print("❌ Aucune campagne enregistrée.")
                return
            
            with open(campaigns_file, 'r') as f:
                campaigns_info = json.load(f)
            
            if not campaigns_info:
                print("❌ Aucune campagne enregistrée.")
                return
            
            print("📋 Campagnes disponibles :")
            for slot, info in campaigns_info.items():
                print(f"   {slot}. {info['name']} ({info['date'][:10]})")
            
            slot_choice = input("\nNuméro du slot (ou Entrée pour annuler) : ")
            if not slot_choice.strip():
                return
            
            slot = slot_choice.strip()
            if slot not in campaigns_info:
                print("❌ Slot invalide.")
                return
            
            campaign = campaigns_info[slot]
            slot_dir = os.path.join(memory_dir, f'slot_{slot}')
            
            print(f"\n🎯 CAMPAGNE : {campaign['name']}")
            print("="*60)
            print(f"📅 Date : {campaign['date']}")
            print(f"🎯 Cibles initiales : {campaign['targets']}")
            print(f"🏷️ Thèmes : {', '.join(campaign['themes'])}")
            print(f"🌍 Langues : {', '.join(campaign['languages'])}")
            print(f"🌎 Pays : {', '.join(campaign['countries'])}")
            print(f"\n💬 Message : {campaign['message_preview']}")
            
            # Statistiques détaillées
            if os.path.exists(slot_dir):
                slot_files = [f for f in os.listdir(slot_dir) if f.endswith('.json')]
                
                if slot_files:
                    print(f"\n📊 STATISTIQUES DÉTAILLÉES")
                    print("-" * 40)
                    
                    total_interactions = 0
                    total_responses = 0
                    conversations = []
                    
                    for file in slot_files:
                        profile_pubkey = file.replace('.json', '')
                        with open(os.path.join(slot_dir, file), 'r') as f:
                            history = json.load(f)
                        
                        interactions = len(history)
                        responses = sum(1 for interaction in history if interaction.get('response_received'))
                        
                        total_interactions += interactions
                        total_responses += responses
                        
                        if responses > 0:
                            conversations.append({
                                'pubkey': profile_pubkey,
                                'interactions': interactions,
                                'responses': responses,
                                'last_response': next((interaction.get('timestamp') for interaction in reversed(history) if interaction.get('response_received')), 'N/A')
                            })
                    
                    print(f"📊 Total interactions : {total_interactions}")
                    print(f"💬 Total réponses : {total_responses}")
                    if total_interactions > 0:
                        response_rate = (total_responses / total_interactions) * 100
                        print(f"📈 Taux de réponse : {response_rate:.1f}%")
                    
                    if conversations:
                        print(f"\n👥 CONVERSATIONS ACTIVES ({len(conversations)})")
                        print("-" * 40)
                        for conv in sorted(conversations, key=lambda x: x['responses'], reverse=True):
                            print(f"   • {conv['pubkey'][:10]}... ({conv['responses']} réponses, dernière: {conv['last_response'][:10]})")
                else:
                    print(f"\n⚠️ Aucune interaction enregistrée pour cette campagne.")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'affichage des détails : {e}")
            print(f"❌ Erreur : {e}")

    def _show_profile_history(self):
        """Affiche l'historique d'un profil spécifique"""
        print("\n👤 HISTORIQUE D'UN PROFIL")
        print("="*50)
        
        try:
            pubkey = input("Clé publique du profil (ou Entrée pour annuler) : ")
            if not pubkey.strip():
                return
            
            pubkey = pubkey.strip()
            memory_dir = self.setup_memory_system()
            
            # Chercher dans tous les slots
            found_slots = []
            for slot in range(12):
                slot_dir = os.path.join(memory_dir, f'slot_{slot}')
                profile_file = os.path.join(slot_dir, f'{pubkey}.json')
                
                if os.path.exists(profile_file):
                    with open(profile_file, 'r') as f:
                        history = json.load(f)
                    found_slots.append((slot, history))
            
            if not found_slots:
                print(f"❌ Aucun historique trouvé pour {pubkey[:10]}...")
                return
            
            print(f"\n📋 HISTORIQUE DE {pubkey[:10]}...")
            print("="*60)
            
            for slot, history in found_slots:
                print(f"\n🎯 SLOT {slot} ({len(history)} interactions)")
                print("-" * 40)
                
                for i, interaction in enumerate(history, 1):
                    print(f"\n📨 Interaction {i}:")
                    print(f"   📅 Date : {interaction['timestamp']}")
                    print(f"   📤 Message envoyé : {interaction['message_sent'][:100]}...")
                    
                    if interaction.get('response_received'):
                        print(f"   📥 Réponse reçue : {interaction['response_received'][:100]}...")
                    else:
                        print(f"   ⏳ En attente de réponse...")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'affichage de l'historique : {e}")
            print(f"❌ Erreur : {e}")

    def execute_command(self, command, message_as_stdin=None):
        """
        Exécute une commande système, avec la possibilité de passer un message
        via l'entrée standard pour plus de robustesse.
        Retourne True en cas de succès, False en cas d'échec.
        """
        try:
            self.logger.debug(f"Exécution de la commande : {' '.join(command)}")
            result = subprocess.run(
                command, 
                check=True, 
                text=True, 
                capture_output=True,
                input=message_as_stdin # Passer le message via stdin
            )
            self.logger.info(f"(RÉEL) Commande exécutée avec succès.")
            self.logger.debug(f"Sortie de la commande : {result.stdout}")
            return True
        except FileNotFoundError:
            self.logger.error(f"Commande non trouvée : {command[0]}", exc_info=True)
            return False
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Erreur lors de l'exécution de la commande. Sortie d'erreur :\n{e.stderr}", exc_info=True)
            return False

    def send_with_jaklis(self, targets, message_template, slot=0):
        jaklis_script = self.shared_state['config']['jaklis_script']
        cesium_node = self.shared_state['config']['cesium_node']

        # Déterminer dynamiquement l'email du capitaine
        try:
            captain_email_file = os.path.expanduser("~/.zen/game/players/.current/.player")
            with open(captain_email_file, 'r') as f:
                captain_email = f.read().strip()
            if not captain_email: raise FileNotFoundError
        except (IOError, FileNotFoundError):
            self.logger.error(f"Impossible de lire l'email du capitaine depuis '{captain_email_file}'.")
            self.shared_state['status']['OperatorAgent'] = "Échec : Email du capitaine introuvable."
            return

        secret_key_path = os.path.expanduser(f"~/.zen/game/nostr/{captain_email}/.secret.dunikey")
        if not os.path.exists(secret_key_path):
            self.logger.error(f"La clé secrète Dunikey n'a pas été trouvée pour {captain_email} à l'emplacement : {secret_key_path}")
            self.shared_state['status']['OperatorAgent'] = "Échec : Clé secrète introuvable."
            return

        opt_out_message = "\n\n---\nPour ne plus recevoir de messages, répondez simplement 'STOP'."
        success = 0
        failures = 0

        self.logger.info(f"🚀 Démarrage de la campagne via Jaklis (authentifié)...")
        for i, target in enumerate(targets):
            uid = target.get('uid', 'N/A')
            pubkey = target.get('pubkey')

            if not pubkey:
                self.logger.warning(f"Cible {uid} ignorée (pas de clé publique).")
                failures += 1
                continue

            # Utiliser la méthode centralisée pour préparer le message
            personalized_message = self._prepare_message(message_template, target)
            title = "Invitation UPlanet"
            
            self.logger.info(f"--- Envoi Jaklis {i+1}/{len(targets)} à {uid} ---")
            
            # On passe le message par un fichier temporaire pour éviter les problèmes avec les caractères spéciaux
            with tempfile.NamedTemporaryFile(mode='w+', delete=True, suffix=".txt") as tmp_file:
                tmp_file.write(personalized_message)
                tmp_file.flush() # S'assurer que tout est écrit sur le disque
                
                command = [
                    'python3', jaklis_script,
                    '-k', secret_key_path,
                    '-n', cesium_node,
                    'send',
                    '-d', pubkey,
                    '-t', title,
                    '-f', tmp_file.name
                ]
                
                if self.execute_command(command):
                    # Enregistrer l'interaction dans la mémoire
                    self.record_interaction(pubkey, uid, personalized_message, slot=slot)
                    success += 1
                else:
                    failures += 1

            time.sleep(self.shared_state['config']['send_delay_seconds'])
        
        report = f"Campagne via Jaklis terminée. Succès : {success}, Échecs : {failures}."
        self.logger.info(f"==================================================\n✅ {report}\n==================================================")
        self.shared_state['status']['OperatorAgent'] = report
    
    def send_with_mailjet(self, targets, message_template, slot=0):
        self.logger.info("🚀 Démarrage de la campagne via Mailjet...")
        self.shared_state['status']['OperatorAgent'] = "Envoi via Mailjet..."
        mailjet_script = self.shared_state['config']['mailjet_script']
        url_oc = self.shared_state['config']['URL_OPEN_COLLECTIVE']
        success, failure = 0, 0

        for i, target in enumerate(targets):
            email = target.get('email')
            if not email:
                self.logger.warning(f"Cible {target.get('uid', 'N/A')} ignorée (email manquant)."); failure+=1; continue

            personalized_message = message_template.replace('[URL_OPEN_COLLECTIVE]', url_oc)
            for key, value in target.items(): personalized_message = personalized_message.replace(f'[{key}]', str(value))

            self.logger.info(f"--- Envoi Mailjet {i+1}/{len(targets)} à {email} ---")
            try:
                with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt", encoding='utf-8') as tmp:
                    tmp.write(personalized_message)
                    tmp_path = tmp.name

                command = ['bash', mailjet_script, email, tmp_path, "Votre invitation pour UPlanet"]
                self.logger.debug(f"Exécution Mailjet : {' '.join(command)}")
                self.execute_command(command)
                success += 1

                os.remove(tmp_path)
            except Exception as e:
                self.logger.error(f"Échec de l'envoi à {email}: {e}", exc_info=True); failure+=1

            if i < len(targets) - 1: time.sleep(self.shared_state['config'].get('send_delay_seconds', 2))

        self.finalize_campaign("Mailjet", success, failure)

    def send_with_nostr(self, targets, message_template, slot=0):
        self.logger.info("🚀 Démarrage de la campagne via Nostr (DM)...")
        self.shared_state['status']['OperatorAgent'] = "Envoi via Nostr (DM)..."
        nostr_script = os.path.abspath(self.shared_state['config']['nostr_dm_script'])
        sender_nsec = self.shared_state['config'].get('uplanet_nsec')

        if not sender_nsec or sender_nsec == "nsec1...":
            self.logger.error("Configuration NSEC manquante ou non initialisée. L'envoi Nostr est impossible.")
            self.finalize_campaign("Nostr", 0, len(targets))
            return

        success, failure = 0, 0

        for i, target in enumerate(targets):
            email = target.get('email')
            if not email:
                self.logger.warning(f"Cible {target.get('uid', 'N/A')} ignorée (email manquant pour la détection)."); failure+=1; continue

            # Détecter si le prospect a un MULTIPASS
            multipass_dir = os.path.expanduser(f"~/.zen/game/nostr/{email}")
            npub_file = os.path.join(multipass_dir, 'NPUB')

            if os.path.isdir(multipass_dir) and os.path.isfile(npub_file):
                with open(npub_file, 'r') as f:
                    recipient_npub = f.read().strip()

                self.logger.info(f"--- Envoi Nostr DM {i+1}/{len(targets)} à {target.get('uid')} ({recipient_npub[:15]}...) ---")

                personalized_message = message_template.replace('[URL_OPEN_COLLECTIVE]', url_oc)
                for key, value in target.items(): personalized_message = personalized_message.replace(f'[{key}]', str(value))

                try:
                    command = ['python3', nostr_script, '-p', recipient_npub, '-m', personalized_message, '-s', sender_nsec]
                    self.logger.debug(f"Exécution Nostr : {' '.join(command)}")
                    self.execute_command(command)
                    success += 1
                except Exception as e:
                    self.logger.error(f"Échec de l'envoi Nostr à {recipient_npub}: {e}", exc_info=True); failure+=1
            else:
                self.logger.warning(f"Cible {target.get('uid', 'N/A')} ignorée (pas de MULTIPASS détecté)."); failure+=1; continue

            if i < len(targets) - 1: time.sleep(self.shared_state['config'].get('send_delay_seconds', 2))

        self.finalize_campaign("Nostr", success, failure)

    def finalize_campaign(self, channel, success, failure):
        final_report = f"Campagne via {channel} terminée. Succès : {success}, Échecs : {failure}."
        self.logger.info("="*50)
        self.logger.info(f"✅ {final_report}")
        self.logger.info("="*50)
        self.shared_state['status']['OperatorAgent'] = final_report 

    def setup_memory_system(self):
        """Configure le système de mémoire pour l'opérateur"""
        memory_dir = os.path.join(self.shared_state['config']['workspace'], 'operator_memory')
        os.makedirs(memory_dir, exist_ok=True)
        
        # Créer les 12 slots de mémoire (0-11)
        for slot in range(12):
            slot_dir = os.path.join(memory_dir, f'slot_{slot}')
            os.makedirs(slot_dir, exist_ok=True)
        
        return memory_dir

    def record_interaction(self, target_pubkey, target_uid, message_sent, response_received=None, slot=0):
        """Enregistre une interaction dans la mémoire de l'opérateur"""
        memory_dir = self.setup_memory_system()
        slot_dir = os.path.join(memory_dir, f'slot_{slot}')
        
        interaction_file = os.path.join(slot_dir, f'{target_pubkey}.json')
        
        interaction_data = {
            'target_pubkey': target_pubkey,
            'target_uid': target_uid,
            'message_sent': message_sent,
            'response_received': response_received,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'slot': slot
        }
        
        # Charger les interactions existantes ou créer un nouveau fichier
        if os.path.exists(interaction_file):
            with open(interaction_file, 'r', encoding='utf-8') as f:
                interactions = json.load(f)
        else:
            interactions = []
        
        interactions.append(interaction_data)
        
        # Garder seulement les 50 dernières interactions
        interactions = interactions[-50:]
        
        with open(interaction_file, 'w', encoding='utf-8') as f:
            json.dump(interactions, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📝 Interaction enregistrée pour {target_uid} (slot {slot})")

    def get_interaction_history(self, target_pubkey, slot=0):
        """Récupère l'historique des interactions avec une cible"""
        memory_dir = self.setup_memory_system()
        slot_dir = os.path.join(memory_dir, f'slot_{slot}')
        interaction_file = os.path.join(slot_dir, f'{target_pubkey}.json')
        
        if os.path.exists(interaction_file):
            with open(interaction_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def generate_follow_up_response(self, target_pubkey, target_uid, incoming_message, slot=0):
        """Génère une réponse de suivi basée sur l'historique des interactions et enrichie par Perplexica"""
        # Récupérer l'historique
        history = self.get_interaction_history(target_pubkey, slot)
        
        if not history:
            return "Désolé, je n'ai pas d'historique d'interaction avec vous."
        
        # Récupérer les informations du prospect depuis la base de connaissance
        prospect_info = self._get_prospect_info(target_pubkey)
        
        # Enrichir avec Perplexica si le message contient des questions ou des références
        perplexica_context = ""
        if self._should_use_perplexica(incoming_message):
            self.logger.info(f"🔍 Utilisation de Perplexica pour enrichir la réponse à {target_uid}")
            perplexica_context = self._call_perplexica_for_response(incoming_message, prospect_info)
        
        # Sélectionner la banque de mémoire appropriée
        selected_bank = self._select_bank_for_response(prospect_info, incoming_message)
        
        # Construire le contexte enrichi pour l'IA
        context = f"""Tu es l'Agent Stratège d'UPlanet, spécialisé dans les réponses aux conversations.

INFORMATIONS DU PROSPECT :
- UID : {target_uid}
- Langue : {prospect_info.get('language', 'fr')}
- Thèmes d'intérêt : {', '.join(prospect_info.get('tags', []))}
- Description : {prospect_info.get('description', 'Non disponible')}

BANQUE DE MÉMOIRE SÉLECTIONNÉE :
- Nom : {selected_bank.get('name', 'Par défaut')}
- Archétype : {selected_bank.get('archetype', 'Non défini')}
- Ton : {selected_bank.get('corpus', {}).get('tone', 'Professionnel')}

HISTORIQUE DES INTERACTIONS :
"""
        for interaction in history[-3:]:  # Dernières 3 interactions
            context += f"- Message envoyé : {interaction['message_sent']}\n"
            if interaction.get('response_received'):
                context += f"- Réponse reçue : {interaction['response_received']}\n"
            context += f"- Date : {interaction['timestamp']}\n\n"
        
        context += f"MESSAGE REÇU MAINTENANT : {incoming_message}\n\n"
        
        if perplexica_context:
            context += f"CONTEXTE ENRICHIT PAR PERPLEXICA : {perplexica_context}\n\n"
        
        context += """INSTRUCTIONS POUR LA RÉPONSE :
1. Reconnais le contexte de la conversation et le profil du prospect
2. Réponds de manière personnalisée et engageante
3. Utilise le ton et le vocabulaire de la banque de mémoire sélectionnée
4. Guide subtilement vers les objectifs d'UPlanet (OpenCollective, MULTIPASS, etc.)
5. Reste authentique et professionnel
6. Si le prospect pose des questions techniques, utilise le contexte Perplexica
7. Limite la réponse à 2-3 phrases maximum

Génère une réponse appropriée :"""
        
        try:
            result = subprocess.run(
                ['python3', self.shared_state['config']['question_script'], context, '--json'],
                capture_output=True, text=True, check=True
            )
            response = json.loads(result.stdout)
            return response.get('answer', 'Erreur lors de la génération de la réponse')
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération de réponse de suivi : {e}")
            return f"Erreur lors de la génération de la réponse : {e}"

    def process_incoming_response(self, target_pubkey, target_uid, incoming_message, slot=0):
        """Traite une réponse reçue et génère une réponse automatique si nécessaire"""
        self.logger.info(f"📨 Réponse reçue de {target_uid} : {incoming_message[:100]}...")
        
        # Enregistrer la réponse reçue
        history = self.get_interaction_history(target_pubkey, slot)
        if history:
            # Mettre à jour la dernière interaction
            last_interaction = history[-1]
            last_interaction['response_received'] = incoming_message
            
            # Sauvegarder la mise à jour
            memory_dir = self.setup_memory_system()
            slot_dir = os.path.join(memory_dir, f'slot_{slot}')
            interaction_file = os.path.join(slot_dir, f'{target_pubkey}.json')
            
            with open(interaction_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        
        # Analyser le contenu de la réponse
        if self._should_auto_respond(incoming_message):
            self.logger.info(f"🤖 Génération d'une réponse automatique pour {target_uid}")
            auto_response = self.generate_follow_up_response(target_pubkey, target_uid, incoming_message, slot)
            
            # Envoyer la réponse automatique
            self._send_auto_response(target_pubkey, auto_response, slot)
            
            return auto_response
        else:
            self.logger.info(f"⚠️ Réponse de {target_uid} nécessite une intervention manuelle")
            return None

    def _should_auto_respond(self, message):
        """Détermine si une réponse automatique est appropriée en utilisant l'IA"""
        try:
            # Construire le prompt d'analyse
            analysis_prompt = f"""Analyse cette réponse reçue dans le contexte d'une campagne UPlanet et détermine si elle nécessite une réponse automatique.

MESSAGE REÇU : "{message}"

CONTEXTE : Ce message est une réponse à une campagne UPlanet qui présente le projet et invite à rejoindre l'aventure.

CRITÈRES D'ANALYSE :
1. POSITIF (réponse automatique) : 
   - Intérêt exprimé (oui, ça m'intéresse, comment faire, etc.)
   - Questions sur le projet, le processus, les étapes
   - Demande d'informations supplémentaires
   - Enthousiasme ou curiosité
   - Volonté de participer ou rejoindre

2. NÉGATIF (intervention manuelle) :
   - Refus explicite (non, pas intéressé, stop, etc.)
   - Plaintes ou critiques
   - Demande de désinscription
   - Messages hostiles ou agressifs

3. NEUTRE/AMBIGU (intervention manuelle) :
   - Messages trop courts ou vagues
   - Réponses non claires
   - Messages qui ne semblent pas liés au projet

INSTRUCTIONS :
- Analyse le ton, l'intention et le contenu du message
- Détermine si le prospect montre de l'intérêt ou non
- Réponds UNIQUEMENT par "POSITIF", "NÉGATIF" ou "NEUTRE"

ANALYSE :"""

            # Appeler question.py pour l'analyse
            question_script = self.shared_state['config']['question_script']
            command = ['python3', question_script, analysis_prompt]
            
            self.logger.debug(f"🔍 Analyse IA de la réponse : {message[:50]}...")
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            analysis_result = result.stdout.strip()
            
            self.logger.debug(f"🔍 Résultat de l'analyse IA : {analysis_result}")
            
            # Parser la réponse
            if "POSITIF" in analysis_result.upper():
                self.logger.info(f"✅ Analyse IA : Réponse positive détectée")
                return True
            elif "NÉGATIF" in analysis_result.upper():
                self.logger.info(f"❌ Analyse IA : Réponse négative détectée")
                return False
            else:
                self.logger.info(f"⚠️ Analyse IA : Réponse neutre/ambiguë détectée")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'analyse IA : {e}")
            # En cas d'erreur, utiliser une logique de fallback simple
            message_lower = message.lower()
            
            # Mots-clés de fallback pour les cas d'urgence
            positive_fallback = ['oui', 'yes', 'intéressé', 'intéressant', 'comment', 'où', 'quand', 'combien', '?']
            negative_fallback = ['non', 'no', 'stop', 'arrêter', 'pas intéressé', 'not interested']
            
            for keyword in negative_fallback:
                if keyword in message_lower:
                    return False
            
            for keyword in positive_fallback:
                if keyword in message_lower:
                    return True
            
            # Par défaut, intervention manuelle si ambigu
            return False

    def _send_auto_response(self, target_pubkey, response, slot=0):
        """Envoie une réponse automatique via le canal approprié"""
        # Utiliser le même canal que l'interaction initiale
        # Pour l'instant, on utilise Jaklis par défaut
        try:
            # Créer un fichier temporaire pour le message
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(response)
                temp_file = f.name
            
            # Envoyer via Jaklis
            captain_email = os.environ.get('CAPTAINEMAIL')
            if not captain_email:
                self.logger.error("CAPTAINEMAIL non défini")
                return False
            
            cesium_node = self.shared_state['config']['cesium_node']
            
            cmd = [
                'python3', self.shared_state['config']['jaklis_script'],
                '-k', captain_email,
                '-n', cesium_node,
                '-p', target_pubkey,
                '-f', temp_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Nettoyer le fichier temporaire
            os.unlink(temp_file)
            
            self.logger.info(f"✅ Réponse automatique envoyée à {target_pubkey}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'envoi de la réponse automatique : {e}")
            return False

    def list_campaign_slots(self):
        """Liste tous les slots avec leurs informations de campagne"""
        print("\n📊 SLOTS DE CAMPAGNES DISPONIBLES")
        print("=" * 60)
        
        # Charger les informations de campagne
        campaigns_file = os.path.join(self.shared_state['config']['workspace'], 'campaigns.json')
        campaigns = {}
        if os.path.exists(campaigns_file):
            try:
                with open(campaigns_file, 'r') as f:
                    campaigns = json.load(f)
            except Exception as e:
                self.logger.error(f"Erreur lors du chargement des campagnes : {e}")
        
        # Vérifier chaque slot
        active_slots = []
        for slot in range(12):
            slot_dir = os.path.join(self.setup_memory_system(), f'slot_{slot}')
            campaign_info = campaigns.get(str(slot), {})
            
            if os.path.exists(slot_dir):
                # Compter les interactions dans ce slot
                files = [f for f in os.listdir(slot_dir) if f.endswith('.json')]
                if files:
                    # Calculer les statistiques
                    total_interactions = 0
                    total_responses = 0
                    last_interaction = None
                    
                    for file in files:
                        pubkey = file.replace('.json', '')
                        history = self.get_interaction_history(pubkey, slot)
                        if history:
                            total_interactions += len(history)
                            responses = sum(1 for h in history if h.get('response_received'))
                            total_responses += responses
                            
                            if not last_interaction or history[-1]['timestamp'] > last_interaction:
                                last_interaction = history[-1]['timestamp']
                    
                    # Calculer le taux de réponse
                    response_rate = (total_responses / total_interactions * 100) if total_interactions > 0 else 0
                    
                    # Informations de campagne
                    campaign_name = campaign_info.get('name', f'Campagne {slot}')
                    campaign_date = campaign_info.get('date', 'Date inconnue')
                    target_count = campaign_info.get('target_count', len(files))
                    
                    active_slots.append({
                        'slot': slot,
                        'name': campaign_name,
                        'date': campaign_date,
                        'targets': target_count,
                        'interactions': total_interactions,
                        'responses': total_responses,
                        'response_rate': response_rate,
                        'last_interaction': last_interaction
                    })
        
        if not active_slots:
            print("❌ Aucune campagne active trouvée")
            return None
        
        # Afficher les slots actifs
        for i, slot_info in enumerate(active_slots, 1):
            print(f"\n{i}. Slot {slot_info['slot']} : {slot_info['name']}")
            print(f"   📅 Date : {slot_info['date']}")
            print(f"   🎯 Cibles : {slot_info['targets']}")
            print(f"   💬 Interactions : {slot_info['interactions']}")
            print(f"   📨 Réponses : {slot_info['responses']} ({slot_info['response_rate']:.1f}%)")
            if slot_info['last_interaction']:
                print(f"   ⏰ Dernière activité : {slot_info['last_interaction']}")
        
        return active_slots

    def view_interaction_history(self, target_pubkey=None, slot=0):
        """Affiche l'historique des interactions avec une interface améliorée"""
        if target_pubkey is None and slot == 0:
            # Afficher d'abord la liste des slots
            active_slots = self.list_campaign_slots()
            if not active_slots:
                return
            
            try:
                choice = input(f"\nChoisissez un slot (1-{len(active_slots)}) ou Entrée pour annuler : ").strip()
                if not choice:
                    return
                
                slot_index = int(choice) - 1
                if 0 <= slot_index < len(active_slots):
                    slot = active_slots[slot_index]['slot']
                else:
                    print("❌ Choix invalide")
                    return
            except ValueError:
                print("❌ Entrée invalide")
                return
        
        memory_dir = self.setup_memory_system()
        slot_dir = os.path.join(memory_dir, f'slot_{slot}')
        
        if target_pubkey:
            # Afficher l'historique d'une cible spécifique
            history = self.get_interaction_history(target_pubkey, slot)
            if history:
                print(f"\n📚 Historique des interactions avec {history[0]['target_uid']} (slot {slot})")
                print("=" * 60)
                for i, interaction in enumerate(history[-10:], 1):  # Dernières 10 interactions
                    print(f"\n{i}. {interaction['timestamp']}")
                    print(f"   Message envoyé : {interaction['message_sent'][:100]}...")
                    if interaction.get('response_received'):
                        print(f"   Réponse reçue : {interaction['response_received'][:100]}...")
                    else:
                        print("   Réponse reçue : Aucune")
            else:
                print(f"❌ Aucun historique trouvé pour {target_pubkey}")
        else:
            # Afficher un résumé de toutes les interactions du slot
            print(f"\n📚 Résumé des interactions (slot {slot})")
            print("=" * 60)
            
            if os.path.exists(slot_dir):
                files = [f for f in os.listdir(slot_dir) if f.endswith('.json')]
                if files:
                    for file in files:
                        pubkey = file.replace('.json', '')
                        history = self.get_interaction_history(pubkey, slot)
                        if history:
                            last_interaction = history[-1]
                            print(f"\n{last_interaction['target_uid']} ({pubkey[:10]}...)")
                            print(f"   Dernière interaction : {last_interaction['timestamp']}")
                            print(f"   Total interactions : {len(history)}")
                else:
                    print("❌ Aucune interaction trouvée dans ce slot")
            else:
                print("❌ Slot non trouvé")

    def _get_prospect_info(self, target_pubkey):
        """Récupère les informations du prospect depuis la base de connaissance"""
        try:
            kb_file = self.shared_state['config']['enriched_prospects_file']
            if os.path.exists(kb_file):
                with open(kb_file, 'r') as f:
                    knowledge_base = json.load(f)
                
                if target_pubkey in knowledge_base:
                    profile_data = knowledge_base[target_pubkey]
                    metadata = profile_data.get('metadata', {})
                    profile = profile_data.get('profile', {})
                    
                    return {
                        'language': metadata.get('language', 'fr'),
                        'tags': metadata.get('tags', []),
                        'description': profile.get('_source', {}).get('description', ''),
                        'country': metadata.get('country', ''),
                        'region': metadata.get('region', '')
                    }
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des infos prospect : {e}")
        
        return {'language': 'fr', 'tags': [], 'description': ''}

    def _should_use_perplexica(self, message):
        """Détermine si Perplexica doit être utilisé pour enrichir la réponse"""
        message_lower = message.lower()
        
        # Mots-clés qui indiquent des questions techniques ou des références
        technical_keywords = [
            'comment', 'comment faire', 'où', 'quand', 'combien', 'prix', 'coût',
            'technique', 'technologie', 'blockchain', 'crypto', 'nostr', 'ipfs',
            'multipass', 'g1', 'monnaie libre', 'décentralisé', 'sécurité',
            'installation', 'configuration', 'documentation', 'github',
            'opencollective', 'financement', 'participer', 'rejoindre'
        ]
        
        # Vérifier si le message contient des mots-clés techniques
        for keyword in technical_keywords:
            if keyword in message_lower:
                return True
        
        # Vérifier si le message contient des questions
        if any(char in message for char in ['?', 'comment', 'où', 'quand', 'combien']):
            return True
        
        return False

    def _call_perplexica_for_response(self, message, prospect_info):
        """Appelle Perplexica pour enrichir le contexte de la réponse"""
        try:
            # Construire une requête contextuelle
            query = f"""Analyse cette question/réponse dans le contexte d'UPlanet et du prospect :

Prospect : {prospect_info.get('description', 'Non disponible')}
Thèmes d'intérêt : {', '.join(prospect_info.get('tags', []))}
Message reçu : {message}

Fournis des informations pertinentes pour répondre de manière appropriée, en te concentrant sur :
- Les aspects techniques d'UPlanet si demandé
- Les informations sur MULTIPASS, G1, blockchain
- Les liens vers la documentation ou les ressources
- Les aspects communautaires et participatifs

Réponse concise et ciblée :"""
            
            # Appeler Perplexica
            perplexica_script = self.shared_state['config']['perplexica_script_search']
            result = subprocess.run(
                [perplexica_script, query],
                capture_output=True, text=True, check=True
            )
            
            return result.stdout.strip()
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'appel Perplexica : {e}")
            return ""

    def _select_bank_for_response(self, prospect_info, message):
        """Sélectionne la banque de mémoire appropriée pour la réponse"""
        try:
            # Charger la configuration des banques
            banks_config_file = os.path.join(self.shared_state['config']['workspace'], 'memory_banks_config.json')
            if os.path.exists(banks_config_file):
                with open(banks_config_file, 'r') as f:
                    banks_config = json.load(f)
                
                # Analyser les thèmes du prospect
                prospect_tags = set(prospect_info.get('tags', []))
                message_lower = message.lower()
                
                # Trouver la meilleure correspondance
                best_bank = None
                best_score = 0
                
                for slot, bank in banks_config.get('banks', {}).items():
                    if not bank.get('corpus'):
                        continue
                    
                    bank_themes = set(bank.get('themes', []))
                    
                    # Score basé sur la correspondance des thèmes
                    theme_score = len(prospect_tags.intersection(bank_themes))
                    
                    # Bonus pour les mots-clés dans le message
                    bank_vocabulary = bank.get('corpus', {}).get('vocabulary', [])
                    keyword_score = sum(1 for word in bank_vocabulary if word.lower() in message_lower)
                    
                    total_score = theme_score + (keyword_score * 0.5)
                    
                    if total_score > best_score:
                        best_score = total_score
                        best_bank = bank
                
                if best_bank:
                    return best_bank
                
                # Fallback vers la première banque disponible
                for slot, bank in banks_config.get('banks', {}).items():
                    if bank.get('corpus'):
                        return bank
                        
        except Exception as e:
            self.logger.error(f"Erreur lors de la sélection de banque : {e}")
        
        # Banque par défaut
        return {
            'name': 'Réponse par défaut',
            'archetype': 'Professionnel',
            'corpus': {'tone': 'Professionnel et engageant'}
        } 