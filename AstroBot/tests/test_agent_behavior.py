#!/usr/bin/env python3
"""
Script de test pour vérifier le comportement de l'agent avec les nouvelles instructions
"""

import sys
import re
import json
import os
import logging

# Ajouter le chemin vers AstroBot
sys.path.append('AstroBot')

from AstroBot.agents.strategist_agent import StrategistAgent

def main():
    """Test du comportement de l'agent"""
    
    print("🧪 TEST DU COMPORTEMENT DE L'AGENT")
    print("=" * 60)
    
    try:
        # Configuration du logger
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        # Configuration minimale pour l'agent
        shared_state = {
            'config': {
                'workspace': 'AstroBot/workspace',
                'question_script': 'AstroBot/scripts/question.py',
                'enriched_prospects_file': 'AstroBot/workspace/enriched_prospects.json'
            },
            'logger': logger,
            'status': {}
        }
        
        # Créer une instance de l'agent
        agent = StrategistAgent(shared_state)
        
        # Charger la configuration des banques
        with open('AstroBot/workspace/memory_banks_config.json', 'r', encoding='utf-8') as f:
            banks_config = json.load(f)
        
        # Tester la banque #1
        bank_1 = banks_config['banks']['1']
        print(f"📝 Test de la banque : {bank_1['name']}")
        print(f"🎭 Archétype : {bank_1['archetype']}")
        
        # Générer un message
        print("\n🔄 Génération du message...")
        message = agent._generate_message_with_bank(bank_1, 'test')
        
        print("\n" + "=" * 50)
        print("MESSAGE GÉNÉRÉ :")
        print("=" * 50)
        print(message)
        print("=" * 50)
        
        # Analyser le message
        placeholders = len(re.findall(r'\[Lien vers [^\]]+\]', message))
        urls = len(re.findall(r'https?://[^\s]+', message))
        
        print(f"\n📊 ANALYSE DU MESSAGE :")
        print(f"  • Placeholders détectés : {placeholders}")
        print(f"  • URLs directes : {urls}")
        
        if urls > 0:
            print("⚠️ L'agent a encore utilisé des URLs directes !")
            print("💡 Le système de correction devrait les remplacer automatiquement")
        else:
            print("✅ L'agent utilise correctement les placeholders !")
        
        # Vérifier si le système de correction a fonctionné
        if placeholders > 0:
            print("✅ Le système de placeholders fonctionne")
        else:
            print("❌ Aucun placeholder détecté")
            
    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 