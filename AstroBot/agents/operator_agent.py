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
        opt_out_message = "\n\n---\nPour ne plus recevoir de messages, répondez simplement 'STOP'."
        
        # Remplacer les placeholders
        message = template.replace("{{uid}}", target.get('uid', ''))
        message = message.replace("[URL_OPEN_COLLECTIVE]", url_oc)
        
        # Ajouter l'opt-out
        message += opt_out_message
        
        return message

    def run(self):
        self.logger.info("🤖 Agent Opérateur : Prêt pour l'envoi de la campagne.")
        self.shared_state['status']['OperatorAgent'] = "En attente de validation."

        # --- 1. Vérifier les prérequis ---
        workspace = self.shared_state['config']['workspace']
        targets_file = os.path.join(workspace, 'todays_targets.json')
        message_file = os.path.join(workspace, 'message_to_send.txt')

        if not os.path.exists(targets_file) or not os.path.exists(message_file):
            self.logger.error("Fichiers de cibles ou de message manquants.")
            self.shared_state['status']['OperatorAgent'] = "Échec : Prérequis manquants."
            return

        # --- 2. Charger les données ---
        try:
            with open(targets_file, 'r') as f: targets = json.load(f)
            with open(message_file, 'r') as f: message_template = f.read()
        except Exception as e:
            self.logger.error(f"Erreur de lecture des fichiers de campagne : {e}", exc_info=True)
            self.shared_state['status']['OperatorAgent'] = "Échec : Fichiers corrompus."
            return

        if not targets:
            self.logger.warning("Aucune cible. Opération annulée.")
            self.shared_state['status']['OperatorAgent'] = "Terminé : Aucune cible."
            return

        # --- 3. Sélection du canal ---
        print("\nChoisissez le canal d'envoi :")
        print("1. Jaklis (Message privé Cesium+)")
        print("2. Mailjet (Email)")
        print("3. Nostr (DM pour les détenteurs de MULTIPASS)")
        try:
            channel_choice = input("> ")
        except KeyboardInterrupt:
            self.logger.info("\nOpération annulée.")
            self.shared_state['status']['OperatorAgent'] = "Annulé par l'utilisateur."
            return

        # --- 4. Validation finale améliorée ---
        channel_name = {
            '1': 'Jaklis', '2': 'Mailjet', '3': 'Nostr (DM)'
        }.get(channel_choice, 'Inconnu')
        
        url_oc = self.shared_state['config']['URL_OPEN_COLLECTIVE']
        
        # Préparer un exemple de message pour l'aperçu
        example_target = targets[0] if targets else {"uid": "Exemple"}
        final_message_preview = self._prepare_message(message_template, example_target)

        print("\n" + "="*60)
        print("           VALIDATION FINALE AVANT ENVOI")
        print("="*60)
        print(f"CANAL CHOISI : {channel_name}")
        print(f"NOMBRE DE CIBLES : {len(targets)}")
        print(f"PROCESSUS : Un message sera envoyé toutes les {self.shared_state['config']['send_delay_seconds']} secondes.")
        print("\n--- MESSAGE FINAL QUI SERA ENVOYÉ ---")
        print(final_message_preview)
        print("--- FIN DU MESSAGE ---")

        # --- BRIEFING DE MISSION ---
        # --- VALIDATION FINALE ---
        print("\nLancer la campagne ? (oui/non) : ", end='', flush=True)
        try:
            # Rendre la confirmation plus flexible
            confirm = input().lower().strip()
            if confirm not in ['o', 'oui', 'y', 'yes']:
                self.logger.info("Envoi annulé.")
                self.shared_state['status']['OperatorAgent'] = "Annulé par l'utilisateur."
                return
        except KeyboardInterrupt:
            self.logger.info("\nEnvoi annulé.")
            self.shared_state['status']['OperatorAgent'] = "Annulé par l'utilisateur."
            return

        # Démarrer la campagne pour de bon
        if channel_choice == '1':
            self.send_with_jaklis(targets, message_template)
        elif channel_choice == '2':
            self.send_with_mailjet(targets, message_template)
        elif channel_choice == '3':
            self.send_with_nostr(targets, message_template)
        else:
            self.logger.error("Choix de canal invalide.")
            self.shared_state['status']['OperatorAgent'] = "Échec : Canal invalide."

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

    def send_with_jaklis(self, targets, message_template):
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
                    self.record_interaction(pubkey, uid, personalized_message)
                    success += 1
                else:
                    failures += 1

            time.sleep(self.shared_state['config']['send_delay_seconds'])
        
        report = f"Campagne via Jaklis terminée. Succès : {success}, Échecs : {failures}."
        self.logger.info(f"==================================================\n✅ {report}\n==================================================")
        self.shared_state['status']['OperatorAgent'] = report
    
    def send_with_mailjet(self, targets, message_template):
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

    def send_with_nostr(self, targets, message_template):
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
        """Génère une réponse de suivi basée sur l'historique des interactions"""
        # Récupérer l'historique
        history = self.get_interaction_history(target_pubkey, slot)
        
        if not history:
            return "Désolé, je n'ai pas d'historique d'interaction avec vous."
        
        # Construire le contexte pour l'IA
        context = f"Historique des interactions avec {target_uid} :\n"
        for interaction in history[-5:]:  # Dernières 5 interactions
            context += f"- Message envoyé : {interaction['message_sent']}\n"
            if interaction.get('response_received'):
                context += f"- Réponse reçue : {interaction['response_received']}\n"
            context += f"- Date : {interaction['timestamp']}\n\n"
        
        context += f"Message reçu maintenant : {incoming_message}\n\n"
        context += "En te basant sur cet historique, génère une réponse appropriée qui :\n"
        context += "1. Reconnaît le contexte de la conversation\n"
        context += "2. Répond de manière personnalisée au message reçu\n"
        context += "3. Maintient le ton et l'approche utilisés précédemment\n"
        context += "4. Guide vers l'objectif d'UPlanet (OpenCollective, MULTIPASS, etc.)\n"
        context += "5. Reste professionnel et engageant"
        
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
        """Détermine si une réponse automatique est appropriée"""
        message_lower = message.lower()
        
        # Mots-clés qui indiquent une réponse positive ou neutre
        positive_keywords = [
            'merci', 'thanks', 'intéressant', 'intéressé', 'oui', 'yes', 'ok', 'd\'accord',
            'plus d\'info', 'plus d\'information', 'comment', 'comment faire',
            'où', 'quand', 'combien', 'prix', 'coût', 'participer', 'rejoindre'
        ]
        
        # Mots-clés qui nécessitent une intervention manuelle
        negative_keywords = [
            'non', 'no', 'pas intéressé', 'not interested', 'stop', 'arrêter',
            'supprimer', 'delete', 'désabonner', 'unsubscribe', 'problème', 'erreur',
            'plainte', 'complaint', 'insatisfait', 'dissatisfied'
        ]
        
        # Vérifier les mots-clés négatifs en premier
        for keyword in negative_keywords:
            if keyword in message_lower:
                return False
        
        # Vérifier les mots-clés positifs
        for keyword in positive_keywords:
            if keyword in message_lower:
                return True
        
        # Par défaut, ne pas répondre automatiquement si le message est ambigu
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

    def view_interaction_history(self, target_pubkey=None, slot=0):
        """Affiche l'historique des interactions"""
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