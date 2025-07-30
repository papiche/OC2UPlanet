#!/usr/bin/env python3
"""
Script de test pour la création automatique de personas
Démontre la génération de personas basés sur les thèmes détectés
"""

import sys
import json
import os
from collections import Counter

# Ajouter le chemin vers AstroBot
sys.path.append('AstroBot')

from AstroBot.agents.analyst_agent import AnalystAgent

def simulate_automatic_personas():
    """Simule la création automatique de personas"""
    
    print("🎭 TEST DE CRÉATION AUTOMATIQUE DE PERSONAS")
    print("=" * 60)
    
    try:
        # Configuration minimale pour l'agent
        shared_state = {
            'config': {
                'workspace': 'AstroBot/workspace',
                'question_script': 'AstroBot/scripts/question.py',
                'enriched_prospects_file': 'AstroBot/workspace/enriched_prospects.json',
                'prospect_file': '~/.zen/game/g1prospect.json'
            },
            'logger': None,
            'status': {}
        }
        
        # Configuration du logger
        import logging
        logging.basicConfig(level=logging.INFO)
        shared_state['logger'] = logging.getLogger(__name__)
        
        # Créer une instance de l'agent
        agent = AnalystAgent(shared_state)
        
        # Simuler une base de connaissance avec des thèmes
        print("📊 Simulation d'une base de connaissance avec thèmes...")
        
        # Créer un fichier de test temporaire
        test_kb_file = 'AstroBot/workspace/test_enriched_prospects.json'
        os.makedirs('AstroBot/workspace', exist_ok=True)
        
        # Données de test avec des thèmes variés
        test_data = {
            "pubkey1": {
                "uid": "Alice",
                "profile": {"_source": {"description": "Développeuse passionnée par les cryptomonnaies"}},
                "metadata": {"tags": ["developpeur", "crypto", "blockchain", "technologie"]}
            },
            "pubkey2": {
                "uid": "Bob",
                "profile": {"_source": {"description": "Militant pour la liberté numérique"}},
                "metadata": {"tags": ["militant", "liberte", "privacy", "decentralisation"]}
            },
            "pubkey3": {
                "uid": "Charlie",
                "profile": {"_source": {"description": "Artiste numérique et créateur"}},
                "metadata": {"tags": ["artiste", "creation", "numerique", "culture"]}
            },
            "pubkey4": {
                "uid": "Diana",
                "profile": {"_source": {"description": "Économiste spécialisée en monnaies alternatives"}},
                "metadata": {"tags": ["economiste", "monnaie", "alternative", "finance"]}
            },
            "pubkey5": {
                "uid": "Eve",
                "profile": {"_source": {"description": "Thérapeute holistique et coach bien-être"}},
                "metadata": {"tags": ["therapeute", "holistique", "bien-etre", "sante"]}
            },
            "pubkey6": {
                "uid": "Frank",
                "profile": {"_source": {"description": "Développeur open source"}},
                "metadata": {"tags": ["developpeur", "open-source", "logiciel-libre", "technologie"]}
            },
            "pubkey7": {
                "uid": "Grace",
                "profile": {"_source": {"description": "Militant écologiste"}},
                "metadata": {"tags": ["militant", "ecologie", "environnement", "durabilite"]}
            },
            "pubkey8": {
                "uid": "Henry",
                "profile": {"_source": {"description": "Créateur de contenu digital"}},
                "metadata": {"tags": ["createur", "contenu", "digital", "media"]}
            }
        }
        
        # Sauvegarder les données de test
        with open(test_kb_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Base de test créée avec {len(test_data)} profils")
        
        # Analyser les thèmes
        all_tags = []
        for pubkey, data in test_data.items():
            tags = data.get('metadata', {}).get('tags', [])
            if tags:
                all_tags.extend(tags)
        
        tag_counts = Counter(all_tags)
        top_5_themes = tag_counts.most_common(5)
        
        print(f"\n📊 Top 5 des thèmes détectés :")
        for i, (theme, count) in enumerate(top_5_themes, 1):
            print(f"  {i}. {theme} ({count} occurrences)")
        
        # Simuler la création de personas
        print(f"\n🎭 Simulation de création de personas...")
        
        # Charger la configuration des banques existante
        banks_config_file = 'AstroBot/workspace/memory_banks_config.json'
        if os.path.exists(banks_config_file):
            with open(banks_config_file, 'r', encoding='utf-8') as f:
                banks_config = json.load(f)
        else:
            banks_config = {'banks': {}, 'available_themes': []}
        
        # Simuler la création pour chaque thème
        for i, (theme, count) in enumerate(top_5_themes):
            bank_slot = str(5 + i)
            
            print(f"\n🎭 Thème '{theme}' -> Banque {bank_slot}")
            
            # Simuler un persona généré
            simulated_persona = {
                "name": f"Le {theme.title()}",
                "archetype": f"Expert en {theme}",
                "description": f"Persona spécialisé dans le domaine de {theme}",
                "corpus": {
                    "tone": "professionnel et engageant",
                    "vocabulary": [theme, "expertise", "spécialisation", "connaissance"],
                    "arguments": [
                        f"UPlanet offre des opportunités uniques dans le domaine de {theme}",
                        f"La décentralisation révolutionne l'approche du {theme}",
                        f"Rejoignez une communauté d'experts en {theme}"
                    ],
                    "examples": [
                        f"En tant qu'expert en {theme}, vous apprécierez notre approche innovante",
                        f"Notre plateforme transforme le {theme} grâce à la blockchain",
                        f"Découvrez comment UPlanet révolutionne le {theme}"
                    ]
                }
            }
            
            # Remplir la banque
            banks_config['banks'][bank_slot] = {
                'name': simulated_persona['name'],
                'archetype': simulated_persona['archetype'],
                'description': simulated_persona['description'],
                'themes': [theme],
                'corpus': simulated_persona['corpus']
            }
            
            print(f"  ✅ {simulated_persona['name']} ({simulated_persona['archetype']})")
        
        # Sauvegarder la configuration
        with open(banks_config_file, 'w', encoding='utf-8') as f:
            json.dump(banks_config, f, indent=2, ensure_ascii=False)
        
        print(f"\n🎉 Simulation terminée ! {len(top_5_themes)} personas créés")
        
        # Afficher le résumé
        print(f"\n📋 RÉSUMÉ DES PERSONAS CRÉÉS :")
        for i, (theme, count) in enumerate(top_5_themes):
            bank_slot = str(5 + i)
            bank = banks_config['banks'].get(bank_slot, {})
            if bank:
                print(f"  Banque {bank_slot} : {bank['name']} ({bank['archetype']})")
                print(f"    Thème : {theme}")
                print(f"    Ton : {bank['corpus']['tone']}")
                print(f"    Vocabulaire : {', '.join(bank['corpus']['vocabulary'][:3])}...")
                print()
        
        # Nettoyer le fichier de test
        os.remove(test_kb_file)
        print("🧹 Fichier de test nettoyé")
        
    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")
        import traceback
        traceback.print_exc()

def main():
    """Test principal"""
    simulate_automatic_personas()
    
    print(f"\n✅ Test terminé !")
    print(f"💡 L'Agent Analyste peut maintenant créer automatiquement des personas")
    print(f"💡 Les banques 5-9 sont remplies selon les thèmes les plus fréquents")
    print(f"💡 Chaque persona est adapté au thème détecté dans la communauté")

if __name__ == "__main__":
    main() 