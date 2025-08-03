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
                "analyst_consolidation_prompt_file": os.path.join(script_dir, "prompts", "analyst_consolidation_prompt.txt"),
                
                # --- Configuration des canaux de communication ---
                "cesium_node": "https://g1.data.e-is.pro",   # Nœud Cesium+ à utiliser

                # --- Scripts Externes (dans ~/.zen/Astroport.ONE) ---
                "question_script": os.path.join(astroport_one_path, "IA", "question.py"),
                "jaklis_script": os.path.join(astroport_one_path, "tools", "jaklis", "jaklis.py"),
                "mailjet_script": os.path.join(astroport_one_path, "tools", "mailjet.sh"),
                "nostr_dm_script": os.path.join(astroport_one_path, "tools", "nostr_send_dm.py"),
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
        self.load_existing_targets()

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
            
            if os.path.exists(keygen_script):
                command = [keygen_script, '-t', 'duniter', f"{uplanet_name}.G1", f"{uplanet_name}.G1"]
                result = subprocess.run(command, capture_output=True, text=True, check=True)
                treasury_pubkey = result.stdout.strip()
            
            if treasury_pubkey:
                self.shared_state['config']['uplanet_treasury_g1pub'] = treasury_pubkey
                self.logger.info(f"✅ Portefeuille Trésor configuré : {treasury_pubkey[:10]}...")
            else:
                self.logger.warning(f"⚠️ Script keygen non trouvé : {keygen_script}")
                self.shared_state['config']['uplanet_treasury_g1pub'] = None
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la configuration du portefeuille Trésor : {e}")
            self.shared_state['config']['uplanet_treasury_g1pub'] = None

    def load_existing_targets(self):
        """Charge automatiquement les cibles existantes au démarrage"""
        targets_file = os.path.join(self.shared_state['config']['workspace'], 'todays_targets.json')
        
        if os.path.exists(targets_file):
            try:
                with open(targets_file, 'r') as f:
                    targets = json.load(f)
                
                if targets:
                    self.shared_state['targets'] = targets
                    self.logger.info(f"✅ {len(targets)} cible(s) chargée(s) depuis 'todays_targets.json'")
                    
                    # Mettre à jour le statut de l'Agent Analyste
                    self.shared_state['status']['AnalystAgent'] = f"{len(targets)} cible(s) sélectionnée(s)"
                    
                    # Afficher un résumé des cibles
                    languages = {}
                    countries = {}
                    themes = set()
                    
                    for target in targets:
                        metadata = target.get('metadata', {})
                        languages[metadata.get('language', 'unknown')] = languages.get(metadata.get('language', 'unknown'), 0) + 1
                        countries[metadata.get('country', 'unknown')] = countries.get(metadata.get('country', 'unknown'), 0) + 1
                        themes.update(metadata.get('tags', []))
                    
                    self.logger.info(f"📊 Résumé des cibles :")
                    if languages:
                        lang_str = ", ".join([f"{lang}({count})" for lang, count in languages.items()])
                        self.logger.info(f"   🌍 Langues : {lang_str}")
                    if countries:
                        country_str = ", ".join([f"{country}({count})" for country, count in countries.items() if country != 'unknown'])
                        if country_str:
                            self.logger.info(f"   🌎 Pays : {country_str}")
                    if themes:
                        theme_str = ", ".join(list(themes)[:5])  # Limiter à 5 thèmes
                        self.logger.info(f"   🏷️ Thèmes principaux : {theme_str}")
                    
                else:
                    self.logger.info("📦 Fichier 'todays_targets.json' vide")
                    
            except (IOError, json.JSONDecodeError) as e:
                self.logger.warning(f"⚠️ Erreur lors du chargement des cibles : {e}")
                self.shared_state['targets'] = []
        else:
            self.logger.debug("📦 Aucun fichier 'todays_targets.json' trouvé")
            self.shared_state['targets'] = []


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
                
                if targets:
                    # Vérifier si les cibles sont chargées en mémoire
                    if self.shared_state['targets']:
                        self.logger.info(f"📦 Workspace: {len(targets)} cible(s) chargée(s) et prêtes")
                    else:
                        self.logger.info(f"📦 Workspace: {len(targets)} cible(s) en attente dans 'todays_targets.json' (recharger avec option 1)")
                else:
                    self.logger.info("📦 Workspace: Fichier 'todays_targets.json' vide")
                    
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
            print("1. Lancer l'Agent ANALYSTE : Identifier les cibles")
            print("2. Lancer l'Agent STRATEGE : Rédiger le message")
            print("3. Lancer l'Agent OPERATEUR : Envoyer la campagne")
            print("")
            print("4. Gérer les Mémoires Persona (0-9)")
            print("5. Gérer les Interactions de l'Opérateur")
            print("")
            # print("6. 🔄 Recharger les cibles existantes")
            print("7. Quitter")

            choice = input("> ")

            if choice == "1":
                result = self.run_analyst_submenu()
                if result == "continue":
                    # L'utilisateur veut continuer vers le Stratège
                    self.agents['stratège'].run()
                    if "Message sauvegardé" in self.shared_state['status'].get('StrategistAgent', ''):
                        last_action = "strategy_complete"
                    else:
                        last_action = None
                elif result == "quit":
                    self.logger.info("À bientôt, commandant ! 👋")
                    break
                elif "sélectionné" in self.shared_state['status'].get('AnalystAgent', ''):
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
                self.load_existing_targets()
                if self.shared_state['targets']:
                    last_action = "analysis_complete"
                    self.logger.info("✅ Cibles rechargées. Vous pouvez maintenant lancer l'Agent Stratège (2).")
                else:
                    self.logger.info("⚠️ Aucune cible à recharger. Utilisez l'Agent Analyste (1) pour sélectionner des cibles.")
                    last_action = None
            elif choice == "7":
                self.logger.info("À bientôt, commandant ! 👋")
                break
            else:
                self.logger.warning("Choix invalide, veuillez réessayer.")
                last_action = None # Réinitialiser en cas de choix invalide
                time.sleep(1)

    def run_analyst_submenu(self):
        progress = self.agents['analyste'].get_analysis_progress()
        total = progress.get('total', 0)
        gps_prospects = progress.get('gps_prospects', 0)
        lang_total = progress.get('language', 0)
        tags_total = progress.get('tags', 0)

        print("\n--- Menu Analyste ---")
        print(f"Statut de la base de connaissance : {total} profils au total.\n")
        
        print("🚀 INITIALISATION ET ANALYSE :")
        print(f"1. 🌍 Analyse Géo-Linguistique         ({lang_total} / {gps_prospects} profils avec GPS)")
        print(f"2. 🏷️ Analyse par Thèmes (Compétences, etc.) ({tags_total} / {total} profils analysés)")
        
        print("\n🔧 PERSONA - RAFFINAGE ET OPTIMISATION :")
        print("3. 🎭 Créer Banques persona (5-9) automatiquement selon les Thèmes détectés")
        print("4. 🌍 Ajouter Traductions Banque(s) persona (au choix, 1, 3, ou 0-3)")
        print("5. 🔄 Optimiser les Thèmes (recalculer le Top 50)")
        print("6. 🧪 Mode Test (cible unique pour validation)")
        
        print("\n🎯 CIBLAGE ET EXPORT :")
        print("7. 🎯 Ciblage Avancé Multi-Sélection (Thèmes + Filtres)")
        print("8. 🌍 Cibler par Langue")
        print("9. 🌍 Cibler par Pays")
        print("10. 🌍 Cibler par Région")
        print("11. 📊 Lancer une campagne à partir d'un Thème")
        print("12. ↩️  Retour")
        
        choice = input("> ")
        
        if choice == "1":
            self.agents['analyste'].run_geo_linguistic_analysis()
        elif choice == "2":
            self.agents['analyste'].run_thematic_analysis()
        elif choice == "3":
            self.agents['analyste'].create_automatic_personas()
        elif choice == "4":
            self.agents['analyste'].translate_persona_bank()
        elif choice == "5":
            self.agents['analyste'].optimize_thematic_analysis()
        elif choice == "6":
            self.agents['analyste'].run_test_mode()
        elif choice == "7":
            result = self.agents['analyste'].advanced_multi_selection_targeting()
            if result == "continue":
                return "continue"
            elif result == "quit":
                return "quit"
        elif choice == "8":
            result = self.agents['analyste'].select_cluster_by_language()
            if result == "continue":
                return "continue"
            elif result == "quit":
                return "quit"
        elif choice == "9":
            result = self.agents['analyste'].select_cluster_by_country()
            if result == "continue":
                return "continue"
            elif result == "quit":
                return "quit"
        elif choice == "10":
            result = self.agents['analyste'].select_cluster_by_region()
            if result == "continue":
                return "continue"
            elif result == "quit":
                return "quit"
        elif choice == "11":
            result = self.agents['analyste'].select_cluster_from_tags()
            if result == "continue":
                return "continue"
            elif result == "quit":
                return "quit"
        elif choice == "12":
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
        
        # Utiliser la nouvelle interface améliorée
        self.agents['opérateur'].view_interaction_history()

    def _process_incoming_response(self):
        """Interface pour traiter une réponse reçue"""
        print("\n📨 TRAITEMENT D'UNE RÉPONSE REÇUE")
        print("-" * 40)
        
        # Option 1: Lire automatiquement les nouveaux messages
        print("Options :")
        print("1. Lire les nouveaux messages (Jaklis)")
        print("2. Traiter une réponse manuelle")
        
        choice = input("> ")
        
        if choice == "1":
            # Utiliser la fonction de lecture automatique
            self.agents['opérateur']._run_receive_messages()
        elif choice == "2":
            # Interface manuelle
            self._process_manual_response()
        else:
            print("❌ Choix invalide")
            return

    def _process_manual_response(self):
        """Interface manuelle pour traiter une réponse"""
        print("\n📝 TRAITEMENT MANUEL D'UNE RÉPONSE")
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