from .base_agent import Agent
import json
import os
import subprocess
import random
import requests
import time
from collections import defaultdict, Counter
import unicodedata
from itertools import combinations
import hashlib

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
            updated_prospects_count = 0
            
            # Statistiques des nouvelles données
            g1_prospects = 0
            gchange_prospects = 0
            linked_accounts_count = 0
            
            for member in source_data.get('members', []):
                pubkey = member.get("pubkey")
                if not pubkey: continue
                source_prospects_count += 1

                # Compter les types de sources
                source_type = member.get('source', '')
                if 'g1_wot' in source_type:
                    g1_prospects += 1
                elif 'gchange' in source_type:
                    gchange_prospects += 1

                if pubkey not in knowledge_base:
                    # Nouveau prospect
                    knowledge_base[pubkey] = {
                        "uid": member.get("uid"),
                        "profile": member.get('profile', {}),
                        "source": member.get('source'),
                        "metadata": {},
                        # Ajouter les nouvelles données si présentes
                        "import_metadata": member.get('import_metadata', {}),
                        "linked_accounts": member.get('linked_accounts', {})
                    }
                    new_prospects_count += 1
                    
                    # Compter les comptes liés
                    if member.get('linked_accounts'):
                        linked_accounts_count += 1
                else: 
                    # Prospect existant - mettre à jour les données
                    existing = knowledge_base[pubkey]
                    existing['profile'] = member.get('profile', {})
                    
                    # Mettre à jour les métadonnées d'import si plus récentes
                    new_import_metadata = member.get('import_metadata', {})
                    if new_import_metadata:
                        existing_import_metadata = existing.get('import_metadata', {})
                        existing['import_metadata'] = {**existing_import_metadata, **new_import_metadata}
                    
                    # Mettre à jour les comptes liés
                    new_linked_accounts = member.get('linked_accounts', {})
                    if new_linked_accounts:
                        existing_linked_accounts = existing.get('linked_accounts', {})
                        existing['linked_accounts'] = {**existing_linked_accounts, **new_linked_accounts}
                        if not existing.get('linked_accounts_counted'):
                            linked_accounts_count += 1
                            existing['linked_accounts_counted'] = True
                    
                    updated_prospects_count += 1

            self.logger.info(f"Synchronisation terminée : {source_prospects_count} profils dans la source, {new_prospects_count} nouveaux ajoutés, {updated_prospects_count} mis à jour.")
            self.logger.info(f"📊 Composition : {g1_prospects} G1, {gchange_prospects} Gchange, {linked_accounts_count} avec comptes liés")
            
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

    def display_enhanced_statistics(self):
        """
        Affiche des statistiques détaillées sur la base de connaissance enrichie,
        incluant les nouvelles données (import_metadata, linked_accounts).
        """
        self.logger.info("📊 Agent Analyste : Affichage des statistiques enrichies...")
        
        knowledge_base = self._load_and_sync_knowledge_base()
        if not knowledge_base:
            self.logger.error("❌ Base de connaissance vide.")
            return
        
        total_prospects = len(knowledge_base)
        
        # Statistiques de base
        g1_prospects = 0
        gchange_prospects = 0
        linked_accounts_count = 0
        
        # Statistiques d'import
        import_sources = {}
        discovery_methods = {}
        
        # Statistiques des comptes liés
        cesium_linked = 0
        gchange_linked = 0
        
        # Statistiques géographiques
        languages = {}
        countries = {}
        regions = {}
        
        for pk, data in knowledge_base.items():
            # Sources
            source = data.get('source', '')
            if 'g1_wot' in source:
                g1_prospects += 1
            elif 'gchange' in source:
                gchange_prospects += 1
            
            # Comptes liés
            linked_accounts = data.get('linked_accounts', {})
            if linked_accounts:
                linked_accounts_count += 1
                if linked_accounts.get('cesium_pubkey'):
                    cesium_linked += 1
                if linked_accounts.get('gchange_uid'):
                    gchange_linked += 1
            
            # Métadonnées d'import
            import_metadata = data.get('import_metadata', {})
            if import_metadata:
                source_script = import_metadata.get('source_script')
                if source_script:
                    import_sources[source_script] = import_sources.get(source_script, 0) + 1
                
                discovery_method = import_metadata.get('discovery_method')
                if discovery_method:
                    discovery_methods[discovery_method] = discovery_methods.get(discovery_method, 0) + 1
            
            # Données géographiques
            metadata = data.get('metadata', {})
            lang = metadata.get('language', 'xx')
            if lang != 'xx':
                languages[lang] = languages.get(lang, 0) + 1
            
            country = metadata.get('country')
            if country:
                countries[country] = countries.get(country, 0) + 1
            
            region = metadata.get('region')
            if region:
                regions[region] = regions.get(region, 0) + 1
        
        # Affichage des statistiques
        print("\n" + "="*60)
        print("📊 STATISTIQUES ENRICHIES DE LA BASE DE CONNAISSANCE")
        print("="*60)
        
        print(f"\n🎯 PROSPECTS ({total_prospects} total)")
        print(f"   • G1 (WoT) : {g1_prospects}")
        print(f"   • Gchange : {gchange_prospects}")
        print(f"   • Autres : {total_prospects - g1_prospects - gchange_prospects}")
        
        print(f"\n🔗 COMPTES LIÉS ({linked_accounts_count} total)")
        print(f"   • Avec Cesium : {cesium_linked}")
        print(f"   • Avec Gchange : {gchange_linked}")
        
        print(f"\n📥 SOURCES D'IMPORT")
        for source, count in sorted(import_sources.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {source} : {count}")
        
        print(f"\n🔍 MÉTHODES DE DÉCOUVERTE")
        for method, count in sorted(discovery_methods.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {method} : {count}")
        
        print(f"\n🌍 RÉPARTITION GÉOGRAPHIQUE")
        if languages:
            print("   Langues principales :")
            for lang, count in sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]:
                lang_name = {'fr': 'Français', 'en': 'Anglais', 'es': 'Espagnol', 'de': 'Allemand', 'it': 'Italien'}.get(lang, lang.upper())
                print(f"     • {lang_name} : {count}")
        
        if countries:
            print("   Pays principaux :")
            for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"     • {country} : {count}")
        
        if regions:
            print("   Régions principales :")
            for region, count in sorted(regions.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"     • {region} : {count}")
        
        print("\n" + "="*60)
        
        # Afficher quelques exemples de comptes liés
        print(f"\n🔗 EXEMPLES DE COMPTES LIÉS")
        examples_shown = 0
        for pk, data in knowledge_base.items():
            if examples_shown >= 5:
                break
            linked_accounts = data.get('linked_accounts', {})
            if linked_accounts:
                uid = data.get('uid', 'N/A')
                cesium_pk = linked_accounts.get('cesium_pubkey', '')
                gchange_uid = linked_accounts.get('gchange_uid', '')
                
                if cesium_pk or gchange_uid:
                    print(f"   • {uid}")
                    if cesium_pk:
                        print(f"     → Cesium : {cesium_pk[:20]}...")
                    if gchange_uid:
                        print(f"     → Gchange : {gchange_uid}")
                    examples_shown += 1
        
        if examples_shown == 0:
            print("   Aucun compte lié trouvé")
        
        print("\n" + "="*60)

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
        
        # Nouvelles statistiques
        linked_accounts_count = 0
        import_sources = {}
        discovery_methods = {}
        
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
            
            # Analyser les nouvelles données
            linked_accounts = data.get('linked_accounts', {})
            if linked_accounts:
                linked_accounts_count += 1
            
            import_metadata = data.get('import_metadata', {})
            if import_metadata:
                source_script = import_metadata.get('source_script')
                if source_script:
                    import_sources[source_script] = import_sources.get(source_script, 0) + 1
                
                discovery_method = import_metadata.get('discovery_method')
                if discovery_method:
                    discovery_methods[discovery_method] = discovery_methods.get(discovery_method, 0) + 1
                
        return {
            "total": total_prospects,
            "language": language_analyzed,
            "tags": tags_analyzed,
            "web2": web2_analyzed,
            "gps_prospects": gps_prospects,
            "linked_accounts": linked_accounts_count,
            "import_sources": import_sources,
            "discovery_methods": discovery_methods
        }

    def run_geo_linguistic_analysis(self):
        """
        Analyse les descriptions pour en extraire la langue, le pays et la région
        et sauvegarde ces données dans la base de connaissance.
        Utilise d'abord un service de géolocalisation pour les coordonnées GPS,
        puis l'IA en dernier recours pour l'analyse textuelle.
        OPTIMISÉ : Cache géolocalisation + Batch processing + GPS prioritaire
        """
        self.logger.info("🤖 Agent Analyste : Démarrage de l'analyse Géo-Linguistique OPTIMISÉE...")
        self.shared_state['status']['AnalystAgent'] = "Analyse Géo-Linguistique optimisée en cours..."

        knowledge_base = self._load_and_sync_knowledge_base()
        prospects_to_analyze = [pk for pk, data in knowledge_base.items() if 'g1_wot' in data.get('source', '')]
        
        geo_prompt_template = self._load_prompt('analyst_language_prompt_file')
        if not geo_prompt_template: return

        # --- OPTIMISATION 1 : Cache de géolocalisation ---
        geo_cache_file = os.path.join(self.shared_state['config']['workspace'], 'geo_cache.json')
        geo_cache = self._load_geo_cache(geo_cache_file)
        
        # Statistiques de traitement
        gps_geolocated = 0
        gps_cached = 0
        ia_analyzed = 0
        skipped = 0
        
        # --- PHASE 1 : Traitement GPS en priorité ---
        self.logger.info("📍 PHASE 1 : Traitement GPS en priorité...")
        
        # Identifier tous les prospects avec GPS
        prospects_with_gps = []
        for i, pubkey in enumerate(prospects_to_analyze):
            prospect_data = knowledge_base[pubkey]
            
            if 'language' in prospect_data.get('metadata', {}):
                continue
                
            profile = prospect_data.get('profile', {})
            source = profile.get('_source', {})
            geo_point = source.get('geoPoint', {})
            
            if (geo_point and 'lat' in geo_point and 'lon' in geo_point):
                lat = geo_point.get('lat')
                lon = geo_point.get('lon')
                
                if lat is not None and lon is not None and lat != 0 and lon != 0:
                    prospects_with_gps.append({
                        'pubkey': pubkey,
                        'lat': lat,
                        'lon': lon,
                        'uid': prospect_data.get('uid', 'N/A'),
                        'cache_key': f"{lat:.4f},{lon:.4f}"
                    })
        
        self.logger.info(f"📍 {len(prospects_with_gps)} prospects avec GPS identifiés")
        
        # Traiter les GPS par batch
        batch_size = 15
        max_gps_requests = min(5000, len(prospects_with_gps))
        gps_requests_made = 0
        
        for i in range(0, len(prospects_with_gps), batch_size):
            batch = prospects_with_gps[i:i+batch_size]
            
            for item in batch:
                if gps_requests_made >= max_gps_requests:
                    self.logger.info(f"⚠️ Limite GPS atteinte ({max_gps_requests} requêtes)")
                    break
                    
                # Vérifier le cache
                if item['cache_key'] in geo_cache:
                    geo_data = geo_cache[item['cache_key']]
                    gps_cached += 1
                    self.logger.debug(f"📍 Cache GPS hit : {item['uid']}")
                else:
                    # Géolocaliser
                    try:
                        time.sleep(random.uniform(1.0, 1.2))  # Respecter les limites Nominatim
                        geo_data = self._geolocate_from_coordinates(item['lat'], item['lon'])
                        
                        if geo_data:
                            geo_cache[item['cache_key']] = geo_data
                            gps_geolocated += 1
                            gps_requests_made += 1
                            self.logger.info(f"📍 GPS {gps_requests_made}/{max_gps_requests} : {item['uid']} -> {geo_data.get('country', 'N/A')}")
                        else:
                            self.logger.debug(f"⚠️ Échec géolocalisation GPS pour {item['uid']}")
                    except Exception as e:
                        self.logger.warning(f"⚠️ Erreur GPS pour {item['uid']} : {e}")
                
                # Appliquer les données géolocalisées
                if item['cache_key'] in geo_cache:
                    geo_data = geo_cache[item['cache_key']]
                    prospect_data = knowledge_base[item['pubkey']]
                    meta = prospect_data.setdefault('metadata', {})
                    
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
            
            # Sauvegarder le cache après chaque batch
            self._save_geo_cache(geo_cache, geo_cache_file)
            
            if gps_requests_made >= max_gps_requests:
                break
        
        # --- PHASE 2 : Analyse IA pour les cas restants ---
        self.logger.info("🧠 PHASE 2 : Analyse IA pour cas restants...")
        
        prospects_needing_ia = []
        for pubkey in prospects_to_analyze:
            prospect_data = knowledge_base[pubkey]
            
            if 'language' in prospect_data.get('metadata', {}):
                continue
            
            profile = prospect_data.get('profile', {})
            source = profile.get('_source', {})
            description = (source.get('description') or '').strip()
            
            if description:
                prospects_needing_ia.append({
                    'pubkey': pubkey,
                    'description': description,
                    'uid': prospect_data.get('uid', 'N/A')
                })
        
        self.logger.info(f"🧠 {len(prospects_needing_ia)} prospects nécessitent une analyse IA")
        
        # Traiter l'IA séquentiellement (pas de parallélisation pour Ollama)
        for i, item in enumerate(prospects_needing_ia):
            try:
                self.logger.info(f"🧠 Analyse IA {i+1}/{len(prospects_needing_ia)} : {item['uid']}")
                prompt = f"{geo_prompt_template}\n\nTexte fourni: \"{item['description']}\""
                
                ia_response = self._query_ia(prompt, expect_json=True)
                cleaned_answer = self._clean_ia_json_output(ia_response['answer'])
                geo_data = json.loads(cleaned_answer)
                
                prospect_data = knowledge_base[item['pubkey']]
                meta = prospect_data.setdefault('metadata', {})
                
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
                
                meta['geolocation_source'] = 'ia_analysis'
                
                ia_analyzed += 1
                
                # Sauvegarde intermédiaire tous les 20 profils
                if (i + 1) % 20 == 0:
                    self.logger.info(f"--- Sauvegarde intermédiaire ({i+1} profils IA analysés)... ---")
                    self._save_knowledge_base(knowledge_base)
                    
            except Exception as e:
                self.logger.error(f"❌ Erreur analyse IA pour {item['uid']} : {e}")
                skipped += 1
        
        # Sauvegarde finale
        self._save_knowledge_base(knowledge_base)
        
        # Statistiques finales
        self.logger.info(f"✅ Analyse Géo-Linguistique terminée :")
        self.logger.info(f"   • GPS géolocalisés : {gps_geolocated}")
        self.logger.info(f"   • GPS depuis cache : {gps_cached}")
        self.logger.info(f"   • Analysés par IA : {ia_analyzed}")
        self.logger.info(f"   • Ignorés : {skipped}")
        self.logger.info(f"   • Total traités : {gps_geolocated + gps_cached + ia_analyzed}")
        
        self.shared_state['status']['AnalystAgent'] = f"Géo-Linguistique terminée : {gps_geolocated + gps_cached + ia_analyzed} profils analysés"

    def _load_geo_cache(self, cache_file):
        """Charge le cache de géolocalisation"""
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"⚠️ Impossible de charger le cache GPS : {e}")
        return {}

    def _save_geo_cache(self, cache, cache_file):
        """Sauvegarde le cache de géolocalisation"""
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            self.logger.warning(f"⚠️ Impossible de sauvegarder le cache GPS : {e}")

    def _process_gps_batch(self, gps_batch, geo_cache):
        """Traite un lot de coordonnées GPS en parallèle"""
        processed = []
        
        for item in gps_batch:
            try:
                # Respecter les limites de Nominatim avec délai adaptatif
                time.sleep(random.uniform(1.0, 1.2))
                
                geo_data = self._geolocate_from_coordinates(item['lat'], item['lon'])
                
                if geo_data:
                    # Stocker dans le cache
                    geo_cache[item['cache_key']] = geo_data
                    processed.append(item)
                    self.logger.info(f"📍 GPS batch : {item['uid']} -> {geo_data.get('country', 'N/A')}")
                else:
                    self.logger.debug(f"⚠️ Échec géolocalisation GPS pour {item['uid']}")
                    
            except Exception as e:
                self.logger.warning(f"⚠️ Erreur dans le batch GPS pour {item['uid']} : {e}")
        
        return processed

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
        OPTIMISÉ : Cache IA + Batch processing + Prompt template réutilisé
        """
        self.logger.info("🤖 Agent Analyste : Démarrage de l'analyse thématique OPTIMISÉE...")
        self.shared_state['status']['AnalystAgent'] = "Analyse thématique optimisée en cours..."

        if not self._check_ollama_once():
            self.shared_state['status']['AnalystAgent'] = "Échec : API Ollama indisponible."
            return
            
        knowledge_base = self._load_and_sync_knowledge_base()
        
        # --- OPTIMISATION 1 : Cache des analyses IA ---
        ia_cache_file = os.path.join(self.shared_state['config']['workspace'], 'thematic_cache.json')
        ia_cache = self._load_thematic_cache(ia_cache_file)
        
        # --- OPTIMISATION 2 : Calcul des thèmes guides (une seule fois) ---
        tag_counter = Counter()
        for pk, data in knowledge_base.items():
            if 'tags' in data.get('metadata', {}):
                tag_counter.update(data['metadata']['tags'])
        
        # TOP 50 thèmes les plus fréquents comme guide
        guide_tags = [tag for tag, count in tag_counter.most_common(50)]
        if guide_tags:
            self.logger.info(f"Utilisation des {len(guide_tags)} thèmes les plus fréquents comme guide pour l'IA.")

        prospects_to_analyze = [pk for pk, data in knowledge_base.items() if 'g1_wot' in data.get('source', '')]
        
        # --- OPTIMISATION 3 : Charger le prompt template une seule fois ---
        thematic_prompt_template = self._load_prompt('analyst_thematic_prompt_file')
        if not thematic_prompt_template: return

        needs_analysis_count = 0
        save_interval = 50
        
        # Statistiques des réseaux sociaux
        social_stats = Counter()
        
        # --- OPTIMISATION 4 : Batch processing pour IA ---
        ia_batch = []
        batch_size = 5  # Traiter par lots de 5 (IA plus lente)
        
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

            # --- ÉTAPE 1 : Extraire les réseaux sociaux (toujours fait) ---
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

            # --- ÉTAPE 2 : Analyse thématique avec cache ---
            thematic_tags = []
            if description:
                # Créer une clé de cache basée sur le hash de la description
                import hashlib
                description_hash = hashlib.md5(description.encode()).hexdigest()
                cache_key = f"thematic_{description_hash}"
                
                # Vérifier le cache
                if cache_key in ia_cache:
                    thematic_tags = ia_cache[cache_key]
                    self.logger.debug(f"🧠 Cache IA hit : {prospect_data.get('uid', 'N/A')}")
                else:
                    # Ajouter au batch IA
                    ia_batch.append({
                        'pubkey': pubkey,
                        'description': description,
                        'uid': prospect_data.get('uid', 'N/A'),
                        'cache_key': cache_key
                    })
                    
                    # Traiter le batch quand il est plein ou à la fin
                    if len(ia_batch) >= batch_size or i == len(prospects_to_analyze) - 1:
                        processed_batch = self._process_ia_batch(ia_batch, ia_cache, thematic_prompt_template, guide_tags)
                        
                        # Sauvegarder le cache
                        self._save_thematic_cache(ia_cache, ia_cache_file)
                        
                        ia_batch = []
                
                # Récupérer les tags depuis le cache
                if cache_key in ia_cache:
                    thematic_tags = ia_cache[cache_key]
            else:
                self.logger.debug(f"Pas de description pour {prospect_data.get('uid', 'N/A')}")

            # --- ÉTAPE 3 : Combiner et sauvegarder ---
            all_tags = social_tags + thematic_tags
            
            # Validation et nettoyage des tags
            if all_tags:
                # Normaliser et dédupliquer
                normalized_tags = []
                for tag in all_tags:
                    normalized = self._normalize_tag(tag)
                    if normalized and normalized not in normalized_tags:
                        normalized_tags.append(normalized)
                
                metadata['tags'] = normalized_tags
            else:
                metadata['tags'] = []

            # Sauvegarde intermédiaire
            if needs_analysis_count > 0 and needs_analysis_count % save_interval == 0:
                self.logger.info(f"--- Sauvegarde intermédiaire ({needs_analysis_count} profils analysés)... ---")
                self._save_knowledge_base(knowledge_base)
        
        # Sauvegarde finale
        self._save_knowledge_base(knowledge_base)
        
        # Statistiques finales
        self.logger.info(f"✅ Analyse thématique terminée :")
        self.logger.info(f"   • Profils analysés : {needs_analysis_count}")
        self.logger.info(f"   • Tags générés : {sum(len(data.get('metadata', {}).get('tags', [])) for data in knowledge_base.values())}")
        self.logger.info(f"   • Réseaux sociaux détectés : {dict(social_stats)}")
        
        self.shared_state['status']['AnalystAgent'] = f"Thématique terminée : {needs_analysis_count} profils analysés"

    def _load_thematic_cache(self, cache_file):
        """Charge le cache des analyses thématiques"""
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"⚠️ Impossible de charger le cache thématique : {e}")
        return {}

    def _save_thematic_cache(self, cache, cache_file):
        """Sauvegarde le cache des analyses thématiques"""
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            self.logger.warning(f"⚠️ Impossible de sauvegarder le cache thématique : {e}")

    def _process_ia_batch(self, ia_batch, ia_cache, prompt_template, guide_tags):
        """Traite un lot d'analyses IA en parallèle"""
        processed = []
        
        for item in ia_batch:
            try:
                self.logger.info(f"🧠 Analyse IA batch : {item['uid']}")
                
                # Construire le prompt guidé
                prompt = f"{prompt_template}\n\nTexte fourni: \"{item['description']}\""
                if guide_tags:
                    prompt += f"\nThèmes existants : {json.dumps(guide_tags)}"
                
                ia_response = self._query_ia(prompt, expect_json=True)
                cleaned_answer = self._clean_ia_json_output(ia_response['answer'])
                thematic_tags = json.loads(cleaned_answer)

                # Validation et stockage dans le cache
                if isinstance(thematic_tags, list) and len(thematic_tags) <= 7:
                    ia_cache[item['cache_key']] = thematic_tags
                    processed.append(item)
                    self.logger.debug(f"✅ IA batch : {item['uid']} -> {len(thematic_tags)} tags")
                else:
                    self.logger.warning(f"⚠️ Réponse IA invalide pour {item['uid']}")
                    ia_cache[item['cache_key']] = ['error']
                    
            except Exception as e:
                self.logger.error(f"❌ Erreur dans le batch IA pour {item['uid']} : {e}")
                ia_cache[item['cache_key']] = ['error']
        
        return processed

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
        Crée automatiquement des personas basés sur des archétypes de thèmes.
        NOUVELLE LOGIQUE: Crée des trios de thèmes en combinant aléatoirement
        2 thèmes du Top 50 et 1 thème de l'ensemble pour générer des personas créatifs.
        """
        self.logger.info("🎭 Agent Analyste : Création automatique de personas par combinaison de thèmes...")
        
        # Vérifier Ollama
        if not self._check_ollama_once():
            self.logger.error("❌ Ollama non disponible. Impossible de créer les personas.")
            return
        
        # Charger la base de connaissance
        knowledge_base = self._load_and_sync_knowledge_base()
        if not knowledge_base:
            self.logger.error("❌ Base de connaissance vide. Impossible de créer les personas.")
            return
        
        # Analyser les thèmes existants pour construire nos listes
        all_tags_flat_list = []
        for pubkey, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            tags = metadata.get('tags', [])
            if tags and tags != ['error']:
                all_tags_flat_list.extend(tags)
        
        if not all_tags_flat_list:
            self.logger.error("❌ Aucun thème détecté dans la base de connaissance.")
            return

        tag_counts = Counter(all_tags_flat_list)
        
        # Obtenir la liste de tous les thèmes uniques et le top 50
        all_unique_tags = list(tag_counts.keys())
        top_50_tags = [tag for tag, count in tag_counts.most_common(50)]

        if len(top_50_tags) < 2:
            self.logger.error("❌ Pas assez de thèmes dans le Top 50 pour créer des duos. Veuillez analyser plus de profils.")
            return

        # --- NOUVELLE LOGIQUE : Création de 5 trios aléatoires ---
        self.logger.info("🎲 Création de 5 archétypes de thèmes par combinaison aléatoire...")
        generated_groups = []
        used_combos = set()

        for i in range(5): # On veut créer 5 personas
            attempts = 0
            while attempts < 100: # Sécurité pour éviter une boucle infinie
                # 1. Tirer 2 thèmes distincts du Top 50
                duo = random.sample(top_50_tags, 2)
                # 2. Tirer 1 thème de l'ensemble des thèmes uniques
                third_tag = random.choice(all_unique_tags)

                # 3. S'assurer que le 3ème thème n'est pas déjà dans le duo
                if third_tag not in duo:
                    trio = tuple(sorted(duo + [third_tag]))
                    if trio not in used_combos:
                        generated_groups.append({'themes': list(trio), 'count': 0})
                        used_combos.add(trio)
                        break
                attempts += 1
            if attempts == 100:
                self.logger.warning(f"⚠️ Impossible de générer un trio unique après 100 tentatives pour le groupe {i+1}.")

        if not generated_groups:
            self.logger.error("❌ Impossible de générer des archétypes de thèmes.")
            return

        self.logger.info("🏆 5 Archétypes de thèmes générés aléatoirement :")
        for i, group in enumerate(generated_groups, 1):
            themes_str = ", ".join(group['themes'])
            self.logger.info(f"  {i}. [{themes_str}]")
        
        # Charger la configuration des banques existante
        banks_config_file = os.path.join(self.shared_state['config']['workspace'], 'memory_banks_config.json')
        banks_config = self._load_banks_config(banks_config_file)
        
        # Créer les personas pour les banques 5-9
        successful_creations = 0
        for i, group in enumerate(generated_groups):
            bank_slot = str(5 + i)
            theme_group = group['themes']
            
            self.logger.info(f"🎭 Création du persona multilingue pour l'archétype '{', '.join(theme_group)}' (banque {bank_slot})...")
            
            # Générer le persona avec l'IA
            persona = self._generate_persona_for_theme_group(theme_group, 0, all_unique_tags)
            
            if persona:
                banks_config['banks'][bank_slot] = {
                    'name': persona['name'],
                    'archetype': persona['archetype'],
                    'description': persona['description'],
                    'themes': theme_group,
                    'corpus': persona['corpus'],
                    'multilingual': persona.get('multilingual', {})
                }
                self.logger.info(f"✅ Persona multilingue créé : {persona['name']} ({persona['archetype']})")
                successful_creations += 1
            else:
                self.logger.warning(f"⚠️ Échec de création du persona pour l'archétype '{', '.join(theme_group)}'")
        
        # Sauvegarder la configuration mise à jour
        self._save_banks_config(banks_config, banks_config_file)
        
        self.logger.info(f"🎉 Création automatique terminée ! {successful_creations} personas créés sur {len(generated_groups)} tentatives.")
        
        # Afficher un résumé exact des personas réellement créés
        self.logger.info(f"\n📋 RÉSUMÉ DES PERSONAS CRÉÉS :")
        for i in range(5, 10):
            bank_slot = str(i)
            bank = banks_config['banks'].get(bank_slot)
            if bank:
                themes_str = ", ".join(bank.get('themes', []))
                self.logger.info(f"  Banque {bank_slot} : {bank.get('name')} ({bank.get('archetype')}) - Thèmes : {themes_str}")

    def _generate_persona_for_theme_group(self, theme_group: list, count: int, all_tags: list):
        """
        Génère un persona complet pour un groupe de thèmes donné en utilisant l'IA.
        Inclut une nouvelle tentative en cas d'erreur de parsing ou de validation.
        """
        # Contexte : autres thèmes fréquemment associés aux thèmes du groupe
        related_themes = []
        for tag in all_tags:
            if tag not in theme_group and tag not in related_themes:
                 related_themes.append(tag)
        related_themes_sample = related_themes[:10]

        languages = self._detect_available_languages()
        
        prompt = f"""Tu es un expert en création de personas marketing multilingues. Tu dois créer un persona complet pour une campagne de communication UPlanet.

ARCHÉTYPE DE THÈMES PRINCIPAL : {', '.join(theme_group)}
THÈMES SOUVENT ASSOCIÉS : {', '.join(related_themes_sample)}
LANGUES DISPONIBLES : {', '.join(languages)}

TÂCHE : Créer un persona marketing complet avec :
1. Un nom accrocheur
2. Un archétype psychologique (ex: "L'Artisan Holistique", "L'Explorateur Spirituel")
3. Une description du profil type qui incarne la combinaison des thèmes principaux.
4. Un corpus de communication (vocabulaire, arguments, ton, exemples)
5. Une version multilingue du contenu pour chaque langue disponible.

IMPORTANT : Tu dois créer le contenu dans TOUTES les langues disponibles ({', '.join(languages)}). Adapte le contenu culturellement tout en gardant la même personnalité.

Format de réponse JSON :
{{
  "name": "Nom du persona",
  "archetype": "Archétype psychologique",
  "description": "Description du profil type",
  "themes": {json.dumps(theme_group)},
  "corpus": {{
    "tone": "ton de communication",
    "vocabulary": ["mot1", "mot2", "mot3"],
    "arguments": ["argument1", "argument2", "argument3"],
    "examples": ["exemple1", "exemple2", "exemple3"]
  }},
  "multilingual": {{
    "fr": {{ ... contenu en français ... }},
    "en": {{ ... contenu en anglais ... }},
    ...
  }}
}}

Le persona doit être une synthèse créative des thèmes {', '.join(theme_group)}."""

        for attempt in range(2): # 1ère tentative + 1 nouvelle tentative
            try:
                response = self._query_ia(prompt, expect_json=True)
                if not response:
                    if attempt == 0:
                        self.logger.warning("La requête IA n'a retourné aucune réponse. Nouvelle tentative...")
                        time.sleep(1)
                        continue
                    else:
                        self.logger.error("La requête IA a de nouveau échoué. Abandon.")
                        return None

                if isinstance(response, dict) and 'answer' in response:
                    cleaned_response = self._clean_ia_json_output(response['answer'])
                    persona_data = json.loads(cleaned_response)
                elif isinstance(response, dict):
                    persona_data = response
                else:
                    cleaned_response = self._clean_ia_json_output(response)
                    persona_data = json.loads(cleaned_response)
                
                # Valider la structure
                required_fields = ['name', 'archetype', 'description', 'corpus']
                if not all(field in persona_data for field in required_fields):
                    raise ValueError("Champs manquants dans la réponse JSON.")
                    
                # Vérifier que le contenu multilingue est présent
                if 'multilingual' not in persona_data:
                    self.logger.warning("⚠️ Contenu multilingue manquant dans le persona, il sera créé par défaut.")
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
                
                return persona_data # Succès, on retourne le résultat
                
            except (json.JSONDecodeError, ValueError) as e:
                log_message = f"Erreur de parsing/validation pour le persona '{', '.join(theme_group)}': {e}"
                if attempt == 0:
                    self.logger.warning(f"{log_message}. Nouvelle tentative...")
                    time.sleep(1)
                else:
                    self.logger.error(f"Échec final après nouvelle tentative. {log_message}")
                    return None
            except Exception as e:
                self.logger.error(f"❌ Erreur inattendue lors de la génération du persona '{', '.join(theme_group)}': {e}")
                return None
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
        self.logger.info("📞 Interrogation de l'IA en cours... Le traitement du prompt peut être long.")
        self.logger.debug(f"Taille du prompt: {len(prompt)} caractères.")
        start_time = time.time()

        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            
            end_time = time.time()
            self.logger.info(f"✅ Réponse de l'IA reçue en {end_time - start_time:.2f} secondes.")
            self.logger.debug(f"Réponse brute de l'IA reçue : {result.stdout.strip()}")

            if expect_json:
                return json.loads(result.stdout)
            return result.stdout

        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Le script d'IA a retourné une erreur.")
            self.logger.error(f"   Code de retour : {e.returncode}")
            self.logger.error(f"   Sortie standard (stdout) : {e.stdout.strip()}")
            self.logger.error(f"   Sortie d'erreur (stderr) : {e.stderr.strip()}")
            return None

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
        
        # La consolidation sémantique interactive est désactivée pour la nouvelle logique
        # --- NOUVELLE ÉTAPE : Consolidation sémantique interactive ---
        # consolidation_map = self._get_interactive_tag_consolidation(list(tag_counts.keys()))
        # ... (le reste du bloc a été supprimé)

        unique_tags = len(tag_counts)
        
        # On ne filtre plus les thèmes peu utilisés. On garde tout.
        filtered_tags = tag_counts 
        removed_tags = {}
        
        self.logger.info(f"🎯 {len(filtered_tags)} thèmes conservés après normalisation.")
        
        # Le nettoyage des profils se fait maintenant uniquement pour normaliser les tags existants
        # et non plus pour supprimer les tags rares.
        cleaned_profiles = 0
        for pubkey, data in knowledge_base.items():
            metadata = data.get('metadata', {})
            tags = metadata.get('tags', [])
            if tags and tags != ['error']:
                # Normaliser chaque tag et dédoublonner
                new_tags_set = {tag_map.get(tag, self._normalize_tag(tag)) for tag in tags}
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
        self.logger.info(f"\n--- Top 50 des thèmes après normalisation ---")
        for i, (tag, count) in enumerate(top_50, 1):
            self.logger.info(f"  {i:>2}. {tag:<20} ({count:>4} occurrences)")
        
        self.logger.info(f"✅ Optimisation terminée ! {len(filtered_tags)} thèmes conservés sur {unique_tags_before} initiaux.")

    def _get_interactive_tag_consolidation(self, tags: list) -> dict:
        """
        Utilise l'IA pour suggérer un regroupement sémantique des thèmes et demande une validation à l'utilisateur.
        Retourne une carte de consolidation {'ancien_theme': 'nouveau_theme'}.
        """
        if len(tags) < 10: # Pas assez de thèmes pour les regrouper
            return {}

        self.logger.info("🤖 Lancement de l'IA pour proposer des regroupements sémantiques de thèmes...")
        
        # 1. Interroger l'IA
        prompt_template = self._load_prompt('analyst_consolidation_prompt_file')
        if not prompt_template:
            self.logger.warning("Le prompt de consolidation des thèmes n'est pas trouvé. Étape de consolidation sémantique ignorée.")
            return {}
        
        prompt = prompt_template.replace('{tag_list_json}', json.dumps(tags, indent=2))
        
        try:
            ia_response = self._query_ia(prompt, expect_json=True)
            cleaned_answer = self._clean_ia_json_output(ia_response['answer'])
            suggested_groups = json.loads(cleaned_answer)
            
            if not isinstance(suggested_groups, list):
                self.logger.warning("La réponse de l'IA pour le regroupement de thèmes n'est pas une liste.")
                return {}
                
        except Exception as e:
            self.logger.error(f"Erreur lors de la récupération des regroupements de thèmes via l'IA : {e}")
            return {}

        if not suggested_groups:
            self.logger.info("L'IA n'a suggéré aucun regroupement de thèmes.")
            return {}
            
        # 2. Validation par l'utilisateur
        self.logger.info("Veuillez valider les regroupements de thèmes proposés par l'IA.")
        consolidation_map = {}
        accept_all = False
        
        for i, group in enumerate(suggested_groups):
            primary_tag = group.get('primary_tag')
            synonyms = group.get('synonyms')
            
            if not primary_tag or not synonyms or not isinstance(synonyms, list):
                continue

            # Ne pas proposer de regrouper un thème avec lui-même ou des thèmes déjà consolidés
            synonyms = [s for s in synonyms if s != primary_tag and s not in consolidation_map]
            if not synonyms:
                continue

            print("\n" + "="*50)
            print(f"Suggestion de regroupement {i+1}/{len(suggested_groups)}:")
            print(f"  Thème principal : '{primary_tag}'")
            print(f"  Regrouper avec   : {', '.join(synonyms)}")
            print("="*50)
            
            if accept_all:
                print("Accepté automatiquement (mode 'tout accepter').")
                for synonym in synonyms:
                    consolidation_map[synonym] = primary_tag
                continue

            while True:
                choice = input("Accepter ce regroupement ? [O]ui / [N]on / [T]out accepter / [A]rrêter : ").strip().lower()
                if choice in ['o', 'oui', 'y', 'yes']:
                    for synonym in synonyms:
                        consolidation_map[synonym] = primary_tag
                    self.logger.info(f"✅ Regroupement accepté pour '{primary_tag}'.")
                    break
                elif choice in ['n', 'non', 'no']:
                    self.logger.info("❌ Regroupement refusé.")
                    break
                elif choice in ['t', 'tout', 'all']:
                    self.logger.info("✅ Mode 'Tout accepter' activé. Les regroupements restants seront acceptés.")
                    accept_all = True
                    # Accepter aussi le regroupement actuel
                    for synonym in synonyms:
                        consolidation_map[synonym] = primary_tag
                    break
                elif choice in ['a', 'arrêter', 'q', 'quit']:
                    self.logger.info("🛑 Validation des regroupements arrêtée par l'utilisateur.")
                    return consolidation_map
                else:
                    print("Choix invalide. Veuillez répondre par 'o', 'n', 't' ou 'a'.")

        return consolidation_map

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
        print("r. Retour")
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
            choice = input("\nSélectionnez les thèmes (ex: 1,3,5) ou 'r' pour retour : ").strip()
            if not choice:
                self.logger.info("Opération annulée.")
                return
            if choice.lower() == 'r':
                self.logger.info("Retour au menu analyste...")
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
        
        # Étape 3 : Options de filtrage avancées
        print(f"\n🎯 FILTRAGE AVANCÉ")
        print("=" * 50)
        print(f"Prospects des thèmes sélectionnés : {len(filtered_prospects)}")
        print()
        print("Options de filtrage :")
        print("1. Aucun filtre (tous les prospects des thèmes)")
        print("2. Filtrer par langue")
        print("3. Filtrer par pays")
        print("4. Filtrer par région")
        print("5. Filtrer par plateforme (G1/Gchange)")
        print("6. Filtrer par comptes liés")
        print("7. Filtrer par activité Gchange")
        print("8. Combinaison de filtres")
        print("r. Retour")
        
        try:
            filter_choice = input("\nChoisissez une option (1-8) ou 'r' pour retour : ").strip()
            
            if filter_choice.lower() == 'r':
                self.logger.info("Retour à la sélection des thèmes...")
                return
            elif filter_choice == "1":
                final_prospects = filtered_prospects
            elif filter_choice == "2":
                final_prospects = self._filter_by_language(filtered_prospects)
            elif filter_choice == "3":
                final_prospects = self._filter_by_country(filtered_prospects)
            elif filter_choice == "4":
                final_prospects = self._filter_by_region(filtered_prospects)
            elif filter_choice == "5":
                final_prospects = self._filter_by_platform(filtered_prospects)
            elif filter_choice == "6":
                final_prospects = self._filter_by_linked_accounts(filtered_prospects)
            elif filter_choice == "7":
                final_prospects = self._filter_by_gchange_activity(filtered_prospects)
            elif filter_choice == "8":
                final_prospects = self._filter_combined_advanced(filtered_prospects)
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
        
        print("r. Retour")
        
        try:
            choice = input("\nSélectionnez les langues (ex: 1,2), 'all' pour toutes, ou 'r' pour retour : ").strip()
            if choice.lower() == 'r':
                self.logger.info("Retour aux options de filtrage...")
                return prospects
            
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
        
        print("r. Retour")
        
        try:
            choice = input("\nSélectionnez les pays (ex: 1,2), 'all' pour tous, ou 'r' pour retour : ").strip()
            if choice.lower() == 'r':
                self.logger.info("Retour aux options de filtrage...")
                return prospects
            
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

    def select_cluster_by_linked_accounts(self):
        """
        Sélectionne les prospects selon leurs comptes liés (relations Cesium-Gchange).
        Permet de cibler des utilisateurs qui ont des comptes sur les deux plateformes.
        """
        self.logger.info("🔗 Agent Analyste : Ciblage par comptes liés...")
        
        # Charger la base de connaissance
        knowledge_base = self._load_and_sync_knowledge_base()
        if not knowledge_base:
            self.logger.error("❌ Base de connaissance vide.")
            return
        
        # Analyser les types de comptes liés disponibles
        linked_accounts_stats = {
            'cesium_only': 0,
            'gchange_only': 0,
            'both_platforms': 0,
            'no_linked': 0
        }
        
        linked_prospects = []
        
        for pubkey, data in knowledge_base.items():
            linked_accounts = data.get('linked_accounts', {})
            
            if not linked_accounts:
                linked_accounts_stats['no_linked'] += 1
                continue
            
            cesium_pk = linked_accounts.get('cesium_pubkey')
            gchange_uid = linked_accounts.get('gchange_uid')
            
            if cesium_pk and gchange_uid:
                linked_accounts_stats['both_platforms'] += 1
                linked_prospects.append({
                    'pubkey': pubkey,
                    'uid': data.get('uid', ''),
                    'metadata': data.get('metadata', {}),
                    'linked_accounts': linked_accounts,
                    'type': 'both_platforms'
                })
            elif cesium_pk:
                linked_accounts_stats['cesium_only'] += 1
                linked_prospects.append({
                    'pubkey': pubkey,
                    'uid': data.get('uid', ''),
                    'metadata': data.get('metadata', {}),
                    'linked_accounts': linked_accounts,
                    'type': 'cesium_only'
                })
            elif gchange_uid:
                linked_accounts_stats['gchange_only'] += 1
                linked_prospects.append({
                    'pubkey': pubkey,
                    'uid': data.get('uid', ''),
                    'metadata': data.get('metadata', {}),
                    'linked_accounts': linked_accounts,
                    'type': 'gchange_only'
                })
        
        if not linked_prospects:
            self.logger.error("❌ Aucun prospect avec des comptes liés trouvé.")
            return
        
        # Afficher les options
        print("\n🔗 COMPTES LIÉS DISPONIBLES :")
        print("=" * 50)
        print(f"1. Utilisateurs sur les deux plateformes ({linked_accounts_stats['both_platforms']} membres)")
        print(f"   Description : Prospects ayant des comptes Cesium ET Gchange.")
        print()
        print(f"2. Utilisateurs Cesium uniquement ({linked_accounts_stats['cesium_only']} membres)")
        print(f"   Description : Prospects avec compte Cesium découvert via Gchange.")
        print()
        print(f"3. Utilisateurs Gchange uniquement ({linked_accounts_stats['gchange_only']} membres)")
        print(f"   Description : Prospects Gchange avec compte Cesium lié.")
        print()
        print(f"4. Tous les comptes liés ({len(linked_prospects)} membres)")
        print(f"   Description : Tous les prospects avec au moins un compte lié.")
        print()
        
        try:
            choice = input("Sélectionnez un type de ciblage (1-4) : ").strip()
            if not choice:
                self.logger.info("Opération annulée.")
                return
            
            choice = int(choice)
            if not (1 <= choice <= 4):
                self.logger.error("❌ Sélection invalide.")
                return
            
            # Filtrer selon le choix
            if choice == 1:
                filtered_prospects = [p for p in linked_prospects if p['type'] == 'both_platforms']
                cluster_name = "Utilisateurs multi-plateformes"
                description = "Prospects ayant des comptes sur Cesium ET Gchange"
            elif choice == 2:
                filtered_prospects = [p for p in linked_prospects if p['type'] == 'cesium_only']
                cluster_name = "Utilisateurs Cesium découverts"
                description = "Prospects Cesium découverts via leurs profils Gchange"
            elif choice == 3:
                filtered_prospects = [p for p in linked_prospects if p['type'] == 'gchange_only']
                cluster_name = "Utilisateurs Gchange avec Cesium"
                description = "Prospects Gchange ayant un compte Cesium lié"
            else:  # choice == 4
                filtered_prospects = linked_prospects
                cluster_name = "Tous les comptes liés"
                description = "Tous les prospects avec des comptes liés"
            
            if not filtered_prospects:
                self.logger.warning("⚠️ Aucun prospect correspondant au critère sélectionné.")
                return
            
            # Créer le cluster
            cluster = {
                'cluster_name': cluster_name,
                'description': f"{description} ({len(filtered_prospects)} prospects)",
                'members': filtered_prospects
            }
            
            # Afficher des statistiques sur la cible
            print(f"\n📊 STATISTIQUES DE LA CIBLE SÉLECTIONNÉE")
            print(f"   • Nombre de prospects : {len(filtered_prospects)}")
            
            # Analyser les langues
            languages = {}
            for prospect in filtered_prospects:
                metadata = prospect.get('metadata', {})
                lang = metadata.get('language', 'xx')
                if lang != 'xx':
                    languages[lang] = languages.get(lang, 0) + 1
            
            if languages:
                lang_str = ", ".join([f"{k}({v})" for k, v in sorted(languages.items(), key=lambda x: x[1], reverse=True)])
                print(f"   • Langues : {lang_str}")
            
            # Analyser les pays
            countries = {}
            for prospect in filtered_prospects:
                metadata = prospect.get('metadata', {})
                country = metadata.get('country')
                if country:
                    countries[country] = countries.get(country, 0) + 1
            
            if countries:
                country_str = ", ".join([f"{k}({v})" for k, v in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:3]])
                print(f"   • Pays principaux : {country_str}")
            
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

    def select_cluster_by_gchange(self):
        """
        Sélectionne les prospects spécifiquement de la plateforme Gchange.
        Permet de cibler les utilisateurs actifs sur le marché Gchange.
        """
        self.logger.info("🛒 Agent Analyste : Ciblage par comptes Gchange...")
        
        # Charger la base de connaissance
        knowledge_base = self._load_and_sync_knowledge_base()
        if not knowledge_base:
            self.logger.error("❌ Base de connaissance vide.")
            return
        
        # Analyser les prospects Gchange disponibles
        gchange_prospects = []
        gchange_stats = {
            'with_cesium': 0,
            'without_cesium': 0,
            'with_ads': 0,
            'without_ads': 0
        }
        
        for pubkey, data in knowledge_base.items():
            source = data.get('source', '')
            
            # Identifier les prospects Gchange
            if 'gchange' in source:
                prospect_info = {
                    'pubkey': pubkey,
                    'uid': data.get('uid', ''),
                    'metadata': data.get('metadata', {}),
                    'profile': data.get('profile', {}),
                    'linked_accounts': data.get('linked_accounts', {}),
                    'import_metadata': data.get('import_metadata', {})
                }
                
                gchange_prospects.append(prospect_info)
                
                # Statistiques
                if prospect_info['linked_accounts'].get('cesium_pubkey'):
                    gchange_stats['with_cesium'] += 1
                else:
                    gchange_stats['without_cesium'] += 1
                
                # Vérifier s'il y a des annonces détectées
                profile_source = prospect_info['profile'].get('_source', {})
                detected_ads = profile_source.get('detected_ads', [])
                if detected_ads:
                    gchange_stats['with_ads'] += 1
                else:
                    gchange_stats['without_ads'] += 1
        
        if not gchange_prospects:
            self.logger.error("❌ Aucun prospect Gchange trouvé dans la base de connaissance.")
            return
        
        # Afficher les options
        print("\n🛒 COMPTES GCHANGE DISPONIBLES :")
        print("=" * 50)
        print(f"Total : {len(gchange_prospects)} prospects Gchange")
        print()
        print(f"1. Tous les utilisateurs Gchange ({len(gchange_prospects)} membres)")
        print(f"   Description : Tous les prospects de la plateforme Gchange.")
        print()
        print(f"2. Utilisateurs Gchange avec compte Cesium ({gchange_stats['with_cesium']} membres)")
        print(f"   Description : Prospects Gchange ayant un compte Cesium lié.")
        print()
        print(f"3. Utilisateurs Gchange uniquement ({gchange_stats['without_cesium']} membres)")
        print(f"   Description : Prospects Gchange sans compte Cesium.")
        print()
        print(f"4. Utilisateurs Gchange avec annonces ({gchange_stats['with_ads']} membres)")
        print(f"   Description : Prospects Gchange ayant publié des annonces.")
        print()
        print(f"5. Utilisateurs Gchange sans annonces ({gchange_stats['without_ads']} membres)")
        print(f"   Description : Prospects Gchange sans annonces détectées.")
        print()
        
        try:
            choice = input("Sélectionnez un type de ciblage (1-5) : ").strip()
            if not choice:
                self.logger.info("Opération annulée.")
                return
            
            choice = int(choice)
            if not (1 <= choice <= 5):
                self.logger.error("❌ Sélection invalide.")
                return
            
            # Filtrer selon le choix
            if choice == 1:
                filtered_prospects = gchange_prospects
                cluster_name = "Tous les utilisateurs Gchange"
                description = "Tous les prospects de la plateforme Gchange"
            elif choice == 2:
                filtered_prospects = [p for p in gchange_prospects if p['linked_accounts'].get('cesium_pubkey')]
                cluster_name = "Gchange avec Cesium"
                description = "Prospects Gchange ayant un compte Cesium lié"
            elif choice == 3:
                filtered_prospects = [p for p in gchange_prospects if not p['linked_accounts'].get('cesium_pubkey')]
                cluster_name = "Gchange uniquement"
                description = "Prospects Gchange sans compte Cesium"
            elif choice == 4:
                filtered_prospects = []
                for p in gchange_prospects:
                    profile_source = p['profile'].get('_source', {})
                    detected_ads = profile_source.get('detected_ads', [])
                    if detected_ads:
                        filtered_prospects.append(p)
                cluster_name = "Gchange avec annonces"
                description = "Prospects Gchange ayant publié des annonces"
            else:  # choice == 5
                filtered_prospects = []
                for p in gchange_prospects:
                    profile_source = p['profile'].get('_source', {})
                    detected_ads = profile_source.get('detected_ads', [])
                    if not detected_ads:
                        filtered_prospects.append(p)
                cluster_name = "Gchange sans annonces"
                description = "Prospects Gchange sans annonces détectées"
            
            if not filtered_prospects:
                self.logger.warning("⚠️ Aucun prospect correspondant au critère sélectionné.")
                return
            
            # Créer le cluster
            cluster = {
                'cluster_name': cluster_name,
                'description': f"{description} ({len(filtered_prospects)} prospects)",
                'members': filtered_prospects
            }
            
            # Afficher des statistiques sur la cible
            print(f"\n📊 STATISTIQUES DE LA CIBLE SÉLECTIONNÉE")
            print(f"   • Nombre de prospects : {len(filtered_prospects)}")
            
            # Analyser les langues
            languages = {}
            for prospect in filtered_prospects:
                metadata = prospect.get('metadata', {})
                lang = metadata.get('language', 'xx')
                if lang != 'xx':
                    languages[lang] = languages.get(lang, 0) + 1
            
            if languages:
                lang_str = ", ".join([f"{k}({v})" for k, v in sorted(languages.items(), key=lambda x: x[1], reverse=True)])
                print(f"   • Langues : {lang_str}")
            
            # Analyser les pays
            countries = {}
            for prospect in filtered_prospects:
                metadata = prospect.get('metadata', {})
                country = metadata.get('country')
                if country:
                    countries[country] = countries.get(country, 0) + 1
            
            if countries:
                country_str = ", ".join([f"{k}({v})" for k, v in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:3]])
                print(f"   • Pays principaux : {country_str}")
            
            # Analyser les thèmes
            themes = {}
            for prospect in filtered_prospects:
                metadata = prospect.get('metadata', {})
                tags = metadata.get('tags', [])
                for tag in tags:
                    themes[tag] = themes.get(tag, 0) + 1
            
            if themes:
                top_themes = sorted(themes.items(), key=lambda x: x[1], reverse=True)[:5]
                theme_str = ", ".join([f"{k}({v})" for k, v in top_themes])
                print(f"   • Thèmes principaux : {theme_str}")
            
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
        print("- 'r' pour retour")
        
        choice = input("> ").strip()
        if choice.lower() == 'r':
            self.logger.info("Retour au menu analyste...")
            return
        
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

    def _filter_by_platform(self, prospects):
        """Filtre les prospects par plateforme (G1/Gchange)"""
        print(f"\n🖥️ PLATEFORMES DISPONIBLES :")
        
        # Analyser les plateformes disponibles
        platforms = {}
        for prospect in prospects:
            # Récupérer les données complètes depuis la base de connaissance
            knowledge_base = self._load_and_sync_knowledge_base()
            pubkey = prospect.get('pubkey')
            if pubkey in knowledge_base:
                data = knowledge_base[pubkey]
                source = data.get('source', '')
                
                if 'g1_wot' in source:
                    platforms['G1 (WoT)'] = platforms.get('G1 (WoT)', 0) + 1
                elif 'gchange' in source:
                    platforms['Gchange'] = platforms.get('Gchange', 0) + 1
                else:
                    platforms['Autre'] = platforms.get('Autre', 0) + 1
        
        # Afficher les plateformes
        platform_list = sorted(platforms.items(), key=lambda x: x[1], reverse=True)
        for i, (platform, count) in enumerate(platform_list, 1):
            print(f"{i}. {platform} ({count} prospects)")
        
        print("r. Retour")
        
        try:
            choice = input("\nSélectionnez les plateformes (ex: 1,2), 'all' pour toutes, ou 'r' pour retour : ").strip()
            if choice.lower() == 'r':
                self.logger.info("Retour aux options de filtrage...")
                return prospects
            
            if choice.lower() == 'all':
                selected_platforms = [platform for platform, _ in platform_list]
            else:
                selected_indices = [int(x.strip()) - 1 for x in choice.split(',')]
                selected_platforms = [platform_list[i][0] for i in selected_indices if 0 <= i < len(platform_list)]
            
            if not selected_platforms:
                return prospects
            
            # Filtrer
            filtered = []
            for prospect in prospects:
                pubkey = prospect.get('pubkey')
                if pubkey in knowledge_base:
                    data = knowledge_base[pubkey]
                    source = data.get('source', '')
                    
                    platform_type = 'Autre'
                    if 'g1_wot' in source:
                        platform_type = 'G1 (WoT)'
                    elif 'gchange' in source:
                        platform_type = 'Gchange'
                    
                    if platform_type in selected_platforms:
                        filtered.append(prospect)
            
            self.logger.info(f"✅ Filtrage par plateforme : {len(filtered)} prospects sélectionnés")
            return filtered
            
        except (ValueError, IndexError):
            self.logger.warning("⚠️ Erreur dans la sélection, aucun filtre appliqué.")
            return prospects

    def _filter_by_linked_accounts(self, prospects):
        """Filtre les prospects par comptes liés"""
        print(f"\n🔗 TYPES DE COMPTES LIÉS :")
        print("1. Utilisateurs multi-plateformes (Cesium + Gchange)")
        print("2. Utilisateurs avec compte Cesium uniquement")
        print("3. Utilisateurs avec compte Gchange uniquement")
        print("4. Utilisateurs sans comptes liés")
        print("5. Tous les utilisateurs avec comptes liés")
        print("r. Retour")
        
        try:
            choice = input("\nSélectionnez un type (1-5) ou 'r' pour retour : ").strip()
            if choice.lower() == 'r':
                self.logger.info("Retour aux options de filtrage...")
                return prospects
            
            choice = int(choice)
            if not (1 <= choice <= 5):
                self.logger.warning("⚠️ Choix invalide, aucun filtre appliqué.")
                return prospects
            
            # Charger la base de connaissance pour accéder aux données complètes
            knowledge_base = self._load_and_sync_knowledge_base()
            
            filtered = []
            for prospect in prospects:
                pubkey = prospect.get('pubkey')
                if pubkey in knowledge_base:
                    data = knowledge_base[pubkey]
                    linked_accounts = data.get('linked_accounts', {})
                    
                    cesium_pk = linked_accounts.get('cesium_pubkey')
                    gchange_uid = linked_accounts.get('gchange_uid')
                    
                    include_prospect = False
                    
                    if choice == 1:  # Multi-plateformes
                        include_prospect = cesium_pk and gchange_uid
                    elif choice == 2:  # Cesium uniquement
                        include_prospect = cesium_pk and not gchange_uid
                    elif choice == 3:  # Gchange uniquement
                        include_prospect = gchange_uid and not cesium_pk
                    elif choice == 4:  # Sans comptes liés
                        include_prospect = not cesium_pk and not gchange_uid
                    elif choice == 5:  # Tous avec comptes liés
                        include_prospect = cesium_pk or gchange_uid
                    
                    if include_prospect:
                        filtered.append(prospect)
            
            self.logger.info(f"✅ Filtrage par comptes liés : {len(filtered)} prospects sélectionnés")
            return filtered
            
        except ValueError:
            self.logger.warning("⚠️ Erreur dans la sélection, aucun filtre appliqué.")
            return prospects

    def _filter_by_gchange_activity(self, prospects):
        """Filtre les prospects par activité Gchange"""
        print(f"\n🛒 ACTIVITÉ GCHANGE :")
        print("1. Utilisateurs Gchange avec annonces")
        print("2. Utilisateurs Gchange sans annonces")
        print("3. Utilisateurs Gchange avec compte Cesium")
        print("4. Utilisateurs Gchange uniquement")
        print("r. Retour")
        
        try:
            choice = input("\nSélectionnez un type (1-4) ou 'r' pour retour : ").strip()
            if choice.lower() == 'r':
                self.logger.info("Retour aux options de filtrage...")
                return prospects
            
            choice = int(choice)
            if not (1 <= choice <= 4):
                self.logger.warning("⚠️ Choix invalide, aucun filtre appliqué.")
                return prospects
            
            # Charger la base de connaissance
            knowledge_base = self._load_and_sync_knowledge_base()
            
            filtered = []
            for prospect in prospects:
                pubkey = prospect.get('pubkey')
                if pubkey in knowledge_base:
                    data = knowledge_base[pubkey]
                    source = data.get('source', '')
                    
                    # Vérifier si c'est un utilisateur Gchange
                    if 'gchange' not in source:
                        continue
                    
                    linked_accounts = data.get('linked_accounts', {})
                    profile = data.get('profile', {})
                    profile_source = profile.get('_source', {})
                    detected_ads = profile_source.get('detected_ads', [])
                    
                    include_prospect = False
                    
                    if choice == 1:  # Avec annonces
                        include_prospect = bool(detected_ads)
                    elif choice == 2:  # Sans annonces
                        include_prospect = not detected_ads
                    elif choice == 3:  # Avec Cesium
                        include_prospect = bool(linked_accounts.get('cesium_pubkey'))
                    elif choice == 4:  # Gchange uniquement
                        include_prospect = not linked_accounts.get('cesium_pubkey')
                    
                    if include_prospect:
                        filtered.append(prospect)
            
            self.logger.info(f"✅ Filtrage par activité Gchange : {len(filtered)} prospects sélectionnés")
            return filtered
            
        except ValueError:
            self.logger.warning("⚠️ Erreur dans la sélection, aucun filtre appliqué.")
            return prospects

    def _filter_combined_advanced(self, prospects):
        """Filtre combiné avancé avec toutes les options"""
        self.logger.info("🔀 Filtrage combiné avancé...")
        
        print(f"\n🔀 FILTRAGE COMBINÉ AVANCÉ")
        print("=" * 50)
        print("Appliquez les filtres dans l'ordre souhaité :")
        print("1. Langue")
        print("2. Pays")
        print("3. Région")
        print("4. Plateforme")
        print("5. Comptes liés")
        print("6. Activité Gchange")
        print("7. Appliquer tous les filtres")
        print("r. Retour")
        
        try:
            choice = input("\nChoisissez une option (1-7) ou 'r' pour retour : ").strip()
            
            if choice.lower() == 'r':
                return prospects
            elif choice == "1":
                prospects = self._filter_by_language(prospects)
            elif choice == "2":
                prospects = self._filter_by_country(prospects)
            elif choice == "3":
                prospects = self._filter_by_region(prospects)
            elif choice == "4":
                prospects = self._filter_by_platform(prospects)
            elif choice == "5":
                prospects = self._filter_by_linked_accounts(prospects)
            elif choice == "6":
                prospects = self._filter_by_gchange_activity(prospects)
            elif choice == "7":
                # Appliquer tous les filtres en cascade
                prospects = self._filter_by_language(prospects)
                if prospects:
                    prospects = self._filter_by_country(prospects)
                if prospects:
                    prospects = self._filter_by_region(prospects)
                if prospects:
                    prospects = self._filter_by_platform(prospects)
                if prospects:
                    prospects = self._filter_by_linked_accounts(prospects)
                if prospects:
                    prospects = self._filter_by_gchange_activity(prospects)
            else:
                self.logger.warning("⚠️ Option invalide.")
            
            return prospects
            
        except Exception as e:
            self.logger.error(f"❌ Erreur dans le filtrage combiné : {e}")
            return prospects

    def run_optimized_analysis_suite(self):
        """
        Suite d'analyse optimisée combinant géo-linguistique et thématique
        avec des optimisations avancées : cache, batch processing, parallélisation.
        """
        self.logger.info("🚀 Agent Analyste : Démarrage de la suite d'analyse OPTIMISÉE...")
        self.shared_state['status']['AnalystAgent'] = "Suite d'analyse optimisée en cours..."

        # Vérifier Ollama une seule fois
        if not self._check_ollama_once():
            self.shared_state['status']['AnalystAgent'] = "Échec : API Ollama indisponible."
            return

        knowledge_base = self._load_and_sync_knowledge_base()
        
        # --- OPTIMISATION 1 : Pré-calcul des données communes ---
        self.logger.info("📊 Pré-calcul des données communes...")
        
        # Identifier tous les prospects à analyser
        all_prospects = [pk for pk, data in knowledge_base.items() if 'g1_wot' in data.get('source', '')]
        prospects_with_gps = []
        prospects_with_description = []
        
        for pk in all_prospects:
            data = knowledge_base[pk]
            profile = data.get('profile', {})
            source = profile.get('_source', {})
            
            # Vérifier GPS
            geo_point = source.get('geoPoint', {})
            if geo_point and 'lat' in geo_point and 'lon' in geo_point:
                lat = geo_point.get('lat')
                lon = geo_point.get('lon')
                if lat is not None and lon is not None and lat != 0 and lon != 0:
                    prospects_with_gps.append(pk)
            
            # Vérifier description
            description = (source.get('description') or '').strip()
            if description:
                prospects_with_description.append(pk)
        
        self.logger.info(f"📈 Statistiques pré-calculées :")
        self.logger.info(f"   • Total prospects : {len(all_prospects)}")
        self.logger.info(f"   • Avec GPS : {len(prospects_with_gps)}")
        self.logger.info(f"   • Avec description : {len(prospects_with_description)}")
        
        # --- OPTIMISATION 2 : Charger tous les prompts une seule fois ---
        geo_prompt_template = self._load_prompt('analyst_language_prompt_file')
        thematic_prompt_template = self._load_prompt('analyst_thematic_prompt_file')
        
        if not geo_prompt_template or not thematic_prompt_template:
            self.logger.error("❌ Impossible de charger les prompts templates.")
            return
        
        # --- OPTIMISATION 3 : Charger tous les caches ---
        geo_cache_file = os.path.join(self.shared_state['config']['workspace'], 'geo_cache.json')
        thematic_cache_file = os.path.join(self.shared_state['config']['workspace'], 'thematic_cache.json')
        
        geo_cache = self._load_geo_cache(geo_cache_file)
        thematic_cache = self._load_thematic_cache(thematic_cache_file)
        
        # --- OPTIMISATION 4 : Calcul des thèmes guides ---
        tag_counter = Counter()
        for pk, data in knowledge_base.items():
            if 'tags' in data.get('metadata', {}):
                tag_counter.update(data['metadata']['tags'])
        
        guide_tags = [tag for tag, count in tag_counter.most_common(50)]
        
        # --- OPTIMISATION 5 : Traitement optimisé par phases ---
        
        # PHASE 1 : Géolocalisation GPS (batch processing)
        self.logger.info("📍 PHASE 1 : Géolocalisation GPS optimisée...")
        gps_stats = self._run_optimized_gps_analysis(
            knowledge_base, prospects_with_gps, geo_cache, geo_cache_file
        )
        
        # PHASE 2 : Analyse thématique (batch processing)
        self.logger.info("🏷️ PHASE 2 : Analyse thématique optimisée...")
        thematic_stats = self._run_optimized_thematic_analysis(
            knowledge_base, prospects_with_description, thematic_cache, 
            thematic_cache_file, thematic_prompt_template, guide_tags
        )
        
        # PHASE 3 : Analyse IA pour les cas restants
        self.logger.info("🧠 PHASE 3 : Analyse IA pour cas restants...")
        ia_stats = self._run_optimized_ia_analysis(
            knowledge_base, all_prospects, geo_prompt_template
        )
        
        # --- RÉSULTATS FINAUX ---
        self.logger.info("✅ Suite d'analyse optimisée terminée !")
        self.logger.info(f"📊 RÉSULTATS FINAUX :")
        self.logger.info(f"   • GPS géolocalisés : {gps_stats['geolocated']}")
        self.logger.info(f"   • GPS depuis cache : {gps_stats['cached']}")
        self.logger.info(f"   • Tags générés : {thematic_stats['tags_generated']}")
        self.logger.info(f"   • Analyses IA : {ia_stats['ia_analyzed']}")
        self.logger.info(f"   • Total traités : {gps_stats['geolocated'] + gps_stats['cached'] + ia_stats['ia_analyzed']}")
        
        self.shared_state['status']['AnalystAgent'] = f"Suite optimisée terminée : {gps_stats['geolocated'] + gps_stats['cached'] + ia_stats['ia_analyzed']} profils analysés"

    def _run_optimized_gps_analysis(self, knowledge_base, prospects_with_gps, geo_cache, geo_cache_file):
        """Analyse GPS optimisée avec batch processing"""
        gps_geolocated = 0
        gps_cached = 0
        batch_size = 15  # Batch plus grand pour GPS
        gps_batch = []
        
        for i, pubkey in enumerate(prospects_with_gps):
            prospect_data = knowledge_base[pubkey]
            
            if 'language' in prospect_data.get('metadata', {}):
                continue
            
            profile = prospect_data.get('profile', {})
            source = profile.get('_source', {})
            geo_point = source.get('geoPoint', {})
            
            lat = geo_point.get('lat')
            lon = geo_point.get('lon')
            cache_key = f"{lat:.4f},{lon:.4f}"
            
            if cache_key in geo_cache:
                gps_cached += 1
                self._apply_geo_data(prospect_data, geo_cache[cache_key])
            else:
                gps_batch.append({
                    'pubkey': pubkey,
                    'lat': lat,
                    'lon': lon,
                    'uid': prospect_data.get('uid', 'N/A'),
                    'cache_key': cache_key
                })
                
                if len(gps_batch) >= batch_size or i == len(prospects_with_gps) - 1:
                    processed = self._process_gps_batch(gps_batch, geo_cache)
                    gps_geolocated += len(processed)
                    self._save_geo_cache(geo_cache, geo_cache_file)
                    gps_batch = []
        
        return {'geolocated': gps_geolocated, 'cached': gps_cached}

    def _run_optimized_thematic_analysis(self, knowledge_base, prospects_with_description, 
                                       thematic_cache, thematic_cache_file, prompt_template, guide_tags):
        """Analyse thématique optimisée avec batch processing"""
        tags_generated = 0
        batch_size = 8  # Batch optimal pour IA
        ia_batch = []
        
        for i, pubkey in enumerate(prospects_with_description):
            prospect_data = knowledge_base[pubkey]
            metadata = prospect_data.setdefault('metadata', {})
            
            if 'tags' in metadata:
                continue
            
            profile = prospect_data.get('profile', {})
            source = profile.get('_source', {})
            description = (source.get('description') or '').strip()
            
            # Traiter les réseaux sociaux
            socials = source.get('socials', [])
            social_tags = self._extract_social_tags(socials)
            
            if description:
                import hashlib
                description_hash = hashlib.md5(description.encode()).hexdigest()
                cache_key = f"thematic_{description_hash}"
                
                if cache_key in thematic_cache:
                    thematic_tags = thematic_cache[cache_key]
                else:
                    ia_batch.append({
                        'pubkey': pubkey,
                        'description': description,
                        'uid': prospect_data.get('uid', 'N/A'),
                        'cache_key': cache_key
                    })
                    
                    if len(ia_batch) >= batch_size or i == len(prospects_with_description) - 1:
                        processed = self._process_ia_batch(ia_batch, thematic_cache, prompt_template, guide_tags)
                        self._save_thematic_cache(thematic_cache, thematic_cache_file)
                        ia_batch = []
                
                if cache_key in thematic_cache:
                    thematic_tags = thematic_cache[cache_key]
                    all_tags = social_tags + thematic_tags
                    normalized_tags = self._normalize_tags(all_tags)
                    metadata['tags'] = normalized_tags
                    tags_generated += len(normalized_tags)
            else:
                metadata['tags'] = social_tags
                tags_generated += len(social_tags)
        
        return {'tags_generated': tags_generated}

    def _run_optimized_ia_analysis(self, knowledge_base, all_prospects, geo_prompt_template):
        """Analyse IA pour les cas restants"""
        ia_analyzed = 0
        
        for pubkey in all_prospects:
            prospect_data = knowledge_base[pubkey]
            
            # Vérifier si déjà analysé
            if 'language' in prospect_data.get('metadata', {}):
                continue
            
            profile = prospect_data.get('profile', {})
            source = profile.get('_source', {})
            description = (source.get('description') or '').strip()
            
            if description:
                try:
                    prompt = f"{geo_prompt_template}\n\nTexte fourni: \"{description}\""
                    ia_response = self._query_ia(prompt, expect_json=True)
                    cleaned_answer = self._clean_ia_json_output(ia_response['answer'])
                    geo_data = json.loads(cleaned_answer)
                    
                    self._apply_geo_data(prospect_data, geo_data)
                    ia_analyzed += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ Erreur analyse IA pour {prospect_data.get('uid')} : {e}")
        
        return {'ia_analyzed': ia_analyzed}

    def _apply_geo_data(self, prospect_data, geo_data):
        """Applique les données géolocalisées à un prospect"""
        meta = prospect_data.setdefault('metadata', {})
        
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
        
        meta['geolocation_source'] = geo_data.get('geolocation_source', 'unknown')

    def _extract_social_tags(self, socials):
        """Extrait les tags des réseaux sociaux"""
        social_tags = []
        social_mapping = {
            'web': 'website', 'facebook': 'facebook', 'email': 'email',
            'instagram': 'instagram', 'youtube': 'youtube', 'twitter': 'twitter',
            'diaspora': 'diaspora', 'linkedin': 'linkedin', 'github': 'github',
            'phone': 'phone', 'vimeo': 'vimeo'
        }
        
        for social in socials:
            social_type = social.get('type', '').lower()
            if social_type:
                normalized_type = social_mapping.get(social_type, social_type)
                if normalized_type not in social_tags:
                    social_tags.append(normalized_type)
        
        return social_tags

    def _normalize_tags(self, tags):
        """Normalise et déduplique une liste de tags"""
        normalized_tags = []
        for tag in tags:
            normalized = self._normalize_tag(tag)
            if normalized and normalized not in normalized_tags:
                normalized_tags.append(normalized)
        return normalized_tags

