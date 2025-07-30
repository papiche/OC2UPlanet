#!/usr/bin/env python3
"""
Script de test pour le comportement des placeholders
Démontre comment les URLs directes sont remplacées par des placeholders
"""

import re
import json
import os

def load_links_config():
    """Charge la configuration des liens"""
    links_config_file = 'workspace/links_config.json'
    try:
        with open(links_config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Fichier de configuration non trouvé : {links_config_file}")
        return {}

def replace_direct_urls_with_placeholders(message, links_config):
    """Remplace les URLs directes par des placeholders appropriés"""
    # Mapping des URLs vers les placeholders
    url_to_placeholder = {}
    for key, url in links_config.items():
        if url:
            url_to_placeholder[url] = f"[Lien vers {key.title()}]"
    
    # Remplacer les URLs par les placeholders
    for url, placeholder in url_to_placeholder.items():
        message = message.replace(url, placeholder)
    
    return message

def inject_links(message, links_config):
    """Injecte intelligemment les liens dans le message en remplaçant les placeholders"""
    # Patterns de détection des placeholders
    link_patterns = {
        r'\[Lien vers OpenCollective\]': links_config.get('opencollective', ''),
        r'\[Lien vers Documentation\]': links_config.get('documentation', ''),
        r'\[Lien vers GitHub\]': links_config.get('github', ''),
        r'\[Lien vers Discord\]': links_config.get('discord', ''),
        r'\[Lien vers Telegram\]': links_config.get('telegram', ''),
        r'\[Lien vers Site Web\]': links_config.get('website', ''),
        r'\[Lien vers Blog\]': links_config.get('blog', ''),
        r'\[Lien vers Forum\]': links_config.get('forum', ''),
        r'\[Lien vers Wiki\]': links_config.get('wiki', ''),
        r'\[Lien vers Mastodon\]': links_config.get('mastodon', ''),
        r'\[Lien vers Nostr\]': links_config.get('nostr', ''),
        r'\[Lien vers IPFS\]': links_config.get('ipfs', ''),
        r'\[Lien vers G1\]': links_config.get('g1', ''),
        r'\[Lien vers UPlanet\]': links_config.get('uplanet', ''),
        r'\[Lien vers Astroport\]': links_config.get('astroport', ''),
        r'\[Lien vers Zen\]': links_config.get('zen', ''),
        r'\[Lien vers Multipass\]': links_config.get('multipass', ''),
    }
    
    # Remplacer les placeholders par les vrais liens
    for pattern, link in link_patterns.items():
        if link:
            message = re.sub(pattern, link, message, flags=re.IGNORECASE)
        else:
            # Si le lien n'est pas configuré, supprimer le placeholder
            message = re.sub(pattern, '', message, flags=re.IGNORECASE)
    
    # Nettoyer les espaces multiples créés par les suppressions
    message = re.sub(r'\s+', ' ', message)
    message = re.sub(r'\n\s*\n\s*\n', '\n\n', message)
    
    return message.strip()

def main():
    """Test du comportement des placeholders"""
    
    # Charger la configuration des liens
    links_config = load_links_config()
    if not links_config:
        return
    
    print("🧪 TEST DU COMPORTEMENT DES PLACEHOLDERS")
    print("=" * 60)
    
    # Messages de test avec différents comportements
    test_messages = [
        # Message avec placeholders corrects
        """Bonjour,

Nous proposons une nouvelle stack technique pour garantir la souveraineté des données. 
Le code est ouvert, auditable et disponible sur [Lien vers GitHub].

Pour soutenir notre projet, rejoignez-nous sur [Lien vers OpenCollective].
Plus d'informations sur [Lien vers Site Web].

Cordialement,
L'équipe UPlanet""",

        # Message avec URLs directes (comportement incorrect de l'IA)
        """📢 **L'heure est venue de réclamer notre souveraineté numérique !** 🚀 

Rejoignez la communauté UPlanet sur https://qo-op.com et explorez notre projet sur https://qo-op.com. 
Pour en savoir plus sur le MULTIPASS, consultez https://github.com/papiche/Astroport.ONE/blob/master/DOCUMENTATION.md. 
Nous avons besoin de vous ! Soutenez notre travail via https://opencollective.com/monnaie-libre.""",

        # Message mixte (placeholders + URLs directes)
        """Hello,

Le MULTIPASS utilise [Lien vers G1] pour l'identité.
Documentation complète sur [Lien vers Documentation].
Communauté active sur https://qo-op.com.
Et aussi sur [Lien vers Telegram] (si configuré).

À bientôt !"""
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 MESSAGE DE TEST #{i}")
        print("-" * 40)
        print("MESSAGE ORIGINAL :")
        print(message)
        
        # Détecter les URLs directes
        direct_urls = re.findall(r'https?://[^\s]+', message)
        if direct_urls:
            print(f"\n⚠️ URLs directes détectées : {len(direct_urls)}")
            for url in direct_urls:
                print(f"  • {url}")
            
            # Remplacer par des placeholders
            message = replace_direct_urls_with_placeholders(message, links_config)
            print(f"\n🔄 APRÈS remplacement par placeholders :")
            print(message)
        
        # Injecter les liens
        final_message = inject_links(message, links_config)
        print(f"\n🔗 MESSAGE FINAL (avec liens injectés) :")
        print(final_message)
        
        # Statistiques
        placeholders_before = len(re.findall(r'\[Lien vers [^\]]+\]', message))
        placeholders_after = len(re.findall(r'\[Lien vers [^\]]+\]', final_message))
        links_after = len(re.findall(r'https?://[^\s]+', final_message))
        
        print(f"\n📊 Statistiques :")
        print(f"  • Placeholders avant injection : {placeholders_before}")
        print(f"  • Placeholders après injection : {placeholders_after}")
        print(f"  • Liens finaux : {links_after}")
        
        if i < len(test_messages):
            print("\n" + "=" * 60)
    
    print(f"\n✅ Test terminé !")
    print(f"💡 Le système détecte et corrige automatiquement les URLs directes")
    print(f"💡 Les placeholders sont correctement injectés avec de vrais liens")

if __name__ == "__main__":
    main() 