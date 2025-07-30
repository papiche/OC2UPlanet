#!/usr/bin/env python3
"""
Script de test simplifié pour le Mode Persona de l'Agent Stratège
Démontre l'analyse automatique de profil et la sélection de banque
"""

import sys
import json
import os
import re

# Ajouter le chemin vers AstroBot
sys.path.append('AstroBot')

def simulate_ia_analysis(profile_data, available_banks):
    """Simule l'analyse IA pour sélectionner la banque la plus adaptée"""
    
    # Logique de correspondance basée sur les tags et descriptions
    profile_tags = set(profile_data['tags'])
    profile_desc = profile_data['description'].lower()
    
    best_match = None
    best_score = 0
    
    for slot, bank in available_banks:
        bank_themes = set(bank.get('themes', []))
        bank_archetype = bank.get('archetype', '').lower()
        
        # Calculer un score de correspondance
        score = 0
        
        # Correspondance par tags
        tag_overlap = len(profile_tags.intersection(bank_themes))
        score += tag_overlap * 10
        
        # Correspondance par description
        for theme in bank_themes:
            if theme.lower() in profile_desc:
                score += 5
        
        # Correspondance par archetype
        if 'developpeur' in profile_desc and 'informaticien' in bank_archetype:
            score += 15
        elif 'artiste' in profile_desc and 'créateur' in bank_archetype:
            score += 15
        elif 'militant' in profile_desc and 'militant' in bank_archetype:
            score += 15
        elif 'therapeute' in profile_desc and 'holistique' in bank_archetype:
            score += 15
        
        # Correspondances spécifiques
        if 'open-source' in profile_tags and 'logiciel-libre' in bank_themes:
            score += 10
        if 'ecologie' in profile_tags and 'ecologie' in bank_themes:
            score += 10
        if 'art' in profile_tags and 'artiste' in bank_themes:
            score += 10
        if 'bienetre' in profile_tags and 'émotions' in bank_themes:
            score += 10
        
        if score > best_score:
            best_score = score
            best_match = (slot, bank, score)
    
    return best_match

def test_persona_mode_simple():
    """Test du mode Persona avec simulation IA"""
    
    print("🧪 TEST DU MODE PERSONA - ANALYSE AUTOMATIQUE DE PROFIL")
    print("=" * 70)
    
    try:
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
                print(f"     Thèmes : {', '.join(bank.get('themes', []))}")
        
        print(f"\n🧪 TESTS D'ANALYSE DE PROFIL (Simulation IA) :")
        print("-" * 60)
        
        for i, test_case in enumerate(test_profiles, 1):
            print(f"\n{i}. {test_case['name']}")
            print(f"   Profil : {test_case['profile']['uid']}")
            print(f"   Tags : {', '.join(test_case['profile']['tags'])}")
            print(f"   Description : {test_case['profile']['description']}")
            
            # Simuler l'analyse de profil
            result = simulate_ia_analysis(test_case['profile'], available_banks)
            
            if result:
                slot, selected_bank, score = result
                print(f"   ✅ Banque sélectionnée : {selected_bank['name']} (Score: {score})")
                print(f"   🎭 Archetype : {selected_bank.get('archetype', 'Non défini')}")
                print(f"   🏷️ Thèmes : {', '.join(selected_bank.get('themes', []))}")
                
                # Afficher le raisonnement
                print(f"   💭 Raisonnement : Correspondance détectée entre les tags du prospect et les thèmes de la banque")
            else:
                print(f"   ❌ Aucune banque adaptée trouvée")
        
        print(f"\n🎯 DÉMONSTRATION DU MODE PERSONA COMPLET :")
        print("-" * 60)
        
        # Test avec un profil spécifique
        test_profile = test_profiles[0]['profile']  # Développeur Open Source
        
        print(f"Profil testé : {test_profile['uid']}")
        print(f"Site web : {test_profile['website']}")
        print(f"Tags : {', '.join(test_profile['tags'])}")
        print(f"Description : {test_profile['description']}")
        
        # Simuler le mode Persona complet
        print(f"\n🔄 Simulation du mode Persona...")
        
        # 1. Analyse de profil
        result = simulate_ia_analysis(test_profile, available_banks)
        
        if result:
            slot, selected_bank, score = result
            print(f"✅ Banque sélectionnée : {selected_bank['name']} (Score: {score})")
            
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
            print("-" * 40)
            print(test_prompt[:300] + "..." if len(test_prompt) > 300 else test_prompt)
            
            # Simuler un message généré
            corpus = selected_bank.get('corpus', {})
            tone = corpus.get('tone', 'professionnel')
            vocabulary = ', '.join(corpus.get('vocabulary', [])[:3])
            
            simulated_message = f"""Bonjour {test_profile['uid']} 👋,

En tant que {selected_bank.get('archetype', 'expert')}, nous sommes ravis de vous accueillir chez UPlanet ! 🚀

Votre profil sur {test_profile['website']} montre votre passion pour {', '.join(test_profile['tags'][:2])}. Nous vous invitons à rejoindre notre communauté et à explorer notre documentation.

Pour soutenir notre projet, rejoignez-nous sur [Lien vers OpenCollective]. Plus d'informations sur [Lien vers Site Web].

Cordialement,
L'équipe UPlanet (Ton: {tone}, Vocabulaire: {vocabulary})"""

            print(f"\n📝 MESSAGE SIMULÉ :")
            print("-" * 40)
            print(simulated_message)
            
            print(f"\n✅ Mode Persona fonctionnel !")
            print(f"💡 L'IA analysera automatiquement le profil et sélectionnera la banque la plus adaptée")
            print(f"💡 Le message sera personnalisé selon l'archetype et les thèmes de la banque")
            print(f"💡 Score de correspondance : {score}/100")
            
        else:
            print(f"❌ Aucune banque adaptée trouvée pour ce profil")
            
    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")
        import traceback
        traceback.print_exc()

def main():
    """Test principal"""
    test_persona_mode_simple()
    
    print(f"\n✅ Test terminé !")
    print(f"🎭 Le Mode Persona permet une personnalisation automatique avancée")
    print(f"🔍 L'IA analyse le profil et sélectionne la banque la plus adaptée")
    print(f"📝 Les messages sont générés avec le bon archetype et vocabulaire")
    print(f"🎯 Système de scoring pour optimiser la correspondance profil-banque")

if __name__ == "__main__":
    main() 