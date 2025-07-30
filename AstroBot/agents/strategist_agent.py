from .base_agent import Agent
import json
import os
import subprocess
import re

class StrategistAgent(Agent):
    """
    L'agent Stratège utilise l'intelligence artificielle pour rédiger
    un message de campagne personnalisé en fonction de la cible fournie par l'Analyste.
    Il peut utiliser Perplexica pour enrichir son contexte.
    """
    def _select_bank_for_targets(self, targets, banks_config):
        """Sélectionne automatiquement la banque de mémoire la plus appropriée pour les cibles"""
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

        # Calculer le score de correspondance pour chaque banque
        bank_scores = {}
        for slot, bank in banks_config['banks'].items():
            if not bank.get('corpus'):
                continue  # Ignorer les banques sans corpus

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
            self.logger.info("Aucune banque de mémoire ne correspond aux thèmes des cibles")
            return None

        # Sélectionner la banque avec le meilleur score
        best_slot = max(bank_scores.keys(), key=lambda x: bank_scores[x]['score'])
        best_match = bank_scores[best_slot]

        self.logger.info(f"Banque sélectionnée : {best_match['bank']['name']} (score: {best_match['score']:.2f})")
        self.logger.info(f"Thèmes correspondants : {', '.join(best_match['matching_themes'])}")

        return best_match['bank']

    def _choose_strategy_mode(self):
        """Permet de choisir le mode de rédaction du message"""
        print("\n🎯 MODE DE RÉDACTION DU MESSAGE")
        print("-" * 40)
        print("1. Mode Persona : Analyse automatique du profil et sélection de banque")
        print("2. Mode Auto : Sélection automatique basée sur les thèmes")
        print("3. Mode Classique : Choix manuel de la banque")
        print()
        
        try:
            choice = input("Choisissez le mode (1-3) : ").strip()
            
            if choice == "1":
                print("✅ Mode Persona sélectionné")
                return "persona"
            elif choice == "2":
                print("✅ Mode Auto sélectionné")
                return "auto"
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

        # Charger la configuration des banques de mémoire
        banks_config_file = os.path.join(self.shared_state['config']['workspace'], 'memory_banks_config.json')
        banks_config = self._load_banks_config(banks_config_file)

        # Choisir le mode de rédaction
        mode = self._choose_strategy_mode()
        
        if mode == "persona":
            # Mode Persona : Analyse automatique du profil et sélection de banque
            selected_bank = self._analyze_profile_and_select_bank(self.shared_state['targets'], banks_config)
            if selected_bank:
                self.logger.info(f"🎭 Mode Persona : Banque sélectionnée automatiquement : {selected_bank['name']}")
                self._generate_message_with_persona_mode(selected_bank, treasury_pubkey)
            else:
                self.logger.warning("⚠️ Mode Persona : Aucune banque adaptée trouvée, passage en mode classique")
                self._generate_message_with_classic_mode(banks_config, treasury_pubkey)
        elif mode == "auto":
            # Mode Auto : Utilisation de la logique existante
            selected_bank = self._select_bank_for_targets(self.shared_state['targets'], banks_config)
            if selected_bank:
                self.logger.info(f"🎭 Mode Auto : Banque sélectionnée : {selected_bank['name']}")
                self._generate_message_with_bank_mode(selected_bank)
            else:
                self.logger.info("📝 Mode Auto : Aucune banque adaptée, passage en mode classique")
                self._generate_message_with_classic_mode(banks_config, treasury_pubkey)
        else:
            # Mode Classique : Choix manuel
            self.logger.info("📝 Mode Classique : Choix manuel de la banque")
            self._generate_message_with_classic_mode(banks_config, treasury_pubkey)

        if not message_content:
            self.logger.error("L'IA n'a retourné aucun message.")
            self.shared_state['status']['StrategistAgent'] = "Échec : Aucun message généré."
            return

        # Sauvegarder le message
        message_file = os.path.join(self.shared_state['config']['workspace'], "message_to_send.txt")
        with open(message_file, 'w') as f:
            f.write(message_content)

        report = "Message de campagne rédigé et sauvegardé dans workspace/message_to_send.txt. Prêt pour validation par l'Opérateur."
        self.logger.info(f"✅ {report}")
        self.shared_state['status']['StrategistAgent'] = report
        self.shared_state['message_to_send'] = message_content

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
        return result.stdout

    def _call_ia_for_writing(self, final_prompt):
        question_script = self.shared_state['config']['question_script']
        command = ['python3', question_script, final_prompt]
        self.logger.info("Génération du message par l'IA...")
        self.logger.debug(f"Exécution de la commande de rédaction : {' '.join(command[:2])}...")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        self.logger.debug(f"Réponse brute de l'IA (rédaction) : {result.stdout.strip()}")
        return result.stdout

    def manage_memory_banks(self):
        """Interface de gestion des banques de mémoire thématiques"""
        self.logger.info("🏦 Gestionnaire de Banques de Mémoire Thématiques")

        # Charger la configuration des banques
        banks_config_file = os.path.join(self.shared_state['config']['workspace'], 'memory_banks_config.json')
        banks_config = self._load_banks_config(banks_config_file)

        try:
            while True:
                print("\n" + "="*60)
                print("🏦 GESTIONNAIRE DE BANQUES DE MÉMOIRE")
                print("="*60)
                print("Chaque banque représente une 'personnalité' pour l'Agent Stratège")
                print()

                # Afficher l'état des banques
                self._display_banks_status(banks_config)

                print("\nOptions :")
                print("1. Créer/Configurer une banque")
                print("2. Associer des thèmes à une banque")
                print("3. Remplir le corpus d'une banque")
                print("4. Tester une banque (générer un message)")
                print("5. Configurer les liens")
                print("6. Synchroniser les thèmes depuis l'Agent Analyste")
                print("7. Sauvegarder et retourner")
                print("8. Retour sans sauvegarder")
                print("9. Sauvegarder maintenant (sans quitter)")

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
                    self._save_banks_config(banks_config, banks_config_file)
                    self.logger.info("✅ Configuration des banques sauvegardée")
                    break
                elif choice == "8":
                    print("⚠️ Attention : Les modifications non sauvegardées seront perdues.")
                    confirm = input("Êtes-vous sûr ? (oui/non) : ").strip().lower()
                    if confirm in ['oui', 'o', 'yes', 'y']:
                        break
                    else:
                        print("Retour au menu principal...")
                elif choice == "9":
                    self._save_banks_config(banks_config, banks_config_file)
                    self.logger.info("✅ Configuration sauvegardée")
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
        """Charge la configuration des banques de mémoire"""
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

    def _display_banks_status(self, banks_config):
        """Affiche l'état des banques de mémoire"""
        print("\n📊 ÉTAT DES BANQUES DE MÉMOIRE :")
        print("-" * 60)

        for slot, bank in banks_config['banks'].items():
            status = "✅" if bank.get('corpus') else "❌"
            themes_count = len(bank.get('themes', []))
            print(f"{status} Banque #{slot}: {bank['name']}")
            print(f"    Archétype: {bank.get('archetype', 'Non défini')}")
            print(f"    Thèmes associés: {themes_count}")
            print(f"    Corpus: {'Rempli' if bank.get('corpus') else 'Vide'}")
            print()

    def _configure_bank(self, banks_config):
        """Configure une banque de mémoire"""
        print("\n🔧 CONFIGURATION D'UNE BANQUE")
        print("-" * 40)

        # Afficher les banques disponibles avec plus de détails
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            name = bank.get('name', 'Non configurée')
            archetype = bank.get('archetype', 'Non défini')
            has_corpus = bool(bank.get('corpus'))
            status = "✅" if has_corpus else "❌"
            print(f"{slot}. {status} {name} ({archetype})")

        try:
            slot = input("\nChoisissez le numéro de la banque (0-11) : ").strip()
            if not (0 <= int(slot) <= 11):
                print("❌ Numéro de banque invalide")
                return banks_config

            slot = str(slot)
            bank = banks_config['banks'].get(slot, {})

            print(f"\n{'='*50}")
            print(f"CONFIGURATION DE LA BANQUE #{slot}")
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

        except ValueError:
            print("❌ Entrée invalide")

        return banks_config

    def _associate_themes_to_bank(self, banks_config):
        """Associe des thèmes à une banque"""
        print("\n🏷️ ASSOCIATION DE THÈMES À UNE BANQUE")
        print("-" * 40)

        # Afficher les banques
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            name = bank.get('name', 'Non configurée')
            themes = bank.get('themes', [])
            print(f"{slot}. {name} ({len(themes)} thèmes)")

        try:
            slot = input("\nChoisissez le numéro de la banque (0-11) : ").strip()
            if not (0 <= int(slot) <= 11):
                print("❌ Numéro de banque invalide")
                return banks_config

            slot = str(slot)
            bank = banks_config['banks'].get(slot, {})

            print(f"\nThèmes disponibles :")
            available_themes = banks_config.get('available_themes', [])
            for i, theme in enumerate(available_themes):
                print(f"{i+1}. {theme}")

            print(f"\nThèmes actuellement associés à la banque #{slot} :")
            current_themes = bank.get('themes', [])
            for theme in current_themes:
                print(f"  - {theme}")

            print("\nEntrez les numéros des thèmes à associer (séparés par des virgules) :")
            print("Exemple: 1,3,5 pour associer les thèmes 1, 3 et 5")

            choice = input("Votre choix : ").strip()
            if choice:
                try:
                    indices = [int(x.strip()) - 1 for x in choice.split(',')]
                    selected_themes = [available_themes[i] for i in indices if 0 <= i < len(available_themes)]
                    bank['themes'] = selected_themes
                    banks_config['banks'][slot] = bank
                    print(f"✅ {len(selected_themes)} thèmes associés à la banque #{slot}")
                except (ValueError, IndexError):
                    print("❌ Format invalide")

        except ValueError:
            print("❌ Entrée invalide")

        return banks_config

    def _fill_bank_corpus(self, banks_config):
        """Remplit le corpus d'une banque de mémoire"""
        print("\n📚 REMPLISSAGE DU CORPUS D'UNE BANQUE")
        print("-" * 40)

        # Afficher les banques
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            name = bank.get('name', 'Non configurée')
            has_corpus = bool(bank.get('corpus'))
            status = "✅" if has_corpus else "❌"
            print(f"{slot}. {status} {name}")

        try:
            slot = input("\nChoisissez le numéro de la banque (0-11) : ").strip()
            if not (0 <= int(slot) <= 11):
                print("❌ Numéro de banque invalide")
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
            print(f"✅ CORPUS DE LA BANQUE #{slot} MIS À JOUR")
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
        """Synchronise les thèmes identifiés par l'Agent Analyste avec la configuration des banques"""
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
        print("💡 Vous pouvez maintenant associer ces thèmes aux banques")

        return banks_config

    def _show_bank_themes_details(self, bank, slot):
        """Affiche les détails des thèmes d'une banque"""
        print(f"\n{'='*60}")
        print(f"REMPLISSAGE DU CORPUS - BANQUE #{slot}")
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

    def _test_bank_message(self, banks_config):
        """Teste la génération d'un message avec une banque spécifique"""
        print("\n🧪 TEST DE GÉNÉRATION DE MESSAGE")
        print("-" * 40)

        # Afficher les banques disponibles
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            if bank.get('name'):
                print(f"{slot}. {bank['name']}")

        try:
            slot = input("\nChoisissez le numéro de la banque à tester : ").strip()
            if not (0 <= int(slot) <= 11):
                print("❌ Numéro de banque invalide")
                return

            slot = str(slot)
            bank = banks_config['banks'].get(slot, {})

            if not bank.get('name'):
                print("❌ Banque non configurée")
                return

            print(f"\nTest de la banque #{slot} : {bank['name']}")

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
            message = self._generate_message_with_bank(bank, self.shared_state['config'])

            print(f"\n{'='*50}")
            print(f"MESSAGE GÉNÉRÉ :")
            print(f"{'='*50}")
            print(message)
            print(f"{'='*50}")

            # Afficher les statistiques du message
            word_count = len(message.split())
            char_count = len(message)
            link_count = len(re.findall(r'https?://[^\s]+', message))

            print(f"\n📊 Statistiques du message :")
            print(f"  • Mots : {word_count}")
            print(f"  • Caractères : {char_count}")
            print(f"  • Liens détectés : {link_count}")

        except KeyboardInterrupt:
            print("\n⚠️ Test interrompu par l'utilisateur.")
        except Exception as e:
            print(f"❌ Erreur lors du test : {e}")

    def _generate_message_with_bank(self, bank, target_description):
        """Génère un message en utilisant une banque de mémoire spécifique"""
        corpus = bank.get('corpus', {})

        prompt = f"""Tu es l'Agent Stratège d'UPlanet. Tu dois rédiger un message de campagne en adoptant la personnalité de la banque de mémoire suivante :

ARCHÉTYPE : {bank.get('archetype', 'Non défini')}
NOM DE LA BANQUE : {bank.get('name', 'Non nommée')}
THÈMES ASSOCIÉS : {', '.join(bank.get('themes', []))}

TON DE COMMUNICATION : {corpus.get('tone', 'Non défini')}

VOCABULAIRE CLÉ À UTILISER : {', '.join(corpus.get('vocabulary', []))}

ARGUMENTS PRINCIPAUX :
{chr(10).join([f"- {arg}" for arg in corpus.get('arguments', [])])}

EXEMPLES DE PHRASES :
{chr(10).join([f"- {example}" for example in corpus.get('examples', [])])}

TÂCHE : Rédige un message de campagne pour présenter UPlanet et le MULTIPASS à des personnes intéressées par : {target_description}

Le message doit :
1. Utiliser le vocabulaire et le ton de cette banque
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

Format : Message de 150-200 mots maximum."""

        try:
            result = subprocess.run(
                ['python3', self.shared_state['config']['question_script'], prompt, '--json'],
                capture_output=True, text=True, check=True
            )
            response = json.loads(result.stdout)
            message_content = response.get('answer', 'Erreur lors de la génération')

            # Vérifier si l'agent a utilisé des URLs directes
            direct_urls = re.findall(r'https?://[^\s]+', message_content)
            if direct_urls:
                self.logger.warning(f"⚠️ L'agent a utilisé des URLs directes au lieu des placeholders : {direct_urls}")
                # Remplacer les URLs directes par des placeholders appropriés
                message_content = self._replace_direct_urls_with_placeholders(message_content)

            return self._inject_links(message_content, self.shared_state['config'])
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération avec banque : {e}")
            return f"Erreur lors de la génération : {e}"

    def _save_banks_config(self, banks_config, config_file):
        """Sauvegarde la configuration des banques"""
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

        # Patterns de détection des placeholders
        link_patterns = {
            r'\[Lien vers OpenCollective\]': links_config.get('opencollective', ''),
            r'\[Lien vers Documentation\]': links_config.get('documentation', ''),
            r'\[Lien vers GitHub\]': links_config.get('github', ''),
            r'\[Lien vers Discord\]': links_config.get('discord', ''),
            r'\[Lien vers Telegram\]': links_config.get('telegram', ''),
            r'\[Lien vers Site Web\]': links_config.get('website', ''),
            r'\[Lien vers Blog\]': links_config.get('blog', ''),
            r'\[Lien vers Forum\]': links_config.get('forum', ''),
            r'\[Lien vers Wiki\]': links_config.get('wiki', ''),
            r'\[Lien vers Mastodon\]': links_config.get('mastodon', ''),
            r'\[Lien vers Nostr\]': links_config.get('nostr', ''),
            r'\[Lien vers IPFS\]': links_config.get('ipfs', ''),
            r'\[Lien vers G1\]': links_config.get('g1', ''),
            r'\[Lien vers UPlanet\]': links_config.get('uplanet', ''),
            r'\[Lien vers Astroport\]': links_config.get('astroport', ''),
            r'\[Lien vers Zen\]': links_config.get('zen', ''),
            r'\[Lien vers Multipass\]': links_config.get('multipass', ''),
        }

        # Remplacer les placeholders par les vrais liens
        for pattern, link in link_patterns.items():
            if link:
                message = re.sub(pattern, link, message, flags=re.IGNORECASE)
            else:
                # Si le lien n'est pas configuré, supprimer le placeholder
                message = re.sub(pattern, '', message, flags=re.IGNORECASE)

        # Nettoyer les espaces multiples créés par les suppressions
        message = re.sub(r'\s+', ' ', message)
        message = re.sub(r'\n\s*\n\s*\n', '\n\n', message)

        return message.strip()

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
            'documentation': 'https://github.com/papiche/Astroport.ONE/blob/master/DOCUMENTATION.md',
            'github': 'https://github.com/papiche/Astroport.ONE',
            'discord': 'https://ipfs.copylaradio.com/ipns/copylaradio.com/bang.html',
            'telegram': 'https://t.me/AstroportN1',
            'website': 'https://copylaradio.com',
            'blog': 'https://www.copylaradio.com/blog/blog-1',
            'forum': 'https://forum.monnaie-libre.fr/',
            'wiki': 'https://pad.p2p.legal',
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
        """Permet de choisir une banque de contexte pour la méthode classique"""
        print("\n🎭 CHOIX DE LA BANQUE DE CONTEXTE")
        print("-" * 40)
        print("Vous pouvez choisir une banque de mémoire pour enrichir le contexte")
        print("ou continuer sans banque (méthode classique pure)")
        print()
        
        # Afficher les banques disponibles
        available_banks = []
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            if bank.get('name') and bank.get('corpus'):
                available_banks.append((slot, bank))
                print(f"{slot}. {bank['name']} ({bank.get('archetype', 'Non défini')})")
        
        if not available_banks:
            print("❌ Aucune banque configurée avec corpus")
            return None
        
        print(f"{len(available_banks)}. Aucune banque (méthode classique pure)")
        
        try:
            choice = input(f"\nChoisissez une banque (0-{len(available_banks)-1}) ou {len(available_banks)} pour aucune : ").strip()
            choice_int = int(choice)
            
            if choice_int == len(available_banks):
                print("✅ Méthode classique pure sélectionnée")
                return None
            elif 0 <= choice_int < len(available_banks):
                selected_slot, selected_bank = available_banks[choice_int]
                print(f"✅ Banque sélectionnée : {selected_bank['name']}")
                return selected_bank
            else:
                print("❌ Choix invalide, utilisation de la méthode classique pure")
                return None
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Choix invalide, utilisation de la méthode classique pure")
            return None

    def _analyze_profile_and_select_bank(self, targets, banks_config):
        """Analyse le profil du prospect et sélectionne automatiquement la banque la plus adaptée"""
        self.logger.info("🔍 Mode Persona : Analyse du profil du prospect...")
        
        if not targets:
            return None
            
        target = targets[0]  # Prendre la première cible pour l'analyse
        
        # Construire le profil complet
        profile_data = {
            'uid': target.get('uid', ''),
            'website': target.get('website', ''),
            'tags': target.get('tags', []),
            'description': target.get('description', ''),
            'analyst_report': self.shared_state.get('analyst_report', ''),
            'web_context': ''
        }
        
        # Enrichir avec le contexte web si disponible
        if target.get('website'):
            self.logger.info(f"🕵️  Recherche Perplexica pour enrichir le profil : {target['website']}")
            search_query = f"Analyse le profil de {target.get('uid', '')} et son site {target['website']}. Identifie ses centres d'intérêt, son domaine d'activité, ses valeurs et son style de communication."
            try:
                profile_data['web_context'] = self._call_perplexica(search_query)
                self.logger.info("✅ Contexte web obtenu pour l'analyse de profil")
            except Exception as e:
                self.logger.warning(f"⚠️ Impossible d'obtenir le contexte web : {e}")
        
        # Construire le prompt d'analyse
        analysis_prompt = f"""Tu es un expert en analyse de profils pour UPlanet. Tu dois analyser le profil d'un prospect et déterminer quelle banque de mémoire (persona) est la plus adaptée pour lui adresser un message personnalisé.

PROFIL DU PROSPECT :
- Identifiant : {profile_data['uid']}
- Site web : {profile_data['website']}
- Tags : {', '.join(profile_data['tags'])}
- Description : {profile_data['description']}
- Rapport Analyste : {profile_data['analyst_report']}
- Contexte Web : {profile_data['web_context']}

BANQUES DE MÉMOIRE DISPONIBLES :"""

        # Ajouter les informations sur les banques disponibles
        available_banks = []
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            if bank.get('name') and bank.get('corpus'):
                available_banks.append((slot, bank))
                analysis_prompt += f"\n- {bank['name']} (Archetype: {bank.get('archetype', 'Non défini')}, Thèmes: {', '.join(bank.get('themes', []))})"
        
        if not available_banks:
            self.logger.warning("⚠️ Aucune banque configurée pour l'analyse de profil")
            return None
        
        analysis_prompt += f"""

INSTRUCTIONS :
1. Analyse le profil du prospect en détail
2. Identifie ses centres d'intérêt, son domaine d'activité, ses valeurs
3. Détermine quel archetype de banque correspond le mieux à son profil
4. Réponds UNIQUEMENT avec le numéro de la banque (0-{len(available_banks)-1}) qui correspond le mieux
5. Si aucune banque ne correspond vraiment, réponds "AUCUNE"

ANALYSE :"""

        # Appeler l'IA pour l'analyse
        try:
            self.logger.info("🧠 Analyse du profil par l'IA...")
            analysis_result = self._call_ia_for_writing(analysis_prompt)
            
            # Extraire le numéro de la banque sélectionnée
            import re
            bank_match = re.search(r'\b(\d+)\b', analysis_result.strip())
            
            if bank_match:
                bank_index = int(bank_match.group(1))
                if 0 <= bank_index < len(available_banks):
                    selected_slot, selected_bank = available_banks[bank_index]
                    self.logger.info(f"✅ Banque sélectionnée automatiquement : {selected_bank['name']}")
                    
                    # Afficher le raisonnement
                    print(f"\n🎭 ANALYSE DE PROFIL - RÉSULTAT")
                    print(f"Prospect : {profile_data['uid']}")
                    print(f"Banque sélectionnée : {selected_bank['name']}")
                    print(f"Archetype : {selected_bank.get('archetype', 'Non défini')}")
                    print(f"Thèmes : {', '.join(selected_bank.get('themes', []))}")
                    print(f"Raisonnement IA : {analysis_result.strip()}")
                    
                    return selected_bank
                else:
                    self.logger.warning(f"⚠️ Index de banque invalide : {bank_index}")
            else:
                self.logger.warning("⚠️ Impossible de déterminer la banque depuis l'analyse IA")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'analyse de profil : {e}")
        
        return None

    def _generate_message_with_persona_mode(self, selected_bank, treasury_pubkey):
        """Génère un message en mode Persona avec la banque sélectionnée automatiquement"""
        self.logger.info(f"🎭 Mode Persona : Génération du message avec {selected_bank['name']}")
        
        try:
            # Construire le contexte enrichi pour la banque
            analyst_report = self.shared_state.get('analyst_report', "Aucun rapport.")
            first_target = self.shared_state['targets'][0]

            # Ajouter le contexte web si disponible
            web_context = ""
            if first_target.get('website'):
                self.logger.info(f"🕵️  Recherche Perplexica sur le site : {first_target['website']}...")
                search_query = f"Fais un résumé de l'activité du site {first_target['website']} et de son propriétaire {first_target.get('uid', '')} pour comprendre ses centres d'intérêt."
                web_context = self._call_perplexica(search_query)
                self.logger.info("✅ Contexte web obtenu.")

            # Construire la description complète pour la banque avec focus sur la personnalisation
            target_description = f"""MODE PERSONA - PERSONNALISATION AVANCÉE

Rapport Analyste: {analyst_report}
Prospect: {json.dumps(first_target, indent=2, ensure_ascii=False)}"""

            if web_context:
                target_description += f"\nContexte Web: {web_context}"
            
            target_description += f"""

INSTRUCTIONS SPÉCIALES MODE PERSONA :
- Utilise l'archetype "{selected_bank.get('archetype', 'Non défini')}" pour adapter ton ton
- Personnalise le message en fonction du profil spécifique du prospect
- Utilise le vocabulaire et les arguments de la banque "{selected_bank['name']}"
- Crée une connexion émotionnelle basée sur les centres d'intérêt identifiés
- Sois authentique et adapte le style au profil analysé"""

            # Générer le message avec la banque
            message_content = self._generate_message_with_bank(selected_bank, target_description)
            
            # Sauvegarder le message
            message_file = os.path.join(self.shared_state['config']['workspace'], 'message_to_send.txt')
            with open(message_file, 'w', encoding='utf-8') as f:
                f.write(message_content)
            
            self.logger.info("✅ Message de campagne rédigé et sauvegardé dans workspace/message_to_send.txt. Prêt pour validation par l'Opérateur.")
            self.shared_state['status']['StrategistAgent'] = f"Message rédigé avec banque {selected_bank['name']} (Mode Persona)"
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération en mode Persona : {e}")
            self.shared_state['status']['StrategistAgent'] = f"Échec : {e}"

    def _generate_message_with_bank_mode(self, selected_bank):
        """Génère un message en mode Auto avec la banque sélectionnée automatiquement"""
        self.logger.info(f"🎭 Mode Auto : Génération du message avec {selected_bank['name']}")
        
        try:
            # Construire le contexte pour la banque
            analyst_report = self.shared_state.get('analyst_report', "Aucun rapport.")
            first_target = self.shared_state['targets'][0]

            # Ajouter le contexte web si disponible
            web_context = ""
            if first_target.get('website'):
                self.logger.info(f"🕵️  Recherche Perplexica sur le site : {first_target['website']}...")
                search_query = f"Fais un résumé de l'activité du site {first_target['website']} et de son propriétaire {first_target.get('uid', '')} pour comprendre ses centres d'intérêt."
                web_context = self._call_perplexica(search_query)
                self.logger.info("✅ Contexte web obtenu.")

            # Construire la description complète pour la banque
            target_description = f"Rapport Analyste: {analyst_report}"
            if web_context:
                target_description += f"\nContexte Web: {web_context}"
            target_description += f"\nExemple de cible: {json.dumps(first_target, indent=2, ensure_ascii=False)}"

            # Générer le message avec la banque
            message_content = self._generate_message_with_bank(selected_bank, target_description)
            
            # Sauvegarder le message
            message_file = os.path.join(self.shared_state['config']['workspace'], 'message_to_send.txt')
            with open(message_file, 'w', encoding='utf-8') as f:
                f.write(message_content)
            
            self.logger.info("✅ Message de campagne rédigé et sauvegardé dans workspace/message_to_send.txt. Prêt pour validation par l'Opérateur.")
            self.shared_state['status']['StrategistAgent'] = f"Message rédigé avec banque {selected_bank['name']} (Mode Auto)"
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération en mode Auto : {e}")
            self.shared_state['status']['StrategistAgent'] = f"Échec : {e}"

    def _generate_message_with_classic_mode(self, banks_config, treasury_pubkey):
        """Génère un message en mode Classique avec choix manuel de banque"""
        self.logger.info("📝 Mode Classique : Génération du message")
        
        try:
            # Proposer le choix d'une banque de contexte
            selected_bank = self._choose_bank_for_classic_method(banks_config)
            
            # --- Construction du Prompt Final ---
            # 1. Charger le prompt de base
            prompt_file = self.shared_state['config']['strategist_prompt_file']
            with open(prompt_file, 'r') as f:
                final_prompt = f.read()

            # Remplacer le placeholder du portefeuille Trésor
            final_prompt = final_prompt.replace('[UPLANET_TREASURY_G1PUB]', treasury_pubkey)

            # 2. Ajouter le contexte de la banque si sélectionnée
            if selected_bank:
                self.logger.info(f"🎭 Contexte de la banque : {selected_bank['name']}")
                corpus = selected_bank.get('corpus', {})
                
                final_prompt += f"\n\n--- CONTEXTE DE LA BANQUE DE MÉMOIRE ---"
                final_prompt += f"\nArchétype : {selected_bank.get('archetype', 'Non défini')}"
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

            # 4. Web-Search avec Perplexica pour enrichir le contexte
            first_target = self.shared_state['targets'][0]
            if first_target.get('website'):
                self.logger.info(f"🕵️  Recherche Perplexica sur le site : {first_target['website']}...")
                search_query = f"Fais un résumé de l'activité du site {first_target['website']} et de son propriétaire {first_target.get('uid', '')} pour comprendre ses centres d'intérêt."

                web_context = self._call_perplexica(search_query)
                self.logger.info("✅ Contexte web obtenu.")
                final_prompt += f"\n\n--- CONTEXTE DU WEB (via Perplexica) ---\n{web_context}"

            # 5. Ajouter un exemple de cible pour la personnalisation
            final_prompt += f"\n\n--- EXEMPLE DE CIBLE ---\n{json.dumps(first_target, indent=2, ensure_ascii=False)}"
            final_prompt += "\n\nMaintenant, en te basant sur TOUTES ces informations, rédige le message de campagne final. Ta réponse DOIT être uniquement le message, sans commentaire additionnel."

            self.logger.info("🧠 Prompt final construit. Interrogation de l'IA locale via question.py...")

            # --- Appel à l'IA locale ---
            message_content = self._call_ia_for_writing(final_prompt)
            
            # Appliquer l'injection de liens
            message_content = self._inject_links(message_content, self.shared_state['config'])
            
            # Sauvegarder le message
            message_file = os.path.join(self.shared_state['config']['workspace'], 'message_to_send.txt')
            with open(message_file, 'w', encoding='utf-8') as f:
                f.write(message_content)
            
            self.logger.info("✅ Message de campagne rédigé et sauvegardé dans workspace/message_to_send.txt. Prêt pour validation par l'Opérateur.")
            self.shared_state['status']['StrategistAgent'] = "Message rédigé (Mode Classique)"
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération en mode Classique : {e}")
            self.shared_state['status']['StrategistAgent'] = f"Échec : {e}"
