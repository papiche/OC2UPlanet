#!/usr/bin/env python3
"""
Script de test pour la synchronisation des thèmes
Démontre comment les thèmes de l'Agent Analyste sont synchronisés avec les banques
"""

import json
import os
import sys

def load_banks_config():
    """Charge la configuration des banques"""
    config_file = 'AstroBot/workspace/memory_banks_config.json'
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Fichier de configuration non trouvé : {config_file}")
        return None

def get_available_themes():
    """Simule la récupération des thèmes depuis l'Agent Analyste"""
    # Thèmes simulés basés sur l'analyse des prospects
    simulated_themes = [
        "technologie", "developpeur", "crypto", "logiciel-libre", "g1",
        "innovation", "digital", "monnaie", "blockchain", "decentralisation",
        "souverainete", "local", "partage", "transition", "ecologie",
        "collectif", "entraide", "communautaire", "liberte", "humain",
        "creatif", "savoir-faire", "artisanat", "creation", "artiste",
        "artisan", "musique", "produits-naturels", "fermentation",
        "spiritualite", "nature", "permaculture", "bien-etre", "therapeute",
        "spirituel", "holistique", "sain", "naturel", "personnel",
        "transformation", "accompagnement"
    ]
    return sorted(simulated_themes)

def show_bank_themes_details(bank, slot):
    """Affiche les détails des thèmes d'une banque"""
    print(f"\n{'='*60}")
    print(f"BANQUE #{slot} - DÉTAILS DES THÈMES")
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
    available_themes = get_available_themes()
    if available_themes:
        print(f"📋 Thèmes disponibles ({len(available_themes)}) : {', '.join(available_themes[:10])}{'...' if len(available_themes) > 10 else ''}")
    
    print(f"{'='*60}")

def sync_themes_from_analyst(banks_config):
    """Synchronise les thèmes identifiés par l'Agent Analyste"""
    print("\n🔄 SYNCHRONISATION DES THÈMES")
    print("-" * 40)
    
    # Récupérer les thèmes disponibles depuis l'analyse
    available_themes = get_available_themes()
    
    if not available_themes:
        print("❌ Aucun thème disponible depuis l'Agent Analyste")
        return banks_config
    
    print(f"📋 Thèmes identifiés par l'Agent Analyste ({len(available_themes)}) :")
    for i, theme in enumerate(available_themes, 1):
        print(f"  {i:2d}. {theme}")
    
    # Mettre à jour la liste des thèmes disponibles dans la configuration
    banks_config['available_themes'] = available_themes
    
    print(f"\n✅ {len(available_themes)} thèmes synchronisés")
    print("💡 Vous pouvez maintenant associer ces thèmes aux banques")
    
    return banks_config

def main():
    """Test de la synchronisation des thèmes"""
    print("🧪 TEST DE LA SYNCHRONISATION DES THÈMES")
    print("=" * 60)
    
    # Charger la configuration des banques
    banks_config = load_banks_config()
    if not banks_config:
        return
    
    print(f"✅ Configuration des banques chargée")
    print(f"📊 Nombre de banques : {len(banks_config.get('banks', {}))}")
    
    # Afficher l'état actuel des thèmes
    print(f"\n📋 ÉTAT ACTUEL DES THÈMES :")
    print("-" * 40)
    
    for slot, bank in banks_config['banks'].items():
        if bank.get('name'):
            current_themes = bank.get('themes', [])
            print(f"Banque #{slot} ({bank['name']}) : {len(current_themes)} thèmes")
            if current_themes:
                print(f"  → {', '.join(current_themes)}")
    
    # Synchroniser les thèmes
    banks_config = sync_themes_from_analyst(banks_config)
    
    # Afficher les détails d'une banque spécifique
    print(f"\n🔍 DÉTAILS D'UNE BANQUE :")
    print("-" * 40)
    
    # Trouver une banque avec des thèmes
    for slot, bank in banks_config['banks'].items():
        if bank.get('name') and bank.get('themes'):
            show_bank_themes_details(bank, slot)
            break
    else:
        # Si aucune banque n'a de thèmes, afficher la première
        for slot, bank in banks_config['banks'].items():
            if bank.get('name'):
                show_bank_themes_details(bank, slot)
                break
    
    print(f"\n✅ Test terminé !")
    print(f"💡 Les thèmes sont maintenant synchronisés avec l'Agent Analyste")

if __name__ == "__main__":
    main() 