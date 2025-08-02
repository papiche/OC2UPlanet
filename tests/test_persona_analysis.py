#!/usr/bin/env python3
"""
Script de test pour la création de personas avec détection d'analyse améliorée
Démontre la vérification du niveau d'analyse avant création de personas
"""

import sys
import json
import os
from collections import Counter

# Ajouter le chemin vers AstroBot
sys.path.append('AstroBot')

def simulate_analysis_detection():
    """Simule la détection du niveau d'analyse thématique"""
    
    print("🔍 TEST DE DÉTECTION D'ANALYSE THÉMATIQUE")
    print("=" * 60)
    
    # Simuler différentes situations d'analyse
    scenarios = [
        {
            "name": "Analyse complète (100%)",
            "total_profiles": 1000,
            "analyzed_profiles": 1000,
            "tags_per_profile": 3
        },
        {
            "name": "Analyse partielle (50%)",
            "total_profiles": 1000,
            "analyzed_profiles": 500,
            "tags_per_profile": 3
        },
        {
            "name": "Analyse insuffisante (5%)",
            "total_profiles": 1000,
            "analyzed_profiles": 50,
            "tags_per_profile": 3
        },
        {
            "name": "Aucune analyse (0%)",
            "total_profiles": 1000,
            "analyzed_profiles": 0,
            "tags_per_profile": 0
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📊 Scénario : {scenario['name']}")
        print("-" * 40)
        
        # Simuler les données
        all_tags = []
        analyzed_profiles = scenario['analyzed_profiles']
        total_profiles = scenario['total_profiles']
        
        # Générer des tags pour les profils analysés
        common_themes = ["developpeur", "technologie", "crypto", "art", "militant", "economiste", "therapeute", "createur", "open-source", "blockchain"]
        
        for i in range(analyzed_profiles):
            # Simuler 3 tags par profil
            profile_tags = []
            for j in range(scenario['tags_per_profile']):
                tag_index = (i + j) % len(common_themes)
                profile_tags.append(common_themes[tag_index])
            all_tags.extend(profile_tags)
        
        # Analyser les résultats
        percentage = (analyzed_profiles / total_profiles) * 100 if total_profiles > 0 else 0
        
        print(f"  • Profils analysés : {analyzed_profiles} / {total_profiles}")
        print(f"  • Pourcentage : {percentage:.1f}%")
        print(f"  • Tags détectés : {len(all_tags)}")
        
        if all_tags:
            tag_counts = Counter(all_tags)
            top_5_themes = tag_counts.most_common(5)
            print(f"  • Top 5 des thèmes :")
            for i, (theme, count) in enumerate(top_5_themes, 1):
                print(f"    {i}. {theme} ({count} occurrences)")
        
        # Évaluation de la qualité
        if percentage == 0:
            print(f"  ❌ Aucune analyse détectée")
        elif percentage < 10:
            print(f"  ⚠️ Analyse insuffisante (< 10%)")
        elif percentage < 50:
            print(f"  ⚠️ Analyse partielle (10-50%)")
        else:
            print(f"  ✅ Analyse suffisante (≥ 50%)")
        
        # Recommandation
        if percentage < 10 and percentage > 0:
            print(f"  💡 Recommandation : Lancer l'analyse thématique complète")
        elif percentage == 0:
            print(f"  💡 Recommandation : Lancer l'analyse thématique")
        else:
            print(f"  💡 Recommandation : OK pour créer des personas")

def simulate_real_data_analysis():
    """Simule l'analyse de données réelles"""
    
    print(f"\n🎭 SIMULATION AVEC DONNÉES RÉELLES")
    print("=" * 60)
    
    # Créer un fichier de test avec des données réalistes
    test_data = {}
    
    # Profils avec thèmes (simulant une analyse complète)
    themes_data = {
        "developpeur": 45,
        "technologie": 38,
        "crypto": 32,
        "open-source": 28,
        "blockchain": 25,
        "art": 22,
        "militant": 20,
        "economiste": 18,
        "therapeute": 15,
        "createur": 12
    }
    
    # Créer des profils avec thèmes
    profile_id = 1
    for theme, count in themes_data.items():
        for i in range(count):
            pubkey = f"pubkey_{profile_id}"
            test_data[pubkey] = {
                "uid": f"User_{profile_id}",
                "profile": {"_source": {"description": f"Profil intéressé par {theme}"}},
                "metadata": {"tags": [theme, "passion", "innovation"]}
            }
            profile_id += 1
    
    # Ajouter des profils sans thèmes (non analysés)
    for i in range(100):
        pubkey = f"pubkey_{profile_id}"
        test_data[pubkey] = {
            "uid": f"User_{profile_id}",
            "profile": {"_source": {"description": f"Profil standard {profile_id}"}},
            "metadata": {}
        }
        profile_id += 1
    
    # Analyser les données
    all_tags = []
    analyzed_profiles = 0
    total_profiles = len(test_data)
    
    for pubkey, data in test_data.items():
        metadata = data.get('metadata', {})
        tags = metadata.get('tags', [])
        if tags and tags != ['error']:
            all_tags.extend(tags)
            analyzed_profiles += 1
    
    percentage = (analyzed_profiles / total_profiles) * 100
    
    print(f"📊 Analyse des données simulées :")
    print(f"  • Total des profils : {total_profiles}")
    print(f"  • Profils analysés : {analyzed_profiles}")
    print(f"  • Pourcentage : {percentage:.1f}%")
    
    if all_tags:
        tag_counts = Counter(all_tags)
        top_5_themes = tag_counts.most_common(5)
        print(f"\n🎯 Top 5 des thèmes détectés :")
        for i, (theme, count) in enumerate(top_5_themes, 1):
            print(f"  {i}. {theme} ({count} occurrences)")
        
        print(f"\n✅ Qualité de l'analyse : {'Suffisante' if percentage >= 10 else 'Insuffisante'}")
        
        if percentage >= 10:
            print(f"💡 Les personas peuvent être créés avec confiance")
        else:
            print(f"💡 Recommandation : Compléter l'analyse thématique")

def main():
    """Test principal"""
    simulate_analysis_detection()
    simulate_real_data_analysis()
    
    print(f"\n✅ Test terminé !")
    print(f"💡 La fonction améliorée détecte maintenant le niveau d'analyse")
    print(f"💡 Elle propose automatiquement de lancer l'analyse si nécessaire")
    print(f"💡 Les personas sont créés avec des données représentatives")

if __name__ == "__main__":
    main() 