#!/usr/bin/env python3
import os
import json
import time
import subprocess
import logging
from agents.analyst_agent import AnalystAgent
from agents.strategist_agent import StrategistAgent
from agents.operator_agent import OperatorAgent

class AstroBotOrchestrator:
    def __init__(self):
        self.setup_logging()
        
        # Base directory for robust path construction using home directory
        base_path = os.path.expanduser("~/.zen")
        astroport_one_path = os.path.join(base_path, "Astroport.ONE")
        script_dir = os.path.dirname(os.path.abspath(__file__))

        self.shared_state = {
            "config": {
                # --- Fichiers de données ---
                "prospect_file": os.path.join(base_path, "game/g1prospect.json"),
                "enriched_prospects_file": os.path.join(script_dir, "workspace", "enriched_prospects.json"),

                # --- Workspace et Prompts (locaux à l'agent) ---
                "workspace": os.path.join(script_dir, "workspace"),
                "blocklist_file": os.path.join(script_dir, "workspace", "blocklist.json"),
                "strategist_prompt_file": os.path.join(script_dir, "prompts", "strategist_prompt.txt"),
                "analyst_prompt_file": os.path.join(script_dir, "prompts", "analyst_prompt.txt"),
                "analyst_deep_dive_prompt_file": os.path.join(script_dir, "prompts", "analyst_deep_dive_prompt.txt"),
                "analyst_language_prompt_file": os.path.join(script_dir, "prompts", "analyst_language_prompt.txt"),
                "analyst_thematic_prompt_file": os.path.join(script_dir, "prompts", "analyst_thematic_prompt.txt"),
                
                # --- Configuration des canaux de communication ---
                "cesium_node": "https://g1.data.e-is.pro",   # Nœud Cesium+ à utiliser

                # --- Scripts Externes (dans ~/.zen/Astroport.ONE) ---
                "question_script": os.path.join(astroport_one_path, "IA", "question.py"),
                "jaklis_script": os.path.join(astroport_one_path, "tools", "jaklis", "jaklis.py"),
                "mailjet_script": os.path.join(astroport_one_path, "tools", "mailjet.sh"),
                "nostr_dm_script": os.path.join(astroport_one_path, "tools", "nostr_send_DM.py"),
                "uplanet_nsec": "nsec1...", # A REMPLACER
                "ollama_script": os.path.join(astroport_one_path, "IA", "ollama.me.sh"),
                "perplexica_script_connector": os.path.join(astroport_one_path, "IA", "perplexica.me.sh"),
                "perplexica_script_search": os.path.join(astroport_one_path, "IA", "perplexica_search.sh"),
                
                "send_delay_seconds": 5,
                "uplanet_treasury_g1pub": None,
                "URL_OPEN_COLLECTIVE": "https://opencollective.com/monnaie-libre"
            },
            "status": {},
            "analyst_report": None,
            "targets": [],
            "message_to_send": None,
            "logger": self.logger
        }
        self.agents = {
            "analyste": AnalystAgent(self.shared_state),
            "stratège": StrategistAgent(self.shared_state),
            "opérateur": OperatorAgent(self.shared_state),
        }
        os.makedirs(self.shared_state['config']['workspace'], exist_ok=True)
        self.ensure_prospect_file_is_set()
        self.setup_treasury_wallet()

    def setup_logging(self):
        """Met en place un logging centralisé vers la console et un fichier."""
        log_directory = os.path.expanduser("~/.zen/tmp")
        os.makedirs(log_directory, exist_ok=True)
        log_file = os.path.join(log_directory, 'astrobot.log')

        self.logger = logging.getLogger("AstroBot")
        self.logger.setLevel(logging.DEBUG)  # Passer en mode DEBUG

        # Évite d'ajouter des handlers si le logger en a déjà
        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Handler pour le fichier
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # Handler pour la console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)


    def setup_treasury_wallet(self):
        """Détermine la clé publique du portefeuille Trésor UPlanet."""
        self.logger.info("--- Configuration du Portefeuille Trésor UPlanet ---")
        try:
            uplanet_name = os.environ.get('UPLANETNAME', 'UPlanet')
            
            # Construire un chemin absolu et robuste vers le script keygen
            keygen_script = os.path.join(os.path.expanduser("~/.zen"), "Astroport.ONE", "tools", "keygen")
            
            command = [keygen_script, '-t', 'duniter', f"{uplanet_name}.G1", f"{uplanet_name}.G1"]
            
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            treasury_pubkey = result.stdout.strip()
            
            if treasury_pubkey:
                self.shared_state['config']['uplanet_treasury_g1pub'] = treasury_pubkey
                self.logger.info(f"Portefeuille Trésor initialisé : {treasury_pubkey[:20]}...")
            else:
                raise Exception("La commande keygen n'a retourné aucune clé.")

        except FileNotFoundError:
            self.logger.error("Le script 'keygen' est introuvable. Impossible d'initialiser le portefeuille Trésor.")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Erreur lors de la génération de la clé du Trésor : {e.stderr}")
        except Exception as e:
            self.logger.error(f"Une erreur inattendue est survenue lors de l'initialisation du Trésor : {e}")


    def ensure_prospect_file_is_set(self):
        """Vérifie si le fichier de prospects existe, sinon demande à l'utilisateur."""
        prospect_file = os.path.expanduser(self.shared_state['config']['prospect_file'])
        
        if os.path.isfile(prospect_file):
            self.logger.info(f"Fichier de prospects trouvé à : {prospect_file}")
            return

        self.logger.warning(f"Fichier de prospects non trouvé à l'emplacement par défaut : {prospect_file}")
        
        while True:
            try:
                new_path = input("Veuillez entrer le chemin complet vers votre fichier g1prospect.json : ")
                expanded_path = os.path.expanduser(new_path)
                if os.path.isfile(expanded_path):
                    self.shared_state['config']['prospect_file'] = expanded_path
                    self.logger.info(f"Chemin du fichier de prospects mis à jour : {expanded_path}")
                    break
                else:
                    self.logger.error("Chemin invalide ou fichier non trouvé. Veuillez réessayer.")
            except KeyboardInterrupt:
                self.logger.info("\nOpération annulée par l'utilisateur.")
                exit()
 

    def print_header(self):
        self.logger.info("\n" + "="*50)
        self.logger.info("🚀 AstroBot - Orchestrateur de Campagne IA 🚀")
        self.logger.info("="*50)

    def print_status(self):
        self.logger.info("\n--- État des Agents et du Workspace ---")
        for name, agent in self.agents.items():
            status = agent.get_status()
            self.logger.info(f"👨‍🚀 Agent {name.capitalize()}: {status}")

        # Statut du workspace
        targets_file = os.path.join(self.shared_state['config']['workspace'], 'todays_targets.json')
        if os.path.exists(targets_file):
            try:
                with open(targets_file, 'r') as f:
                    targets = json.load(f)
                self.logger.info(f"📦 Workspace: {len(targets)} cible(s) en attente dans 'todays_targets.json'")
            except (IOError, json.JSONDecodeError):
                 self.logger.warning("📦 Workspace: Fichier de cibles corrompu ou illisible.")
        else:
            self.logger.info("📦 Workspace: Aucune cible définie.")
            
        message_file = os.path.join(self.shared_state['config']['workspace'], 'message_to_send.txt')
        if os.path.exists(message_file):
            self.logger.info("📦 Workspace: Un message est prêt à être envoyé.")
        else:
            self.logger.info("📦 Workspace: Aucun message à envoyer.")
        self.logger.info("-" * 37)


    def main_menu(self):
        last_action = None
        while True:
            # self.print_header() # Header is now just logging
            self.print_status()
            
            # --- Affichage des conseils ---
            if last_action == "analysis_complete":
                self.logger.info("\nCONSEIL : Analyse terminée. L'étape suivante est de lancer l'Agent Stratège (2) pour rédiger un message.")
            elif last_action == "strategy_complete":
                self.logger.info("\nCONSEIL : Message rédigé. L'étape suivante est de lancer l'Agent Opérateur (3) pour l'envoyer.")

            print("\nQue souhaitez-vous faire ?")
            print("1. Lancer l'Agent Analyste (Identifier les cibles)")
            print("2. Lancer l'Agent Stratège (Rédiger le message)")
            print("3. Lancer l'Agent Opérateur (Envoyer la campagne)")
            print("4. Gérer les Banques de Mémoire Thématiques")
            print("5. Gérer les Interactions de l'Opérateur")
            print("6. Quitter")

            choice = input("> ")

            if choice == "1":
                self.run_analyst_submenu()
                if "sélectionné" in self.shared_state['status'].get('AnalystAgent', ''):
                    last_action = "analysis_complete"
                else:
                    last_action = None
            elif choice == "2":
                self.agents['stratège'].run()
                if "Message sauvegardé" in self.shared_state['status'].get('StrategistAgent', ''):
                    last_action = "strategy_complete"
                else:
                    last_action = None
            elif choice == "3":
                self.agents['opérateur'].run()
                last_action = None # Réinitialiser après l'envoi
            elif choice == "4":
                self.agents['stratège'].manage_memory_banks()
                last_action = None
            elif choice == "5":
                self.run_operator_submenu()
                last_action = None
            elif choice == "6":
                self.logger.info("À bientôt, commandant ! 👋")
                break
            else:
                self.logger.warning("Choix invalide, veuillez réessayer.")
                last_action = None # Réinitialiser en cas de choix invalide
                time.sleep(1)

    def run_analyst_submenu(self):
        progress = self.agents['analyste'].get_analysis_progress()
        total = progress.get('total', 0)
        lang_total = progress.get('language', 0)
        tags_total = progress.get('tags', 0)

        print("\n--- Menu Analyste ---")
        print(f"Statut de la base de connaissance : {total} profils au total.\n")
        print("Analyse et Enrichissement :")
        print(f"1. Lancer l'analyse Géo-Linguistique         ({lang_total} / {total} profils analysés)")
        print(f"2. Lancer l'analyse par Thèmes (Compétences, etc.) ({tags_total} / {total} profils analysés)")
        print("\nCiblage et Export :")
        print("3. Lancer une campagne à partir d'un Thème")
        print("4. Mode Test (cible unique pour validation)")
        print("\n🎭 Création Automatique de Personas :")
        print("5. Créer des personas basés sur les thèmes détectés (banques 5-9)")
        print("6. Retour")
        
        choice = input("> ")
        
        if choice == "1":
            self.agents['analyste'].run_geo_linguistic_analysis()
        elif choice == "2":
            self.agents['analyste'].run_thematic_analysis()
        elif choice == "3":
            self.agents['analyste'].select_cluster_from_tags()
        elif choice == "4":
            self.agents['analyste'].run_test_mode()
        elif choice == "5":
            self.agents['analyste'].create_automatic_personas()
        elif choice == "6":
            return
        else:
            self.logger.warning("Choix invalide.")
        
        time.sleep(1) # Pause après chaque action

    def run_operator_submenu(self):
        """Sous-menu pour gérer les interactions de l'Opérateur"""
        print("\n--- Menu Opérateur ---")
        print("Gestion des interactions et réponses automatiques :")
        print("1. Voir l'historique des interactions")
        print("2. Traiter une réponse reçue")
        print("3. Configurer les réponses automatiques")
        print("4. Retour")
        
        choice = input("> ")
        
        if choice == "1":
            self._view_interaction_history()
        elif choice == "2":
            self._process_incoming_response()
        elif choice == "3":
            self._configure_auto_responses()
        elif choice == "4":
            return
        else:
            self.logger.warning("Choix invalide.")
        
        time.sleep(1)

    def _view_interaction_history(self):
        """Interface pour voir l'historique des interactions"""
        print("\n📚 CONSULTATION DE L'HISTORIQUE")
        print("-" * 40)
        
        # Demander le slot
        try:
            slot = input("Numéro du slot (0-11, Entrée pour 0) : ").strip()
            slot = int(slot) if slot else 0
            if not (0 <= slot <= 11):
                print("❌ Slot invalide")
                return
        except ValueError:
            print("❌ Entrée invalide")
            return
        
        # Demander si on veut voir une cible spécifique
        target_pubkey = input("Clé publique de la cible (Entrée pour voir toutes) : ").strip()
        
        if target_pubkey:
            self.agents['opérateur'].view_interaction_history(target_pubkey, slot)
        else:
            self.agents['opérateur'].view_interaction_history(slot=slot)

    def _process_incoming_response(self):
        """Interface pour traiter une réponse reçue"""
        print("\n📨 TRAITEMENT D'UNE RÉPONSE REÇUE")
        print("-" * 40)
        
        # Demander les informations
        target_pubkey = input("Clé publique de la cible : ").strip()
        if not target_pubkey:
            print("❌ Clé publique requise")
            return
        
        target_uid = input("UID de la cible : ").strip()
        if not target_uid:
            print("❌ UID requis")
            return
        
        incoming_message = input("Message reçu : ").strip()
        if not incoming_message:
            print("❌ Message requis")
            return
        
        try:
            slot = input("Slot (0-11, Entrée pour 0) : ").strip()
            slot = int(slot) if slot else 0
            if not (0 <= slot <= 11):
                print("❌ Slot invalide")
                return
        except ValueError:
            print("❌ Entrée invalide")
            return
        
        # Traiter la réponse
        response = self.agents['opérateur'].process_incoming_response(
            target_pubkey, target_uid, incoming_message, slot
        )
        
        if response:
            print(f"\n✅ Réponse automatique générée et envoyée :")
            print(f"📝 {response}")
        else:
            print(f"\n⚠️ Réponse nécessite une intervention manuelle")

    def _configure_auto_responses(self):
        """Interface pour configurer les réponses automatiques"""
        print("\n⚙️ CONFIGURATION DES RÉPONSES AUTOMATIQUES")
        print("-" * 40)
        print("Cette fonctionnalité sera implémentée dans une prochaine version.")
        print("Pour l'instant, les réponses automatiques sont basées sur des mots-clés prédéfinis.")
        
        # Afficher les mots-clés actuels
        print("\nMots-clés positifs (réponse automatique) :")
        positive_keywords = [
            'merci', 'thanks', 'intéressant', 'intéressé', 'oui', 'yes', 'ok', 'd\'accord',
            'plus d\'info', 'plus d\'information', 'comment', 'comment faire',
            'où', 'quand', 'combien', 'prix', 'coût', 'participer', 'rejoindre'
        ]
        for keyword in positive_keywords:
            print(f"  - {keyword}")
        
        print("\nMots-clés négatifs (intervention manuelle) :")
        negative_keywords = [
            'non', 'no', 'pas intéressé', 'not interested', 'stop', 'arrêter',
            'supprimer', 'delete', 'désabonner', 'unsubscribe', 'problème', 'erreur',
            'plainte', 'complaint', 'insatisfait', 'dissatisfied'
        ]
        for keyword in negative_keywords:
            print(f"  - {keyword}")


if __name__ == "__main__":
    orchestrator = AstroBotOrchestrator()
    orchestrator.main_menu() 