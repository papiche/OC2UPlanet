from .base_agent import Agent
import json
import os
import subprocess
import random
from collections import defaultdict, Counter

class AnalystAgent(Agent):
    """
    L'agent Analyste utilise l'IA pour analyser la base de prospects,
    identifier des clusters socio-géographiques, et permettre à l'utilisateur
    de choisir une cible stratégique. Il propose deux modes : Rapide et Profond.
    """

    def _clean_ia_json_output(self, ia_output_str: str) -> str:
        """
        Nettoie la sortie brute de l'IA pour en extraire une chaîne JSON valide.
        Supprime les blocs de code Markdown (```json...```) et autres textes parasites.
        """
        cleaned_str = ia_output_str.strip()
        
        # Trouve le début du JSON (soit {, soit [)
        json_start = -1
        for i, char in enumerate(cleaned_str):
            if char in ['{', '[']:
                json_start = i
                break
        
        if json_start == -1:
            return cleaned_str # Pas de JSON trouvé

        # Trouve la fin du JSON (soit }, soit ])
        json_end = -1
        # On parcourt la chaîne à l'envers
        for i, char in enumerate(reversed(cleaned_str)):
            if char in ['}', ']']:
                json_end = len(cleaned_str) - 1 - i
                break
        
        if json_end == -1:
            return cleaned_str

        return cleaned_str[json_start:json_end+1]

    def _load_and_sync_knowledge_base(self):
        """
        Charge la base de connaissance existante, la synchronise avec le
        fichier de prospects source pour ajouter/mettre à jour les entrées,
        et la retourne. La base est un dictionnaire indexé par pubkey.
        """
        kb_file = self.shared_state['config']['enriched_prospects_file']
        prospect_file = os.path.expanduser(self.shared_state['config']['prospect_file'])
        
        # 1. Charger la base de connaissance existante
        knowledge_base = {}
        if os.path.exists(kb_file):
            try:
                with open(kb_file, 'r') as f:
                    knowledge_base = json.load(f)
                self.logger.info(f"{len(knowledge_base)} profils chargés depuis la base de connaissance.")
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Impossible de charger la base de connaissance '{kb_file}'. Erreur : {e}")

        # 2. Lire le fichier source et synchroniser
        if not os.path.exists(prospect_file):
            self.logger.error(f"Fichier de prospects source '{prospect_file}' non trouvé.")
            return knowledge_base # On retourne ce qu'on a

        try:
            with open(prospect_file, 'r') as f:
                source_data = json.load(f)

            source_prospects_count = 0
            new_prospects_count = 0
            for member in source_data.get('members', []):
                pubkey = member.get("pubkey")
                if not pubkey: continue
                source_prospects_count += 1

                if pubkey not in knowledge_base:
                    knowledge_base[pubkey] = {
                        "uid": member.get("uid"),
                        "profile": member.get('profile', {}),
                        "source": member.get('source'),
                        "metadata": {} 
                    }
                    new_prospects_count += 1
                else: 
                    knowledge_base[pubkey]['profile'] = member.get('profile', {})

            self.logger.info(f"Synchronisation terminée : {source_prospects_count} profils dans la source, {new_prospects_count} nouveaux ajoutés.")
        except Exception as e:
            self.logger.error(f"Erreur lors de la synchronisation avec '{prospect_file}': {e}", exc_info=True)
            
        return knowledge_base

    def _save_knowledge_base(self, knowledge_base):
        """Sauvegarde la base de connaissance enrichie dans son fichier."""
        kb_file = self.shared_state['config']['enriched_prospects_file']
        try:
            with open(kb_file, 'w') as f:
                json.dump(knowledge_base, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Base de connaissance sauvegardée avec {len(knowledge_base)} profils.")
        except IOError as e:
            self.logger.error(f"Impossible de sauvegarder la base de connaissance : {e}")

    def get_analysis_progress(self):
        """
        Calcule et retourne l'état d'avancement de l'enrichissement
        de la base de connaissance.
        """
        knowledge_base = self._load_and_sync_knowledge_base()
        total_prospects = len(knowledge_base)
        
        language_analyzed = 0
        tags_analyzed = 0
        
        for pk, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            if 'language' in metadata:
                language_analyzed += 1
            if 'tags' in metadata:
                tags_analyzed += 1
                
        return {
            "total": total_prospects,
            "language": language_analyzed,
            "tags": tags_analyzed
        }

    def run_geo_linguistic_analysis(self):
        """
        Analyse les descriptions pour en extraire la langue, le pays et la région
        et sauvegarde ces données dans la base de connaissance.
        """
        self.logger.info("🤖 Agent Analyste : Démarrage de l'analyse Géo-Linguistique (avec persistance)...")
        self.shared_state['status']['AnalystAgent'] = "Analyse Géo-Linguistique en cours..."

        if not self._check_ollama_once():
            self.shared_state['status']['AnalystAgent'] = "Échec : API Ollama indisponible."
            return
            
        knowledge_base = self._load_and_sync_knowledge_base()
        prospects_to_analyze = [pk for pk, data in knowledge_base.items() if 'g1_wot' in data.get('source', '')]
        
        geo_prompt_template = self._load_prompt('analyst_language_prompt_file')
        if not geo_prompt_template: return

        needs_analysis_count = 0
        save_interval = 50
        
        for i, pubkey in enumerate(prospects_to_analyze):
            prospect_data = knowledge_base[pubkey]
            
            if 'language' in prospect_data.get('metadata', {}):
                continue
            
            needs_analysis_count += 1
            profile = prospect_data.get('profile', {})
            description = (profile.get('_source', {}).get('description') or '').strip()

            if not description:
                meta = prospect_data.setdefault('metadata', {})
                meta['language'] = 'xx'
                meta['country'] = None
                meta['region'] = None
                continue

            self.logger.info(f"Analyse Géo-Linguistique {needs_analysis_count}/{len(prospects_to_analyze)} : {prospect_data.get('uid', 'N/A')}")
            prompt = f"{geo_prompt_template}\n\nTexte fourni: \"{description}\""
            
            try:
                ia_response = self._query_ia(prompt, expect_json=True)
                cleaned_answer = self._clean_ia_json_output(ia_response['answer'])
                geo_data = json.loads(cleaned_answer)
                
                meta = prospect_data.setdefault('metadata', {})
                meta['language'] = geo_data.get('language', 'xx')
                meta['country'] = geo_data.get('country')
                meta['region'] = geo_data.get('region')

                if needs_analysis_count > 0 and needs_analysis_count % save_interval == 0:
                    self.logger.info(f"--- Sauvegarde intermédiaire de la base de connaissance ({needs_analysis_count} profils analysés)... ---")
                    self._save_knowledge_base(knowledge_base)
            except Exception as e:
                self.logger.error(f"Impossible de géo-classifier le profil {prospect_data.get('uid')} : {e}")

        self.logger.info(f"Analyse Géo-Linguistique terminée. {needs_analysis_count} nouveaux profils ont été analysés. Sauvegarde finale.")
        self._save_knowledge_base(knowledge_base)

        # Agréger les résultats par PAYS
        self.logger.info("--- Agrégation des résultats par Pays ---")
        members_by_country = defaultdict(list)
        for pubkey, data in knowledge_base.items():
            country = data.get('metadata', {}).get('country')
            if country:
                members_by_country[country].append(data)
        
        clusters = []
        sorted_countries = sorted(members_by_country.items(), key=lambda item: len(item[1]), reverse=True)

        for country, members in sorted_countries:
            clusters.append({
                "cluster_name": f"Pays : {country}",
                "description": f"Groupe de {len(members)} membres localisés en '{country}'.",
                "members": members
            })
        
        self._select_and_save_cluster(clusters)

    def select_cluster_from_tags(self):
        """
        Agrège les tags existants dans la base de connaissance,
        présente les thèmes sous forme de clusters, et permet à 
        l'utilisateur de sélectionner une cible pour une campagne.
        """
        self.logger.info("🤖 Agent Analyste : Préparation du ciblage par thème...")
        knowledge_base = self._load_and_sync_knowledge_base()
        
        # Agréger les résultats
        self.logger.info("--- Agrégation des thèmes existants ---")
        members_by_tag = defaultdict(list)
        for pubkey, data in knowledge_base.items():
            if 'tags' in data.get('metadata', {}):
                for tag in data['metadata']['tags']:
                    members_by_tag[tag].append(data)
        
        if not members_by_tag:
            self.logger.warning("Aucun thème n'a encore été analysé. Veuillez lancer l'analyse par thèmes d'abord (option 2).")
            self.shared_state['status']['AnalystAgent'] = "Aucun thème à cibler."
            return

        clusters = []
        # Trier par nombre de membres, du plus grand au plus petit
        sorted_tags = sorted(members_by_tag.items(), key=lambda item: len(item[1]), reverse=True)

        # Limiter à l'affichage des 50 thèmes les plus populaires pour ne pas surcharger le menu
        for tag, members in sorted_tags[:50]:
            clusters.append({
                "cluster_name": f"Thème : {tag.capitalize()}",
                "description": f"Groupe de {len(members)} membres partageant l'intérêt ou la compétence '{tag}'.",
                "members": members
            })
        
        self.logger.info("Les 50 thèmes les plus populaires :")
        self._select_and_save_cluster(clusters)

    def run_thematic_analysis(self):
        """
        Analyse les descriptions des prospects pour en extraire des mots-clés
        thématiques (tags) et les sauvegarde dans la base de connaissance.
        """
        self.logger.info("🤖 Agent Analyste : Démarrage de l'analyse thématique (avec persistance)...")
        self.shared_state['status']['AnalystAgent'] = "Analyse thématique en cours..."

        if not self._check_ollama_once():
            self.shared_state['status']['AnalystAgent'] = "Échec : API Ollama indisponible."
            return
            
        knowledge_base = self._load_and_sync_knowledge_base()
        
        # --- Calculer les thèmes les plus pertinents pour guider l'IA ---
        tag_counter = Counter()
        for pk, data in knowledge_base.items():
            if 'tags' in data.get('metadata', {}):
                tag_counter.update(data['metadata']['tags'])
        
        # On prend les 100 thèmes les plus fréquents comme guide
        guide_tags = [tag for tag, count in tag_counter.most_common(100)]
        if guide_tags:
            self.logger.info(f"Utilisation des {len(guide_tags)} thèmes les plus fréquents comme guide pour l'IA.")

        prospects_to_analyze = [pk for pk, data in knowledge_base.items() if 'g1_wot' in data.get('source', '')]
        
        thematic_prompt_template = self._load_prompt('analyst_thematic_prompt_file')
        if not thematic_prompt_template: return

        needs_analysis_count = 0
        save_interval = 50
        
        for i, pubkey in enumerate(prospects_to_analyze):
            prospect_data = knowledge_base[pubkey]
            
            metadata = prospect_data.setdefault('metadata', {})
            if 'tags' in metadata: # 'tags' peut être une liste vide ou ['error']
                continue
            
            needs_analysis_count += 1
            profile = prospect_data.get('profile', {})
            description = (profile.get('_source', {}).get('description') or '').strip()

            if not description:
                metadata['tags'] = []
                continue

            self.logger.info(f"Analyse thématique {needs_analysis_count}/{len(prospects_to_analyze)} : {prospect_data.get('uid', 'N/A')}")
            
            # Construire le prompt guidé avec la liste concise
            prompt = f"{thematic_prompt_template}\n\nTexte fourni: \"{description}\""
            if guide_tags:
                prompt += f"\nThèmes existants : {json.dumps(guide_tags)}"
            
            try:
                ia_response = self._query_ia(prompt, expect_json=True)
                cleaned_answer = self._clean_ia_json_output(ia_response['answer'])
                tags = json.loads(cleaned_answer)

                # --- VALIDATION STRICTE ---
                if not isinstance(tags, list) or len(tags) > 7:
                    self.logger.warning(f"Réponse IA invalide pour {prospect_data.get('uid')} (format ou trop de tags). Marqué comme erreur.")
                    metadata['tags'] = ['error']
                    continue
                
                metadata['tags'] = tags
                
                if needs_analysis_count > 0 and needs_analysis_count % save_interval == 0:
                    self.logger.info(f"--- Sauvegarde intermédiaire de la base de connaissance ({needs_analysis_count} profils analysés)... ---")
                    self._save_knowledge_base(knowledge_base)
            except Exception as e:
                self.logger.error(f"Impossible de tagger le profil {prospect_data.get('uid')} : {e}")
                metadata['tags'] = ['error']

        self.logger.info(f"Analyse thématique terminée. {needs_analysis_count} nouveaux profils ont été taggés. Sauvegarde finale.")
        self._save_knowledge_base(knowledge_base)

        # Agréger les résultats
        self.logger.info("--- Agrégation des résultats thématiques ---")
        members_by_tag = defaultdict(list)
        for pubkey, data in knowledge_base.items():
            if 'tags' in data.get('metadata', {}):
                for tag in data['metadata']['tags']:
                    members_by_tag[tag].append(data)
        
        clusters = []
        sorted_tags = sorted(members_by_tag.items(), key=lambda item: len(item[1]), reverse=True)

        for tag, members in sorted_tags:
            clusters.append({
                "cluster_name": f"Thème : {tag.capitalize()}",
                "description": f"Groupe de {len(members)} membres partageant l'intérêt ou la compétence '{tag}'.",
                "members": members
            })
        
        self._select_and_save_cluster(clusters)

    def run_test_mode(self):
        """
        Génère un fichier de cible avec un unique profil de test
        pour valider rapidement les agents Stratège et Opérateur.
        """
        self.logger.info("🤖 Agent Analyste : Activation du Mode Test...")
        self.shared_state['status']['AnalystAgent'] = "Mode Test activé."
        
        test_pubkey = "DsEx1pS33vzYZg4MroyBV9hCw98j1gtHEhwiZ5tK7ech"

        # On charge la base pour avoir le profil complet
        knowledge_base = self._load_and_sync_knowledge_base()
        
        target_profile = knowledge_base.get(test_pubkey)

        if not target_profile:
            self.logger.error(f"Le profil de test avec la clé publique '{test_pubkey}' n'a pas été trouvé dans la base de connaissance.")
            self.shared_state['status']['AnalystAgent'] = "Échec : Profil de test non trouvé."
            return

        # On ne met que les informations nécessaires pour les agents suivants
        final_targets = [{
            "pubkey": test_pubkey,
            "uid": target_profile.get("uid"),
            "profile": target_profile.get("profile") # Le stratège peut en avoir besoin
        }]

        # On utilise la même méthode de sauvegarde que pour les vrais clusters
        target_file = os.path.join(self.shared_state['config']['workspace'], "todays_targets.json")
        try:
            with open(target_file, 'w') as f:
                json.dump(final_targets, f, indent=4, ensure_ascii=False)

            report = f"Mode Test : Cible unique '{target_profile.get('uid')}' enregistrée."
            self.logger.info(f"✅ {report}")
            self.shared_state['status']['AnalystAgent'] = report
            self.shared_state['analyst_report'] = "Cible du jour : Profil de test unique."
            self.shared_state['targets'] = final_targets
        except (IOError, TypeError) as e:
            self.logger.error(f"Impossible de créer le fichier de cible de test : {e}")
            self.shared_state['status']['AnalystAgent'] = "Échec de la création du fichier de test." 

    def create_automatic_personas(self):
        """
        Crée automatiquement des personas basés sur les thèmes les plus fréquents
        détectés dans la base de connaissance et remplit les banques 5-9.
        """
        self.logger.info("🎭 Agent Analyste : Création automatique de personas basés sur les thèmes...")
        
        # Vérifier Ollama
        if not self._check_ollama_once():
            self.logger.error("❌ Ollama non disponible. Impossible de créer les personas.")
            return
        
        # Charger la base de connaissance
        knowledge_base = self._load_and_sync_knowledge_base()
        if not knowledge_base:
            self.logger.error("❌ Base de connaissance vide. Impossible de créer les personas.")
            return
        
        # Analyser les thèmes existants
        all_tags = []
        analyzed_profiles = 0
        for pubkey, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            tags = metadata.get('tags', [])
            if tags and tags != ['error']:
                all_tags.extend(tags)
                analyzed_profiles += 1
        
        total_profiles = len(knowledge_base)
        self.logger.info(f"📊 Profils analysés : {analyzed_profiles} / {total_profiles}")
        
        # Vérifier si l'analyse est suffisante
        if not all_tags:
            self.logger.error("❌ Aucun thème détecté dans la base de connaissance. Lancez d'abord l'analyse thématique.")
            return
        
        # Si moins de 10% des profils sont analysés, proposer de lancer l'analyse
        if analyzed_profiles < total_profiles * 0.1:
            self.logger.warning(f"⚠️ Seulement {analyzed_profiles} profils analysés sur {total_profiles} ({analyzed_profiles/total_profiles*100:.1f}%)")
            self.logger.warning("⚠️ L'analyse thématique semble incomplète. Les personas générés pourraient ne pas être représentatifs.")
            
            choice = input("Voulez-vous lancer l'analyse thématique complète maintenant ? (o/n) : ").strip().lower()
            if choice in ['o', 'oui', 'y', 'yes']:
                self.logger.info("🔄 Lancement de l'analyse thématique complète...")
                self.run_thematic_analysis()
                
                # Recharger les données après analyse
                knowledge_base = self._load_and_sync_knowledge_base()
                all_tags = []
                analyzed_profiles = 0
                for pubkey, data in knowledge_base.items():
                    metadata = data.get('metadata', {})
                    tags = metadata.get('tags', [])
                    if tags and tags != ['error']:
                        all_tags.extend(tags)
                        analyzed_profiles += 1
                
                self.logger.info(f"📊 Profils analysés après analyse complète : {analyzed_profiles} / {total_profiles}")
            else:
                self.logger.info("ℹ️ Continuation avec les données existantes...")
        
        # Compter les occurrences et prendre le top 5
        tag_counts = Counter(all_tags)
        top_5_themes = tag_counts.most_common(5)
        
        self.logger.info(f"📊 Top 5 des thèmes détectés :")
        for i, (theme, count) in enumerate(top_5_themes, 1):
            self.logger.info(f"  {i}. {theme} ({count} occurrences)")
        
        # Charger la configuration des banques existante
        banks_config_file = os.path.join(self.shared_state['config']['workspace'], 'memory_banks_config.json')
        banks_config = self._load_banks_config(banks_config_file)
        
        # Créer les personas pour les banques 5-9
        for i, (theme, count) in enumerate(top_5_themes):
            bank_slot = str(5 + i)  # Banques 5, 6, 7, 8, 9
            
            self.logger.info(f"🎭 Création du persona pour le thème '{theme}' (banque {bank_slot})...")
            
            # Générer le persona avec l'IA
            persona = self._generate_persona_for_theme(theme, count, all_tags)
            
            if persona:
                # Remplir la banque
                banks_config['banks'][bank_slot] = {
                    'name': persona['name'],
                    'archetype': persona['archetype'],
                    'description': persona['description'],
                    'themes': [theme],
                    'corpus': persona['corpus']
                }
                
                self.logger.info(f"✅ Persona créé : {persona['name']} ({persona['archetype']})")
            else:
                self.logger.warning(f"⚠️ Échec de création du persona pour le thème '{theme}'")
        
        # Sauvegarder la configuration mise à jour
        self._save_banks_config(banks_config, banks_config_file)
        
        self.logger.info(f"🎉 Création automatique terminée ! {len(top_5_themes)} personas créés dans les banques 5-9.")
        
        # Afficher un résumé
        self.logger.info(f"\n📋 RÉSUMÉ DES PERSONAS CRÉÉS :")
        for i, (theme, count) in enumerate(top_5_themes):
            bank_slot = str(5 + i)
            bank = banks_config['banks'].get(bank_slot, {})
            if bank:
                self.logger.info(f"  Banque {bank_slot} : {bank['name']} ({bank['archetype']}) - Thème : {theme}")

    def _generate_persona_for_theme(self, theme, theme_count, all_tags):
        """
        Génère un persona complet pour un thème donné en utilisant l'IA.
        """
        # Construire le contexte avec les thèmes associés
        related_themes = [t for t in all_tags if t != theme and t in all_tags]
        related_themes_sample = related_themes[:10]  # Limiter pour éviter un prompt trop long
        
        prompt = f"""Tu es un expert en création de personas marketing. Tu dois créer un persona complet pour une campagne de communication UPlanet.

THÈME PRINCIPAL : {theme}
OCCURRENCES DÉTECTÉES : {theme_count}
THÈMES ASSOCIÉS : {', '.join(related_themes_sample)}

TÂCHE : Créer un persona marketing complet avec :
1. Un nom accrocheur
2. Un archétype psychologique
3. Une description du profil type
4. Un corpus de communication (vocabulaire, arguments, ton, exemples)

Le persona doit être adapté pour communiquer avec des personnes intéressées par le thème "{theme}" dans le contexte d'UPlanet (monnaie libre, identité numérique, décentralisation).

RÉPONSE ATTENDUE (JSON strict) :
{{
    "name": "Nom du Persona",
    "archetype": "Archétype psychologique",
    "description": "Description détaillée du profil type",
    "corpus": {{
        "tone": "Ton de communication (ex: bienveillant, technique, militant)",
        "vocabulary": ["mot1", "mot2", "mot3", "mot4", "mot5"],
        "arguments": [
            "Argument principal 1",
            "Argument principal 2", 
            "Argument principal 3"
        ],
        "examples": [
            "Exemple de phrase 1",
            "Exemple de phrase 2",
            "Exemple de phrase 3"
        ]
    }}
}}

IMPORTANT : 
- Le vocabulaire doit être spécifique au thème {theme}
- Les arguments doivent expliquer pourquoi UPlanet intéresse ce profil
- Le ton doit être adapté à l'archétype
- Les exemples doivent être des phrases complètes et engageantes
- Réponds UNIQUEMENT en JSON valide, sans commentaire."""

        try:
            response = self._query_ia(prompt, expect_json=True)
            cleaned_response = self._clean_ia_json_output(response['answer'])
            persona = json.loads(cleaned_response)
            
            # Validation de la structure
            required_keys = ['name', 'archetype', 'description', 'corpus']
            corpus_keys = ['tone', 'vocabulary', 'arguments', 'examples']
            
            if not all(key in persona for key in required_keys):
                self.logger.error(f"Structure du persona invalide pour {theme}")
                return None
                
            if not all(key in persona['corpus'] for key in corpus_keys):
                self.logger.error(f"Structure du corpus invalide pour {theme}")
                return None
            
            return persona
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la génération du persona pour {theme} : {e}")
            return None

    def _load_banks_config(self, config_file):
        """Charge la configuration des banques de mémoire."""
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Erreur lors du chargement de la config des banques : {e}")
        
        # Configuration par défaut si le fichier n'existe pas
        return {
            'banks': {},
            'available_themes': []
        }

    def _save_banks_config(self, banks_config, config_file):
        """Sauvegarde la configuration des banques de mémoire."""
        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(banks_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erreur lors de la sauvegarde de la config des banques : {e}")

    def _prepare_data(self):
        prospect_file = os.path.expanduser(self.shared_state['config']['prospect_file'])
        blocklist_file = self.shared_state['config']['blocklist_file']
        
        blocklist = set()
        if os.path.exists(blocklist_file):
            try:
                with open(blocklist_file, 'r') as f:
                    blocklist = set(u.get('pubkey') for u in json.load(f))
            except (json.JSONDecodeError, IOError):
                self.logger.warning(f"Impossible de lire la blocklist '{blocklist_file}'.")

        if not os.path.exists(prospect_file):
            self.logger.error(f"Fichier de prospects '{prospect_file}' non trouvé.")
            return []
        
        qualified_prospects = []
        try:
            with open(prospect_file, 'r') as f:
                data = json.load(f)
            
            for member in data.get('members', []):
                pubkey = member.get("pubkey")
                if pubkey in blocklist: continue
                if 'g1_wot' in member.get('source', ''):
                    profile = member.get('profile', {}).get('_source', {})
                    qualified_prospects.append({
                        "uid": member.get("uid"),
                        "pubkey": pubkey,
                        "description": profile.get("description"),
                        "city": profile.get("city"),
                        "geoPoint": profile.get("geoPoint")
                    })
            self.logger.info(f"{len(qualified_prospects)} prospects qualifiés ('Bâtisseurs') trouvés pour l'analyse.")
            return qualified_prospects
        except Exception as e:
            self.logger.error(f"Erreur lors de la préparation des données : {e}", exc_info=True)
            return []

    def _query_ia(self, prompt, expect_json=False):
        command = ['python3', self.shared_state['config']['question_script'], prompt]
        if expect_json:
            command.append('--json')
        
        self.logger.debug(f"Exécution de la commande IA : {' '.join(command[:2])}...")
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        self.logger.debug(f"Réponse brute de l'IA reçue : {result.stdout.strip()}")

        if expect_json:
            return json.loads(result.stdout)
        return result.stdout

    def _load_prompt(self, prompt_key):
        try:
            prompt_file = self.shared_state['config'][prompt_key]
            with open(prompt_file, 'r') as f:
                return f.read()
        except (KeyError, FileNotFoundError) as e:
            self.logger.error(f"Impossible de charger le fichier de prompt '{prompt_key}': {e}")
            return None

    def _select_and_save_cluster(self, clusters):
        if not clusters or not isinstance(clusters, list):
            self.logger.warning("Aucun cluster valide n'a été retourné par l'IA.")
            self.shared_state['status']['AnalystAgent'] = "Terminé : Aucun cluster formé."
            return

        self.logger.info("Clusters finaux identifiés par l'IA :")
        
        valid_clusters = []
        for i, cluster in enumerate(clusters):
            # --- VALIDATION DE LA STRUCTURE DU CLUSTER ---
            if not isinstance(cluster, dict):
                self.logger.warning(f"Item {i} n'est pas un cluster valide (n'est pas un dictionnaire), ignoré.")
                continue

            name = cluster.get('cluster_name', f'Cluster sans nom {i+1}')
            desc = cluster.get('description', 'Pas de description.')
            members = cluster.get('members')

            if not isinstance(members, list):
                self.logger.warning(f"Le cluster '{name}' a été ignoré car sa liste de membres est invalide ou manquante.")
                continue
            
            valid_clusters.append(cluster)
            
            print(f"\n{len(valid_clusters)}. {name} ({len(members)} membres)")
            print(f"   Description : {desc}")
        
        if not valid_clusters:
            self.logger.error("Aucun des clusters retournés par l'IA n'avait le format requis. Impossible de continuer.")
            self.shared_state['status']['AnalystAgent'] = "Échec : Format de cluster invalide."
            return

        try:
            choice = int(input("\nChoisissez le numéro du cluster à cibler : ")) - 1
            if not (0 <= choice < len(valid_clusters)): raise ValueError()
            
            selected_cluster = valid_clusters[choice]
            final_targets = selected_cluster['members']

            target_file = os.path.join(self.shared_state['config']['workspace'], "todays_targets.json")
            with open(target_file, 'w') as f:
                json.dump(final_targets, f, indent=4, ensure_ascii=False)

            report = f"Cluster '{selected_cluster['cluster_name']}' sélectionné. {len(final_targets)} cibles enregistrées."
            self.logger.info(f"✅ {report}")
            self.shared_state['status']['AnalystAgent'] = report
            self.shared_state['analyst_report'] = f"Cible du jour : {selected_cluster['description']}"
            self.shared_state['targets'] = final_targets
        except (ValueError, IndexError):
            self.logger.error("Choix invalide.")
        except KeyboardInterrupt:
            self.logger.info("Opération annulée.") 

    def _check_ollama_once(self):
        """Vérifie une seule fois que l'API Ollama est disponible."""
        if not getattr(self, '_ollama_checked', False):
            ollama_script = self.shared_state['config']['ollama_script']
            self.logger.info("Vérification de la disponibilité de l'API Ollama...")
            self.logger.debug(f"Exécution du script de vérification : {ollama_script}")
            try:
                subprocess.run([ollama_script], check=True, capture_output=True, text=True)
                self.logger.info("✅ API Ollama accessible.")
                self._ollama_checked = True
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                self.logger.error(f"L'API Ollama n'est pas accessible. Erreur : {e}")
                self._ollama_checked = False
        return self._ollama_checked 

    def run_test_mode(self):
        """
        Génère un fichier de cible avec un unique profil de test
        pour valider rapidement les agents Stratège et Opérateur.
        """
        self.logger.info("🤖 Agent Analyste : Activation du Mode Test...")
        self.shared_state['status']['AnalystAgent'] = "Mode Test activé."
        
        test_pubkey = "DsEx1pS33vzYZg4MroyBV9hCw98j1gtHEhwiZ5tK7ech"

        # On charge la base pour avoir le profil complet
        knowledge_base = self._load_and_sync_knowledge_base()
        
        target_profile = knowledge_base.get(test_pubkey)

        if not target_profile:
            self.logger.error(f"Le profil de test avec la clé publique '{test_pubkey}' n'a pas été trouvé dans la base de connaissance.")
            self.shared_state['status']['AnalystAgent'] = "Échec : Profil de test non trouvé."
            return

        # On ne met que les informations nécessaires pour les agents suivants
        final_targets = [{
            "pubkey": test_pubkey,
            "uid": target_profile.get("uid"),
            "profile": target_profile.get("profile") # Le stratège peut en avoir besoin
        }]

        # On utilise la même méthode de sauvegarde que pour les vrais clusters
        target_file = os.path.join(self.shared_state['config']['workspace'], "todays_targets.json")
        try:
            with open(target_file, 'w') as f:
                json.dump(final_targets, f, indent=4, ensure_ascii=False)

            report = f"Mode Test : Cible unique '{target_profile.get('uid')}' enregistrée."
            self.logger.info(f"✅ {report}")
            self.shared_state['status']['AnalystAgent'] = report
            self.shared_state['analyst_report'] = "Cible du jour : Profil de test unique."
            self.shared_state['targets'] = final_targets
        except (IOError, TypeError) as e:
            self.logger.error(f"Impossible de créer le fichier de cible de test : {e}")
            self.shared_state['status']['AnalystAgent'] = "Échec de la création du fichier de test." 