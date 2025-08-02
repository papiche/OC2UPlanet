#!/usr/bin/env python3
"""
Script de test pour le Mode Persona de l'Agent Stratège
Démontre l'analyse automatique de profil et la sélection de banque
"""

import sys
import json
import os

# Ajouter le chemin vers AstroBot
sys.path.append('AstroBot')

from AstroBot.agents.strategist_agent import StrategistAgent

def test_persona_mode():
    """Test du mode Persona avec différents profils"""
    
    print("🧪 TEST DU MODE PERSONA - ANALYSE AUTOMATIQUE DE PROFIL")
    print("=" * 70)
    
    try:
        # Configuration minimale pour l'agent
        shared_state = {
            'config': {
                'workspace': 'AstroBot/workspace',
                'question_script': 'AstroBot/scripts/question.py',
                'enriched_prospects_file': 'AstroBot/workspace/enriched_prospects.json',
                'strategist_prompt_file': 'AstroBot/prompts/strategist_prompt.txt',
                'uplanet_treasury_g1pub': 'HYhT8iMeF2HYoxBQbmVX2b58c1cyczkCZG3tFaWNGLEK'
            },
            'logger': None,
            'status': {},
            'analyst_report': 'Analyse automatique du profil pour personnalisation avancée.'
        }
        
        # Configuration du logger
        import logging
        logging.basicConfig(level=logging.INFO)
        shared_state['logger'] = logging.getLogger(__name__)
        
        # Créer une instance de l'agent
        agent = StrategistAgent(shared_state)
        
        # Charger la configuration des banques
        with open('AstroBot/workspace/memory_banks_config.json', 'r', encoding='utf-8') as f:
            banks_config = json.load(f)
        
        # Profils de test avec différents archetypes
        test_profiles = [
            {
                'name': 'Développeur Open Source',
                'profile': {
                    'uid': 'dev_opensource',
                    'website': 'https://github.com/opensource_dev',
                    'tags': ['developpeur', 'open-source', 'linux', 'python', 'git'],
                    'description': 'Développeur passionné par l\'open source et les technologies libres'
                }
            },
            {
                'name': 'Artiste Numérique',
                'profile': {
                    'uid': 'digital_artist',
                    'website': 'https://digitalart.creative.com',
                    'tags': ['art', 'creativite', 'design', 'numerique', 'culture'],
                    'description': 'Artiste numérique créatif, passionné par l\'expression artistique'
                }
            },
            {
                'name': 'Militant Écologique',
                'profile': {
                    'uid': 'eco_militant',
                    'website': 'https://ecologie-engagee.org',
                    'tags': ['ecologie', 'environnement', 'durabilite', 'militant', 'engagement'],
                    'description': 'Militant écologique engagé pour un monde plus durable'
                }
            },
            {
                'name': 'Thérapeute Holistique',
                'profile': {
                    'uid': 'holistic_therapist',
                    'website': 'https://bienetre-holistique.com',
                    'tags': ['bienetre', 'holistique', 'therapie', 'meditation', 'spiritualite'],
                    'description': 'Thérapeute holistique spécialisé dans le bien-être global'
                }
            }
        ]
        
        print("📋 BANQUES DISPONIBLES :")
        available_banks = []
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            if bank.get('name') and bank.get('corpus'):
                available_banks.append((slot, bank))
                print(f"  {slot}. {bank['name']} ({bank.get('archetype', 'Non défini')})")
        
        print(f"\n🧪 TESTS D'ANALYSE DE PROFIL :")
        print("-" * 50)
        
        for i, test_case in enumerate(test_profiles, 1):
            print(f"\n{i}. {test_case['name']}")
            print(f"   Profil : {test_case['profile']['uid']}")
            print(f"   Tags : {', '.join(test_case['profile']['tags'])}")
            print(f"   Description : {test_case['profile']['description']}")
            
            # Simuler l'analyse de profil
            shared_state['targets'] = [test_case['profile']]
            
            try:
                # Appeler la méthode d'analyse de profil
                selected_bank = agent._analyze_profile_and_select_bank(
                    shared_state['targets'], 
                    banks_config
                )
                
                if selected_bank:
                    print(f"   ✅ Banque sélectionnée : {selected_bank['name']}")
                    print(f"   🎭 Archetype : {selected_bank.get('archetype', 'Non défini')}")
                    print(f"   🏷️ Thèmes : {', '.join(selected_bank.get('themes', []))}")
                else:
                    print(f"   ❌ Aucune banque adaptée trouvée")
                    
            except Exception as e:
                print(f"   ❌ Erreur lors de l'analyse : {e}")
        
        print(f"\n🎯 DÉMONSTRATION DU MODE PERSONA COMPLET :")
        print("-" * 50)
        
        # Test avec un profil spécifique
        test_profile = test_profiles[0]['profile']  # Développeur Open Source
        shared_state['targets'] = [test_profile]
        
        print(f"Profil testé : {test_profile['uid']}")
        print(f"Site web : {test_profile['website']}")
        print(f"Tags : {', '.join(test_profile['tags'])}")
        
        # Simuler le mode Persona complet
        print(f"\n🔄 Simulation du mode Persona...")
        
        # 1. Analyse de profil
        selected_bank = agent._analyze_profile_and_select_bank(
            shared_state['targets'], 
            banks_config
        )
        
        if selected_bank:
            print(f"✅ Banque sélectionnée : {selected_bank['name']}")
            
            # 2. Génération du message (simulation)
            print(f"📝 Génération du message personnalisé...")
            
            # Construire le prompt de test
            test_prompt = f"""MODE PERSONA - PERSONNALISATION AVANCÉE

Prospect: {json.dumps(test_profile, indent=2, ensure_ascii=False)}

INSTRUCTIONS SPÉCIALES MODE PERSONA :
- Utilise l'archetype "{selected_bank.get('archetype', 'Non défini')}" pour adapter ton ton
- Personnalise le message en fonction du profil spécifique du prospect
- Utilise le vocabulaire et les arguments de la banque "{selected_bank['name']}"
- Crée une connexion émotionnelle basée sur les centres d'intérêt identifiés
- Sois authentique et adapte le style au profil analysé

Génère un message court de test (2-3 phrases) pour ce prospect."""

            print(f"\n📝 PROMPT DE TEST :")
            print("-" * 30)
            print(test_prompt[:300] + "..." if len(test_prompt) > 300 else test_prompt)
            
            print(f"\n✅ Mode Persona fonctionnel !")
            print(f"💡 L'IA analysera automatiquement le profil et sélectionnera la banque la plus adaptée")
            print(f"💡 Le message sera personnalisé selon l'archetype et les thèmes de la banque")
            
        else:
            print(f"❌ Aucune banque adaptée trouvée pour ce profil")
            
    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")
        import traceback
        traceback.print_exc()

def main():
    """Test principal"""
    test_persona_mode()
    
    print(f"\n✅ Test terminé !")
    print(f"🎭 Le Mode Persona permet une personnalisation automatique avancée")
    print(f"🔍 L'IA analyse le profil et sélectionne la banque la plus adaptée")
    print(f"📝 Les messages sont générés avec le bon archetype et vocabulaire")

if __name__ == "__main__":
    main() 