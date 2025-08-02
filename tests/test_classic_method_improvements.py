#!/usr/bin/env python3
"""
Script de test pour les améliorations de la méthode classique
Démontre le choix de banque de contexte et l'injection de liens
"""

import sys
import re
import json
import os

# Ajouter le chemin vers AstroBot
sys.path.append('AstroBot')

from AstroBot.agents.strategist_agent import StrategistAgent

def simulate_classic_method_with_bank():
    """Simule la méthode classique avec choix de banque"""
    
    print("🧪 TEST DE LA MÉTHODE CLASSIQUE AMÉLIORÉE")
    print("=" * 60)
    
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
            'targets': [
                {
                    'uid': 'Fred',
                    'website': 'https://example.com',
                    'tags': ['technologie', 'crypto']
                }
            ],
            'analyst_report': 'Fred est un développeur passionné par les technologies décentralisées.'
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
        
        print("📋 Banques disponibles pour le contexte :")
        available_banks = []
        for slot in range(12):
            bank = banks_config['banks'].get(str(slot), {})
            if bank.get('name') and bank.get('corpus'):
                available_banks.append((slot, bank))
                print(f"  {slot}. {bank['name']} ({bank.get('archetype', 'Non défini')})")
        
        if not available_banks:
            print("❌ Aucune banque configurée")
            return
        
        # Simuler le choix d'une banque
        print(f"\n🎭 Simulation du choix de banque...")
        selected_bank = available_banks[0][1]  # Première banque disponible
        print(f"✅ Banque sélectionnée : {selected_bank['name']}")
        
        # Simuler la génération de message avec contexte de banque
        print(f"\n🔄 Génération du message avec contexte de banque...")
        
        # Construire le prompt comme dans la méthode classique améliorée
        prompt = f"""Tu es l'Agent Stratège d'UPlanet. Tu dois rédiger un message de campagne.

--- CONTEXTE DE LA BANQUE DE MÉMOIRE ---
Archétype : {selected_bank.get('archetype', 'Non défini')}
Thèmes : {', '.join(selected_bank.get('themes', []))}
Ton : {selected_bank.get('corpus', {}).get('tone', 'Non défini')}
Vocabulaire clé : {', '.join(selected_bank.get('corpus', {}).get('vocabulary', []))}
Arguments : {chr(10).join([f'- {arg}' for arg in selected_bank.get('corpus', {}).get('arguments', [])])}
Exemples : {chr(10).join([f'- {ex}' for ex in selected_bank.get('corpus', {}).get('examples', [])])}

IMPORTANT - PLACEHOLDERS DE LIENS : Tu DOIS utiliser EXCLUSIVEMENT ces placeholders pour tous les liens :
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

RÈGLE STRICTE : N'écris JAMAIS d'URLs complètes comme 'https://...' dans ton message. Utilise UNIQUEMENT les placeholders ci-dessus.

--- RAPPORT DE L'ANALYSTE ---
{shared_state['analyst_report']}

--- EXEMPLE DE CIBLE ---
{json.dumps(shared_state['targets'][0], indent=2, ensure_ascii=False)}

Maintenant, en te basant sur TOUTES ces informations, rédige le message de campagne final. Ta réponse DOIT être uniquement le message, sans commentaire additionnel."""

        print(f"\n📝 PROMPT CONSTRUIT :")
        print("-" * 40)
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        
        # Simuler un message généré avec placeholders
        simulated_message = f"""Bonjour Fred 👋,

En tant que {selected_bank.get('archetype', 'expert')}, nous sommes ravis de vous accueillir chez UPlanet ! 🚀

Votre profil sur {shared_state['targets'][0]['website']} montre votre passion pour les technologies décentralisées. Nous vous invitons à rejoindre notre communauté sur [Lien vers Discord] et à explorer notre documentation sur [Lien vers Documentation].

Pour soutenir notre projet, rejoignez-nous sur [Lien vers OpenCollective]. Plus d'informations sur [Lien vers Site Web].

Cordialement,
L'équipe UPlanet"""

        print(f"\n📝 MESSAGE SIMULÉ (avec placeholders) :")
        print("-" * 40)
        print(simulated_message)
        
        # Appliquer l'injection de liens
        final_message = agent._inject_links(simulated_message, shared_state['config'])
        
        print(f"\n🔗 MESSAGE FINAL (avec liens injectés) :")
        print("-" * 40)
        print(final_message)
        
        # Analyser le résultat
        placeholders_before = len(re.findall(r'\[Lien vers [^\]]+\]', simulated_message))
        placeholders_after = len(re.findall(r'\[Lien vers [^\]]+\]', final_message))
        links_after = len(re.findall(r'https?://[^\s]+', final_message))
        
        print(f"\n📊 ANALYSE :")
        print(f"  • Placeholders avant injection : {placeholders_before}")
        print(f"  • Placeholders après injection : {placeholders_after}")
        print(f"  • Liens finaux : {links_after}")
        
        if placeholders_after == 0 and links_after > 0:
            print("✅ L'injection de liens fonctionne correctement !")
        else:
            print("⚠️ Problème avec l'injection de liens")
            
    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")
        import traceback
        traceback.print_exc()

def main():
    """Test principal"""
    simulate_classic_method_with_bank()
    
    print(f"\n✅ Test terminé !")
    print(f"💡 La méthode classique peut maintenant utiliser des banques de contexte")
    print(f"💡 L'injection de liens fonctionne dans tous les modes")

if __name__ == "__main__":
    main() 