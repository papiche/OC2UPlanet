from .base_agent import Agent
import json
import os
import subprocess
import random
import requests
import time
from collections import defaultdict, Counter
import unicodedata

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
        web2_analyzed = 0
        gps_prospects = 0
        
        for pk, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            if 'language' in metadata:
                language_analyzed += 1
            if 'tags' in metadata:
                tags_analyzed += 1
            if 'web2' in metadata:
                web2_analyzed += 1
            
            # Compter les profils avec GPS
            profile = data.get('profile', {})
            if profile and '_source' in profile:
                source = profile['_source']
                geo_point = source.get('geoPoint', {})
                if geo_point and 'lat' in geo_point and 'lon' in geo_point:
                    lat = geo_point.get('lat')
                    lon = geo_point.get('lon')
                    if lat is not None and lon is not None and lat != 0 and lon != 0:
                        gps_prospects += 1
                
        return {
            "total": total_prospects,
            "language": language_analyzed,
            "tags": tags_analyzed,
            "web2": web2_analyzed,
            "gps_prospects": gps_prospects
        }

    def run_geo_linguistic_analysis(self):
        """
        Analyse les descriptions pour en extraire la langue, le pays et la région
        et sauvegarde ces données dans la base de connaissance.
        Utilise d'abord un service de géolocalisation pour les coordonnées GPS,
        puis l'IA en dernier recours pour l'analyse textuelle.
        """
        self.logger.info("🤖 Agent Analyste : Démarrage de l'analyse Géo-Linguistique optimisée...")
        self.shared_state['status']['AnalystAgent'] = "Analyse Géo-Linguistique en cours..."

        knowledge_base = self._load_and_sync_knowledge_base()
        prospects_to_analyze = [pk for pk, data in knowledge_base.items() if 'g1_wot' in data.get('source', '')]
        
        geo_prompt_template = self._load_prompt('analyst_language_prompt_file')
        if not geo_prompt_template: return

        needs_analysis_count = 0
        save_interval = 50
        
        # Statistiques de traitement
        gps_geolocated = 0
        ia_analyzed = 0
        skipped = 0
        
        # Limite pour éviter de surcharger Nominatim (max 10000 requêtes GPS par session)
        gps_requests_made = 0
                
        for i, pubkey in enumerate(prospects_to_analyze):
            prospect_data = knowledge_base[pubkey]
            
            if 'language' in prospect_data.get('metadata', {}):
                continue
            
            needs_analysis_count += 1
            profile = prospect_data.get('profile', {})
            source = profile.get('_source', {})
            description = (source.get('description') or '').strip()
            geo_point = source.get('geoPoint', {})

            # Étape 1 : Vérifier si on a des coordonnées GPS ET si on n'a pas dépassé la limite
            if (geo_point and 'lat' in geo_point and 'lon' in geo_point):
                lat = geo_point.get('lat')
                lon = geo_point.get('lon')
                
                if lat is not None and lon is not None and lat != 0 and lon != 0:
                    gps_requests_made += 1
                    self.logger.info(f"📍 Géolocalisation GPS {gps_requests_made} : {needs_analysis_count}/{len(prospects_to_analyze)} : {prospect_data.get('uid', 'N/A')}")
                    
                    # Utiliser le service de géolocalisation
                    geo_data = self._geolocate_from_coordinates(lat, lon)
                    
                    if geo_data:
                        meta = prospect_data.setdefault('metadata', {})
                        
                        # Ne pas écrire les champs si les valeurs sont inconnues
                        language = geo_data.get('language', 'xx')
                        if language != 'xx':
                            meta['language'] = language
                        
                        country = geo_data.get('country')
                        if country:
                            meta['country'] = country
                        
                        region = geo_data.get('region')
                        if region:
                            meta['region'] = region
                        
                        city = geo_data.get('city')
                        if city:
                            meta['city'] = city
                        
                        meta['geolocation_source'] = 'gps_service'
                        
                        gps_geolocated += 1
                        self.logger.debug(f"✅ Géolocalisé via GPS : {geo_data.get('country', 'N/A')} - {geo_data.get('region', 'N/A')}")
                        
                        if needs_analysis_count > 0 and needs_analysis_count % save_interval == 0:
                            self.logger.info(f"--- Sauvegarde intermédiaire ({needs_analysis_count} profils analysés)... ---")
                            self._save_knowledge_base(knowledge_base)
                        continue
                    else:
                        self.logger.debug(f"⚠️ Échec géolocalisation GPS pour {prospect_data.get('uid', 'N/A')}")
            
            # Étape 2 : Si pas de GPS, ou géolocalisation échouée, essayer l'analyse textuelle
            if description:
                self.logger.info(f"🧠 Analyse IA {needs_analysis_count}/{len(prospects_to_analyze)} : {prospect_data.get('uid', 'N/A')}")
                prompt = f"{geo_prompt_template}\n\nTexte fourni: \"{description}\""
                
                try:
                    ia_response = self._query_ia(prompt, expect_json=True)
                    cleaned_answer = self._clean_ia_json_output(ia_response['answer'])
                    geo_data = json.loads(cleaned_answer)
                    
                    meta = prospect_data.setdefault('metadata', {})
                    
                    # Ne pas écrire les champs si les valeurs sont inconnues
                    language = geo_data.get('language', 'xx')
                    if language != 'xx':
                        meta['language'] = language
                    
                    country = geo_data.get('country')
                    if country:
                        meta['country'] = country
                    
                    region = geo_data.get('region')
                    if region:
                        meta['region'] = region
                    
                    meta['geolocation_source'] = 'ia_analysis'
                    
                    ia_analyzed += 1
                    
                    if needs_analysis_count > 0 and needs_analysis_count % save_interval == 0:
                        self.logger.info(f"--- Sauvegarde intermédiaire ({needs_analysis_count} profils analysés)... ---")
                        self._save_knowledge_base(knowledge_base)
                except Exception as e:
                    self.logger.error(f"Impossible de géo-classifier le profil {prospect_data.get('uid')} : {e}")
                    # En cas d'erreur, ne pas écrire de métadonnées vides
                    skipped += 1

        self.logger.info(f"✅ Analyse Géo-Linguistique terminée.")
        self.logger.info(f"📊 Statistiques :")
        self.logger.info(f"   • Géolocalisés via GPS : {gps_geolocated}")
        self.logger.info(f"   • Analysés via IA : {ia_analyzed}")
        self.logger.info(f"   • Passés (pas de données) : {skipped}")
        self.logger.info(f"   • Total traités : {needs_analysis_count}")
        
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

    def _geolocate_from_coordinates(self, lat, lon):
        """
        Utilise un service de géolocalisation pour obtenir les informations
        de pays, région et ville à partir de coordonnées GPS.
        """
        try:
            # Respecter les limites de Nominatim : max 1 requête par seconde
            # Utiliser un délai aléatoire entre 1.1 et 1.3 secondes (> 1)
            time.sleep(random.uniform(1.1, 1.3))
            
            # Utiliser l'API Nominatim (OpenStreetMap) - gratuite et fiable
            import requests
            
            url = f"https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'accept-language': 'fr,en',
                'addressdetails': 1
            }
            
            # Ajouter un User-Agent pour respecter les conditions d'utilisation
            headers = {
                'User-Agent': 'UPlanet ORIGIN ZEN - AstroBot/1.0 (https://qo-op.com)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'error' in data:
                self.logger.warning(f"⚠️ Erreur de géolocalisation : {data['error']}")
                return None
            
            # Extraire les informations
            address = data.get('address', {})
            
            # Déterminer le pays
            country = address.get('country') or address.get('country_code', '').upper()
            
            # Déterminer la région/état
            region = (
                address.get('state') or 
                address.get('region') or 
                address.get('province') or 
                address.get('county')
            )
            
            # Déterminer la ville
            city = (
                address.get('city') or 
                address.get('town') or 
                address.get('village') or 
                address.get('municipality')
            )
            
            # Déterminer la langue basée sur le pays
            language = self._get_language_from_country(country)
            
            geo_data = {
                'language': language,
                'country': country,
                'region': region,
                'city': city
            }
            
            self.logger.debug(f"📍 Géolocalisation réussie : {country} - {region} - {city}")
            return geo_data
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"⚠️ Erreur de requête géolocalisation : {e}")
            return None
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur de géolocalisation : {e}")
            return None

    def _get_language_from_country(self, country):
        """
        Détermine la langue principale basée sur le pays.
        """
        if not country:
            return 'xx'
        
        # Mapping pays -> langue principale
        country_language_map = {
            'FRANCE': 'fr',
            'FR': 'fr',
            'BELGIUM': 'fr',
            'BE': 'fr',
            'SWITZERLAND': 'fr',
            'CH': 'fr',
            'CANADA': 'fr',
            'CA': 'fr',
            'UNITED STATES': 'en',
            'US': 'en',
            'USA': 'en',
            'UNITED KINGDOM': 'en',
            'GB': 'en',
            'UK': 'en',
            'SPAIN': 'es',
            'ES': 'es',
            'MEXICO': 'es',
            'MX': 'es',
            'ARGENTINA': 'es',
            'AR': 'es',
            'GERMANY': 'de',
            'DE': 'de',
            'AUSTRIA': 'de',
            'AT': 'de',
            'SWITZERLAND': 'de',  # Suisse germanophone
            'ITALY': 'it',
            'IT': 'it',
            'PORTUGAL': 'pt',
            'PT': 'pt',
            'BRAZIL': 'pt',
            'BR': 'pt',
            'NETHERLANDS': 'nl',
            'NL': 'nl',
            'CATALONIA': 'ca',
            'CATALUNYA': 'ca'
        }
        
        return country_language_map.get(country.upper(), 'xx')

    def select_cluster_from_tags(self):
        """
        Agrège les tags existants dans la base de connaissance,
        présente les thèmes sous forme de clusters, et permet à 
        l'utilisateur de sélectionner une cible pour une campagne.
        Inclut également les réseaux sociaux (web2).
        """
        self.logger.info("🤖 Agent Analyste : Préparation du ciblage par thème et réseaux sociaux...")
        knowledge_base = self._load_and_sync_knowledge_base()
        
        # Agréger les résultats (thèmes + réseaux sociaux)
        self.logger.info("--- Agrégation des thèmes et réseaux sociaux existants ---")
        members_by_tag = defaultdict(list)
        
        for pubkey, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            
            # Ajouter les tags thématiques
            if 'tags' in metadata:
                for tag in metadata['tags']:
                    members_by_tag[tag].append(data)
            
            # Ajouter les réseaux sociaux (web2)
            if 'web2' in metadata:
                for social in metadata['web2']:
                    members_by_tag[social].append(data)
        
        if not members_by_tag:
            self.logger.warning("Aucun thème ou réseau social n'a encore été analysé. Veuillez lancer l'analyse par thèmes d'abord (option 2).")
            self.shared_state['status']['AnalystAgent'] = "Aucun thème à cibler."
            return

        clusters = []
        # Trier par nombre de membres, du plus grand au plus petit
        sorted_tags = sorted(members_by_tag.items(), key=lambda item: len(item[1]), reverse=True)

        # Limiter à l'affichage des 50 thèmes/réseaux les plus populaires pour ne pas surcharger le menu
        for tag, members in sorted_tags[:50]:
            # Déterminer le type (thème ou réseau social)
            tag_type = "Réseau" if tag in ['website', 'facebook', 'email', 'instagram', 'youtube', 'twitter', 'diaspora', 'linkedin', 'github', 'phone', 'vimeo'] else "Thème"
            
            clusters.append({
                "cluster_name": f"{tag_type} : {tag.capitalize()}",
                "description": f"Groupe de {len(members)} membres avec '{tag}'.",
                "members": members
            })
        
        self.logger.info("Les 50 thèmes et réseaux sociaux les plus populaires :")
        self._select_and_save_cluster(clusters)

    def run_thematic_analysis(self):
        """
        Analyse les descriptions des prospects pour en extraire des mots-clés
        thématiques (tags) et les sauvegarde dans la base de connaissance.
        Inclut également les réseaux sociaux détectés dans les profils.
        """
        self.logger.info("🤖 Agent Analyste : Démarrage de l'analyse thématique enrichie (avec persistance)...")
        self.shared_state['status']['AnalystAgent'] = "Analyse thématique enrichie en cours..."

        if not self._check_ollama_once():
            self.shared_state['status']['AnalystAgent'] = "Échec : API Ollama indisponible."
            return
            
        knowledge_base = self._load_and_sync_knowledge_base()
        
        # --- Calculer les thèmes les plus pertinents pour guider l'IA ---
        tag_counter = Counter()
        for pk, data in knowledge_base.items():
            if 'tags' in data.get('metadata', {}):
                tag_counter.update(data['metadata']['tags'])
        
        # TOP 50 thèmes les plus fréquents comme guide
        guide_tags = [tag for tag, count in tag_counter.most_common(50)]
        if guide_tags:
            self.logger.info(f"Utilisation des {len(guide_tags)} thèmes les plus fréquents comme guide pour l'IA.")

        prospects_to_analyze = [pk for pk, data in knowledge_base.items() if 'g1_wot' in data.get('source', '')]
        
        thematic_prompt_template = self._load_prompt('analyst_thematic_prompt_file')
        if not thematic_prompt_template: return

        needs_analysis_count = 0
        save_interval = 50
        
        # Statistiques des réseaux sociaux
        social_stats = Counter()
        
        for i, pubkey in enumerate(prospects_to_analyze):
            prospect_data = knowledge_base[pubkey]
            
            metadata = prospect_data.setdefault('metadata', {})
            if 'tags' in metadata: # 'tags' peut être une liste vide ou ['error']
                continue
            
            needs_analysis_count += 1
            profile = prospect_data.get('profile', {})
            source = profile.get('_source', {})
            description = (source.get('description') or '').strip()
            socials = source.get('socials', [])

            # --- ÉTAPE 1 : Extraire les réseaux sociaux ---
            social_tags = []
            for social in socials:
                social_type = social.get('type', '').lower()
                if social_type:
                    # Normaliser les noms des réseaux sociaux
                    social_mapping = {
                        'web': 'website',
                        'facebook': 'facebook',
                        'email': 'email',
                        'instagram': 'instagram',
                        'youtube': 'youtube',
                        'twitter': 'twitter',
                        'diaspora': 'diaspora',
                        'linkedin': 'linkedin',
                        'github': 'github',
                        'phone': 'phone',
                        'vimeo': 'vimeo'
                    }
                    
                    normalized_type = social_mapping.get(social_type, social_type)
                    if normalized_type not in social_tags:
                        social_tags.append(normalized_type)
                        social_stats[normalized_type] += 1

            # --- ÉTAPE 2 : Analyse thématique de la description ---
            thematic_tags = []
            if description:
                self.logger.info(f"Analyse thématique {needs_analysis_count}/{len(prospects_to_analyze)} : {prospect_data.get('uid', 'N/A')}")
                
                # Construire le prompt guidé avec la liste concise
                prompt = f"{thematic_prompt_template}\n\nTexte fourni: \"{description}\""
                if guide_tags:
                    prompt += f"\nThèmes existants : {json.dumps(guide_tags)}"
                
                try:
                    ia_response = self._query_ia(prompt, expect_json=True)
                    cleaned_answer = self._clean_ia_json_output(ia_response['answer'])
                    thematic_tags = json.loads(cleaned_answer)

                    # --- VALIDATION STRICTE ---
                    if not isinstance(thematic_tags, list) or len(thematic_tags) > 7:
                        self.logger.warning(f"Réponse IA invalide pour {prospect_data.get('uid')} (format ou trop de tags). Marqué comme erreur.")
                        thematic_tags = ['error']
                except Exception as e:
                    self.logger.error(f"Impossible de tagger le profil {prospect_data.get('uid')} : {e}")
                    thematic_tags = ['error']
            else:
                self.logger.debug(f"Pas de description pour {prospect_data.get('uid', 'N/A')}")

            # --- ÉTAPE 3 : Séparer les tags thématiques et les réseaux sociaux ---
            # Tags thématiques uniquement (pas de réseaux sociaux mélangés)
            metadata['tags'] = thematic_tags
            
            # Réseaux sociaux dans un champ séparé
            if social_tags:
                metadata['web2'] = social_tags
                self.logger.debug(f"📱 Réseaux sociaux détectés pour {prospect_data.get('uid', 'N/A')} : {', '.join(social_tags)}")
            else:
                # Ne pas créer le champ web2 s'il n'y a pas de réseaux sociaux
                pass

            if needs_analysis_count > 0 and needs_analysis_count % save_interval == 0:
                self.logger.info(f"--- Sauvegarde intermédiaire de la base de connaissance ({needs_analysis_count} profils analysés)... ---")
                self._save_knowledge_base(knowledge_base)

        # Afficher les statistiques des réseaux sociaux
        self.logger.info(f"📊 Statistiques des réseaux sociaux détectés :")
        for social_type, count in social_stats.most_common():
            self.logger.info(f"   • {social_type}: {count} profils")

        self.logger.info(f"Analyse thématique enrichie terminée. {needs_analysis_count} nouveaux profils ont été taggés. Sauvegarde finale.")
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
        self.logger.info("🧪 Agent Analyste : Activation du Mode Test...")
        self.shared_state['status']['AnalystAgent'] = "Mode Test activé."
        
        # Charger la base de connaissance
        knowledge_base = self._load_and_sync_knowledge_base()
        
        print("\n🧪 MODE TEST - SÉLECTION DE LA CIBLE")
        print("=" * 50)
        print("Choisissez une option pour la cible de test :")
        print("1. 🎯 Utiliser la cible de test par défaut")
        print("2. 🔑 Spécifier une clé publique (pubkey)")
        print("3. 👤 Spécifier un identifiant utilisateur (uid)")
        print("4. 📋 Voir les prospects disponibles")
        
        try:
            choice = input("\nChoisissez une option (1-4) : ").strip()
            
            target_profile = None
            test_pubkey = None
            test_uid = None
            
            if choice == "1":
                # Cible de test par défaut
                test_pubkey = "DsEx1pS33vzYZg4MroyBV9hCw98j1gtHEhwiZ5tK7ech"
                target_profile = knowledge_base.get(test_pubkey)
                
                if not target_profile:
                    self.logger.error(f"Le profil de test par défaut n'a pas été trouvé dans la base de connaissance.")
                    self.shared_state['status']['AnalystAgent'] = "Échec : Profil de test par défaut non trouvé."
                    return
                
                test_uid = target_profile.get("uid")
                self.logger.info(f"🎯 Utilisation de la cible de test par défaut : {test_uid}")
                
            elif choice == "2":
                # Spécifier une pubkey
                test_pubkey = input("Entrez la clé publique (pubkey) : ").strip()
                if not test_pubkey:
                    self.logger.warning("Aucune clé publique spécifiée. Utilisation de la cible par défaut.")
                    test_pubkey = "DsEx1pS33vzYZg4MroyBV9hCw98j1gtHEhwiZ5tK7ech"
                
                target_profile = knowledge_base.get(test_pubkey)
                if not target_profile:
                    self.logger.error(f"Le profil avec la clé publique '{test_pubkey}' n'a pas été trouvé dans la base de connaissance.")
                    self.shared_state['status']['AnalystAgent'] = "Échec : Profil non trouvé."
                    return
                
                test_uid = target_profile.get("uid")
                self.logger.info(f"🔑 Cible trouvée par pubkey : {test_uid}")
                
            elif choice == "3":
                # Spécifier un uid
                test_uid = input("Entrez l'identifiant utilisateur (uid) : ").strip()
                if not test_uid:
                    self.logger.warning("Aucun uid spécifié. Utilisation de la cible par défaut.")
                    test_pubkey = "DsEx1pS33vzYZg4MroyBV9hCw98j1gtHEhwiZ5tK7ech"
                    target_profile = knowledge_base.get(test_pubkey)
                else:
                    # Chercher par uid
                    target_profile = None
                    for pubkey, data in knowledge_base.items():
                        if data.get("uid") == test_uid:
                            target_profile = data
                            test_pubkey = pubkey
                            break
                    
                    if not target_profile:
                        self.logger.error(f"Le profil avec l'uid '{test_uid}' n'a pas été trouvé dans la base de connaissance.")
                        self.shared_state['status']['AnalystAgent'] = "Échec : Profil non trouvé."
                        return
                
                self.logger.info(f"👤 Cible trouvée par uid : {test_uid}")
                
            elif choice == "4":
                # Afficher les prospects disponibles
                print(f"\n📋 PROSPECTS DISPONIBLES POUR LE MODE TEST")
                print("=" * 60)
                print("Affichage des 20 premiers prospects (uid | pubkey | tags)")
                print("-" * 60)
                
                count = 0
                for pubkey, data in knowledge_base.items():
                    if count >= 20:
                        break
                    uid = data.get("uid", "N/A")
                    metadata = data.get("metadata", {})
                    tags = metadata.get("tags", [])
                    tags_str = ", ".join(tags[:3]) if tags else "Aucun tag"
                    if len(tags) > 3:
                        tags_str += "..."
                    
                    print(f"{count+1:2d}. {uid:<20} | {pubkey[:20]}... | {tags_str}")
                    count += 1
                
                print("-" * 60)
                print(f"Total : {len(knowledge_base)} prospects dans la base de connaissance")
                print("Utilisez l'option 2 (pubkey) ou 3 (uid) pour sélectionner un prospect spécifique")
                return
                
            else:
                self.logger.warning("Option invalide. Utilisation de la cible de test par défaut.")
                test_pubkey = "DsEx1pS33vzYZg4MroyBV9hCw98j1gtHEhwiZ5tK7ech"
                target_profile = knowledge_base.get(test_pubkey)
                if not target_profile:
                    self.logger.error("Le profil de test par défaut n'a pas été trouvé.")
                    return
                test_uid = target_profile.get("uid")
            
            # Afficher les informations de la cible sélectionnée
            if target_profile:
                uid = target_profile.get("uid", "N/A")
                pubkey = target_profile.get("pubkey", "N/A")
                metadata = target_profile.get("metadata", {})
                
                print(f"\n🎯 INFORMATIONS DE LA CIBLE SÉLECTIONNÉE")
                print("=" * 50)
                print(f"👤 UID : {uid}")
                print(f"🔑 Pubkey : {pubkey}")
                
                # Informations géographiques
                language = metadata.get("language", "Non détecté")
                country = metadata.get("country", "Non détecté")
                region = metadata.get("region", "Non détecté")
                
                print(f"🌍 Langue : {language}")
                print(f"🌍 Pays : {country}")
                print(f"🌍 Région : {region}")
                
                # Tags/thèmes
                tags = metadata.get("tags", [])
                if tags:
                    print(f"🏷️  Tags : {', '.join(tags)}")
                else:
                    print(f"🏷️  Tags : Aucun tag")
                
                # Description
                profile = target_profile.get("profile", {})
                description = profile.get("_source", {}).get("description", "")
                if description:
                    print(f"📝 Description : {description[:100]}{'...' if len(description) > 100 else ''}")
                else:
                    print(f"📝 Description : Aucune description")
                
                print("=" * 50)
            
            # On ne met que les informations nécessaires pour les agents suivants
            final_targets = [{
                "pubkey": test_pubkey,
                "uid": test_uid,
                "profile": target_profile.get("profile") # Le stratège peut en avoir besoin
            }]

            # On utilise la même méthode de sauvegarde que pour les vrais clusters
            target_file = os.path.join(self.shared_state['config']['workspace'], "todays_targets.json")
            try:
                with open(target_file, 'w') as f:
                    json.dump(final_targets, f, indent=4, ensure_ascii=False)

                report = f"Mode Test : Cible unique '{test_uid}' enregistrée."
                self.logger.info(f"✅ {report}")
                self.shared_state['status']['AnalystAgent'] = report
                self.shared_state['analyst_report'] = f"Cible du jour : Profil de test unique ({test_uid})."
                self.shared_state['targets'] = final_targets
            except (IOError, TypeError) as e:
                self.logger.error(f"Impossible de créer le fichier de cible de test : {e}")
                self.shared_state['status']['AnalystAgent'] = "Échec de la création du fichier de test."
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la sélection de la cible de test : {e}")
            self.shared_state['status']['AnalystAgent'] = "Échec : Erreur lors de la sélection." 

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
        
        # Détecter les langues disponibles
        languages = self._detect_available_languages()
        self.logger.info(f"🌍 Langues détectées pour les personas multilingues :")
        for lang in languages:
            lang_name = {
                'fr': 'Français', 'en': 'Anglais', 'es': 'Espagnol',
                'de': 'Allemand', 'it': 'Italien', 'pt': 'Portugais'
            }.get(lang, lang.upper())
            self.logger.info(f"  • {lang} : {lang_name}")
        
        # Créer les personas pour les banques 5-9
        for i, (theme, count) in enumerate(top_5_themes):
            bank_slot = str(5 + i)  # Banques 5, 6, 7, 8, 9
            
            self.logger.info(f"🎭 Création du persona multilingue pour le thème '{theme}' (banque {bank_slot})...")
            
            # Générer le persona avec l'IA
            persona = self._generate_persona_for_theme(theme, count, all_tags)
            
            if persona:
                # Remplir la banque avec le contenu multilingue
                banks_config['banks'][bank_slot] = {
                    'name': persona['name'],
                    'archetype': persona['archetype'],
                    'description': persona['description'],
                    'themes': [theme],
                    'corpus': persona['corpus'],
                    'multilingual': persona.get('multilingual', {})
                }
                
                # Afficher les langues supportées
                supported_langs = list(persona.get('multilingual', {}).keys())
                lang_names = []
                for lang in supported_langs:
                    lang_name = {
                        'fr': 'Français', 'en': 'Anglais', 'es': 'Espagnol',
                        'de': 'Allemand', 'it': 'Italien', 'pt': 'Portugais'
                    }.get(lang, lang.upper())
                    lang_names.append(lang_name)
                
                self.logger.info(f"✅ Persona multilingue créé : {persona['name']} ({persona['archetype']})")
                self.logger.info(f"🌍 Langues supportées : {', '.join(supported_langs)}")
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
        Inclut maintenant la génération multilingue.
        """
        # Construire le contexte avec les thèmes associés
        related_themes = [t for t in all_tags if t != theme and t in all_tags]
        related_themes_sample = related_themes[:10]  # Limiter pour éviter un prompt trop long
        
        # Détecter les langues disponibles dans la base
        languages = self._detect_available_languages()
        
        prompt = f"""Tu es un expert en création de personas marketing multilingues. Tu dois créer un persona complet pour une campagne de communication UPlanet.

THÈME PRINCIPAL : {theme}
OCCURRENCES DÉTECTÉES : {theme_count}
THÈMES ASSOCIÉS : {', '.join(related_themes_sample)}
LANGUES DISPONIBLES : {', '.join(languages)}

TÂCHE : Créer un persona marketing complet avec :
1. Un nom accrocheur
2. Un archétype psychologique
3. Une description du profil type
4. Un corpus de communication (vocabulaire, arguments, ton, exemples)
5. Une version multilingue du contenu pour chaque langue

IMPORTANT : Tu dois créer le contenu dans TOUTES les langues disponibles ({', '.join(languages)}).
Pour chaque langue, adapte le contenu culturellement tout en gardant la même personnalité.

Format de réponse JSON :
{{
  "name": "Nom du persona",
    "archetype": "Archétype psychologique",
  "description": "Description du profil type",
  "themes": ["{theme}"],
    "corpus": {{
    "tone": "ton de communication",
    "vocabulary": ["mot1", "mot2", "mot3"],
    "arguments": ["argument1", "argument2", "argument3"],
    "examples": ["exemple1", "exemple2", "exemple3"]
  }},
  "multilingual": {{
    "fr": {{
      "name": "Nom en français",
      "archetype": "Archétype en français",
      "tone": "ton en français",
      "vocabulary": ["mot1", "mot2", "mot3"],
      "arguments": ["argument1", "argument2", "argument3"],
      "examples": ["exemple1", "exemple2", "exemple3"]
    }},
    "en": {{
      "name": "Name in English",
      "archetype": "Archetype in English",
      "tone": "tone in English",
      "vocabulary": ["word1", "word2", "word3"],
      "arguments": ["argument1", "argument2", "argument3"],
      "examples": ["example1", "example2", "example3"]
    }},
    "es": {{
      "name": "Nombre en español",
      "archetype": "Arquetipo en español",
      "tone": "tono en español",
      "vocabulary": ["palabra1", "palabra2", "palabra3"],
      "arguments": ["argumento1", "argumento2", "argumento3"],
      "examples": ["ejemplo1", "ejemplo2", "ejemplo3"]
    }},
    "de": {{
      "name": "Name auf Deutsch",
      "archetype": "Archetyp auf Deutsch",
      "tone": "Ton auf Deutsch",
      "vocabulary": ["Wort1", "Wort2", "Wort3"],
      "arguments": ["Argument1", "Argument2", "Argument3"],
      "examples": ["Beispiel1", "Beispiel2", "Beispiel3"]
    }},
    "it": {{
      "name": "Nome in italiano",
      "archetype": "Archetipo in italiano",
      "tone": "tono in italiano",
      "vocabulary": ["parola1", "parola2", "parola3"],
      "arguments": ["argomento1", "argomento2", "argomento3"],
      "examples": ["esempio1", "esempio2", "esempio3"]
    }},
    "pt": {{
      "name": "Nome em português",
      "archetype": "Arquetipo em português",
      "tone": "tom em português",
      "vocabulary": ["palavra1", "palavra2", "palavra3"],
      "arguments": ["argumento1", "argumento2", "argumento3"],
      "examples": ["exemplo1", "exemplo2", "exemplo3"]
    }}
  }}
}}

Le persona doit être adapté au thème "{theme}" et aux personnes intéressées par ce domaine."""

        try:
            response = self._query_ia(prompt, expect_json=True)
            if not response:
                return None
            
            # La réponse de l'IA est structurée comme {"answer": "```json\n{...}\n```"}
            if isinstance(response, dict) and 'answer' in response:
                # Extraire le contenu JSON de la clé 'answer'
                answer_content = response['answer']
                # Nettoyer le contenu (enlever les backticks et 'json')
                cleaned_response = self._clean_ia_json_output(answer_content)
                persona_data = json.loads(cleaned_response)
            elif isinstance(response, dict):
                # Si c'est déjà un dictionnaire sans clé 'answer', l'utiliser directement
                persona_data = response
            else:
                # Sinon, nettoyer et parser la réponse JSON
                cleaned_response = self._clean_ia_json_output(response)
                persona_data = json.loads(cleaned_response)
            
            # Valider la structure
            required_fields = ['name', 'archetype', 'description', 'corpus']
            for field in required_fields:
                if field not in persona_data:
                    self.logger.warning(f"⚠️ Champ manquant dans le persona : {field}")
                return None
                
            # Vérifier que le contenu multilingue est présent
            if 'multilingual' not in persona_data:
                self.logger.warning("⚠️ Contenu multilingue manquant dans le persona")
                # Créer une structure multilingue basique
                persona_data['multilingual'] = {}
                for lang in languages:
                    persona_data['multilingual'][lang] = {
                        'name': persona_data['name'],
                        'archetype': persona_data['archetype'],
                        'tone': persona_data['corpus']['tone'],
                        'vocabulary': persona_data['corpus']['vocabulary'],
                        'arguments': persona_data['corpus']['arguments'],
                        'examples': persona_data['corpus']['examples']
                    }
            
            return persona_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Erreur de parsing JSON pour le persona '{theme}': {e}")
            return None
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la génération du persona '{theme}': {e}")
            return None

    def _detect_available_languages(self):
        """
        Détecte les langues disponibles dans la base de connaissance.
        Retourne une liste des codes de langue.
        """
        knowledge_base = self._load_and_sync_knowledge_base()
        if not knowledge_base:
            return ['fr']  # Défaut français
        
        languages = set()
        for pubkey, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            lang = metadata.get('language', 'xx')
            if lang != 'xx':
                languages.add(lang)
        
        # Ajouter les langues par défaut si aucune détectée
        if not languages:
            languages = {'fr'}
        
        # Trier par ordre d'importance
        priority_languages = ['fr', 'en', 'es', 'de', 'it', 'pt']
        sorted_languages = []
        
        # Ajouter d'abord les langues prioritaires dans l'ordre
        for lang in priority_languages:
            if lang in languages:
                sorted_languages.append(lang)
        
        # Ajouter les autres langues
        for lang in sorted(languages):
            if lang not in sorted_languages:
                sorted_languages.append(lang)
        
        return sorted_languages

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

        # Si un seul cluster, le sélectionner automatiquement
        if len(valid_clusters) == 1:
            selected_cluster = valid_clusters[0]
            final_targets = selected_cluster['members']
            
            target_file = os.path.join(self.shared_state['config']['workspace'], "todays_targets.json")
            with open(target_file, 'w') as f:
                json.dump(final_targets, f, indent=4, ensure_ascii=False)

            report = f"Cluster '{selected_cluster['cluster_name']}' sélectionné automatiquement. {len(final_targets)} cibles enregistrées."
            self.logger.info(f"✅ {report}")
            self.shared_state['status']['AnalystAgent'] = report
            self.shared_state['analyst_report'] = f"Cible du jour : {selected_cluster['description']}"
            self.shared_state['targets'] = final_targets
            
            # Proposer de revenir au menu ou continuer
            print(f"\n✅ {report}")
            print("\nQue souhaitez-vous faire ?")
            print("1. Revenir au menu Analyste (pour ajouter d'autres filtres)")
            print("2. Continuer vers l'Agent Stratège")
            
            next_choice = input("> ").strip()
            
            if next_choice == "1":
                self.logger.info("Retour au menu Analyste...")
                return "menu"  # Signal pour revenir au menu
            elif next_choice == "2":
                self.logger.info("Prêt pour l'Agent Stratège...")
                return "continue"  # Signal pour continuer
            else:
                self.logger.info("Choix invalide, retour au menu Analyste...")
                return "menu"

        # Si plusieurs clusters, demander à l'utilisateur de choisir
        try:
            user_input = input("\nChoisissez le numéro du cluster à cibler : ").strip()
            self.logger.debug(f"Entrée utilisateur : '{user_input}'")
            
            if not user_input:
                self.logger.error("Aucune entrée fournie")
                raise ValueError("Entrée vide")
            
            choice = int(user_input) - 1
            self.logger.debug(f"Choix calculé : {choice}, nombre de clusters valides : {len(valid_clusters)}")
            
            if not (0 <= choice < len(valid_clusters)): 
                self.logger.error(f"Choix {choice} hors de la plage [0, {len(valid_clusters)})")
                raise ValueError(f"Choix {choice + 1} invalide. Veuillez choisir entre 1 et {len(valid_clusters)}")
            
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
            
            # Proposer de revenir au menu ou continuer
            print(f"\n✅ {report}")
            print("\nQue souhaitez-vous faire ?")
            print("1. Revenir au menu Analyste (pour ajouter d'autres filtres)")
            print("2. Continuer vers l'Agent Stratège")
            
            next_choice = input("> ").strip()
            
            if next_choice == "1":
                self.logger.info("Retour au menu Analyste...")
                return "menu"  # Signal pour revenir au menu
            elif next_choice == "2":
                self.logger.info("Prêt pour l'Agent Stratège...")
                return "continue"  # Signal pour continuer
            else:
                self.logger.info("Choix invalide, retour au menu Analyste...")
                return "menu"
        except ValueError as e:
            self.logger.error(f"Choix invalide : {e}")
        except IndexError:
            self.logger.error("Choix invalide : index hors limites.")
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

    def _normalize_tag(self, tag: str) -> str:
        """Normalise un tag en le passant en minuscules et en supprimant les accents."""
        # Passage en minuscules
        tag = tag.lower()
        # Suppression des accents
        nfkd_form = unicodedata.normalize('NFD', tag)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    def optimize_thematic_analysis(self):
        """
        Optimise les thèmes en consolidant et nettoyant le Top 50.
        Supprime les thèmes peu utilisés (< 3 occurrences) et consolide les variantes.
        """
        self.logger.info("🔄 Agent Analyste : Optimisation des thèmes...")
        
        # Charger la base de connaissance
        knowledge_base = self._load_and_sync_knowledge_base()
        if not knowledge_base:
            self.logger.error("❌ Base de connaissance vide. Impossible d'optimiser les thèmes.")
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
        self.logger.info(f"📊 {analyzed_profiles} profils analysés trouvés. Consolidation des thèmes...")
        
        if not all_tags:
            self.logger.error("❌ Aucun thème détecté dans la base de connaissance.")
            return
        
        # Compter les occurrences
        tag_counts = Counter(all_tags)
        unique_tags_before = len(tag_counts)
        self.logger.info(f"📊 {unique_tags_before} thèmes uniques détectés avant normalisation.")
        
        # --- Consolidation des thèmes (accents, casse, etc.) ---
        normalized_tag_counts = Counter()
        tag_map = {}  # Mappe les anciens tags vers les nouveaux normalisés
        
        for tag, count in tag_counts.items():
            normalized_tag = self._normalize_tag(tag)
            tag_map[tag] = normalized_tag
            normalized_tag_counts[normalized_tag] += count

        unique_tags_after = len(normalized_tag_counts)
        if unique_tags_before != unique_tags_after:
            self.logger.info(f"📊 {unique_tags_after} thèmes uniques après normalisation (consolidation de {unique_tags_before - unique_tags_after} variantes).")

        # Remplacer tag_counts par les comptes normalisés pour la suite du traitement
        tag_counts = normalized_tag_counts
        unique_tags = unique_tags_after
        
        # Filtrer les thèmes avec moins de 3 occurrences
        filtered_tags = {tag: count for tag, count in tag_counts.items() if count >= 3}
        removed_tags = {tag: count for tag, count in tag_counts.items() if count < 3}
        
        self.logger.info(f"🎯 {len(filtered_tags)} thèmes conservés (≥ 3 occurrences)")
        self.logger.info(f"🗑️ {len(removed_tags)} thèmes supprimés (< 3 occurrences)")
        
        if removed_tags:
            self.logger.info("\n--- Thèmes supprimés (trop peu utilisés) ---")
            for tag, count in sorted(removed_tags.items(), key=lambda x: x[1], reverse=True):
                # Trouver les profils qui utilisent ce thème
                profiles_with_tag = []
                for pubkey, data in knowledge_base.items():
                    metadata = data.get('metadata', {})
                    tags = metadata.get('tags', [])
                    if tags and tags != ['error']:
                        # On vérifie la version normalisée
                        normalized_profile_tags = [self._normalize_tag(t) for t in tags]
                        if tag in normalized_profile_tags:
                            profiles_with_tag.append(data.get('uid', pubkey[:10]))
                
                self.logger.info(f"  ❌ {tag:<20} ({count:>2} occurrences) - Profils: {', '.join(profiles_with_tag[:3])}")
                if len(profiles_with_tag) > 3:
                    self.logger.info(f"      ... et {len(profiles_with_tag) - 3} autres")
        
        # Nettoyer et normaliser les tags dans les profils
        cleaned_profiles = 0
        for pubkey, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            tags = metadata.get('tags', [])
            if tags and tags != ['error']:
                # Normaliser chaque tag, filtrer ceux qui ne sont pas conservés, et dédoublonner
                new_tags_set = {tag_map[tag] for tag in tags if tag_map.get(tag) in filtered_tags}
                new_tags = sorted(list(new_tags_set))
                
                # Mettre à jour si la liste a changé
                if new_tags != tags:
                    metadata['tags'] = new_tags
                    cleaned_profiles += 1
        
        self.logger.info(f"🔄 {cleaned_profiles} profils nettoyés et normalisés. Sauvegarde...")
        
        # Sauvegarder la base optimisée
        self._save_knowledge_base(knowledge_base)
        
        # Afficher le nouveau Top 50
        top_50 = sorted(filtered_tags.items(), key=lambda x: x[1], reverse=True)[:50]
        self.logger.info(f"\n--- Nouveau Top 50 des thèmes après consolidation ---")
        for i, (tag, count) in enumerate(top_50, 1):
            self.logger.info(f"  {i:>2}. {tag:<20} ({count:>4} occurrences)")
        
        self.logger.info(f"✅ Optimisation terminée ! {len(filtered_tags)} thèmes conservés sur {unique_tags_before} initiaux.")

    def advanced_multi_selection_targeting(self):
        """
        Ciblage avancé multi-sélection avec filtres croisés par thèmes, langue, pays, région.
        """
        self.logger.info("🎯 Agent Analyste : Ciblage avancé multi-sélection...")
        
        # Charger la base de connaissance
        knowledge_base = self._load_and_sync_knowledge_base()
        if not knowledge_base:
            self.logger.error("❌ Base de connaissance vide.")
            return
        
        # Étape 1 : Sélection des thèmes
        print("\n🎯 SÉLECTION DES THÈMES")
        print("=" * 50)
        print("Sélectionnez les thèmes qui vous intéressent (numéros séparés par des virgules)")
        print("Exemple : 1,3,5 pour sélectionner les thèmes 1, 3 et 5")
        print("Entrée pour annuler")
        print()
        
        # Analyser les thèmes disponibles
        all_tags = []
        for pubkey, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            tags = metadata.get('tags', [])
            if tags and tags != ['error']:
                all_tags.extend(tags)
        
        tag_counts = Counter(all_tags)
        top_themes = tag_counts.most_common(20)
        
        for i, (theme, count) in enumerate(top_themes, 1):
            print(f" {i:>2}. {theme:<20} ({count:>4} membres)")
        
        try:
            choice = input("\nSélectionnez les thèmes (ex: 1,3,5) : ").strip()
            if not choice:
                self.logger.info("Opération annulée.")
                return
            
            selected_indices = [int(x.strip()) - 1 for x in choice.split(',')]
            selected_themes = [top_themes[i][0] for i in selected_indices if 0 <= i < len(top_themes)]
            
            if not selected_themes:
                self.logger.error("❌ Aucun thème valide sélectionné.")
                return
            
            self.logger.info(f"✅ Thèmes sélectionnés : {', '.join(selected_themes)}")
            
        except (ValueError, IndexError) as e:
            self.logger.error(f"❌ Erreur dans la sélection : {e}")
            return
        
        # Étape 2 : Filtrer les prospects par thèmes
        filtered_prospects = []
        for pubkey, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            tags = metadata.get('tags', [])
            if tags and tags != ['error']:
                # Vérifier si le prospect a au moins un des thèmes sélectionnés
                if any(theme in tags for theme in selected_themes):
                    filtered_prospects.append({
                        'pubkey': pubkey,
                        'uid': data.get('uid', ''),
                        'metadata': metadata
                    })
        
        self.logger.info(f"📊 Prospects des thèmes sélectionnés : {len(filtered_prospects)}")
        
        if not filtered_prospects:
            self.logger.warning("⚠️ Aucun prospect trouvé avec les thèmes sélectionnés.")
            return
        
        # Étape 3 : Options de filtrage géographique
        print(f"\n🌍 FILTRAGE GÉOGRAPHIQUE")
        print("=" * 50)
        print(f"Prospects des thèmes sélectionnés : {len(filtered_prospects)}")
        print()
        print("Options de filtrage :")
        print("1. Aucun filtre (tous les prospects des thèmes)")
        print("2. Filtrer par langue")
        print("3. Filtrer par pays")
        print("4. Filtrer par région")
        print("5. Combinaison de filtres")
        
        try:
            filter_choice = input("\nChoisissez une option (1-5) : ").strip()
            
            if filter_choice == "1":
                final_prospects = filtered_prospects
            elif filter_choice == "2":
                final_prospects = self._filter_by_language(filtered_prospects)
            elif filter_choice == "3":
                final_prospects = self._filter_by_country(filtered_prospects)
            elif filter_choice == "4":
                final_prospects = self._filter_by_region(filtered_prospects)
            elif filter_choice == "5":
                final_prospects = self._filter_combined(filtered_prospects)
            else:
                self.logger.warning("⚠️ Option invalide, aucun filtre appliqué.")
                final_prospects = filtered_prospects
                
        except KeyboardInterrupt:
            self.logger.info("Opération annulée.")
            return
        
        if not final_prospects:
            self.logger.warning("⚠️ Aucun prospect ne correspond aux critères de filtrage.")
            return
        
        # Étape 4 : Afficher les résultats et sauvegarder
        self._display_multi_selection_results(final_prospects, selected_themes)
        
        # Sauvegarder la cible
        self._save_multi_selection_targets(final_prospects, selected_themes)

    def _filter_by_language(self, prospects):
        """Filtre les prospects par langue"""
        print(f"\n🌍 LANGUES DISPONIBLES :")
        
        # Analyser les langues disponibles
        languages = {}
        for prospect in prospects:
            metadata = prospect.get('metadata', {})
            lang = metadata.get('language', 'xx')
            if lang != 'xx':
                languages[lang] = languages.get(lang, 0) + 1
        
        # Afficher les langues
        lang_list = sorted(languages.items(), key=lambda x: x[1], reverse=True)
        for i, (lang, count) in enumerate(lang_list, 1):
            lang_name = {
                'fr': 'Français', 'en': 'Anglais', 'es': 'Espagnol',
                'de': 'Allemand', 'it': 'Italien', 'pt': 'Portugais'
            }.get(lang, lang.upper())
            print(f"{i}. {lang_name} ({count} prospects)")
        
        try:
            choice = input("\nSélectionnez les langues (ex: 1,2) ou 'all' pour toutes : ").strip()
            
            if choice.lower() == 'all':
                selected_langs = [lang for lang, _ in lang_list]
            else:
                selected_indices = [int(x.strip()) - 1 for x in choice.split(',')]
                selected_langs = [lang_list[i][0] for i in selected_indices if 0 <= i < len(lang_list)]
            
            if not selected_langs:
                return prospects
            
            # Filtrer
            filtered = []
            for prospect in prospects:
                metadata = prospect.get('metadata', {})
                lang = metadata.get('language', 'xx')
                if lang in selected_langs:
                    filtered.append(prospect)
            
            self.logger.info(f"✅ Filtrage par langue : {len(filtered)} prospects sélectionnés")
            return filtered
            
        except (ValueError, IndexError):
            self.logger.warning("⚠️ Erreur dans la sélection, aucun filtre appliqué.")
            return prospects

    def _filter_by_country(self, prospects):
        """Filtre les prospects par pays"""
        print(f"\n🌍 PAYS DISPONIBLES :")
        
        # Analyser les pays disponibles
        countries = {}
        for prospect in prospects:
            metadata = prospect.get('metadata', {})
            country = metadata.get('country')
            if country:
                countries[country] = countries.get(country, 0) + 1
        
        # Afficher les pays
        country_list = sorted(countries.items(), key=lambda x: x[1], reverse=True)
        for i, (country, count) in enumerate(country_list, 1):
            print(f"{i}. {country} ({count} prospects)")
        
        try:
            choice = input("\nSélectionnez les pays (ex: 1,2) ou 'all' pour tous : ").strip()
            
            if choice.lower() == 'all':
                selected_countries = [country for country, _ in country_list]
            else:
                selected_indices = [int(x.strip()) - 1 for x in choice.split(',')]
                selected_countries = [country_list[i][0] for i in selected_indices if 0 <= i < len(country_list)]
            
            if not selected_countries:
                return prospects
            
            # Filtrer
            filtered = []
            for prospect in prospects:
                metadata = prospect.get('metadata', {})
                country = metadata.get('country')
                if country in selected_countries:
                    filtered.append(prospect)
            
            self.logger.info(f"✅ Filtrage par pays : {len(filtered)} prospects sélectionnés")
            return filtered
            
        except (ValueError, IndexError):
            self.logger.warning("⚠️ Erreur dans la sélection, aucun filtre appliqué.")
            return prospects

    def _filter_by_region(self, prospects):
        """Filtre les prospects par région"""
        print(f"\n🌍 RÉGIONS DISPONIBLES :")
        
        # Analyser les régions disponibles
        regions = {}
        for prospect in prospects:
            metadata = prospect.get('metadata', {})
            region = metadata.get('region')
            country = metadata.get('country', '')
            if region:
                region_key = f"{region}, {country}" if country else region
                regions[region_key] = regions.get(region_key, 0) + 1
        
        # Afficher les régions
        region_list = sorted(regions.items(), key=lambda x: x[1], reverse=True)
        for i, (region, count) in enumerate(region_list, 1):
            print(f"{i}. {region} ({count} prospects)")
        
        try:
            choice = input("\nSélectionnez les régions (ex: 1,2) ou 'all' pour toutes : ").strip()
            
            if choice.lower() == 'all':
                selected_regions = [region for region, _ in region_list]
            else:
                selected_indices = [int(x.strip()) - 1 for x in choice.split(',')]
                selected_regions = [region_list[i][0] for i in selected_indices if 0 <= i < len(region_list)]
            
            if not selected_regions:
                return prospects
            
            # Filtrer
            filtered = []
            for prospect in prospects:
                metadata = prospect.get('metadata', {})
                region = metadata.get('region')
                country = metadata.get('country', '')
                region_key = f"{region}, {country}" if country else region
                if region_key in selected_regions:
                    filtered.append(prospect)
            
            self.logger.info(f"✅ Filtrage par région : {len(filtered)} prospects sélectionnés")
            return filtered
            
        except (ValueError, IndexError):
            self.logger.warning("⚠️ Erreur dans la sélection, aucun filtre appliqué.")
            return prospects

    def _filter_combined(self, prospects):
        """Filtre combiné (langue + pays + région)"""
        self.logger.info("🔀 Filtrage combiné...")
        
        # Appliquer les filtres en cascade
        prospects = self._filter_by_language(prospects)
        if prospects:
            prospects = self._filter_by_country(prospects)
        if prospects:
            prospects = self._filter_by_region(prospects)
        
        return prospects

    def _display_multi_selection_results(self, prospects, selected_themes):
        """Affiche les résultats du ciblage multi-sélection"""
        print(f"\n🎯 RÉSULTATS DU CIBLAGE MULTI-SÉLECTION")
        print("=" * 60)
        print(f"Thèmes sélectionnés : {', '.join(selected_themes)}")
        print(f"Nombre de prospects ciblés : {len(prospects)}")
        print()
        
        # Analyser la composition
        languages = {}
        countries = {}
        regions = {}
        
        for prospect in prospects:
            metadata = prospect.get('metadata', {})
            
            # Langues
            lang = metadata.get('language', 'xx')
            if lang != 'xx':
                languages[lang] = languages.get(lang, 0) + 1
            
            # Pays
            country = metadata.get('country')
            if country:
                countries[country] = countries.get(country, 0) + 1
            
            # Régions
            region = metadata.get('region')
            if region:
                regions[region] = regions.get(region, 0) + 1
        
        print("📊 COMPOSITION DE LA CIBLE :")
        if languages:
            lang_str = ", ".join([f"{k}({v})" for k, v in sorted(languages.items(), key=lambda x: x[1], reverse=True)])
            print(f"🌍 Langues : {lang_str}")
        
        if countries:
            country_str = ", ".join([f"{k}({v})" for k, v in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5]])
            print(f"🌍 Pays : {country_str}")
        
        if regions:
            region_str = ", ".join([f"{k}({v})" for k, v in sorted(regions.items(), key=lambda x: x[1], reverse=True)[:5]])
            print(f"🌍 Régions : {region_str}")

    def _save_multi_selection_targets(self, prospects, selected_themes):
        """Sauvegarde les cibles du ciblage multi-sélection"""
        # Générer un nom descriptif
        themes_str = "+".join(selected_themes)
        count = len(prospects)
        target_name = f"Multi-{themes_str}-{count}prospects"
        
        # Sauvegarder
        targets_file = os.path.join(self.shared_state['config']['workspace'], 'todays_targets.json')
        with open(targets_file, 'w', encoding='utf-8') as f:
            json.dump(prospects, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"💾 Cible sauvegardée : {target_name} ({count} prospects)")
        self.shared_state['targets'] = prospects

    def select_cluster_by_language(self):
        """Sélectionne les prospects selon leur langue détectée"""
        self.logger.info("🌍 Agent Analyste : Ciblage par langue...")
        
        # Charger la base de connaissance
        knowledge_base = self._load_and_sync_knowledge_base()
        if not knowledge_base:
            self.logger.error("❌ Base de connaissance vide.")
            return
        
        # Analyser les langues disponibles
        languages = {}
        for pubkey, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            lang = metadata.get('language', 'xx')
            if lang != 'xx':
                languages[lang] = languages.get(lang, 0) + 1
        
        if not languages:
            self.logger.error("❌ Aucune langue détectée dans la base de connaissance.")
            return
        
        # Afficher les options
        print("\n🌍 LANGUES DISPONIBLES :")
        print("=" * 50)
        
        lang_list = sorted(languages.items(), key=lambda x: x[1], reverse=True)
        for i, (lang, count) in enumerate(lang_list, 1):
            lang_name = {
                'fr': 'Français', 'en': 'Anglais', 'es': 'Espagnol',
                'de': 'Allemand', 'it': 'Italien', 'pt': 'Portugais'
            }.get(lang, lang.upper())
            print(f"{i}. Langue : {lang_name} ({count} membres)")
            print(f"    Description : Groupe de {count} membres parlant {lang_name}.")
            print()
        
        try:
            choice = input("Sélectionnez une langue (numéro) : ").strip()
            if not choice:
                self.logger.info("Opération annulée.")
                return
            
            selected_index = int(choice) - 1
            if not (0 <= selected_index < len(lang_list)):
                self.logger.error("❌ Sélection invalide.")
                return
            
            selected_lang, count = lang_list[selected_index]
            
            # Filtrer les prospects
            filtered_prospects = []
            for pubkey, data in knowledge_base.items():
                metadata = data.get('metadata', {})
                lang = metadata.get('language', 'xx')
                if lang == selected_lang:
                    filtered_prospects.append({
                        'pubkey': pubkey,
                        'uid': data.get('uid', ''),
                        'metadata': metadata
                    })
            
            # Créer un cluster simple pour la langue sélectionnée
            cluster = {
                'cluster_name': f'Langue {selected_lang}',
                'description': f'Prospects parlant {selected_lang}',
                'members': filtered_prospects
            }
            
            # Sauvegarder et gérer le retour
            result = self._select_and_save_cluster([cluster])
            
            if result == "quit":
                return
            elif result == "continue":
                # L'utilisateur veut continuer vers l'Agent Stratège
                print("\n🎯 Prêt pour l'Agent Stratège ! Retournez au menu principal et choisissez l'option 2.")
                return
            
        except (ValueError, KeyboardInterrupt):
            self.logger.error("❌ Erreur dans la sélection.")

    def select_cluster_by_country(self):
        """Sélectionne les prospects selon leur pays"""
        self.logger.info("🌍 Agent Analyste : Ciblage par pays...")
        
        # Charger la base de connaissance
        knowledge_base = self._load_and_sync_knowledge_base()
        if not knowledge_base:
            self.logger.error("❌ Base de connaissance vide.")
            return
        
        # Analyser les pays disponibles
        countries = {}
        for pubkey, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            country = metadata.get('country')
            if country:
                countries[country] = countries.get(country, 0) + 1
        
        if not countries:
            self.logger.error("❌ Aucun pays détecté dans la base de connaissance.")
            return
        
        # Afficher les options
        print("\n🌍 PAYS DISPONIBLES :")
        print("=" * 50)
        
        country_list = sorted(countries.items(), key=lambda x: x[1], reverse=True)
        for i, (country, count) in enumerate(country_list, 1):
            print(f"{i}. Pays : {country} ({count} membres)")
            print(f"    Description : Groupe de {count} membres localisés en '{country}'.")
            print()
        
        try:
            choice = input("Sélectionnez un pays (numéro) : ").strip()
            if not choice:
                self.logger.info("Opération annulée.")
                return
            
            selected_index = int(choice) - 1
            if not (0 <= selected_index < len(country_list)):
                self.logger.error("❌ Sélection invalide.")
                return
            
            selected_country, count = country_list[selected_index]
            
            # Filtrer les prospects
            filtered_prospects = []
            for pubkey, data in knowledge_base.items():
                metadata = data.get('metadata', {})
                country = metadata.get('country')
                if country == selected_country:
                    filtered_prospects.append({
                        'pubkey': pubkey,
                        'uid': data.get('uid', ''),
                        'metadata': metadata
                    })
            
            # Créer un cluster simple pour le pays sélectionné
            cluster = {
                'cluster_name': f'Pays {selected_country}',
                'description': f'Prospects localisés en {selected_country}',
                'members': filtered_prospects
            }
            
            # Sauvegarder et gérer le retour
            result = self._select_and_save_cluster([cluster])
            
            if result == "quit":
                return
            elif result == "continue":
                # L'utilisateur veut continuer vers l'Agent Stratège
                print("\n🎯 Prêt pour l'Agent Stratège ! Retournez au menu principal et choisissez l'option 2.")
                return
            
        except (ValueError, KeyboardInterrupt):
            self.logger.error("❌ Erreur dans la sélection.")

    def select_cluster_by_region(self):
        """Sélectionne les prospects selon leur région"""
        self.logger.info("🌍 Agent Analyste : Ciblage par région...")
        
        # Charger la base de connaissance
        knowledge_base = self._load_and_sync_knowledge_base()
        if not knowledge_base:
            self.logger.error("❌ Base de connaissance vide.")
            return
        
        # Analyser les régions disponibles
        regions = {}
        for pubkey, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            region = metadata.get('region')
            country = metadata.get('country', '')
            if region:
                region_key = f"{region}, {country}" if country else region
                regions[region_key] = regions.get(region_key, 0) + 1
        
        if not regions:
            self.logger.error("❌ Aucune région détectée dans la base de connaissance.")
            return
        
        # Afficher les options
        print("\n🌍 RÉGIONS DISPONIBLES :")
        print("=" * 50)
        
        region_list = sorted(regions.items(), key=lambda x: x[1], reverse=True)
        for i, (region, count) in enumerate(region_list, 1):
            print(f"{i}. Région : {region} ({count} membres)")
            print(f"    Description : Groupe de {count} membres localisés en '{region}'.")
            print()
        
        try:
            choice = input("Sélectionnez une région (numéro) : ").strip()
            if not choice:
                self.logger.info("Opération annulée.")
                return
            
            selected_index = int(choice) - 1
            if not (0 <= selected_index < len(region_list)):
                self.logger.error("❌ Sélection invalide.")
                return
            
            selected_region, count = region_list[selected_index]
            
            # Filtrer les prospects
            filtered_prospects = []
            for pubkey, data in knowledge_base.items():
                metadata = data.get('metadata', {})
                region = metadata.get('region')
                country = metadata.get('country', '')
                region_key = f"{region}, {country}" if country else region
                if region_key == selected_region:
                    filtered_prospects.append({
                        'pubkey': pubkey,
                        'uid': data.get('uid', ''),
                        'metadata': metadata
                    })
            
            # Créer un cluster simple pour la région sélectionnée
            cluster = {
                'cluster_name': f'Région {selected_region}',
                'description': f'Prospects localisés en {selected_region}',
                'members': filtered_prospects
            }
            
            # Sauvegarder et gérer le retour
            result = self._select_and_save_cluster([cluster])
            
            if result == "quit":
                return
            elif result == "continue":
                # L'utilisateur veut continuer vers l'Agent Stratège
                print("\n🎯 Prêt pour l'Agent Stratège ! Retournez au menu principal et choisissez l'option 2.")
                return
            
        except (ValueError, KeyboardInterrupt):
            self.logger.error("❌ Erreur dans la sélection.") 

    def translate_persona_bank(self):
        """
        Traduit automatiquement une banque de persona dans les langues détectées des profils.
        Permet de choisir une banque spécifique (1, 3, ou 0-3) et génère le contenu multilingue.
        """
        self.logger.info("🌍 Agent Analyste : Traduction de banque de persona...")
        
        # Charger la base de connaissance pour détecter les langues
        knowledge_base = self._load_and_sync_knowledge_base()
        
        # Détecter les langues disponibles
        available_languages = self._detect_available_languages()
        if not available_languages:
            self.logger.error("❌ Aucune langue détectée dans la base de connaissance")
            return
        
        self.logger.info(f"🌍 Langues détectées : {', '.join(available_languages)}")
        
        # Charger la configuration des banques
        banks_config_file = os.path.join(self.shared_state['config']['workspace'], 'memory_banks_config.json')
        banks_config = self._load_banks_config(banks_config_file)
        
        # Afficher les banques disponibles
        print("\n🏦 BANQUES DE PERSONAS DISPONIBLES")
        print("=" * 50)
        available_banks = []
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            if bank.get('name') and bank.get('corpus'):
                available_banks.append((slot, bank))
                has_multilingual = "✅" if bank.get('multilingual') else "❌"
                print(f"{slot}. {bank['name']} {has_multilingual} multilingue")
        
        if not available_banks:
            self.logger.error("❌ Aucune banque configurée")
            return
        
        # Demander le choix de la banque
        print(f"\nChoisissez la banque à traduire (0-{len(available_banks)-1}) :")
        print("Exemples :")
        print("- '1' pour traduire la banque 1")
        print("- '3' pour traduire la banque 3") 
        print("- '0-3' pour traduire les banques 0, 1, 2, 3")
        
        choice = input("> ").strip()
        
        # Parser le choix
        banks_to_translate = []
        if '-' in choice:
            # Format range : 0-3
            try:
                start, end = map(int, choice.split('-'))
                banks_to_translate = [(slot, bank) for slot, bank in available_banks if start <= slot <= end]
            except ValueError:
                self.logger.error("❌ Format de plage invalide")
                return
        else:
            # Format single : 1, 3
            try:
                slot_num = int(choice)
                for slot, bank in available_banks:
                    if slot == slot_num:
                        banks_to_translate = [(slot, bank)]
                        break
                if not banks_to_translate:
                    self.logger.error(f"❌ Banque {slot_num} non trouvée")
                    return
            except ValueError:
                self.logger.error("❌ Choix invalide")
                return
        
        if not banks_to_translate:
            self.logger.error("❌ Aucune banque sélectionnée")
            return
        
        self.logger.info(f"🎯 Banques sélectionnées pour traduction : {len(banks_to_translate)}")
        
        # Traduire chaque banque
        for slot, bank in banks_to_translate:
            self.logger.info(f"🌍 Traduction de la banque '{bank['name']}' (slot {slot})...")
            
            # Générer le contenu multilingue
            multilingual_content = self._generate_multilingual_content_for_bank(bank, available_languages)
            
            if multilingual_content:
                # Ajouter le contenu multilingue à la banque
                bank['multilingual'] = multilingual_content
                self.logger.info(f"✅ Contenu multilingue généré pour {bank['name']}")
            else:
                self.logger.warning(f"⚠️ Échec de la génération multilingue pour {bank['name']}")
        
        # Sauvegarder la configuration mise à jour
        self._save_banks_config(banks_config, banks_config_file)
        self.logger.info("✅ Configuration des banques sauvegardée avec les traductions")

    def _generate_multilingual_content_for_bank(self, bank, languages):
        """
        Génère le contenu multilingue pour une banque donnée dans les langues spécifiées.
        """
        corpus = bank.get('corpus', {})
        if not corpus:
            self.logger.warning(f"⚠️ Banque '{bank['name']}' sans corpus")
            return None
        
        multilingual_content = {}
        
        # Langues supportées avec leurs codes
        language_codes = {
            'fr': 'français',
            'en': 'english', 
            'es': 'español',
            'de': 'deutsch',
            'it': 'italiano',
            'pt': 'português',
            'ca': 'català',
            'nl': 'nederlands'
        }
        
        for lang_code in languages:
            if lang_code not in language_codes:
                continue
                
            lang_name = language_codes[lang_code]
            self.logger.debug(f"🌍 Génération du contenu en {lang_name}...")
            
            # Construire le prompt de traduction
            prompt = f"""Tu es un expert en traduction et localisation pour UPlanet. Tu dois traduire le contenu d'une banque de mémoire (persona) en {lang_name}.

BANQUE À TRADUIRE :
- Nom : {bank['name']}
- Archétype : {bank.get('archetype', 'Non défini')}
- Thèmes : {', '.join(bank.get('themes', []))}

CONTENU ORIGINAL (français) :
- Ton : {corpus.get('tone', '')}
- Vocabulaire : {', '.join(corpus.get('vocabulary', []))}
- Arguments : {chr(10).join([f'- {arg}' for arg in corpus.get('arguments', [])])}
- Exemples : {chr(10).join([f'- {ex}' for ex in corpus.get('examples', [])])}

TÂCHE : Traduis tout ce contenu en {lang_name} en conservant le sens, le ton et l'esprit de la banque. Adapte les références culturelles si nécessaire.

Réponds UNIQUEMENT avec un objet JSON valide au format suivant :
{{
  "name": "Nom traduit de la banque",
  "archetype": "Archétype traduit",
  "tone": "Ton traduit",
  "vocabulary": ["mot1", "mot2", "mot3"],
  "arguments": ["argument1", "argument2", "argument3"],
  "examples": ["exemple1", "exemple2", "exemple3"]
}}"""

            try:
                # Appeler l'IA pour la traduction
                response = self._query_ia(prompt, expect_json=True)
                if not response:
                    continue
                
                # Parser la réponse JSON
                if isinstance(response, dict) and 'answer' in response:
                    # Extraire JSON du champ 'answer'
                    answer_content = response['answer']
                    cleaned_response = self._clean_ia_json_output(answer_content)
                    translated_content = json.loads(cleaned_response)
                elif isinstance(response, dict):
                    # Réponse déjà en format dict
                    translated_content = response
                else:
                    # Nettoyer et parser la réponse
                    cleaned_response = self._clean_ia_json_output(response)
                    translated_content = json.loads(cleaned_response)
                
                # Valider et stocker le contenu traduit
                if all(key in translated_content for key in ['name', 'tone', 'vocabulary', 'arguments', 'examples']):
                    multilingual_content[lang_code] = translated_content
                    self.logger.debug(f"✅ Contenu {lang_name} généré pour {bank['name']}")
                else:
                    self.logger.warning(f"⚠️ Réponse incomplète pour {lang_name}")
                    
            except Exception as e:
                self.logger.error(f"❌ Erreur lors de la traduction en {lang_name} : {e}")
                continue
        
        return multilingual_content if multilingual_content else None 

