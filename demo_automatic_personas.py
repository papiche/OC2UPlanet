#!/usr/bin/env python3
"""
Démonstration de la création automatique de personas avec IA
Utilise l'IA réelle pour générer des personas basés sur les thèmes détectés
"""

import sys
import json
import os
import subprocess

# Ajouter le chemin vers AstroBot
sys.path.append('AstroBot')

def generate_persona_with_ai(theme, theme_count, related_themes):
    """Génère un persona avec l'IA pour un thème donné"""
    
    prompt = f"""Tu es un expert en création de personas marketing. Tu dois créer un persona complet pour une campagne de communication UPlanet.

THÈME PRINCIPAL : {theme}
OCCURRENCES DÉTECTÉES : {theme_count}
THÈMES ASSOCIÉS : {', '.join(related_themes[:10])}

TÂCHE : Créer un persona marketing complet avec :
1. Un nom accrocheur et mémorable
2. Un archétype psychologique précis
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
        # Utiliser le script question.py
        question_script = os.path.expanduser("~/.zen/Astroport.ONE/IA/question.py")
        if not os.path.exists(question_script):
            print(f"❌ Script question.py non trouvé : {question_script}")
            return None
        
        result = subprocess.run(
            ['python3', question_script],
            input=prompt,
            text=True,
            capture_output=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"❌ Erreur lors de l'appel à l'IA : {result.stderr}")
            return None
        
        # Nettoyer la réponse
        response = result.stdout.strip()
        
        # Trouver le JSON dans la réponse
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            print(f"❌ Réponse IA invalide pour {theme}")
            return None
        
        json_str = response[json_start:json_end]
        persona = json.loads(json_str)
        
        # Validation
        required_keys = ['name', 'archetype', 'description', 'corpus']
        corpus_keys = ['tone', 'vocabulary', 'arguments', 'examples']
        
        if not all(key in persona for key in required_keys):
            print(f"❌ Structure du persona invalide pour {theme}")
            return None
            
        if not all(key in persona['corpus'] for key in corpus_keys):
            print(f"❌ Structure du corpus invalide pour {theme}")
            return None
        
        return persona
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération du persona pour {theme} : {e}")
        return None

def demo_automatic_personas():
    """Démonstration de la création automatique de personas"""
    
    print("🎭 DÉMONSTRATION : CRÉATION AUTOMATIQUE DE PERSONAS")
    print("=" * 60)
    
    # Thèmes de démonstration (basés sur des données réelles typiques)
    demo_themes = [
        ("developpeur", 45, ["technologie", "programmation", "open-source", "logiciel-libre", "crypto", "blockchain"]),
        ("militant", 32, ["liberte", "privacy", "decentralisation", "resistance", "alternatives", "engagement"]),
        ("artiste", 28, ["creation", "culture", "numerique", "expression", "innovation", "beaute"]),
        ("economiste", 25, ["monnaie", "finance", "alternative", "economie", "tresor", "echange"]),
        ("therapeute", 18, ["holistique", "bien-etre", "sante", "equilibre", "harmonie", "conscience"])
    ]
    
    print(f"📊 Thèmes de démonstration (basés sur des données réelles) :")
    for i, (theme, count, related) in enumerate(demo_themes, 1):
        print(f"  {i}. {theme} ({count} occurrences)")
    
    # Charger la configuration des banques existante
    banks_config_file = 'AstroBot/workspace/memory_banks_config.json'
    if os.path.exists(banks_config_file):
        with open(banks_config_file, 'r', encoding='utf-8') as f:
            banks_config = json.load(f)
    else:
        banks_config = {'banks': {}, 'available_themes': []}
    
    print(f"\n🎭 Génération des personas avec l'IA...")
    print(f"⏳ Cela peut prendre quelques minutes...")
    
    # Créer les personas pour les banques 5-9
    for i, (theme, count, related_themes) in enumerate(demo_themes):
        bank_slot = str(5 + i)
        
        print(f"\n🎭 Génération du persona pour '{theme}' (banque {bank_slot})...")
        
        # Générer le persona avec l'IA
        persona = generate_persona_with_ai(theme, count, related_themes)
        
        if persona:
            # Remplir la banque
            banks_config['banks'][bank_slot] = {
                'name': persona['name'],
                'archetype': persona['archetype'],
                'description': persona['description'],
                'themes': [theme],
                'corpus': persona['corpus']
            }
            
            print(f"  ✅ {persona['name']} ({persona['archetype']})")
            print(f"     Ton : {persona['corpus']['tone']}")
            print(f"     Vocabulaire : {', '.join(persona['corpus']['vocabulary'][:3])}...")
        else:
            print(f"  ❌ Échec de génération pour '{theme}'")
    
    # Sauvegarder la configuration
    os.makedirs('AstroBot/workspace', exist_ok=True)
    with open(banks_config_file, 'w', encoding='utf-8') as f:
        json.dump(banks_config, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Génération terminée !")
    
    # Afficher le résumé
    print(f"\n📋 RÉSUMÉ DES PERSONAS CRÉÉS :")
    for i, (theme, count, related) in enumerate(demo_themes):
        bank_slot = str(5 + i)
        bank = banks_config['banks'].get(bank_slot, {})
        if bank:
            print(f"\n  🎭 Banque {bank_slot} : {bank['name']}")
            print(f"     Archétype : {bank['archetype']}")
            print(f"     Thème : {theme}")
            print(f"     Ton : {bank['corpus']['tone']}")
            print(f"     Arguments :")
            for arg in bank['corpus']['arguments'][:2]:
                print(f"       • {arg}")
            print(f"     Exemples :")
            for ex in bank['corpus']['examples'][:1]:
                print(f"       • {ex}")

def main():
    """Démonstration principale"""
    demo_automatic_personas()
    
    print(f"\n✅ Démonstration terminée !")
    print(f"💡 Les personas ont été générés avec l'IA réelle")
    print(f"💡 Ils sont maintenant disponibles dans les banques 5-9")
    print(f"💡 Vous pouvez les utiliser dans l'Agent Stratège")

if __name__ == "__main__":
    main() 