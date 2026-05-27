from .base_agent import Agent
import json
import os
import subprocess
import re
import requests
from bs4 import BeautifulSoup
import html2text

class StrategistAgent(Agent):
    """
    L'agent Stratège utilise l'intelligence artificielle pour rédiger
    un message de campagne personnalisé en fonction de la cible fournie par l'Analyste.
    Il peut utiliser Perplexica pour enrichir son contexte.
    """
    def _select_bank_for_targets(self, targets, banks_config):
        """Sélectionne automatiquement le persona le plus appropriée pour les cibles"""
        if not targets or not banks_config.get('banks'):
            return None

        # Analyser les thèmes des cibles
        target_themes = set()
        for target in targets:
            # Extraire les thèmes du profil si disponibles
            if 'metadata' in target and 'tags' in target['metadata']:
                tags = target['metadata']['tags']
                if isinstance(tags, list) and tags != ['error']:
                    target_themes.update(tags)

        if not target_themes:
            self.logger.info("Aucun thème détecté dans les cibles, utilisation de la méthode classique")
            return None

        # Calculer le score de correspondance pour chaque persona
        bank_scores = {}
        for slot, bank in banks_config['banks'].items():
            if not bank.get('corpus'):
                continue  # Ignorer les personas sans corpus

            bank_themes = set(bank.get('themes', []))
            if not bank_themes:
                continue

            # Calculer l'intersection
            intersection = target_themes.intersection(bank_themes)
            if intersection:
                # Score basé sur le nombre de thèmes correspondants
                score = len(intersection) / len(bank_themes)
                bank_scores[slot] = {
                    'score': score,
                    'bank': bank,
                    'matching_themes': list(intersection)
                }

        if not bank_scores:
            self.logger.info("Aucun persona de mémoire ne correspond aux thèmes des cibles")
            return None

        # Sélectionner le persona avec le meilleur score
        best_slot = max(bank_scores.keys(), key=lambda x: bank_scores[x]['score'])
        best_match = bank_scores[best_slot]

        self.logger.info(f"Banque sélectionnée : {best_match['bank']['name']} (score: {best_match['score']:.2f})")
        self.logger.info(f"Thèmes correspondants : {', '.join(best_match['matching_themes'])}")

        return best_match['bank']

    def _choose_strategy_mode(self):
        """Permet de choisir le mode de rédaction du message"""
        print("\n🎯 MODE DE RÉDACTION DU MESSAGE")
        print("-" * 40)
        print("1. Mode Auto : Analyse automatique du profil et sélection de persona")
        print("2. Mode Persona : Sélection automatique basée sur les thèmes")
        print("3. Mode Classique : Choix manuel du persona")
        print()
        
        try:
            choice = input("Choisissez le mode (1-3) : ").strip()
            
            if choice == "1":
                print("✅ Mode Auto sélectionné")
                return "auto"  # ✅ Corrigé pour correspondre au nom affiché
            elif choice == "2":
                print("✅ Mode Persona sélectionné")
                return "persona"  # ✅ Corrigé pour correspondre au nom affiché
            elif choice == "3":
                print("✅ Mode Classique sélectionné")
                return "classic"
            else:
                print("❌ Choix invalide, utilisation du mode Auto")
                return "auto"
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Choix invalide, utilisation du mode Auto")
            return "auto"

    def run(self):
        """Lance la phase de rédaction du message de campagne"""
        self.logger.info("🤖 Agent Stratège : Démarrage de la rédaction du message...")
        self.shared_state['status']['StrategistAgent'] = "Rédaction en cours..."

        # Vérifier si l'analyse a été faite
        if not self.shared_state.get('targets'):
            self.logger.error("Aucune cible n'a été définie. Lancez l'Agent Analyste d'abord.")
            self.shared_state['status']['StrategistAgent'] = "Échec : Cibles manquantes."
            return

        # Vérifier si le portefeuille Trésor est configuré
        treasury_pubkey = self.shared_state['config'].get('uplanet_treasury_g1pub')
        if not treasury_pubkey:
            self.logger.error("La clé publique du Trésor UPlanet n'est pas configurée. Impossible de continuer.")
            self.shared_state['status']['StrategistAgent'] = "Échec : Clé du Trésor manquante."
            return

        # Vérification des API nécessaires au début
        if not self._check_ollama_once() or not self._check_perplexica_once():
            self.shared_state['status']['StrategistAgent'] = "Échec : Une API requise est indisponible."
            return

        # Charger la configuration des personas de mémoire
        banks_config_file = os.path.join(self.shared_state['config']['workspace'], 'memory_banks_config.json')
        banks_config = self._load_banks_config(banks_config_file)

        # Choisir le mode de rédaction
        mode = self._choose_strategy_mode()
        
        # Sélectionner le persona une seule fois pour toutes les cibles (sauf mode persona)
        selected_bank = None
        if mode == "classic":
            # Mode Classique : Choix manuel du persona une seule fois
            self.logger.info("📝 Mode Classique : Choix manuel du persona (une seule fois pour toutes les cibles)")
            selected_bank = self._choose_bank_for_classic_method(banks_config)
            if selected_bank:
                self.logger.info(f"🎭 Persona sélectionné pour toutes les cibles : {selected_bank['name']}")
        
        # Générer les messages personnalisés pour chaque cible
        personalized_messages = []
        
        for i, target in enumerate(self.shared_state['targets']):
            self.logger.info(f"🎯 Génération du message personnalisé pour la cible {i+1}/{len(self.shared_state['targets'])} : {target.get('uid', 'Unknown')}")
            
            if mode == "auto":
                # Mode Auto : Analyse automatique du profil et sélection de persona
                target_selected_bank = self._analyze_profile_and_select_bank([target], banks_config)
                if target_selected_bank:
                    self.logger.info(f"🎭 Mode Auto : Banque sélectionnée automatiquement : {target_selected_bank['name']}")
                    message_content = self._generate_personalized_message_with_persona_mode(target_selected_bank, treasury_pubkey, target)
                else:
                    self.logger.warning("⚠️ Mode Auto : Aucun persona adaptée trouvée, passage en mode classique")
                    message_content = self._generate_personalized_message_with_classic_mode(banks_config, treasury_pubkey, target, selected_bank)
            elif mode == "persona":
                # Mode Persona : Utilisation de la logique existante (sélection basée sur les thèmes)
                target_selected_bank = self._select_bank_for_targets([target], banks_config)
                if target_selected_bank:
                    self.logger.info(f"🎭 Mode Persona : Banque sélectionnée : {target_selected_bank['name']}")
                    message_content = self._generate_personalized_message_with_bank_mode(target_selected_bank, target)
                else:
                    self.logger.info("📝 Mode Persona : Aucun persona adaptée, passage en mode classique")
                    message_content = self._generate_personalized_message_with_classic_mode(banks_config, treasury_pubkey, target, selected_bank)
            else:
                # Mode Classique : Utiliser le persona déjà sélectionné
                self.logger.info("📝 Mode Classique : Utilisation du persona sélectionné")
                message_content = self._generate_personalized_message_with_classic_mode(banks_config, treasury_pubkey, target, selected_bank)

            if message_content and 'title' in message_content and 'text' in message_content:
                personalized_messages.append({
                    'target': target,
                    'title': message_content['title'],
                    'message': message_content['text'],
                    'mode': mode
                })
                self.logger.info(f"✅ Message personnalisé généré pour {target.get('uid', 'Unknown')}")
            else:
                self.logger.warning(f"⚠️ Échec de génération du message pour {target.get('uid', 'Unknown')}")

        if not personalized_messages:
            self.logger.error("Aucun message n'a pu être généré.")
            self.shared_state['status']['StrategistAgent'] = "Échec : Aucun message généré."
            return

        # Sauvegarder tous les messages personnalisés
        messages_file = os.path.join(self.shared_state['config']['workspace'], "personalized_messages.json")
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(personalized_messages, f, indent=2, ensure_ascii=False)

        report = f"{len(personalized_messages)} messages personnalisés générés et sauvegardés dans personalized_messages.json. Prêt pour validation par l'Opérateur."
        self.logger.info(f"✅ {report}")
        self.shared_state['status']['StrategistAgent'] = report
        self.shared_state['personalized_messages'] = personalized_messages

    def _check_ollama_once(self):
        """Vérifie une seule fois que l'API Ollama est disponible."""
        if not getattr(self, '_ollama_checked', False):
            ollama_script = self.shared_state['config']['ollama_script']
            self.logger.info("Vérification de l'API Ollama...")
            self.logger.debug(f"Exécution du script Ollama : {' '.join(ollama_script)}")
            subprocess.run(ollama_script, check=True, capture_output=True)
            self.logger.info("✅ Ollama API vérifiée.")
            setattr(self, '_ollama_checked', True)
        return getattr(self, '_ollama_checked', False)

    def _check_perplexica_once(self):
        """Vérifie une seule fois que l'API Perplexica est disponible."""
        if not getattr(self, '_perplexica_checked', False):
            perplexica_connector = self.shared_state['config']['perplexica_script_connector']
            perplexica_search = self.shared_state['config']['perplexica_script_search']
            self.logger.info("Vérification de la connexion à Perplexica...")
            self.logger.debug(f"Exécution du connecteur Perplexica : {' '.join(perplexica_connector)}")
            subprocess.run(perplexica_connector, check=True, capture_output=True)
            self.logger.info("✅ Perplexica API vérifiée.")
            setattr(self, '_perplexica_checked', True)
        return getattr(self, '_perplexica_checked', False)

    def _call_perplexica(self, query):
        perplexica_search = self.shared_state['config']['perplexica_script_search']
        self.logger.info(f"Recherche web assistée sur : \"{query}\"")
        self.logger.debug(f"Exécution de la recherche Perplexica : {perplexica_search} \"{query}\"")
        result = subprocess.run([perplexica_search, query], capture_output=True, text=True, check=True)
        self.logger.debug(f"Réponse brute de Perplexica : {result.stdout.strip()}")
        if result.stderr.strip():
            self.logger.debug(f"Erreurs Perplexica (stderr) : {result.stderr.strip()}")
        return result.stdout

    def _call_ia_for_writing(self, final_prompt, target_language='fr'):
        """Appelle l'IA pour la rédaction du message dans la langue spécifiée"""
        # Vérifier si le prompt contient déjà des instructions de langue
        language_indicators = {
            'en': ['english', 'in english', 'write in english', 'you are uplanet'],
            'fr': ['français', 'en français', 'écris en français', 'tu es l\'agent stratège'],
            'es': ['español', 'en español', 'escribe en español'],
            'de': ['deutsch', 'auf deutsch', 'schreibe auf deutsch'],
            'it': ['italiano', 'in italiano', 'scrivi in italiano'],
            'pt': ['português', 'em português', 'escreva em português']
        }
        
        prompt_lower = final_prompt.lower()
        prompt_is_in_target_language = False
        
        # Vérifier si le prompt contient déjà des indicateurs de langue cible
        if target_language in language_indicators:
            for indicator in language_indicators[target_language]:
                if indicator in prompt_lower:
                    prompt_is_in_target_language = True
                    break
        
        # Ajouter l'instruction de langue seulement si nécessaire
        if not prompt_is_in_target_language:
            language_instructions = {
                'fr': "\n\nIMPORTANT : Écris le message en français.",
                'en': "\n\nIMPORTANT : Write the message in English.",
                'es': "\n\nIMPORTANT : Escribe el mensaje en español.",
                'de': "\n\nIMPORTANT : Schreibe die Nachricht auf Deutsch.",
                'it': "\n\nIMPORTANT : Scrivi il messaggio in italiano.",
                'pt': "\n\nIMPORTANT : Escreva a mensagem em português."
            }
            
            language_instruction = language_instructions.get(target_language, f"\n\nIMPORTANT : Écris le message en {target_language.upper()}.")
            prompt_with_language = final_prompt + language_instruction
        else:
            prompt_with_language = final_prompt
        
        question_script = self.shared_state['config']['question_script']
        command = ['python3', question_script, prompt_with_language]
        self.logger.info("Génération du message par l'IA...")
        # self.logger.debug(f"Exécution de la commande de rédaction : {' '.join(command[:2])}...")
        # self.logger.debug(f"Prompt envoyé à l'IA (premiers 3500 caractères) : {prompt_with_language[:3500]}...")
        self.logger.debug(f"🌍 Langue cible : {target_language}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        # self.logger.debug(f"Réponse brute de l'IA (rédaction) : {result.stdout.strip()}")
        if result.stderr.strip():
            self.logger.debug(f"Erreurs de l'IA (stderr) : {result.stderr.strip()}")
        return result.stdout

    def manage_memory_banks(self):
        """Interface de gestion des mémoires persona thématiques"""
        self.logger.info("🏦 Gestionnaire de Persona Thématiques")

        # Charger la configuration des personas
        banks_config_file = os.path.join(self.shared_state['config']['workspace'], 'memory_banks_config.json')
        banks_config = self._load_banks_config(banks_config_file)

        try:
            while True:
                print("\n" + "="*60)
                print("🏦 GESTIONNAIRE DE BANQUES DE MÉMOIRE")
                print("="*60)
                print("Chaque persona représente une 'personnalité' pour l'Agent Stratège")
                print()

                # Afficher l'état des personas
                self._display_banks_status(banks_config)

                print("\nOptions :")
                print("1. Créer/Configurer un persona")
                print("2. Associer des thèmes à un persona")
                print("3. Remplir le corpus d'un persona")
                print("4. Tester un persona (générer un message)")
                print("5. Configurer les Liens")
                print("6. Synchroniser les thèmes depuis l'Agent Analyste")
                print("7. 📥 Importer un prompt G1FabLab dans la banque 4")
                print("8. 👤 Importer une mémoire utilisateur comme persona")
                print("9. 👁️ Voir les détails d'un persona")
                print("10. 🔍 Auditer un import de mémoire")
                print("11. Terminé.")

                choice = input("\nVotre choix : ").strip()

                if choice == "1":
                    banks_config = self._configure_bank(banks_config)
                elif choice == "2":
                    banks_config = self._associate_themes_to_bank(banks_config)
                elif choice == "3":
                    banks_config = self._fill_bank_corpus(banks_config)
                elif choice == "4":
                    self._test_bank_message(banks_config)
                elif choice == "5":
                    self.shared_state['config'] = self._configure_links(self.shared_state['config'])
                elif choice == "6":
                    banks_config = self._sync_themes_from_analyst(banks_config)
                elif choice == "7":
                    banks_config = self._import_g1fablab_prompt(banks_config)
                elif choice == "8":
                    banks_config = self._import_user_memory(banks_config)
                elif choice == "9":
                    self._view_bank_details(banks_config)
                elif choice == "10":
                    self._audit_memory_import(banks_config)
                elif choice == "11":
                    self._save_banks_config(banks_config, banks_config_file)
                    self.logger.info("✅ Configuration des personas sauvegardée")
                    break
                else:
                    print("❌ Choix invalide")

        except KeyboardInterrupt:
            print("\n\n⚠️ Gestionnaire interrompu par l'utilisateur.")
            print("💾 Sauvegarde automatique des modifications...")
            self._save_banks_config(banks_config, banks_config_file)
            self.logger.info("✅ Configuration sauvegardée automatiquement")
        except Exception as e:
            print(f"\n❌ Erreur dans le gestionnaire : {e}")
            print("💾 Tentative de sauvegarde des modifications...")
            try:
                self._save_banks_config(banks_config, banks_config_file)
                self.logger.info("✅ Configuration sauvegardée malgré l'erreur")
            except:
                self.logger.error("❌ Impossible de sauvegarder la configuration")

    def _load_banks_config(self, config_file):
        """Charge la configuration Persona"""
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Erreur lors du chargement de la config : {e}")

        # Configuration par défaut avec les 4 archétypes
        return {
            "banks": {
                "0": {
                    "name": "Ingénieur/Technicien",
                    "description": "Voix experte et pragmatique qui s'adresse à des pairs. Met l'accent sur la robustesse du protocole, la décentralisation réelle et le code open-source.",
                    "archetype": "Le Bâtisseur",
                    "themes": ["technologie", "developpeur", "crypto", "logiciel-libre", "g1", "innovation", "digital", "monnaie"],
                    "corpus": {
                        "vocabulary": ["protocole", "infrastructure", "décentralisation", "souveraineté cryptographique", "blockchain", "open-source", "résilience", "API", "IPFS", "NOSTR", "stack technique", "scalabilité", "on-chain"],
                        "arguments": [
                            "Le MULTIPASS est une implémentation NOSTR sécurisée, liant l'identité à une preuve cryptographique via la ToC Ğ1.",
                            "L'architecture Astroport (IPFS+NOSTR) est conçue pour la scalabilité, évitant la lourdeur de synchronisation inhérente à des protocoles comme Scuttlebutt.",
                            "Le Ẑen offre une comptabilité on-chain transparente pour la coopérative, transformant la gestion des actifs en transactions auditables."
                        ],
                        "tone": "pragmatique, précis, direct, informatif",
                        "examples": [
                            "Notre objectif est de fournir une stack technique complète pour l'auto-hébergement, de la gestion des clés à la persistance des données.",
                            "Le code est auditable sur notre dépôt Git ; les contributions et les tests de performance sont les bienvenus."
                        ]
                    }
                },
                "1": {
                    "name": "Philosophe/Militant",
                    "description": "Voix visionnaire et engagée qui s'adresse aux citoyens acteurs du changement. Met l'accent sur l'impact sociétal, la résilience collective et l'éthique des biens communs.",
                    "archetype": "Le Militant",
                    "themes": ["souverainete", "transition", "ecologie", "collectif", "local", "partage", "entraide", "communautaire", "liberte", "humain"],
                    "corpus": {
                        "vocabulary": ["souveraineté populaire", "biens communs", "résilience", "alternative aux GAFAM", "coopérative", "gouvernance", "pacte social", "reprendre le contrôle", "monnaie citoyenne", "dystopie cognitive", "régénération écologique"],
                        "arguments": [
                            "Nous bâtissons une alternative aux GAFAM où vos données ne sont pas une marchandise mais la fondation d'un bien commun.",
                            "Nous ne bâtissons pas un logiciel, nous construisons une société où la coopération prime sur la compétition.",
                            "Notre modèle coopératif garantit que les bénéfices sont réinvestis dans des projets concrets, comme l'acquisition de forêts-jardins.",
                            "Le projet est un acte politique : chaque nœud hébergé est une parcelle de souveraineté numérique reprise au système centralisé."
                        ],
                        "tone": "inspirant, visionnaire, éthique",
                        "examples": [
                            "Rejoignez un mouvement qui transforme la valeur numérique en un impact tangible et positif pour le vivant.",
                            "C'est une invitation à devenir co-propriétaire de notre futur numérique et écologique commun."
                        ]
                    }
                },
                "2": {
                    "name": "Créateur/Artisan",
                    "description": "Voix concrète et valorisante qui s'adresse aux artisans et créateurs. Met l'accent sur l'autonomie, les outils pratiques et la juste rémunération du savoir-faire.",
                    "archetype": "Le Créateur",
                    "themes": ["creatif", "savoir-faire", "artisanat", "creation", "artiste", "artisan", "creation", "musique", "produits-naturels", "fermentation"],
                    "corpus": {
                        "vocabulary": ["création de valeur" , "autonomie" , "circuit-court" , "juste rémunération" , "atelier numérique" , "savoir-faire" , "économie réelle" , "sans intermédiaire" , "portfolio décentralisé", "pièce unique", "atelier", "valorisation"],
                        "arguments": [
                            "Notre écosystème vous fournit les outils pour vendre vos créations en direct, sans verser de commission aux plateformes.",
                            "Le Ẑen est un outil stable qui permet de fixer un prix juste pour votre travail et d'être payé instantanément en Ğ1.",
                            "UPlanet est votre atelier numérique personnel : un espace pour exposer, partager et monétiser votre talent en toute liberté."
                        ],
                        "tone": "concret, valorisant, pragmatique, passionné",
                        "examples": [
                            "Votre talent a de la valeur. Notre système est conçu pour la reconnaître et la rémunérer équitablement.",
                            "Imaginez une place de marché où chaque artisan est aussi co-propriétaire de la place elle-même."
                        ]
                    }
                },
                "3": {
                    "name": "Holistique/Thérapeute",
                    "description": "Voix bienveillante et inspirante qui s'adresse à la communauté du bien-être et de la spiritualité. Met l'accent sur la qualité du lien, l'authenticité et un environnement sain.",
                    "archetype": "L'Holistique",
                    "themes": ["spiritualite", "nature", "permaculture", "bien-etre", "therapeute", "spirituel", "holistique", "sain", "naturel", "personnel", "transformation", "accompagnement"],
                    "corpus": {
                        "vocabulary": [ "harmonie", "équilibre", "bien-être", "conscience", "croissance", "connexion", "régénération", "soin", "énergie", "alignement", "communauté de confiance", "jardin numérique", "authenticité"],
                        "arguments": [
                            "Nous créons un espace numérique aligné avec des valeurs de respect et de bienveillance, loin du bruit et de la toxicité des réseaux sociaux.",
                            "La Toile de Confiance Ğ1 garantit des échanges entre humains certifiés, pour une communication authentique et sécurisée.",
                            "Notre technologie est conçue pour être au service du lien humain, et non pour capter et monétiser votre attention."
                        ],
                        "tone": "inspirant, doux, bienveillant",
                        "examples": [
                            "Retrouvez une connexion véritable au sein d'une communauté qui partage vos valeurs de croissance et de respect.",
                            "Nous bâtissons un jardin numérique où les belles idées et les relations saines peuvent grandir en paix."
                        ]
                    }
                }
            },
            "available_themes": self._get_available_themes()
        }

    def _get_available_themes(self):
        """Récupère la liste des thèmes disponibles depuis l'analyse"""
        try:
            enriched_file = self.shared_state['config']['enriched_prospects_file']
            if os.path.exists(enriched_file):
                with open(enriched_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extraire tous les thèmes uniques
                themes = set()
                for pubkey, profile_data in data.items():
                    metadata = profile_data.get('metadata', {})
                    tags = metadata.get('tags', [])
                    if isinstance(tags, list) and tags != ['error']:
                        themes.update(tags)

                return sorted(list(themes))
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des thèmes : {e}")

        return []

    def _get_top_themes_with_frequency(self, limit=50):
        """Récupère le top N des thèmes avec leur fréquence d'occurrence"""
        try:
            enriched_file = self.shared_state['config']['enriched_prospects_file']
            if os.path.exists(enriched_file):
                with open(enriched_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Compter la fréquence de chaque thème
                theme_counts = {}
                for pubkey, profile_data in data.items():
                    metadata = profile_data.get('metadata', {})
                    tags = metadata.get('tags', [])
                    if isinstance(tags, list) and tags != ['error']:
                        for tag in tags:
                            theme_counts[tag] = theme_counts.get(tag, 0) + 1

                # Trier par fréquence décroissante et prendre le top N
                sorted_themes = sorted(theme_counts.items(), key=lambda x: x[1], reverse=True)
                return sorted_themes[:limit]
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des thèmes : {e}")

        return []

    def _display_banks_status(self, banks_config):
        """Affiche l'état des mémoire persona"""
        print("\n📊 ÉTAT DE LA MÉMOIRE :")
        print("-" * 60)

        for slot, bank in banks_config['banks'].items():
            status = "✅" if bank.get('corpus') else "❌"
            themes_count = len(bank.get('themes', []))
            name = bank.get('name', 'Non configuré')
            print(f"{status} Persona #{slot}: {name}")
            print(f"    Archétype: {bank.get('archetype', 'Non défini')}")
            print(f"    Thèmes associés: {themes_count}")
            print(f"    Corpus: {'Rempli' if bank.get('corpus') else 'Vide'}")
            print()

    def _configure_bank(self, banks_config, bank_id=None):
        """Configure une mémoire Persona"""
        print("\n🔧 CONFIGURATION D'UN PERSONA")
        print("-" * 40)

        # Si bank_id est fourni, l'utiliser directement
        if bank_id is not None:
            slot = bank_id
        else:
            # Afficher les personas disponibles avec plus de détails
            for slot in range(12):
                bank = banks_config['banks'].get(str(slot), {})
                name = bank.get('name', 'Non configurée')
                archetype = bank.get('archetype', 'Non défini')
                has_corpus = bool(bank.get('corpus'))
                status = "✅" if has_corpus else "❌"
                print(f"{slot}. {status} {name} ({archetype})")

            try:
                slot = input("\nChoisissez le numéro du persona (0-11) : ").strip()
                if not (0 <= int(slot) <= 11):
                    print("❌ Numéro de persona invalide")
                    return banks_config
                slot = str(slot)
            except ValueError:
                print("❌ Entrée invalide")
                return banks_config

        bank = banks_config['banks'].get(slot, {})

        print(f"\n{'='*50}")
        print(f"CONFIGURATION DU PERSONA #{slot}")
        print(f"{'='*50}")

        # Afficher la configuration actuelle
        print(f"📝 Nom actuel : {bank.get('name', 'Non défini')}")
        print(f"🎭 Archétype actuel : {bank.get('archetype', 'Non défini')}")
        print(f"📖 Description actuelle :")
        current_desc = bank.get('description', 'Aucune description')
        if current_desc:
            print(f"   {current_desc}")
        else:
            print("   Aucune description")

        print(f"\n{'='*50}")
        print("MODIFICATIONS (Entrée pour garder la valeur actuelle)")
        print(f"{'='*50}")

        # Nom
        name = input(f"Nouveau nom [{bank.get('name', 'Non défini')}] : ").strip()
        if name:
            bank['name'] = name

        # Description
        print(f"\nDescription actuelle :")
        if current_desc:
            print(f"   {current_desc}")
        else:
            print("   Aucune description")
        description = input("Nouvelle description (Entrée pour garder) : ").strip()
        if description:
            bank['description'] = description

        # Archétype
        archetype = input(f"Nouvel archétype [{bank.get('archetype', 'Non défini')}] : ").strip()
        if archetype:
            bank['archetype'] = archetype

        banks_config['banks'][slot] = bank
        print(f"\n✅ Banque #{slot} configurée avec succès")

        return banks_config

    def _associate_themes_to_bank(self, banks_config):
        """Associe des thèmes à un Persona"""
        print("\n🏷️ ASSOCIATION DE THÈMES À UN PERSONA")
        print("-" * 40)

        # Afficher les personas avec leurs thèmes
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            name = bank.get('name', 'Non configurée')
            themes = bank.get('themes', [])
            if themes:
                themes_str = ', '.join(themes[:3])  # Afficher les 3 premiers thèmes
                if len(themes) > 3:
                    themes_str += f" (+{len(themes)-3} autres)"
                print(f"{slot}. {name}")
                print(f"   Thèmes : {themes_str}")
            else:
                print(f"{slot}. {name} (aucun thème)")

        try:
            slot = input("\nChoisissez le numéro du persona (0-11) : ").strip()
            if not (0 <= int(slot) <= 11):
                print("❌ Numéro de persona invalide")
                return banks_config

            slot = str(slot)
            bank = banks_config['banks'].get(slot, {})

            print(f"\nThèmes disponibles (Top 50 par fréquence) :")
            top_themes = self._get_top_themes_with_frequency(50)
            theme_names = [theme for theme, count in top_themes]
            
            for i, (theme, count) in enumerate(top_themes):
                print(f"{i+1:2d}. {theme} ({count} profils)")

            print(f"\nThèmes actuellement associés au persona #{slot} :")
            current_themes = bank.get('themes', [])
            
            if current_themes:
                for theme in current_themes:
                    print(f"  - {theme}")
                else:
                    print("  - Aucun thème associé")

            print("\nEntrez les numéros des thèmes à associer (séparés par des virgules) :")
            print("Exemple: 1,3,5 pour associer les thèmes 1, 3 et 5")
            print("💡 Conseil : Choisissez des thèmes pertinents pour ce persona")

            choice = input("Votre choix : ").strip()
            if choice:
                try:
                    indices = [int(x.strip()) - 1 for x in choice.split(',')]
                    selected_themes = [theme_names[i] for i in indices if 0 <= i < len(theme_names)]
                    bank['themes'] = selected_themes
                    banks_config['banks'][slot] = bank
                    print(f"✅ {len(selected_themes)} thèmes associés au persona #{slot}")
                except (ValueError, IndexError):
                    print("❌ Format invalide")

        except ValueError:
            print("❌ Entrée invalide")

        return banks_config

    def _fill_bank_corpus(self, banks_config):
        """Remplit le corpus d'un persona de mémoire"""
        print("\n📚 REMPLISSAGE DU CORPUS D'UN PERSONA")
        print("-" * 40)

        # Afficher les personas
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            name = bank.get('name', 'Non configurée')
            has_corpus = bool(bank.get('corpus'))
            status = "✅" if has_corpus else "❌"
            print(f"{slot}. {status} {name}")

        try:
            slot = input("\nChoisissez le numéro du persona (0-11) : ").strip()
            if not (0 <= int(slot) <= 11):
                print("❌ Numéro de persona invalide")
                return banks_config

            slot = str(slot)
            bank = banks_config['banks'].get(slot, {})

            # Afficher les détails des thèmes
            self._show_bank_themes_details(bank, slot)

            corpus = bank.get('corpus', {})

            # 1. Vocabulaire clé
            print(f"\n1️⃣ VOCABULAIRE CLÉ")
            print("-" * 30)
            current_vocab = ', '.join(corpus.get('vocabulary', []))
            print(f"Actuel : {current_vocab}")
            print("💡 Conseil : Entrez 8-12 mots techniques spécifiques, séparés par des virgules")
            vocab = input("Nouveau vocabulaire (Entrée pour garder) : ").strip()
            if vocab:
                corpus['vocabulary'] = [word.strip() for word in vocab.split(',') if word.strip()]
                print(f"✅ Vocabulaire mis à jour ({len(corpus['vocabulary'])} mots)")

            # 2. Arguments clés
            print(f"\n2️⃣ ARGUMENTS PRINCIPAUX")
            print("-" * 30)
            current_args = corpus.get('arguments', [])
            if current_args:
                print("Arguments actuels :")
                for i, arg in enumerate(current_args, 1):
                    print(f"  {i}. {arg}")

            print("\n💡 Conseil : Entrez 3-5 arguments clés (une phrase par ligne)")
            print("💡 Conseil : Appuyez sur Entrée deux fois pour terminer")
            print("💡 Conseil : Laissez vide pour garder les arguments actuels")

            new_args = []
            try:
                while True:
                    arg = input("Nouvel argument (ou Entrée pour terminer) : ").strip()
                    if not arg:
                        if new_args:  # Si on a déjà saisi des arguments
                            break
                        else:  # Si c'est le premier Entrée, garder les actuels
                            new_args = current_args
                            break
                    new_args.append(arg)
            except KeyboardInterrupt:
                print("\n⚠️ Saisie interrompue. Arguments actuels conservés.")
                new_args = current_args

            if new_args:
                corpus['arguments'] = new_args
                print(f"✅ Arguments mis à jour ({len(corpus['arguments'])} arguments)")

            # 3. Ton de communication
            print(f"\n3️⃣ TON DE COMMUNICATION")
            print("-" * 30)
            current_tone = corpus.get('tone', 'Non défini')
            print(f"Actuel : {current_tone}")
            print("💡 Conseil : 3-4 adjectifs maximum (ex: pragmatique, précis, direct)")
            tone = input("Nouveau ton (Entrée pour garder) : ").strip()
            if tone:
                corpus['tone'] = tone
                print(f"✅ Ton mis à jour : {tone}")

            # 4. Exemples de phrases
            print(f"\n4️⃣ EXEMPLES DE PHRASES")
            print("-" * 30)
            current_examples = corpus.get('examples', [])
            if current_examples:
                print("Exemples actuels :")
                for i, example in enumerate(current_examples, 1):
                    print(f"  {i}. {example}")

            print("\n💡 Conseil : Entrez 2-3 exemples de phrases engageantes")
            print("💡 Conseil : Appuyez sur Entrée deux fois pour terminer")
            print("💡 Conseil : Laissez vide pour garder les exemples actuels")

            new_examples = []
            try:
                while True:
                    example = input("Nouvel exemple (ou Entrée pour terminer) : ").strip()
                    if not example:
                        if new_examples:  # Si on a déjà saisi des exemples
                            break
                        else:  # Si c'est le premier Entrée, garder les actuels
                            new_examples = current_examples
                            break
                    new_examples.append(example)
            except KeyboardInterrupt:
                print("\n⚠️ Saisie interrompue. Exemples actuels conservés.")
                new_examples = current_examples

            if new_examples:
                corpus['examples'] = new_examples
                print(f"✅ Exemples mis à jour ({len(corpus['examples'])} exemples)")

            # Sauvegarder les modifications
            bank['corpus'] = corpus
            banks_config['banks'][slot] = bank

            print(f"\n{'='*60}")
            print(f"✅ CORPUS DU PERSONA #{slot} MIS À JOUR")
            print(f"{'='*60}")
            print(f"📝 Nom : {bank['name']}")
            print(f"🎭 Archétype : {bank['archetype']}")
            print(f"📚 Vocabulaire : {len(corpus.get('vocabulary', []))} mots")
            print(f"💬 Arguments : {len(corpus.get('arguments', []))} arguments")
            print(f"🎯 Ton : {corpus.get('tone', 'Non défini')}")
            print(f"📖 Exemples : {len(corpus.get('examples', []))} exemples")

        except KeyboardInterrupt:
            print("\n\n⚠️ Configuration interrompue par l'utilisateur.")
            print("💾 Les données saisies jusqu'à présent ont été sauvegardées.")
        except Exception as e:
            print(f"\n❌ Erreur lors du remplissage du corpus : {e}")
            print("💾 Les données saisies jusqu'à présent ont été sauvegardées.")

        return banks_config

    def _sync_themes_from_analyst(self, banks_config):
        """Synchronise les thèmes identifiés par l'Agent Analyste avec la configuration des personas"""
        print("\n🔄 SYNCHRONISATION DES THÈMES")
        print("-" * 40)

        # Récupérer les thèmes disponibles depuis l'analyse
        available_themes = self._get_available_themes()

        if not available_themes:
            print("❌ Aucun thème disponible depuis l'Agent Analyste")
            print("💡 Assurez-vous que l'Agent Analyste a été exécuté")
            return banks_config

        print(f"📋 Thèmes identifiés par l'Agent Analyste ({len(available_themes)}) :")
        for i, theme in enumerate(available_themes, 1):
            print(f"  {i:2d}. {theme}")

        # Mettre à jour la liste des thèmes disponibles dans la configuration
        banks_config['available_themes'] = available_themes

        print(f"\n✅ {len(available_themes)} thèmes synchronisés")
        print("💡 Vous pouvez maintenant associer ces thèmes aux personas")

        return banks_config

    def _show_bank_themes_details(self, bank, slot):
        """Affiche les détails des thèmes d'un persona"""
        print(f"\n{'='*60}")
        print(f"REMPLISSAGE DU CORPUS - PERSONA #{slot}")
        print(f"{'='*60}")
        print(f"📝 Nom : {bank.get('name', 'Non nommée')}")
        print(f"🎭 Archétype : {bank.get('archetype', 'Non défini')}")

        # Afficher les thèmes actuels
        current_themes = bank.get('themes', [])
        if current_themes:
            print(f"🏷️ Thèmes associés ({len(current_themes)}) : {', '.join(current_themes)}")
        else:
            print(f"🏷️ Thèmes associés : Aucun")

        # Afficher les thèmes disponibles pour référence
        available_themes = self._get_available_themes()
        if available_themes:
            print(f"📋 Thèmes disponibles ({len(available_themes)}) : {', '.join(available_themes[:10])}{'...' if len(available_themes) > 10 else ''}")

        print(f"{'='*60}")

    def _test_bank_message(self, banks_config, bank_id=None):
        """Teste la génération d'un message avec un persona spécifique"""
        print("\n🧪 TEST DE GÉNÉRATION DE MESSAGE")
        print("-" * 40)

        # Si bank_id est fourni, l'utiliser directement
        if bank_id is not None:
            slot = bank_id
        else:
            # Afficher les personas disponibles
            available_slots = []
            for slot in range(12):
                bank = banks_config['banks'].get(str(slot), {})
                if bank.get('name'):
                    print(f"{slot}. {bank['name']}")
                    available_slots.append(str(slot))

            print("r. Retour")

            try:
                slot = input("\nChoisissez le numéro du persona à tester (ou 'r' pour retour) : ").strip()
                if slot.lower() == 'r':
                    print("Retour au gestionnaire de banques...")
                    return
                if not (0 <= int(slot) <= 11):
                    print("❌ Numéro de persona invalide")
                    return
                slot = str(slot)
            except ValueError:
                print("❌ Entrée invalide")
                return

        bank = banks_config['banks'].get(slot, {})

        if not bank.get('name'):
            print("❌ Banque non configurée")
            return

        print(f"\nTest du persona #{slot} : {bank['name']}")

        # Afficher les liens disponibles
        available_links = self._get_available_links(self.shared_state['config'])
        if available_links:
            print(f"\n🔗 Liens disponibles pour injection :")
            for link in available_links:
                print(f"  {link}")
            print(f"\n💡 L'agent peut utiliser ces placeholders dans ses messages :")
            print(f"  • [Lien vers OpenCollective]")
            print(f"  • [Lien vers Documentation]")
            print(f"  • [Lien vers GitHub]")
            print(f"  • [Lien vers Discord]")
            print(f"  • etc...")
        else:
            print(f"\n⚠️ Aucun lien configuré. Les placeholders seront supprimés.")

        # Générer le message
        test_target_description = "Ceci est un test pour le persona. Le prospect est un utilisateur générique intéressé par UPlanet."
        message_obj = self._generate_message_with_bank(bank, test_target_description)

        print(f"\n{'='*50}")
        print(f"MESSAGE GÉNÉRÉ :")
        print(f"{'='*50}")

        if message_obj and 'title' in message_obj and 'text' in message_obj:
            print(f"Titre: {message_obj['title']}")
            print("-" * 20)
            print(message_obj['text'])
            message = message_obj['text']
        else:
            print("Erreur de génération du message.")
            message = ""
        
        print(f"{'='*50}")

        # Afficher les statistiques du message
        word_count = len(message.split())
        char_count = len(message)
        link_count = len(re.findall(r'https?://[^\s]+', message))

        print(f"\n📊 Statistiques du message :")
        print(f"  • Mots : {word_count}")
        print(f"  • Caractères : {char_count}")
        print(f"  • Liens détectés : {link_count}")

        try:
            pass  # Gestion des exceptions déjà présente
        except KeyboardInterrupt:
            print("\n⚠️ Test interrompu par l'utilisateur.")
        except Exception as e:
            print(f"❌ Erreur lors du test : {e}")

    def _generate_message_with_bank(self, bank, target_description, target_language='fr'):
        """Génère un message en utilisant une mémoire persona spécifique dans la langue cible"""
        # Vérifier si le persona a du contenu multilingue
        multilingual = bank.get('multilingual', {})
        
        if target_language in multilingual:
            # Utiliser le contenu multilingue
            lang_content = multilingual[target_language]
            corpus = {
                'tone': lang_content.get('tone', ''),
                'vocabulary': lang_content.get('vocabulary', []),
                'arguments': lang_content.get('arguments', []),
                'examples': lang_content.get('examples', [])
            }
            bank_name = lang_content.get('name', bank.get('name', ''))
            bank_archetype = lang_content.get('archetype', bank.get('archetype', ''))
            self.logger.debug(f"🌍 Utilisation du contenu multilingue pour {target_language}")
        else:
            # Fallback vers le contenu français
            corpus = bank.get('corpus', {})
            bank_name = bank.get('name', '')
            bank_archetype = bank.get('archetype', '')
            self.logger.debug(f"🌍 Utilisation du contenu français (fallback)")
        
        prompt = f"""Tu es l'Agent Stratège d'UPlanet. Tu dois rédiger un message de campagne personnalisé en adoptant la personnalité du persona de mémoire suivante :

ARCHÉTYPE : {bank_archetype}
NOM DU PERSONA : {bank_name}
THÈMES ASSOCIÉS : {', '.join(bank.get('themes', []))}

TON DE COMMUNICATION : {corpus.get('tone', 'Non défini')}

VOCABULAIRE CLÉ À UTILISER : {', '.join(corpus.get('vocabulary', []))}

ARGUMENTS PRINCIPAUX :
{chr(10).join([f"- {arg}" for arg in corpus.get('arguments', [])])}

EXEMPLES DE PHRASES :
{chr(10).join([f"- {example}" for example in corpus.get('examples', [])])}

{target_description}

TÂCHE : Rédige un message de campagne personnalisé pour présenter UPlanet et le MULTIPASS à ce prospect spécifique.

Le message doit :
1. Utiliser le vocabulaire et le ton de cette persona
2. Intégrer les arguments principaux
3. S'inspirer des exemples fournis
4. Être personnalisé et engageant
5. Inclure un appel à l'action vers OpenCollective

IMPORTANT - PLACEHOLDERS DE LIENS : Tu DOIS utiliser EXCLUSIVEMENT ces placeholders pour tous les liens. NE PAS écrire d'URLs directement :

OBLIGATOIRE - Utilise ces placeholders :
- [Lien vers OpenCollective] pour le financement participatif
- [Lien vers Documentation] pour la documentation technique
- [Lien vers GitHub] pour le code source
- [Lien vers Discord] pour la communauté
- [Lien vers Site Web] pour le site principal
- [Lien vers Blog] pour les actualités
- [Lien vers Forum] pour les discussions
- [Lien vers Wiki] pour la documentation collaborative
- [Lien vers Mastodon] pour le réseau social décentralisé
- [Lien vers Nostr] pour le protocole de communication
- [Lien vers IPFS] pour le stockage décentralisé
- [Lien vers G1] pour la monnaie libre
- [Lien vers UPlanet] pour le projet principal
- [Lien vers Astroport] pour l'infrastructure
- [Lien vers Zen] pour la comptabilité
- [Lien vers Multipass] pour l'identité

RÈGLE STRICTE : N'écris JAMAIS d'URLs complètes comme "https://..." dans ton message. Utilise UNIQUEMENT les placeholders ci-dessus.

Exemple correct : "Rejoignez-nous sur [Lien vers Discord]"
Exemple INCORRECT : "Rejoignez-nous sur https://discord.gg/uplanet"

Format de sortie : Ta réponse DOIT être un objet JSON valide avec deux clés :
1. "title": un titre court et percutant pour le message (5-10 mots maximum).
2. "text": le corps du message (150-200 mots maximum).

Exemple de format de sortie :
{{
  "title": "Invitation à co-créer le futur numérique",
  "text": "Bonjour {{uid}}, nous avons vu votre intérêt pour les technologies décentralisées et nous pensons que UPlanet pourrait vous passionner..."
}}"""

        try:
            raw_response = self._call_ia_for_writing(prompt, target_language)
            message_data = self._parse_ai_message_response(raw_response)
            
            # Inject links into the text part
            if message_data and 'text' in message_data:
                message_data['text'] = self._inject_links(message_data['text'], self.shared_state['config'])
            
            return message_data
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération avec persona : {e}")
            return {"title": "Erreur de génération", "text": f"Une erreur est survenue: {e}"}

    def _save_banks_config(self, banks_config, config_file):
        """Sauvegarde la configuration des personas"""
        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(banks_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde : {e}")

    def _inject_links(self, message, config):
        """Injecte intelligemment les liens dans le message en remplaçant les placeholders"""
        # Charger la configuration des liens depuis le fichier
        links_config = self._load_links_config()

        # Patterns de détection des placeholders avec gestion des caractères collés
        # Le pattern capture le placeholder ET les caractères collés après le ]
        link_patterns = {
            r'\[Lien vers OpenCollective\]([^\w\s]*)': links_config.get('opencollective', ''),
            r'\[Lien vers Documentation\]([^\w\s]*)': links_config.get('documentation', ''),
            r'\[Lien vers GitHub\]([^\w\s]*)': links_config.get('github', ''),
            r'\[Lien vers Discord\]([^\w\s]*)': links_config.get('discord', ''),
            r'\[Lien vers Telegram\]([^\w\s]*)': links_config.get('telegram', ''),
            r'\[Lien vers Site Web\]([^\w\s]*)': links_config.get('website', ''),
            r'\[Lien vers Blog\]([^\w\s]*)': links_config.get('blog', ''),
            r'\[Lien vers Forum\]([^\w\s]*)': links_config.get('forum', ''),
            r'\[Lien vers Wiki\]([^\w\s]*)': links_config.get('wiki', ''),
            r'\[Lien vers Mastodon\]([^\w\s]*)': links_config.get('mastodon', ''),
            r'\[Lien vers Nostr\]([^\w\s]*)': links_config.get('nostr', ''),
            r'\[Lien vers IPFS\]([^\w\s]*)': links_config.get('ipfs', ''),
            r'\[Lien vers G1\]([^\w\s]*)': links_config.get('g1', ''),
            r'\[Lien vers UPlanet\]([^\w\s]*)': links_config.get('uplanet', ''),
            r'\[Lien vers Astroport\]([^\w\s]*)': links_config.get('astroport', ''),
            r'\[Lien vers Zen\]([^\w\s]*)': links_config.get('zen', ''),
            r'\[Lien vers Multipass\]([^\w\s]*)': links_config.get('multipass', ''),
        }

        # Remplacer les placeholders par les vrais liens
        for pattern, link in link_patterns.items():
            if link:
                message = re.sub(pattern, link, message, flags=re.IGNORECASE)
            else:
                # Si le lien n'est pas configuré, supprimer le placeholder et les caractères collés
                message = re.sub(pattern, '', message, flags=re.IGNORECASE)

        # Nettoyer les espaces multiples créés par les suppressions
        message = re.sub(r'\s+', ' ', message)
        message = re.sub(r'\n\s*\n\s*\n', '\n\n', message)

        return message.strip()

    def _get_target_language(self, target):
        """
        Récupère la langue du profil depuis la base de connaissance.
        Retourne 'fr' par défaut si pas d'information disponible.
        """
        try:
            # Charger la base de connaissance
            kb_file = self.shared_state['config']['enriched_prospects_file']
            if not os.path.exists(kb_file):
                return 'fr'  # Défaut français
            
            with open(kb_file, 'r') as f:
                knowledge_base = json.load(f)
            
            # Chercher le profil par pubkey
            pubkey = target.get('pubkey')
            if not pubkey or pubkey not in knowledge_base:
                return 'fr'  # Défaut français
            
            profile_data = knowledge_base[pubkey]
            metadata = profile_data.get('metadata', {})
            language = metadata.get('language')
            
            # Retourner la langue si valide, sinon français par défaut
            if language and language != 'xx':
                self.logger.debug(f"🌍 Langue détectée pour {target.get('uid', 'N/A')} : {language}")
                return language
            else:
                self.logger.debug(f"🌍 Langue par défaut pour {target.get('uid', 'N/A')} : fr")
                return 'fr'
                
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur lors de la récupération de la langue : {e}")
            return 'fr'  # Défaut français

    def _get_available_links(self, config):
        """Retourne la liste des liens disponibles pour l'aide"""
        # Charger la configuration des liens depuis le fichier
        links_config = self._load_links_config()
        available_links = []

        link_names = {
            'opencollective': 'OpenCollective',
            'documentation': 'Documentation',
            'github': 'GitHub',
            'discord': 'Discord',
            'telegram': 'Telegram',
            'website': 'Site Web',
            'blog': 'Blog',
            'forum': 'Forum',
            'wiki': 'Wiki',
            'mastodon': 'Mastodon',
            'nostr': 'Nostr',
            'ipfs': 'IPFS',
            'g1': 'G1',
            'uplanet': 'UPlanet',
            'astroport': 'Astroport',
            'zen': 'Zen',
            'multipass': 'Multipass'
        }

        for key, name in link_names.items():
            if links_config.get(key):
                available_links.append(f"• {name}: {links_config[key]}")

        return available_links

    def _load_links_config(self):
        """Charge la configuration des liens depuis le fichier"""
        links_config_file = os.path.join(self.shared_state['config']['workspace'], 'links_config.json')

        # Configuration par défaut
        default_links = {
            'opencollective': 'https://opencollective.com/monnaie-libre',
            'documentation': 'https://github.com/papiche/Astroport.ONE/blob/master/WELCOME.md',
            'github': 'https://github.com/papiche/Astroport.ONE',
            'discord': 'https://ipfs.copylaradio.com/ipns/copylaradio.com/bang.html',
            'telegram': 'https://t.me/AstroportN1',
            'website': 'https://www.copylaradio.com',
            'blog': 'https://www.copylaradio.com/blog/blog-1',
            'forum': 'https://forum.monnaie-libre.fr/',
            'wiki': 'https://pad.p2p.legal/wiki',
            'mastodon': 'https://mastodon.social/@qoop',
            'nostr': 'https://fr.wikipedia.org/wiki/Nostr',
            'ipfs': 'https://fr.wikipedia.org/wiki/InterPlanetary_File_System',
            'g1': 'https://monnaie-libre.fr/',
            'uplanet': 'https://qo-op.com',
            'astroport': 'https://astroport.com',
            'zen': 'https://zen.g1sms.fr',
            'multipass': 'https://u.copylaradio.com/g1',
        }

        try:
            if os.path.exists(links_config_file):
                with open(links_config_file, 'r', encoding='utf-8') as f:
                    saved_links = json.load(f)
                    # Fusionner avec les valeurs par défaut (les valeurs sauvegardées ont la priorité)
                    links_config = {**default_links, **saved_links}
                    self.logger.info(f"✅ Configuration des liens chargée depuis {links_config_file}")
                    return links_config
            else:
                # Créer le fichier avec les valeurs par défaut
                self._save_links_config(default_links)
                self.logger.info(f"✅ Fichier de configuration des liens créé avec les valeurs par défaut")
                return default_links
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du chargement de la configuration des liens : {e}")
            return default_links

    def _save_links_config(self, links_config):
        """Sauvegarde la configuration des liens dans le fichier"""
        links_config_file = os.path.join(self.shared_state['config']['workspace'], 'links_config.json')

        try:
            os.makedirs(os.path.dirname(links_config_file), exist_ok=True)
            with open(links_config_file, 'w', encoding='utf-8') as f:
                json.dump(links_config, f, indent=2, ensure_ascii=False)
            self.logger.info(f"✅ Configuration des liens sauvegardée dans {links_config_file}")
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la sauvegarde de la configuration des liens : {e}")

    def _configure_links(self, config):
        """Configure les liens pour l'injection automatique"""
        print("\n🔗 CONFIGURATION DES LIENS")
        print("-" * 40)
        print("Ces liens seront automatiquement injectés dans les messages")
        print("quand l'agent utilise des placeholders comme [Lien vers OpenCollective]")
        print()

        # Charger la configuration actuelle
        links_config = self._load_links_config()

        # Liste des liens configurables avec leurs noms d'affichage
        link_configs = [
            ('opencollective', 'OpenCollective'),
            ('documentation', 'Documentation'),
            ('github', 'GitHub'),
            ('discord', 'Discord'),
            ('telegram', 'Telegram'),
            ('website', 'Site Web'),
            ('blog', 'Blog'),
            ('forum', 'Forum'),
            ('wiki', 'Wiki'),
            ('mastodon', 'Mastodon'),
            ('nostr', 'Nostr'),
            ('ipfs', 'IPFS'),
            ('g1', 'G1'),
            ('uplanet', 'UPlanet'),
            ('astroport', 'Astroport'),
            ('zen', 'Zen'),
            ('multipass', 'Multipass'),
        ]

        for key, name in link_configs:
            current_url = links_config.get(key, '')
            print(f"\n🔗 {name}")
            print(f"   Placeholder : [Lien vers {name}]")
            if current_url:
                print(f"   Actuel : {current_url}")
            else:
                print(f"   Actuel : Non configuré")

            new_url = input(f"   Nouveau lien (Entrée pour garder) : ").strip()
            if new_url:
                links_config[key] = new_url
                print(f"   ✅ {name} mis à jour")

        # Sauvegarder la configuration
        self._save_links_config(links_config)

        # Mettre à jour la configuration dans le shared_state
        config['links'] = links_config

        print(f"\n{'='*50}")
        print(f"✅ CONFIGURATION DES LIENS TERMINÉE")
        print(f"{'='*50}")
        print(f"🔗 Liens configurés : {len([k for k, v in links_config.items() if v])}")
        print(f"❌ Liens manquants : {len([k for k, v in links_config.items() if not v])}")

        return config

    def _replace_direct_urls_with_placeholders(self, message):
        """Remplace les URLs directes par des placeholders appropriés"""
        links_config = self._load_links_config()

        # Mapping des URLs vers les placeholders
        url_to_placeholder = {}
        for key, url in links_config.items():
            if url:
                url_to_placeholder[url] = f"[Lien vers {key.title()}]"

        # Remplacer les URLs par les placeholders
        for url, placeholder in url_to_placeholder.items():
            message = message.replace(url, placeholder)

        return message

    def _choose_bank_for_classic_method(self, banks_config):
        """Permet de choisir un persona de contexte pour la méthode classique"""
        print("\n🎭 CHOIX DU PERSONA DE CONTEXTE")
        print("-" * 40)
        print("Vous pouvez choisir un persona de mémoire pour enrichir le contexte")
        print("ou continuer sans persona (méthode classique pure)")
        print()
        
        # Afficher les personas disponibles dans l'ordre normal
        available_banks = []
        display_numbers = []
        
        # Parcourir les banques dans l'ordre (0, 1, 2, 3, 4, etc.)
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            if bank.get('name') and bank.get('corpus'):
                available_banks.append((slot, bank))
                display_numbers.append(slot)
                
                # Ajouter l'icône 🎯 pour la banque 4 si elle a un prompt G1FabLab
                if slot == 4 and bank.get('corpus', {}).get('g1fablab_prompt'):
                    print(f"🎯 {slot}. {bank['name']} - PROMPT G1FabLab ({bank.get('archetype', 'Non défini')})")
                else:
                    print(f"{slot}. {bank['name']} ({bank.get('archetype', 'Non défini')})")
        
        if not available_banks:
            print("❌ Aucun persona configurée avec corpus")
            return None
        
        print(f"{len(available_banks)}. Aucun persona (méthode classique pure)")
        
        try:
            choice = input(f"\nChoisissez un persona ({', '.join(map(str, display_numbers))}) ou {len(available_banks)} pour aucune : ").strip()
            choice_int = int(choice)
            
            if choice_int == len(available_banks):
                print("✅ Méthode classique pure sélectionnée")
                return None
            elif choice_int in display_numbers:
                # Trouver l'index dans available_banks
                index = display_numbers.index(choice_int)
                selected_slot, selected_bank = available_banks[index]
                print(f"✅ Banque sélectionnée : {selected_bank['name']}")
                if selected_slot == 4 and selected_bank.get('corpus', {}).get('g1fablab_prompt'):
                    print("🎯 Utilisation du prompt G1FabLab importé")
                return selected_bank
            else:
                print("❌ Choix invalide, utilisation de la méthode classique pure")
                return None
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Choix invalide, utilisation de la méthode classique pure")
            return None

    def _analyze_profile_and_select_bank(self, targets, banks_config):
        """Analyse le profil du prospect et sélectionne automatiquement le persona la plus adaptée"""
        self.logger.info("🔍 Mode Persona : Analyse du profil du prospect...")
        
        if not targets:
            return None
            
        target = targets[0]  # Prendre la première cible pour l'analyse
        
        # Construire le profil complet en enrichissant avec la base de connaissance
        profile_data = {
            'uid': target.get('uid', ''),
            'website': '',
            'tags': [],
            'description': '',
            'analyst_report': self.shared_state.get('analyst_report', ''),
            'web_context': ''
        }
        
        # Enrichir avec les données de la base de connaissance
        try:
            kb_file = self.shared_state['config']['enriched_prospects_file']
            if os.path.exists(kb_file):
                with open(kb_file, 'r') as f:
                    knowledge_base = json.load(f)
                
                # Chercher par pubkey d'abord, puis par uid
                profile_info = None
                search_key = None
                
                # Essayer par pubkey
                pubkey = target.get('pubkey')
                if pubkey and pubkey in knowledge_base:
                    profile_info = knowledge_base[pubkey]
                    search_key = pubkey
                    self.logger.debug(f"🔍 Profil trouvé par pubkey : {pubkey}")
                
                # Si pas trouvé par pubkey, essayer par uid
                if not profile_info:
                    uid = target.get('uid')
                    if uid:
                        for key, info in knowledge_base.items():
                            if info.get('uid') == uid:
                                profile_info = info
                                search_key = key
                                self.logger.debug(f"🔍 Profil trouvé par uid : {uid} (pubkey: {key})")
                                break
                
                if profile_info:
                    # Extraire les tags depuis les métadonnées
                    metadata = profile_info.get('metadata', {})
                    profile_data['tags'] = metadata.get('tags', [])
                    
                    # Extraire la description depuis le profil
                    profile = profile_info.get('profile', {})
                    if profile and '_source' in profile:
                        source = profile['_source']
                        profile_data['description'] = source.get('description', '')
                        
                        # Extraire le site web depuis les réseaux sociaux
                        socials = source.get('socials', [])
                        for social in socials:
                            if isinstance(social, dict) and social.get('type') == 'web':
                                profile_data['website'] = social.get('url', '')
                                break
                            elif isinstance(social, str) and 'http' in social:
                                profile_data['website'] = social
                                break
                    
                    self.logger.debug(f"✅ Profil enrichi pour {profile_data['uid']} : {len(profile_data['tags'])} tags, description: {len(profile_data['description'])} chars")
                    self.logger.debug(f"🔍 Tags extraits : {profile_data['tags']}")
                    self.logger.debug(f"🔍 Description extraite : {profile_data['description'][:100]}...")
                else:
                    self.logger.warning(f"⚠️ Profil non trouvé dans la base de connaissance pour {target.get('uid', 'Unknown')} (pubkey: {pubkey})")
            else:
                self.logger.warning("⚠️ Base de connaissance non trouvée")
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'enrichissement du profil : {e}")
        
        # Enrichir avec le contexte web si disponible (désactivé pour le premier message)
        if profile_data['website']:
            self.logger.debug(f"🔍 Site web détecté pour {profile_data['uid']} : {profile_data['website']}")
            profile_data['web_context'] = ""
        else:
            self.logger.debug(f"🔍 Pas de site web pour {profile_data['uid']}")
            profile_data['web_context'] = ""
        
        # Construire le prompt d'analyse
        analysis_prompt = f"""Tu es un expert en analyse de profils pour UPlanet. Tu dois analyser le profil d'un prospect et déterminer quelle persona de mémoire (persona) est la plus adaptée pour lui adresser un message personnalisé.

PROFIL DU PROSPECT :
- Identifiant : {profile_data['uid']}
- Site web : {profile_data['website']}
- Tags : {', '.join(profile_data['tags']) if profile_data['tags'] else 'Aucun tag'}
- Description : {profile_data['description'] if profile_data['description'] else 'Aucune description'}
- Rapport Analyste : {profile_data['analyst_report'] if profile_data['analyst_report'] else 'Aucun rapport'}
- Contexte Web : {profile_data['web_context'] if profile_data['web_context'] else 'Aucun contexte'}

BANQUES DE MÉMOIRE DISPONIBLES :"""

        # Debug : afficher les données du profil
        self.logger.debug(f"🔍 Données du profil pour l'analyse :")
        self.logger.debug(f"  - UID : {profile_data['uid']}")
        self.logger.debug(f"  - Site web : {profile_data['website']}")
        self.logger.debug(f"  - Tags : {profile_data['tags']}")
        self.logger.debug(f"  - Description : {profile_data['description'][:200] if profile_data['description'] else 'Aucune'}...")

        # Ajouter les informations sur les personas disponibles
        available_banks = []
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            if bank.get('name') and bank.get('corpus'):
                available_banks.append((slot, bank))
                vocab = ', '.join(bank.get('corpus', {}).get('vocabulary', []))  # All vocabulary keywords
                analysis_prompt += f"\n- Banque {slot}: {bank['name']} (Archetype: {bank.get('archetype', 'Non défini')}, Thèmes: {', '.join(bank.get('themes', []))}, Vocabulaire: {vocab})"
        
        self.logger.debug(f"🔍 Banques disponibles pour l'analyse : {len(available_banks)}")
        for slot, bank in available_banks:
            vocab = ', '.join(bank.get('corpus', {}).get('vocabulary', []))
            self.logger.debug(f"  - Banque {slot}: {bank['name']} ({bank.get('archetype', 'Non défini')}) : {vocab}")
        
        if not available_banks:
            self.logger.warning("⚠️ Aucun persona configurée pour l'analyse de profil")
            return None
        
        analysis_prompt += f"""

INSTRUCTIONS :
1. Analyse le profil du prospect en détail
2. Identifie ses centres d'intérêt, son domaine d'activité, ses valeurs
3. Détermine quel archetype de persona correspond le mieux à son profil
4. Réponds UNIQUEMENT avec le numéro du persona (0-{len(available_banks)}) qui correspond le mieux
5. Si aucun persona ne correspond vraiment, réponds "AUCUNE"

IMPORTANT : Assure-toi que ta réponse numérique correspond à ton raisonnement !

ANALYSE :"""

        # Appeler l'IA pour l'analyse
        try:
            self.logger.info("🧠 Analyse du profil par l'IA...")
            analysis_result = self._call_ia_for_writing(analysis_prompt)
            
            # Debug : afficher la réponse complète
            # self.logger.debug(f"🔍 Réponse complète de l'IA : {analysis_result}")
            
            # Extraire le numéro du persona sélectionnée
            import re
            bank_match = re.search(r'\b(\d+)\b', analysis_result.strip())
            
            if bank_match:
                bank_index = int(bank_match.group(1))
                self.logger.debug(f"🔍 Numéro de persona extrait : {bank_index} (/{len(available_banks)})")
                bank_list = [f"{slot}:{bank['name']}" for slot, bank in available_banks]
                self.logger.debug(f"🔍 Banques disponibles : {bank_list}")
                
                if 0 <= bank_index < len(available_banks):
                    selected_slot, selected_bank = available_banks[bank_index]
                    self.logger.info(f"✅ Banque sélectionnée automatiquement : {selected_bank['name']} (slot {selected_slot})")
                    
                    # Afficher le raisonnement
                    print(f"\n🎭 ANALYSE DE PROFIL - RÉSULTAT")
                    print(f"Prospect : {profile_data['uid']}")
                    print(f"Banque sélectionnée : {selected_bank['name']}")
                    print(f"Archetype : {selected_bank.get('archetype', 'Non défini')}")
                    print(f"Thèmes : {', '.join(selected_bank.get('themes', []))}")
                    print(f"Raisonnement IA : {bank_index}")
                    print(f"\n{analysis_result.strip()}")
                    
                    return selected_bank
                else:
                    self.logger.warning(f"⚠️ Index de persona invalide : {bank_index} (max: {len(available_banks)-1})")
                    bank_list = [f"{slot}:{bank['name']}" for slot, bank in available_banks]
                    self.logger.debug(f"🔍 Banques disponibles : {bank_list}")
            else:
                self.logger.warning("⚠️ Impossible de déterminer le persona depuis l'analyse IA")
                self.logger.debug(f"🔍 Réponse qui n'a pas de numéro : {analysis_result}")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'analyse de profil : {e}")
        
        return None

    def _generate_personalized_message_with_persona_mode(self, selected_bank, treasury_pubkey, target):
        """Génère un message personnalisé en mode Persona pour une cible spécifique"""
        self.logger.info(f"🎭 Mode Persona : Génération du message personnalisé pour {target.get('uid', 'Unknown')}")
        
        try:
            # Construire le contexte enrichi pour le persona
            analyst_report = self.shared_state.get('analyst_report', "Aucun rapport.")

            # Récupération du contenu du site web si disponible
            web_context = ""
            target_website = self._get_target_website(target)
            
            if target_website:
                self.logger.debug(f"🔍 Site web détecté pour {target.get('uid', 'Unknown')} : {target_website}")
                self.logger.info(f"🌐 Récupération du contenu du site : {target_website}...")
                web_context = self._fetch_website_content(target_website)
                self.logger.info("✅ Contenu web récupéré.")
            else:
                self.logger.debug(f"🔍 Pas de site web pour {target.get('uid', 'Unknown')}")

            # Construire la description complète pour le persona avec focus sur la personnalisation
            target_description = f"""PROFIL DU PROSPECT :

IDENTITÉ : {target.get('uid', 'Unknown')}
SITE WEB : {target_website}
TAGS : {', '.join(target.get('tags', []))}
DESCRIPTION : {target.get('description', '...')}
RAPPORT ANALYSTE : {analyst_report}

CONTEXTE WEB : {web_context if web_context else 'Non disponible'}

INSTRUCTIONS DE PERSONNALISATION :
- Adresse-toi directement à {target.get('uid', 'le prospect')}
- Utilise l'archetype "{selected_bank.get('archetype', 'Non défini')}" pour adapter ton ton
- Personnalise le message en fonction de ses centres d'intérêt spécifiques
- Crée une connexion émotionnelle basée sur son profil unique
- Sois authentique et adapte le style à sa personnalité"""

            # Récupérer la langue du profil
            target_language = self._get_target_language(target)
            
            # Générer le message avec le persona dans la langue cible
            message_content = self._generate_message_with_bank(selected_bank, target_description, target_language)
            
            return message_content
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération en mode Persona pour {target.get('uid', 'Unknown')} : {e}")
            return None

    def _generate_message_with_persona_mode(self, selected_bank, treasury_pubkey):
        """Génère un message en mode Persona avec le persona sélectionnée automatiquement (méthode legacy)"""
        return self._generate_personalized_message_with_persona_mode(selected_bank, treasury_pubkey, self.shared_state['targets'][0])

    def _generate_personalized_message_with_bank_mode(self, selected_bank, target):
        """Génère un message personnalisé en mode Auto pour une cible spécifique"""
        self.logger.info(f"🎭 Mode Auto : Génération du message personnalisé pour {target.get('uid', 'Unknown')}")
        
        try:
            # Construire le contexte pour le persona
            analyst_report = self.shared_state.get('analyst_report', "Aucun rapport.")

            # Récupération du contenu du site web si disponible
            web_context = ""
            target_website = self._get_target_website(target)
            
            if target_website:
                self.logger.debug(f"🔍 Site web détecté pour {target.get('uid', 'Unknown')} : {target_website}")
                self.logger.info(f"🌐 Récupération du contenu du site : {target_website}...")
                web_context = self._fetch_website_content(target_website)
                self.logger.info("✅ Contenu web récupéré.")
            else:
                self.logger.debug(f"🔍 Pas de site web pour {target.get('uid', 'Unknown')}")

            # Construire la description complète pour le persona
            target_description = f"Rapport Analyste: {analyst_report}"
            if web_context:
                target_description += f"\nContexte Web: {web_context}"
            target_description += f"\nCible spécifique: {json.dumps(target, indent=2, ensure_ascii=False)}"
            target_description += f"\nAdresse-toi directement à {target.get('uid', 'le prospect')}"

            # Récupérer la langue du profil
            target_language = self._get_target_language(target)
            
            # Générer le message avec le persona dans la langue cible
            message_content = self._generate_message_with_bank(selected_bank, target_description, target_language)
            
            return message_content
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération en mode Auto pour {target.get('uid', 'Unknown')} : {e}")
            return None

    def _generate_message_with_bank_mode(self, selected_bank):
        """Génère un message en mode Auto avec le persona sélectionnée automatiquement (méthode legacy)"""
        return self._generate_personalized_message_with_bank_mode(selected_bank, self.shared_state['targets'][0])

    def _generate_personalized_message_with_classic_mode(self, banks_config, treasury_pubkey, target, selected_bank=None):
        """Génère un message personnalisé en mode Classique pour une cible spécifique"""
        self.logger.info(f"📝 Mode Classique : Génération du message personnalisé pour {target.get('uid', 'Unknown')}")
        
        try:
            # Proposer le choix d'un persona de contexte seulement si pas déjà sélectionné
            if selected_bank is None:
                selected_bank = self._choose_bank_for_classic_method(banks_config)
            
            # Récupérer la langue du profil (doit être défini avant le bloc if)
            target_language = self._get_target_language(target)
            
            # --- Construction du Prompt Final ---
            # 1. Charger le prompt de base
            prompt_file = self.shared_state['config']['strategist_prompt_file']
            with open(prompt_file, 'r') as f:
                final_prompt = f.read()

            # Remplacer le placeholder du portefeuille Trésor
            final_prompt = final_prompt.replace('[UPLANET_TREASURY_G1PUB]', treasury_pubkey)

            # 2. Vérifier si c'est une banque G1FabLab et utiliser la fonction appropriée
            if selected_bank and selected_bank.get('corpus', {}).get('g1fablab_prompt'):
                # Utiliser directement la fonction G1FabLab
                self.logger.info(f"🎯 Mode Classique : Utilisation du prompt G1FabLab pour {selected_bank['name']}")
                
                # Construire la description de la cible
                target_description = f"Prospect : {target.get('uid', 'Unknown')}\n"
                target_description += f"Langue : {target_language}\n"
                if target.get('website'):
                    target_description += f"Site web : {target['website']}\n"
                if target.get('tags'):
                    target_description += f"Thèmes : {', '.join(target['tags'])}\n"
                
                # Utiliser la fonction spécialisée G1FabLab
                message_content = self._generate_message_with_bank(selected_bank, target_description, target_language)
                return message_content
            elif selected_bank:
                # Utiliser l'approche classique avec contexte
                self.logger.info(f"🎭 Contexte du persona : {selected_bank['name']}")
                
                # Utiliser le contenu multilingue si disponible
                multilingual = selected_bank.get('multilingual', {})
                if target_language in multilingual:
                    # Utiliser le contenu multilingue
                    lang_content = multilingual[target_language]
                    corpus = {
                        'tone': lang_content.get('tone', ''),
                        'vocabulary': lang_content.get('vocabulary', []),
                        'arguments': lang_content.get('arguments', []),
                        'examples': lang_content.get('examples', [])
                    }
                    bank_name = lang_content.get('name', selected_bank.get('name', ''))
                    bank_archetype = lang_content.get('archetype', selected_bank.get('archetype', ''))
                    self.logger.info(f"🌍 Utilisation du contenu multilingue pour {target_language}")
                else:
                    # Fallback vers le contenu français
                    corpus = selected_bank.get('corpus', {})
                    bank_name = selected_bank.get('name', '')
                    bank_archetype = selected_bank.get('archetype', '')
                    self.logger.info(f"🌍 Utilisation du contenu français (fallback)")
                
                final_prompt += f"\n\n--- CONTEXTE DU PERSONA DE MÉMOIRE ---"
                final_prompt += f"\nArchétype : {bank_archetype}"
                final_prompt += f"\nNom du persona : {bank_name}"
                final_prompt += f"\nThèmes : {', '.join(selected_bank.get('themes', []))}"
                final_prompt += f"\nTon : {corpus.get('tone', 'Non défini')}"
                final_prompt += f"\nVocabulaire clé : {', '.join(corpus.get('vocabulary', []))}"
                final_prompt += f"\nArguments : {chr(10).join([f'- {arg}' for arg in corpus.get('arguments', [])])}"
                final_prompt += f"\nExemples : {chr(10).join([f'- {ex}' for ex in corpus.get('examples', [])])}"
                
                # Ajouter les instructions pour les placeholders
                final_prompt += f"\n\nIMPORTANT - PLACEHOLDERS DE LIENS : Tu DOIS utiliser EXCLUSIVEMENT ces placeholders pour tous les liens :"
                final_prompt += f"\n- [Lien vers OpenCollective] pour le financement participatif"
                final_prompt += f"\n- [Lien vers Documentation] pour la documentation technique"
                final_prompt += f"\n- [Lien vers GitHub] pour le code source"
                final_prompt += f"\n- [Lien vers Discord] pour la communauté"
                final_prompt += f"\n- [Lien vers Site Web] pour le site principal"
                final_prompt += f"\n- [Lien vers Blog] pour les actualités"
                final_prompt += f"\n- [Lien vers Forum] pour les discussions"
                final_prompt += f"\n- [Lien vers Wiki] pour la documentation collaborative"
                final_prompt += f"\n- [Lien vers Mastodon] pour le réseau social décentralisé"
                final_prompt += f"\n- [Lien vers Nostr] pour le protocole de communication"
                final_prompt += f"\n- [Lien vers IPFS] pour le stockage décentralisé"
                final_prompt += f"\n- [Lien vers G1] pour la monnaie libre"
                final_prompt += f"\n- [Lien vers UPlanet] pour le projet principal"
                final_prompt += f"\n- [Lien vers Astroport] pour l'infrastructure"
                final_prompt += f"\n- [Lien vers Zen] pour la comptabilité"
                final_prompt += f"\n- [Lien vers Multipass] pour l'identité"
                final_prompt += f"\n\nRÈGLE STRICTE : N'écris JAMAIS d'URLs complètes comme 'https://...' dans ton message. Utilise UNIQUEMENT les placeholders ci-dessus."

            # 3. Ajouter le rapport de l'analyste
            analyst_report = self.shared_state.get('analyst_report', "Aucun rapport.")
            final_prompt += f"\n\n--- RAPPORT DE L'ANALYSTE ---\n{analyst_report}"

            # 4. Récupération directe du contenu du site web
            if target.get('website'):
                self.logger.info(f"🌐 Récupération du contenu du site : {target['website']}...")
                web_context = self._fetch_website_content(target['website'])
                self.logger.info("✅ Contenu web récupéré.")
                final_prompt += f"\n\n--- CONTENU DU SITE WEB ---\n{web_context}"

            # 5. Ajouter la cible spécifique pour la personnalisation
            final_prompt += f"\n\n--- CIBLE SPÉCIFIQUE ---\n{json.dumps(target, indent=2, ensure_ascii=False)}"
            final_prompt += f"\n\nAdresse-toi directement à {target.get('uid', 'le prospect')}"
            final_prompt += "\n\nMaintenant, en te basant sur TOUTES ces informations, rédige le message de campagne final. Ta réponse DOIT être uniquement le message, sans commentaire additionnel."

            self.logger.info("🧠 Prompt final construit. Interrogation de l'IA locale via question.py...")

            # --- Appel à l'IA locale ---
            message_content = self._call_ia_for_writing(final_prompt, target_language)
            
            # Appliquer l'injection de liens
            message_content = self._inject_links(message_content, self.shared_state['config'])
            
            return message_content
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération en mode Classique pour {target.get('uid', 'Unknown')} : {e}")
            return None

    def _generate_message_with_classic_mode(self, banks_config, treasury_pubkey):
        """Génère un message en mode Classique avec choix manuel de persona (méthode legacy)"""
        return self._generate_personalized_message_with_classic_mode(banks_config, treasury_pubkey, self.shared_state['targets'][0])

    def _parse_ai_message_response(self, raw_response: str) -> dict:
        """Parses the JSON response from the AI to extract title and text."""
        if not raw_response:
            return {"title": "Invitation UPlanet", "text": "Aucun message n'a été généré."}

        # The AI might wrap the JSON in markdown ```json ... ``` or just be noisy.
        # We look for the first '{' and the last '}' to extract the JSON object.
        match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if not match:
            self.logger.warning(f"No JSON object found in AI response. Response was: {raw_response}")
            return {"title": "Invitation UPlanet", "text": raw_response}
        
        clean_json_str = match.group(0)

        try:
            message_data = json.loads(clean_json_str)
            if not isinstance(message_data, dict) or 'title' not in message_data or 'text' not in message_data:
                self.logger.warning(f"AI response is not a valid message object: {message_data}")
                return {"title": "Invitation UPlanet", "text": raw_response}
            return message_data
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse AI JSON response. Cleaned string was: {clean_json_str}")
            return {"title": "Invitation UPlanet", "text": raw_response}

    def _import_g1fablab_prompt(self, banks_config):
        """Importe un prompt G1FabLab dans la banque 4 avec analyse IA automatique"""
        print("\n📥 IMPORTATION D'UN PROMPT G1FabLab")
        print("-" * 40)
        
        # Chemin vers le dossier g1fablab
        g1fablab_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'prompts', 'g1fablab')
        
        if not os.path.exists(g1fablab_dir):
            print(f"❌ Dossier G1FabLab non trouvé : {g1fablab_dir}")
            return banks_config
            
        # Lister les fichiers .sh disponibles
        g1fablab_files = []
        for file in os.listdir(g1fablab_dir):
            if file.endswith('.sh'):
                g1fablab_files.append(file)
        
        if not g1fablab_files:
            print("❌ Aucun fichier .sh trouvé dans le dossier G1FabLab")
            return banks_config
            
        # Afficher les fichiers disponibles
        print("📁 Fichiers G1FabLab disponibles :")
        for i, file in enumerate(sorted(g1fablab_files), 1):
            print(f"  {i}. {file}")
        
        print(f"\n💡 Sélectionnez un fichier (1-{len(g1fablab_files)}) ou 0 pour annuler")
        
        try:
            choice = input("Votre choix : ").strip()
            if choice == "0":
                print("❌ Importation annulée")
                return banks_config
                
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(g1fablab_files):
                selected_file = sorted(g1fablab_files)[choice_idx]
                file_path = os.path.join(g1fablab_dir, selected_file)
                
                # Lire le contenu du fichier
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                print(f"\n📄 Contenu du fichier {selected_file} :")
                print("-" * 50)
                print(content)
                print("-" * 50)
                
                # Demander confirmation
                confirm = input("\n✅ Voulez-vous importer ce prompt dans la banque 4 ? (o/n) : ").strip().lower()
                if confirm in ['o', 'oui', 'y', 'yes']:
                    # Extraire SUBJECT et MESSAGE_BODY
                    subject_match = re.search(r'SUBJECT="([^"]*)"', content)
                    message_match = re.search(r'MESSAGE_BODY="([^"]*)"', content, re.DOTALL)
                    
                    subject = subject_match.group(1) if subject_match else "Sujet non trouvé"
                    message_body = message_match.group(1) if message_match else "Message non trouvé"
                    
                    print(f"\n🤖 Analyse IA du prompt en cours...")
                    
                    # Analyser le prompt avec l'IA pour compléter les champs
                    bank_config = self._analyze_g1fablab_prompt_with_ai(subject, message_body, selected_file)
                    
                    # Créer ou mettre à jour la banque 4
                    banks_config['banks']["4"] = bank_config
                    
                    self.logger.info(f"✅ Prompt G1FabLab {selected_file} analysé et importé avec succès dans la banque 4")
                    print(f"✅ Prompt importé ! La banque 4 contient maintenant le prompt {selected_file}")
                    print(f"🤖 Configuration générée par IA :")
                    print(f"   📝 Nom : {bank_config['name']}")
                    print(f"   🎭 Archétype : {bank_config['archetype']}")
                    print(f"   🏷️ Thèmes : {', '.join(bank_config['themes'])}")
                    print(f"   📚 Vocabulaire : {len(bank_config['corpus']['vocabulary'])} mots")
                    print(f"   💬 Arguments : {len(bank_config['corpus']['arguments'])} arguments")
                    
                else:
                    print("❌ Importation annulée")
                    
            else:
                print("❌ Choix invalide")
                
        except (ValueError, IndexError):
            print("❌ Choix invalide")
        except Exception as e:
            print(f"❌ Erreur lors de l'importation : {e}")
            self.logger.error(f"Erreur lors de l'importation G1FabLab : {e}")

        return banks_config

    def _analyze_g1fablab_prompt_with_ai(self, subject, message_body, filename):
        """Analyse un prompt G1FabLab avec l'IA pour générer la configuration complète de la banque"""
        
        prompt = f"""Tu es un expert en marketing et en analyse de contenu. Tu dois analyser un prompt de campagne G1FabLab et générer une configuration complète pour un persona de mémoire.

PROMPT À ANALYSER :
Fichier : {filename}
Sujet : {subject}
Message : {message_body}

TÂCHE : Génère une configuration JSON complète pour un persona de mémoire avec les champs suivants :

1. **name** : Un nom court et descriptif pour ce persona (ex: "Bâtisseur Souverain", "Militant Écologique")
2. **description** : Une description claire du persona et de son rôle (2-3 phrases)
3. **archetype** : L'archétype principal (ex: "Le Bâtisseur", "Le Militant", "Le Visionnaire", "L'Entrepreneur")
4. **themes** : Liste de 6-8 thèmes clés extraits du message (ex: ["souverainete", "decentralisation", "monnaie-libre", "ecologie", "innovation", "communaute"])
5. **corpus** : Un objet avec :
   - **vocabulary** : 8-12 mots techniques spécifiques au domaine
   - **arguments** : 3-4 arguments clés extraits du message
   - **tone** : 3-4 adjectifs décrivant le ton de communication
   - **g1fablab_prompt** : Les données originales du prompt

IMPORTANT :
- Analyse le ton, l'objectif et la cible du message
- Identifie les thèmes principaux et les mots-clés
- Détermine l'archétype le plus approprié
- Génère un nom qui reflète l'essence du message

Format de sortie : Ta réponse DOIT être un objet JSON valide avec la structure exacte demandée.

Exemple de format :
{{
  "name": "Nom du Persona",
  "description": "Description du persona...",
  "archetype": "L'Archétype",
  "themes": ["theme1", "theme2", "theme3"],
  "corpus": {{
    "vocabulary": ["mot1", "mot2", "mot3"],
    "arguments": ["arg1", "arg2", "arg3"],
    "tone": "ton1, ton2, ton3",
    "examples": ["exemple1"],
    "g1fablab_prompt": {{
      "file": "{filename}",
      "subject": "{subject}",
      "message_body": "{message_body}"
    }}
  }}
}}"""

        try:
            print("🧠 Interrogation de l'IA pour l'analyse du prompt...")
            raw_response = self._call_ia_for_writing(prompt, 'fr')
            
            # Parser la réponse JSON
            try:
                # Nettoyer la réponse pour extraire le JSON
                json_start = raw_response.find('{')
                json_end = raw_response.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    json_str = raw_response[json_start:json_end]
                    bank_config = json.loads(json_str)
                    
                    # Validation des champs requis
                    required_fields = ['name', 'description', 'archetype', 'themes', 'corpus']
                    corpus_fields = ['vocabulary', 'arguments', 'tone', 'examples', 'g1fablab_prompt']
                    
                    for field in required_fields:
                        if field not in bank_config:
                            raise ValueError(f"Champ manquant : {field}")
                    
                    for field in corpus_fields:
                        if field not in bank_config['corpus']:
                            raise ValueError(f"Champ corpus manquant : {field}")
                    
                    return bank_config
                else:
                    raise ValueError("JSON non trouvé dans la réponse")
                    
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Erreur parsing JSON IA : {e}")
                print(f"⚠️ Erreur d'analyse IA, utilisation de la configuration par défaut")
                
                # Configuration par défaut en cas d'erreur
                return {
                    "name": f"G1FabLab - {filename}",
                    "description": f"Persona basé sur le prompt G1FabLab {filename}",
                    "archetype": "G1FabLab",
                    "themes": ["g1fablab", "monnaie-libre", "souverainete", "decentralisation"],
                    "corpus": {
                        "vocabulary": ["G1FabLab", "Ğ1", "monnaie libre", "souveraineté", "décentralisation", "MULTIPASS", "UPlanet", "Astroport"],
                        "arguments": [
                            f"Campagne G1FabLab : {subject}",
                            "Le G1FabLab travaille depuis 2018 à bâtir la suite logique de la Monnaie Libre",
                            "Notre écosystème souverain pour nos données, nos échanges et nos projets"
                        ],
                        "tone": "engagé, visionnaire, technique, communautaire",
                        "g1fablab_prompt": {
                            "file": filename,
                            "subject": subject,
                            "message_body": message_body
                        }
                    }
                }
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Erreur lors de l'analyse IA : {e}")
            print(f"❌ Erreur lors de l'analyse IA : {e}")
            
            # Configuration par défaut en cas d'erreur
            return {
                "name": f"G1FabLab - {filename}",
                "description": f"Persona basé sur le prompt G1FabLab {filename}",
                "archetype": "G1FabLab",
                "themes": ["g1fablab", "monnaie-libre", "souverainete", "decentralisation"],
                "corpus": {
                    "vocabulary": ["G1FabLab", "Ğ1", "monnaie libre", "souveraineté", "décentralisation", "MULTIPASS", "UPlanet", "Astroport"],
                    "arguments": [
                        f"Campagne G1FabLab : {subject}",
                        "Le G1FabLab travaille depuis 2018 à bâtir la suite logique de la Monnaie Libre",
                        "Notre écosystème souverain pour nos données, nos échanges et nos projets"
                    ],
                    "tone": "engagé, visionnaire, technique, communautaire",
                    "g1fablab_prompt": {
                        "file": filename,
                        "subject": subject,
                        "message_body": message_body
                    }
                }
            }

    def _import_user_memory(self, banks_config):
        """Importe une mémoire utilisateur comme persona avec analyse IA automatique"""
        print("\n👤 IMPORTATION D'UNE MÉMOIRE UTILISATEUR")
        print("-" * 40)
        
        # Chemin vers le dossier des mémoires utilisateur
        memory_base_dir = os.path.expanduser("~/.zen/flashmem")
        
        if not os.path.exists(memory_base_dir):
            print(f"❌ Dossier des mémoires non trouvé : {memory_base_dir}")
            return banks_config
            
        # Lister les utilisateurs disponibles (dossiers)
        user_dirs = []
        for item in os.listdir(memory_base_dir):
            item_path = os.path.join(memory_base_dir, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                # Vérifier s'il y a des fichiers slot*.json
                slot_files = [f for f in os.listdir(item_path) if f.startswith('slot') and f.endswith('.json')]
                if slot_files:
                    user_dirs.append((item, len(slot_files)))
        
        if not user_dirs:
            print("❌ Aucun utilisateur avec des mémoires trouvé")
            return banks_config
            
        # Afficher les utilisateurs disponibles
        print("👥 Utilisateurs avec mémoires disponibles :")
        for i, (user_id, slot_count) in enumerate(sorted(user_dirs), 1):
            print(f"  {i}. {user_id} ({slot_count} slot(s))")
        
        print(f"\n💡 Sélectionnez un utilisateur (1-{len(user_dirs)}) ou 0 pour annuler")
        
        try:
            choice = input("Votre choix : ").strip()
            if choice == "0":
                print("❌ Importation annulée")
                return banks_config
                
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(user_dirs):
                selected_user, slot_count = sorted(user_dirs)[choice_idx]
                user_memory_dir = os.path.join(memory_base_dir, selected_user)
                
                # Lister les slots disponibles pour cet utilisateur
                slot_files = []
                for file in os.listdir(user_memory_dir):
                    if file.startswith('slot') and file.endswith('.json'):
                        slot_num = file.replace('slot', '').replace('.json', '')
                        slot_files.append((int(slot_num), file))
                
                slot_files.sort()  # Trier par numéro de slot
                
                print(f"\n📁 Slots disponibles pour {selected_user} :")
                for slot_num, filename in slot_files:
                    slot_path = os.path.join(user_memory_dir, filename)
                    try:
                        with open(slot_path, 'r', encoding='utf-8') as f:
                            slot_data = json.load(f)
                        message_count = len(slot_data.get('messages', []))
                        print(f"  {slot_num}. Slot {slot_num} ({message_count} messages)")
                    except:
                        print(f"  {slot_num}. Slot {slot_num} (erreur de lecture)")
                
                # Adapter le message selon le nombre de slots
                if len(slot_files) == 1:
                    print(f"\n💡 Sélectionnez le slot {slot_files[0][0]} ou 'q' pour annuler")
                else:
                    print(f"\n💡 Sélectionnez un slot (0-{max([s[0] for s in slot_files])}) ou 'q' pour annuler")
                
                slot_choice = input("Votre choix : ").strip()
                if slot_choice.lower() in ['q', 'quit', 'annuler', 'cancel']:
                    print("❌ Importation annulée")
                    return banks_config
                
                try:
                    slot_num = int(slot_choice)
                    slot_filename = f"slot{slot_num}.json"
                    slot_path = os.path.join(user_memory_dir, slot_filename)
                    
                    if not os.path.exists(slot_path):
                        print(f"❌ Slot {slot_num} non trouvé")
                        return banks_config
                    
                    # Lire le contenu du slot
                    with open(slot_path, 'r', encoding='utf-8') as f:
                        slot_data = json.load(f)
                    
                    messages = slot_data.get('messages', [])
                    if not messages:
                        print(f"❌ Aucun message trouvé dans le slot {slot_num}")
                        return banks_config
                    
                    print(f"\n📄 Contenu du slot {slot_num} de {selected_user} :")
                    print("-" * 50)
                    for i, msg in enumerate(messages[-10:], 1):  # Afficher les 10 derniers messages
                        timestamp = msg.get('timestamp', 'N/A')
                        content = msg.get('content', 'N/A')
                        print(f"{i}. [{timestamp}] {content[:100]}{'...' if len(content) > 100 else ''}")
                    if len(messages) > 10:
                        print(f"... et {len(messages) - 10} autres messages")
                    print("-" * 50)
                    
                    # Demander confirmation
                    confirm = input(f"\n✅ Voulez-vous importer cette mémoire comme persona ? (o/n) : ").strip().lower()
                    if confirm in ['o', 'oui', 'y', 'yes']:
                        # Demander le numéro de banque
                        print(f"\n🏦 Dans quelle banque voulez-vous importer ce persona ?")
                        print("Banques disponibles : 0-9 (0 = banque par défaut)")
                        bank_choice = input("Numéro de banque : ").strip()
                        
                        try:
                            bank_num = int(bank_choice)
                            if not (0 <= bank_num <= 9):
                                print("❌ Numéro de banque invalide (0-9)")
                                return banks_config
                        except ValueError:
                            print("❌ Numéro de banque invalide")
                            return banks_config
                        
                        print(f"\n🤖 Analyse IA de la mémoire en cours...")
                        
                        # Analyser la mémoire avec l'IA pour compléter les champs
                        bank_config = self._analyze_user_memory_with_ai(messages, selected_user, slot_num)
                        
                        # Créer ou mettre à jour la banque
                        banks_config['banks'][str(bank_num)] = bank_config
                        
                        self.logger.info(f"✅ Mémoire utilisateur {selected_user}/slot{slot_num} analysée et importée avec succès dans la banque {bank_num}")
                        print(f"✅ Mémoire importée ! La banque {bank_num} contient maintenant le persona de {selected_user}")
                        print(f"🤖 Configuration générée par IA :")
                        print(f"   📝 Nom : {bank_config['name']}")
                        print(f"   🎭 Archétype : {bank_config['archetype']}")
                        print(f"   🏷️ Thèmes : {', '.join(bank_config['themes'])}")
                        print(f"   📚 Vocabulaire : {len(bank_config['corpus']['vocabulary'])} mots")
                        print(f"   💬 Arguments : {len(bank_config['corpus']['arguments'])} arguments")
                        
                    else:
                        print("❌ Importation annulée")
                        
                except ValueError:
                    print("❌ Choix de slot invalide")
                    
            else:
                print("❌ Choix invalide")
                
        except (ValueError, IndexError):
            print("❌ Choix invalide")
        except Exception as e:
            print(f"❌ Erreur lors de l'importation : {e}")
            self.logger.error(f"Erreur lors de l'importation mémoire utilisateur : {e}")

        return banks_config

    def _analyze_user_memory_with_ai(self, messages, user_id, slot_num):
        """Analyse une mémoire utilisateur avec l'IA pour générer la configuration complète de la banque"""
        
        # Filtrer les messages selon les règles spécifiées
        filtered_messages = []
        audit_log = []
        
        for msg in messages:
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', 'N/A')
            
            # Vérifier si le message contient des tags
            has_bro_bot = '#BRO' in content.upper() or '#BOT' in content.upper()
            has_rec = '#rec' in content.lower()
            has_rec2 = '#rec2' in content.lower()
            has_search = '#search' in content.lower()
            has_mem = '#mem' in content.lower()
            has_hist = 'Historique' in content or '📝' in content
            
            # Nettoyer le contenu pour l'analyse
            cleaned_content = content.replace('#BRO', '').replace('#BOT', '').replace('#rec', '').replace('#rec2', '').replace('#search', '').replace('#mem', '').strip()
            
            # Règles de filtrage améliorées
            should_include = False
            reason = ""
            
            # Règle 1: Messages sans tags (conversation naturelle)
            if not has_bro_bot and not has_rec and not has_rec2 and not has_search and not has_mem and not has_hist:
                if len(cleaned_content) > 5:  # Réduire le seuil minimum
                    should_include = True
                    reason = "Message naturel sans tags"
            
            # Règle 2: Messages avec #rec (demande utilisateur)
            elif has_rec and not has_rec2 and not has_hist:
                if len(cleaned_content) > 5:
                    should_include = True
                    reason = "Demande utilisateur (#rec)"
            
            # Règle 3: Messages avec #rec2 (réponse du bot) - mais filtrer les réponses trop longues
            elif has_rec2 and not has_hist:
                if len(cleaned_content) > 10 and len(cleaned_content) < 3000:  # Augmenter les limites
                    should_include = True
                    reason = "Réponse bot (#rec2)"
            
            # Règle 4: Messages avec #search (recherche utilisateur)
            elif has_search and not has_rec2 and not has_hist:
                if len(cleaned_content) > 5:
                    should_include = True
                    reason = "Recherche utilisateur (#search)"
            
            # Règle 5: Messages avec #BRO/#BOT mais contenu substantiel
            elif has_bro_bot and not has_rec2 and not has_hist:
                if len(cleaned_content) > 10:
                    should_include = True
                    reason = "Message avec tags mais contenu substantiel"
            
            if should_include:
                filtered_messages.append(msg)
                audit_log.append(f"✅ INCLUS [{timestamp}] - {reason}: {cleaned_content[:100]}...")
            else:
                audit_log.append(f"❌ EXCLU [{timestamp}] - {reason}: {cleaned_content[:100]}...")
        
        # Afficher l'audit si demandé
        print(f"📊 Filtrage des messages : {len(messages)} total → {len(filtered_messages)} valides")
        if len(filtered_messages) < 2:
            print("⚠️ Très peu de messages valides trouvés. Audit détaillé :")
            for log_entry in audit_log:
                print(f"  {log_entry}")
        
        if not filtered_messages:
            print(f"⚠️ Aucun message valide trouvé après filtrage pour {user_id}/slot{slot_num}")
            # Retourner une configuration par défaut
            return {
                "name": f"Persona - {user_id}",
                "description": f"Persona basé sur la mémoire de {user_id} (slot {slot_num}) - Aucun message valide après filtrage",
                "archetype": "Utilisateur",
                "themes": ["utilisateur", "personnalite", "conversation", "interet"],
                "corpus": {
                    "vocabulary": ["utilisateur", "personnalite", "conversation", "interet", "discussion"],
                    "arguments": [
                        f"Persona basé sur {user_id}",
                        f"Mémoire de conversation du slot {slot_num}",
                        f"Style de communication personnalisé"
                    ],
                    "tone": "personnel, authentique, naturel",
                    "examples": ["Messages de l'utilisateur"],
                    "user_memory": {
                        "user_id": user_id,
                        "slot": slot_num,
                        "message_count": len(messages),
                        "filtered_message_count": 0,
                        "sample_messages": []
                    }
                }
            }
        
        # Préparer le contenu des messages filtrés pour l'analyse
        messages_text = ""
        sample_messages = []
        
        for i, msg in enumerate(filtered_messages[-10:], 1):  # Utiliser les 10 derniers messages filtrés
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', 'N/A')
            # Nettoyer les tags pour l'analyse
            cleaned_content = content.replace('#BRO', '').replace('#BOT', '').replace('#rec', '').replace('#rec2', '').replace('#search', '').replace('#mem', '').strip()
            
            if len(cleaned_content) > 5:  # Éviter les messages vides après nettoyage
                messages_text += f"Message {i} [{timestamp}]: {cleaned_content}\n\n"
                sample_messages.append(cleaned_content[:200] + "..." if len(cleaned_content) > 200 else cleaned_content)
        
        # Si pas assez de contenu, essayer d'inclure plus de messages
        if len(messages_text.strip()) < 100:
            print("⚠️ Contenu insuffisant, élargissement du filtrage...")
            for msg in messages[-20:]:
                content = msg.get('content', '')
                timestamp = msg.get('timestamp', 'N/A')
                cleaned_content = content.replace('#BRO', '').replace('#BOT', '').replace('#rec', '').replace('#rec2', '').replace('#search', '').replace('#mem', '').strip()
                
                if len(cleaned_content) > 20 and 'Historique' not in content and '📝' not in content:
                    messages_text += f"Message [{timestamp}]: {cleaned_content}\n\n"
                    sample_messages.append(cleaned_content[:200] + "..." if len(cleaned_content) > 200 else cleaned_content)
        
        prompt = f"""Tu es un expert en analyse de personnalité et en marketing. Tu dois analyser une mémoire de conversation d'un utilisateur et générer une configuration complète pour un persona de mémoire.

MÉMOIRE À ANALYSER :
Utilisateur : {user_id}
Slot : {slot_num}
Nombre total de messages : {len(messages)}
Nombre de messages filtrés (valides) : {len(filtered_messages)}

MESSAGES FILTRÉS (pour analyse) :
{messages_text}

TÂCHE : Génère une configuration JSON complète pour un persona de mémoire avec les champs suivants :

1. **name** : Un nom court et descriptif pour ce persona basé sur sa personnalité (ex: "Le Curieux", "Le Technique", "Le Créatif")
2. **description** : Une description claire du persona et de sa personnalité (2-3 phrases)
3. **archetype** : L'archétype principal (ex: "Le Curieux", "Le Technique", "Le Créatif", "Le Pragmatique", "Le Visionnaire")
4. **themes** : Liste de 6-8 thèmes clés extraits des conversations (ex: ["technologie", "ecologie", "monnaie-libre", "innovation", "communaute", "developpement"])
5. **corpus** : Un objet avec :
   - **vocabulary** : 8-12 mots techniques ou expressions spécifiques utilisées
   - **arguments** : 3-4 arguments clés ou points de vue exprimés
   - **tone** : 3-4 adjectifs décrivant le ton de communication
   - **examples** : 2-3 exemples de phrases typiques du persona
   - **user_memory** : Informations sur la source (user_id, slot, message_count, filtered_message_count, sample_messages)

IMPORTANT : 
- Analyse le CONTENU RÉEL des messages, pas les tags ou commandes
- Identifie les VRAIS centres d'intérêt et la personnalité
- Évite les généralités, sois spécifique
- Si le contenu est insuffisant, indique-le clairement

Réponds UNIQUEMENT avec le JSON valide, sans texte avant ou après."""

        print("🧠 Interrogation de l'IA pour l'analyse de la mémoire...")
        
        try:
            response = self._call_ia_for_writing(prompt, 'fr')
            config = self._parse_persona_config_response(response)
            
            # Ajouter les informations de mémoire utilisateur
            if 'corpus' not in config:
                config['corpus'] = {}
            config['corpus']['user_memory'] = {
                "user_id": user_id,
                "slot": slot_num,
                "message_count": len(messages),
                "filtered_message_count": len(filtered_messages),
                "sample_messages": sample_messages[:5]  # Limiter à 5 exemples
            }
            
            return config
            
        except Exception as e:
            print(f"❌ Erreur lors de l'analyse IA : {e}")
            # Retourner une configuration par défaut en cas d'erreur
            return {
                "name": f"Persona - {user_id}",
                "description": f"Persona basé sur la mémoire de {user_id} (slot {slot_num}) - Erreur d'analyse IA",
                "archetype": "Utilisateur",
                "themes": ["utilisateur", "personnalite", "conversation"],
                "corpus": {
                    "vocabulary": ["utilisateur", "personnalite", "conversation"],
                    "arguments": [
                        f"Persona basé sur {user_id}",
                        f"Mémoire de conversation du slot {slot_num}",
                        f"Erreur lors de l'analyse IA"
                    ],
                    "tone": "personnel, authentique",
                    "examples": ["Messages de l'utilisateur"],
                    "user_memory": {
                        "user_id": user_id,
                        "slot": slot_num,
                        "message_count": len(messages),
                        "filtered_message_count": len(filtered_messages),
                        "sample_messages": sample_messages[:3]
                    }
                }
            }

    def _view_bank_details(self, banks_config):
        """Affiche les détails complets d'un persona configuré"""
        print("\n👁️ CONSULTATION DES DÉTAILS D'UN PERSONA")
        print("-" * 50)
        
        # Lister les personas disponibles
        available_banks = []
        for bank_id, bank in banks_config['banks'].items():
            if bank.get('name'):  # Seulement les personas configurés
                available_banks.append((bank_id, bank))
        
        if not available_banks:
            print("❌ Aucun persona configuré trouvé")
            return
        
        print("📋 Personas disponibles :")
        for bank_id, bank in available_banks:
            print(f"  {bank_id}. {bank['name']}")
        
        print(f"\n💡 Sélectionnez un persona (0-{max([int(b[0]) for b in available_banks])}) ou 'q' pour annuler")
        
        choice = input("Votre choix : ").strip()
        if choice.lower() in ['q', 'quit', 'annuler', 'cancel']:
            print("❌ Consultation annulée")
            return
        
        try:
            bank_id = int(choice)
            if str(bank_id) not in banks_config['banks']:
                print("❌ Persona non trouvé")
                return
            
            bank = banks_config['banks'][str(bank_id)]
            
            # Afficher les détails complets
            print(f"\n" + "="*60)
            print(f"👁️ DÉTAILS DU PERSONA #{bank_id}")
            print("="*60)
            
            print(f"📝 Nom : {bank.get('name', 'Non défini')}")
            print(f"🎭 Archétype : {bank.get('archetype', 'Non défini')}")
            print(f"📄 Description : {bank.get('description', 'Non définie')}")
            
            # Thèmes
            themes = bank.get('themes', [])
            if themes:
                print(f"\n🏷️ Thèmes associés ({len(themes)}) :")
                for i, theme in enumerate(themes, 1):
                    print(f"  {i}. {theme}")
            else:
                print(f"\n🏷️ Aucun thème associé")
            
            # Corpus
            corpus = bank.get('corpus', {})
            if corpus:
                print(f"\n📚 Corpus :")
                
                # Vocabulaire
                vocabulary = corpus.get('vocabulary', [])
                if vocabulary:
                    print(f"  📖 Vocabulaire ({len(vocabulary)} mots) :")
                    for i, word in enumerate(vocabulary, 1):
                        print(f"    {i}. {word}")
                else:
                    print(f"  📖 Aucun vocabulaire défini")
                
                # Arguments
                arguments = corpus.get('arguments', [])
                if arguments:
                    print(f"  💬 Arguments ({len(arguments)}) :")
                    for i, arg in enumerate(arguments, 1):
                        print(f"    {i}. {arg}")
                else:
                    print(f"  💬 Aucun argument défini")
                
                # Ton
                tone = corpus.get('tone', '')
                if tone:
                    print(f"  🎭 Ton : {tone}")
                else:
                    print(f"  🎭 Aucun ton défini")
                
                # Exemples
                examples = corpus.get('examples', [])
                if examples:
                    print(f"  📝 Exemples ({len(examples)}) :")
                    for i, example in enumerate(examples, 1):
                        print(f"    {i}. {example}")
                else:
                    print(f"  📝 Aucun exemple défini")
                
                # Données spéciales (G1FabLab ou User Memory)
                if 'g1fablab_prompt' in corpus:
                    g1fablab = corpus['g1fablab_prompt']
                    print(f"\n🔧 Données G1FabLab :")
                    print(f"  📁 Fichier : {g1fablab.get('file', 'Non défini')}")
                    print(f"  📄 Sujet : {g1fablab.get('subject', 'Non défini')}")
                    print(f"  💬 Message : {g1fablab.get('message_body', 'Non défini')[:100]}...")
                
                if 'user_memory' in corpus:
                    user_memory = corpus['user_memory']
                    print(f"\n👤 Données Mémoire Utilisateur :")
                    print(f"  👤 Utilisateur : {user_memory.get('user_id', 'Non défini')}")
                    print(f"  📁 Slot : {user_memory.get('slot', 'Non défini')}")
                    print(f"  📊 Messages totaux : {user_memory.get('message_count', 0)}")
                    print(f"  ✅ Messages filtrés : {user_memory.get('filtered_message_count', 0)}")
                    
                    sample_messages = user_memory.get('sample_messages', [])
                    if sample_messages:
                        print(f"  📝 Exemples de messages :")
                        for i, msg in enumerate(sample_messages[:3], 1):
                            print(f"    {i}. {msg[:80]}...")
            else:
                print(f"\n📚 Aucun corpus défini")
            
            print("\n" + "="*60)
            
            # Options d'action
            print("\n🔧 Actions disponibles :")
            print("1. Modifier ce persona")
            print("2. Tester ce persona")
            print("3. Retour")
            
            action = input("Votre choix : ").strip()
            
            if action == "1":
                # Rediriger vers la configuration
                banks_config = self._configure_bank(banks_config, str(bank_id))
            elif action == "2":
                # Rediriger vers le test
                self._test_bank_message(banks_config, str(bank_id))
            elif action == "3":
                print("↩️ Retour au menu principal")
            else:
                print("❌ Choix invalide")
                
        except ValueError:
            print("❌ Choix invalide")
        except Exception as e:
            print(f"❌ Erreur lors de la consultation : {e}")
            self.logger.error(f"Erreur lors de la consultation des détails : {e}")

    def _audit_memory_import(self, banks_config):
        """Audite la qualité des imports de mémoire existants"""
        print("\n🔍 AUDIT DES IMPORTS DE MÉMOIRE")
        print("-" * 40)
        
        # Trouver les personas basés sur des mémoires utilisateur
        memory_based_personas = []
        for bank_id, bank in banks_config['banks'].items():
            if bank.get('corpus', {}).get('user_memory'):
                memory_based_personas.append((bank_id, bank))
        
        if not memory_based_personas:
            print("❌ Aucun persona basé sur une mémoire utilisateur trouvé")
            return
        
        print("📋 Personas basés sur des mémoires utilisateur :")
        for i, (bank_id, bank) in enumerate(memory_based_personas, 1):
            user_memory = bank['corpus']['user_memory']
            print(f"  {i}. Banque {bank_id}: {bank['name']} ({user_memory['user_id']}/slot{user_memory['slot']})")
        
        print(f"\n💡 Sélectionnez un persona à auditer (1-{len(memory_based_personas)}) ou 0 pour annuler")
        
        try:
            choice = input("Votre choix : ").strip()
            if choice == "0":
                print("❌ Audit annulé")
                return
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(memory_based_personas):
                bank_id, bank = memory_based_personas[choice_idx]
                user_memory = bank['corpus']['user_memory']
                
                print(f"\n🔍 AUDIT DU PERSONA {bank_id}: {bank['name']}")
                print("=" * 60)
                
                # Vérifier la source de données
                print(f"📊 DONNÉES SOURCE :")
                print(f"   👤 Utilisateur : {user_memory['user_id']}")
                print(f"   📁 Slot : {user_memory['slot']}")
                print(f"   📈 Messages totaux : {user_memory['message_count']}")
                print(f"   ✅ Messages filtrés : {user_memory['filtered_message_count']}")
                print(f"   📊 Taux de filtrage : {(user_memory['filtered_message_count']/user_memory['message_count']*100):.1f}%")
                
                # Analyser la qualité du persona généré
                print(f"\n🎭 QUALITÉ DU PERSONA :")
                print(f"   📝 Nom : {bank['name']}")
                print(f"   🎭 Archétype : {bank['archetype']}")
                print(f"   🏷️ Thèmes : {len(bank['themes'])} thèmes")
                print(f"   📚 Vocabulaire : {len(bank['corpus']['vocabulary'])} mots")
                print(f"   💬 Arguments : {len(bank['corpus']['arguments'])} arguments")
                print(f"   🎨 Ton : {bank['corpus']['tone']}")
                
                # Afficher les exemples de messages
                print(f"\n📝 EXEMPLES DE MESSAGES :")
                for i, msg in enumerate(user_memory['sample_messages'][:3], 1):
                    print(f"   {i}. {msg}")
                
                # Évaluer la qualité
                quality_score = 0
                quality_issues = []
                
                # Critères de qualité
                if user_memory['filtered_message_count'] < 2:
                    quality_issues.append("⚠️ Très peu de messages filtrés")
                    quality_score -= 2
                
                if len(bank['themes']) < 3:
                    quality_issues.append("⚠️ Peu de thèmes identifiés")
                    quality_score -= 1
                
                if len(bank['corpus']['vocabulary']) < 5:
                    quality_issues.append("⚠️ Vocabulaire limité")
                    quality_score -= 1
                
                if len(bank['corpus']['arguments']) < 2:
                    quality_issues.append("⚠️ Arguments insuffisants")
                    quality_score -= 1
                
                if "utilisateur" in bank['themes'] or "personnalite" in bank['themes']:
                    quality_issues.append("⚠️ Thèmes trop génériques")
                    quality_score -= 1
                
                if quality_score >= 0:
                    quality_issues.append("✅ Qualité acceptable")
                else:
                    quality_issues.append("❌ Qualité insuffisante")
                
                print(f"\n📊 ÉVALUATION DE LA QUALITÉ :")
                for issue in quality_issues:
                    print(f"   {issue}")
                
                # Suggestions d'amélioration
                print(f"\n💡 SUGGESTIONS D'AMÉLIORATION :")
                if user_memory['filtered_message_count'] < 2:
                    print("   • Collecter plus de messages de conversation naturelle")
                if len(bank['themes']) < 3:
                    print("   • Améliorer l'analyse des centres d'intérêt")
                if "utilisateur" in bank['themes'] or "personnalite" in bank['themes']:
                    print("   • Affiner l'analyse pour éviter les généralités")
                
                # Option de réimport
                print(f"\n🔄 ACTIONS DISPONIBLES :")
                print("1. Réimporter avec des paramètres améliorés")
                print("2. Supprimer ce persona")
                print("3. Retour")
                
                action = input("Votre choix : ").strip()
                if action == "1":
                    print("🔄 Réimport en cours...")
                    # TODO: Implémenter le réimport avec paramètres améliorés
                    print("⚠️ Fonctionnalité de réimport à implémenter")
                elif action == "2":
                    confirm = input("⚠️ Êtes-vous sûr de vouloir supprimer ce persona ? (o/n) : ").strip().lower()
                    if confirm in ['o', 'oui', 'y', 'yes']:
                        del banks_config['banks'][bank_id]
                        print(f"✅ Persona {bank_id} supprimé")
                else:
                    print("Retour au menu principal")
                
            else:
                print("❌ Choix invalide")
                
        except (ValueError, IndexError):
            print("❌ Choix invalide")
        except Exception as e:
            print(f"❌ Erreur lors de l'audit : {e}")
            self.logger.error(f"Erreur lors de l'audit : {e}")

    def _parse_persona_config_response(self, raw_response: str) -> dict:
        """Parses the JSON response from the AI to extract persona configuration."""
        if not raw_response:
            return {
                "name": "Persona par défaut",
                "description": "Persona généré automatiquement",
                "archetype": "Utilisateur",
                "themes": ["utilisateur", "personnalite"],
                "corpus": {
                    "vocabulary": ["utilisateur", "personnalite"],
                    "arguments": ["Persona généré automatiquement"],
                    "tone": "personnel, authentique",
                    "examples": ["Messages de l'utilisateur"]
                }
            }

        # The AI might wrap the JSON in markdown ```json ... ``` or just be noisy.
        # We look for the first '{' and the last '}' to extract the JSON object.
        match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if not match:
            self.logger.warning(f"No JSON object found in AI response. Response was: {raw_response}")
            return {
                "name": "Persona par défaut",
                "description": "Persona généré automatiquement - Erreur de parsing",
                "archetype": "Utilisateur",
                "themes": ["utilisateur", "personnalite"],
                "corpus": {
                    "vocabulary": ["utilisateur", "personnalite"],
                    "arguments": ["Persona généré automatiquement"],
                    "tone": "personnel, authentique",
                    "examples": ["Messages de l'utilisateur"]
                }
            }
        
        clean_json_str = match.group(0)

        try:
            config_data = json.loads(clean_json_str)
            if not isinstance(config_data, dict):
                raise ValueError("Response is not a dictionary")
            
            # Validation des champs requis
            required_fields = ['name', 'description', 'archetype', 'themes', 'corpus']
            for field in required_fields:
                if field not in config_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validation du corpus
            if not isinstance(config_data['corpus'], dict):
                raise ValueError("Corpus must be a dictionary")
            
            corpus_fields = ['vocabulary', 'arguments', 'tone', 'examples']
            for field in corpus_fields:
                if field not in config_data['corpus']:
                    config_data['corpus'][field] = []
            
            return config_data
            
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.warning(f"Failed to parse AI persona config response: {e}. Cleaned string was: {clean_json_str}")
            return {
                "name": "Persona par défaut",
                "description": f"Persona généré automatiquement - Erreur: {str(e)}",
                "archetype": "Utilisateur",
                "themes": ["utilisateur", "personnalite"],
                "corpus": {
                    "vocabulary": ["utilisateur", "personnalite"],
                    "arguments": ["Persona généré automatiquement"],
                    "tone": "personnel, authentique",
                    "examples": ["Messages de l'utilisateur"]
                }
            }

    def _get_target_website(self, target):
        """Récupère le site web d'une cible depuis les métadonnées enrichies"""
        try:
            kb_file = self.shared_state['config']['enriched_prospects_file']
            if os.path.exists(kb_file):
                with open(kb_file, 'r') as f:
                    knowledge_base = json.load(f)
                
                pubkey = target.get('pubkey')
                if pubkey and pubkey in knowledge_base:
                    profile_info = knowledge_base[pubkey]
                    profile = profile_info.get('profile', {})
                    if profile and '_source' in profile:
                        source = profile['_source']
                        socials = source.get('socials', [])
                        for social in socials:
                            if isinstance(social, dict) and social.get('type') == 'web':
                                return social.get('url', '')
                            elif isinstance(social, str) and 'http' in social:
                                return social
        except Exception as e:
            self.logger.debug(f"⚠️ Erreur lors de la récupération du site web : {e}")
        
        return ""

    def _fetch_website_content(self, url, max_length=2000):
        """Récupère le contenu d'un site web et le convertit en markdown"""
        try:
            import requests
            from bs4 import BeautifulSoup
            import html2text
            
            self.logger.info(f"🌐 Récupération du contenu de : {url}")
            
            # Configuration des headers pour éviter d'être bloqué
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Récupération du contenu avec timeout
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parsing HTML avec BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Suppression des éléments non désirés
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # Extraction du contenu principal
            content = ""
            
            # Essayer de trouver le contenu principal
            main_selectors = ['main', 'article', '.content', '.main', '#content', '#main']
            for selector in main_selectors:
                main_content = soup.select_one(selector)
                if main_content:
                    content = main_content.get_text(separator=' ', strip=True)
                    break
            
            # Si pas de contenu principal trouvé, prendre le body
            if not content:
                content = soup.get_text(separator=' ', strip=True)
            
            # Nettoyage du contenu
            import re
            # Supprimer les espaces multiples
            content = re.sub(r'\s+', ' ', content)
            # Supprimer les lignes vides
            content = re.sub(r'\n\s*\n', '\n', content)
            # Limiter la longueur
            if len(content) > max_length:
                content = content[:max_length] + "..."
            
            # Conversion en markdown basique
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.body_width = 0  # Pas de limite de largeur
            
            markdown_content = h.handle(str(soup))
            
            # Nettoyer le markdown
            markdown_content = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown_content)
            if len(markdown_content) > max_length:
                markdown_content = markdown_content[:max_length] + "..."
            
            self.logger.info(f"✅ Contenu récupéré : {len(markdown_content)} caractères")
            return markdown_content
            
        except requests.exceptions.Timeout:
            self.logger.warning(f"⚠️ Timeout lors de la récupération de {url}")
            return f"Site web : {url} (timeout lors de la récupération)"
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"⚠️ Erreur lors de la récupération de {url} : {e}")
            return f"Site web : {url} (erreur de récupération)"
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur lors du traitement de {url} : {e}")
            return f"Site web : {url} (erreur de traitement)"
