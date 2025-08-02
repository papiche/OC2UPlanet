#!/usr/bin/env python3
"""
Script de test pour le système d'injection de liens
Démontre comment les placeholders sont remplacés par de vrais liens
"""

import re
import json
import os

def inject_links(message, config):
    """Injecte intelligemment les liens dans le message en remplaçant les placeholders"""
    links_config = config.get('links', {})
    
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
    """Test du système d'injection de liens"""
    
    # Charger la configuration depuis le fichier
    links_config_file = 'workspace/links_config.json'
    
    try:
        with open(links_config_file, 'r', encoding='utf-8') as f:
            test_config = {'links': json.load(f)}
        print(f"✅ Configuration chargée depuis {links_config_file}")
    except FileNotFoundError:
        print(f"❌ Fichier de configuration non trouvé : {links_config_file}")
        print("💡 Création d'une configuration de test...")
        test_config = {
            'links': {
                'opencollective': 'https://opencollective.com/monnaie-libre',
                'github': 'https://github.com/papiche/Astroport.ONE',
                'discord': 'https://qo-op.com',
                'website': 'https://uplanet.org',
                'documentation': 'https://github.com/papiche/Astroport.ONE/blob/master/DOCUMENTATION.md',
                'g1': 'https://monnaie-libre.fr/',
                'nostr': 'https://fr.wikipedia.org/wiki/Nostr',
                'ipfs': 'https://fr.wikipedia.org/wiki/InterPlanetary_File_System',
                # Les autres liens ne sont pas configurés pour démontrer la suppression
            }
        }
    
    # Messages de test avec différents placeholders
    test_messages = [
        # Message avec placeholders configurés
        """Bonjour,

Nous proposons une nouvelle stack technique pour garantir la souveraineté des données. 
Le code est ouvert, auditable et disponible sur [Lien vers GitHub].

Pour soutenir notre projet, rejoignez-nous sur [Lien vers OpenCollective].
Plus d'informations sur [Lien vers Site Web].

Cordialement,
L'équipe UPlanet""",

        # Message avec placeholders non configurés
        """Salut,

Découvrez notre [Lien vers Blog] pour les dernières actualités.
Rejoignez notre [Lien vers Forum] pour discuter.
Consultez notre [Lien vers Wiki] pour la documentation.

Merci !""",

        # Message mixte
        """Hello,

Le MULTIPASS utilise [Lien vers G1] pour l'identité.
Documentation complète sur [Lien vers Documentation].
Communauté active sur [Lien vers Discord].
Et aussi sur [Lien vers Telegram] (si configuré).

À bientôt !"""
    ]
    
    print("🧪 TEST DU SYSTÈME D'INJECTION DE LIENS")
    print("=" * 60)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 MESSAGE DE TEST #{i}")
        print("-" * 40)
        print("AVANT injection :")
        print(message)
        
        print(f"\n🔗 APRÈS injection :")
        result = inject_links(message, test_config)
        print(result)
        
        # Compter les liens
        links_before = len(re.findall(r'\[Lien vers [^\]]+\]', message))
        links_after = len(re.findall(r'https?://[^\s]+', result))
        
        print(f"\n📊 Statistiques :")
        print(f"  • Placeholders détectés : {links_before}")
        print(f"  • Liens injectés : {links_after}")
        
        if i < len(test_messages):
            print("\n" + "=" * 60)
    
    print(f"\n✅ Test terminé !")
    print(f"💡 Les placeholders configurés sont remplacés par de vrais liens")
    print(f"💡 Les placeholders non configurés sont supprimés proprement")

if __name__ == "__main__":
    main() 