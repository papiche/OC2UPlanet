# 🚀 AstroBot - Guide Complet

> **📚 Documentation associée :**
> - [📋 Résumé du Mode Persona](MODE_PERSONA_SUMMARY.md) - Fonctionnalités avancées de personnalisation
> - [🎯 Guide Marketing](../MARKETING.md) - Stratégies de prospection dans les bases Ğ1 & ğchange
> - [📊 Résumé du Système](../SUMMARY.md) - Architecture du système de prospection unifié

## Vue d'ensemble

AstroBot est un système d'agents IA spécialisé dans la gestion de campagnes de communication pour UPlanet. Il combine analyse intelligente, rédaction contextuelle et gestion multicanal pour optimiser vos campagnes marketing.

## 🆕 Nouvelles Fonctionnalités (v2.0)

### 🎭 Création Automatique de Personas
- **Génération IA** de personas basés sur les thèmes réels de la communauté
- **Détection intelligente** du niveau d'analyse (alerte si < 10% des profils analysés)
- **Analyse automatique** si données insuffisantes
- **Banques 5-9** automatiquement remplies avec des personas représentatifs

### 🔗 Injection Automatique de Liens
- **Placeholders intelligents** : `[Lien vers OpenCollective]` → liens fonctionnels
- **Configuration centralisée** des liens externes
- **Méthode classique améliorée** avec injection de liens
- **Choix de banque de contexte** même en mode classique

### 🎯 Sélection Automatique de Personas
- **Matching intelligent** entre thèmes des cibles et personas disponibles
- **Fallback intelligent** vers la méthode classique si aucun persona approprié
- **Personnalisation contextuelle** selon les centres d'intérêt détectés

## 🏗️ Architecture

### Les 3 Agents Principaux

#### 1. 🤖 Agent Analyste
- **Rôle** : Analyse et segmentation des prospects
- **Fonctionnalités** :
  - Analyse géo-linguistique des profils
  - Classification thématique (compétences, intérêts)
  - Clustering intelligent des cibles
  - Base de connaissance persistante
  - **🎭 Création automatique de personas** basés sur les thèmes détectés
  - **🔍 Détection intelligente** du niveau d'analyse
  - **🔄 Analyse automatique** si données insuffisantes
- **Sortie** : Cibles qualifiées et segmentées + Personas automatiques

#### 2. 🎭 Agent Stratège
- **Rôle** : Rédaction de messages personnalisés
- **Fonctionnalités** :
  - Banques de mémoire thématiques (12 personnalités)
  - **🎯 Trois modes de rédaction** : Persona, Auto, Classique
  - **🔗 Injection automatique de liens** (OpenCollective, Discord, etc.)
  - **🎭 Choix de banque de contexte** même en mode classique
  - Intégration du contexte web (Perplexica)
  - **🔄 Méthode classique améliorée** avec injection de liens
  - Génération de messages ultra-ciblés
- **Sortie** : Messages de campagne optimisés avec liens fonctionnels

#### 3. 📡 Agent Opérateur
- **Rôle** : Exécution multicanal et suivi
- **Fonctionnalités** :
  - Envoi via Jaklis (Cesium+), Mailjet, Nostr DM
  - Mémoire contextuelle des interactions
  - Réponses automatiques intelligentes
  - Gestion des opt-out
- **Sortie** : Campagnes exécutées et suivies

## 🎯 Fonctionnalités Avancées

### Banques de Mémoire Thématiques

Chaque banque représente une "personnalité" spécialisée :

| Banque | Archétype | Thèmes Cibles | Ton | Type |
|--------|-----------|---------------|-----|------|
| #0 | Bâtisseur/Technicien | technologie, developpeur, crypto | Pragmatique, précis | Manuel |
| #1 | Philosophe/Militant | souverainete, transition, ecologie | Engagé, visionnaire | Manuel |
| #2 | Créateur/Artisan | creatif, savoir-faire, artisanat | Concret, valorisant | Manuel |
| #3 | Holistique/Thérapeute | spiritualite, nature, bien-etre | Inspirant, bienveillant | Manuel |
| #4 | [Personnalisé] | [Thèmes personnalisés] | [Ton personnalisé] | Manuel |
| **#5** | **🎭 Auto-généré** | **Top thème #1** | **Adaptatif** | **Automatique** |
| **#6** | **🎭 Auto-généré** | **Top thème #2** | **Adaptatif** | **Automatique** |
| **#7** | **🎭 Auto-généré** | **Top thème #3** | **Adaptatif** | **Automatique** |
| **#8** | **🎭 Auto-généré** | **Top thème #4** | **Adaptatif** | **Automatique** |
| **#9** | **🎭 Auto-généré** | **Top thème #5** | **Adaptatif** | **Automatique** |

**Banques 5-9** : Personas automatiquement générés basés sur les thèmes les plus fréquents détectés dans la communauté.

### Mémoire Contextuelle

- **12 slots de mémoire** (0-11) pour organiser les conversations
- **Historique automatique** des interactions par cible
- **Réponses automatiques** basées sur les mots-clés
- **Détection intelligente** des réponses nécessitant une intervention

## 🚀 Guide d'Utilisation

### Installation et Configuration

1. **Prérequis**
   ```bash
   # Vérifier que les scripts externes sont accessibles
   ls ~/.zen/Astroport.ONE/IA/question.py
   ls ~/.zen/Astroport.ONE/IA/ollama.me.sh
   ls ~/.zen/Astroport.ONE/tools/jaklis/jaklis.py
   ```

2. **Configuration initiale**
   ```bash
   cd OC2UPlanet/AstroBot
   python3 main.py
   ```

3. **Configuration du portefeuille Trésor**
   - Le système détecte automatiquement le portefeuille `$UPLANETNAME_G1` de la UPlanet à laquelle est raccordée votre Astroport
   - Vérifiez que `~/.zen/Astroport.ONE/tools/keygen` est accessible

### Workflow Type

#### Étape 1 : Analyse des Prospects
```bash
# Lancer AstroBot
python3 main.py

# 1. Lancer l'Agent Analyste
> 1

# Sous-menu Analyste :
# 1. Analyse Géo-Linguistique (langue, pays, région)
# 2. Analyse par Thèmes (compétences, intérêts)
# 3. Campagne à partir d'un Thème
# 4. Mode Test (cible unique)
# 5. 🎭 Créer des personas basés sur les thèmes détectés (banques 5-9)

# 2. Choisir l'analyse par thèmes
> 2

# 3. Sélectionner un cluster de cibles
> [numéro du cluster]
```

#### Étape 2 : Création Automatique de Personas (Recommandé)
```bash
# 5. 🎭 Créer des personas basés sur les thèmes détectés (banques 5-9)
> 5

# Le système détecte automatiquement le niveau d'analyse :
# 📊 Profils analysés : 5 / 8269
# ⚠️ Seulement 5 profils analysés sur 8269 (0.1%)
# ⚠️ L'analyse thématique semble incomplète.
# Voulez-vous lancer l'analyse thématique complète maintenant ? (o/n) : o

# 🔄 Lancement de l'analyse thématique complète...
# 📊 Profils analysés après analyse complète : 8269 / 8269

# 🎯 Top 5 des thèmes détectés :
# 1. developpeur (1247 occurrences)
# 2. technologie (892 occurrences)
# 3. crypto (756 occurrences)
# 4. open-source (634 occurrences)
# 5. blockchain (523 occurrences)

# 🎉 Création automatique terminée ! 5 personas créés dans les banques 5-9.
```

#### Étape 3 : Configuration Manuelle des Banques (Optionnel)
```bash
# 4. Gérer les Banques de Mémoire Thématiques
> 4

# 1. Créer/Configurer une banque
> 1

# Choisir la banque #0 (Bâtisseur)
> 0

# Remplir le corpus avec :
# - Vocabulaire : protocole, infrastructure, décentralisation...
# - Arguments : Le MULTIPASS est une implémentation...
# - Ton : pragmatique, précis, direct
# - Exemples : Nous proposons une nouvelle stack...
```

#### Étape 4 : Rédaction du Message
```bash
# 2. Lancer l'Agent Stratège
> 2

# Le système propose trois modes :

# 🎯 MODE DE RÉDACTION DU MESSAGE
# 1. Mode Persona : Analyse automatique du profil et sélection de banque
# 2. Mode Auto : Sélection automatique basée sur les thèmes
# 3. Mode Classique : Choix manuel de la banque

# Mode 1 : Mode Persona (recommandé pour personnalisation maximale)
> 1

# 🔍 Mode Persona : Analyse du profil du prospect...
# 🎯 Correspondance détectée : Ingénieur/Technicien (Score: 25)
# 🎭 Archetype sélectionné : L'Informaticien
# ✅ Message de campagne rédigé et sauvegardé

# Mode 2 : Mode Auto avec choix de contexte
> 2

# Mode 3 : Méthode classique avec choix de contexte
> 3

# 🎭 CHOIX DE LA BANQUE DE CONTEXTE
# 0. Le Codeur Libre (L'Architecte Numérique)
# 1. Le Technologue (L'Innovateur Digital)
# 2. Le Cryptophile (L'Explorateur Blockchain)
# 3. L'Open-Sourcer (Le Collaborateur Libre)
# 4. Le Blockchainiste (L'Architecte Décentralisé)
# 5. Aucune banque (méthode classique pure)
# Choisissez une banque (0-4) ou 5 pour aucune : 0

# 🔗 Injection automatique de liens :
# [Lien vers OpenCollective] → https://opencollective.com/monnaie-libre
# [Lien vers Discord] → https://ipfs.copylaradio.com/ipns/copylaradio.com/bang.html
# [Lien vers Documentation] → https://github.com/papiche/Astroport.ONE/blob/master/DOCUMENTATION.md
```

**🆕 Nouveauté v2.1 : Personnalisation par Cible**

Le système génère maintenant **un message personnalisé pour chaque cible** :

- **Analyse individuelle** : Chaque profil est analysé séparément
- **Sélection de banque adaptée** : La banque la plus appropriée est choisie pour chaque cible
- **Contexte web enrichi** : Recherche Perplexica pour chaque cible ayant un site web
- **Messages sauvegardés** : 
  - `workspace/personalized_messages.json` : Tous les messages personnalisés
  - `workspace/message_to_send.txt` : Premier message (compatibilité)

**Exemple de sortie :**
```
🎯 Génération du message personnalisé pour la cible 1/5 : Cobart31
🎭 Mode Persona : Banque sélectionnée automatiquement : Le Codeur Libre
✅ Message personnalisé généré pour Cobart31

🎯 Génération du message personnalisé pour la cible 2/5 : AliceDev
🎭 Mode Persona : Banque sélectionnée automatiquement : L'Innovateur Digital
✅ Message personnalisé généré pour AliceDev

...

✅ 5 messages personnalisés générés et sauvegardés. Prêt pour validation par l'Opérateur.
```

#### Étape 5 : Envoi de la Campagne
```bash
# 3. Lancer l'Agent Opérateur
> 3

# Choisir le canal d'envoi :
# 1. Jaklis (Cesium+) - Recommandé
# 2. Mailjet (Email)
# 3. Nostr (DM pour MULTIPASS)

# Valider l'envoi
> oui
```

#### Étape 6 : Suivi des Interactions
```bash
# 5. Gérer les Interactions de l'Opérateur
> 5

# 1. Voir l'historique des interactions
> 1

# 2. Traiter une réponse reçue
> 2
```

## 📊 Gestion des Données

### Fichiers de Configuration

- `workspace/memory_banks_config.json` : Configuration des banques de mémoire (manuelles + auto-générées)
- `workspace/enriched_prospects.json` : Base de connaissance des prospects (analyse persistante)
- `workspace/todays_targets.json` : Cibles du jour
- `workspace/message_to_send.txt` : Premier message généré (compatibilité)
- `workspace/personalized_messages.json` : **🆕 Tous les messages personnalisés par cible**
- `workspace/links_config.json` : Configuration des liens externes (OpenCollective, Discord, etc.)
- `~/.zen/tmp/astrobot.log` : Logs détaillés du système

### Structure des Données

#### Prospect Enrichi
```json
{
  "pubkey": "7YschDTUmy13KZQzrDzNkvDE43RzK6JtUqPvSuiqoqZi",
  "uid": "Cobart31",
  "profile": {
    "_source": {
      "description": "Développeur passionné par les technologies décentralisées..."
    }
  },
  "metadata": {
    "language": "fr",
    "country": "France",
    "region": "Île-de-France",
    "tags": ["developpeur", "crypto", "technologie"],
    "analysis_date": "2025-07-30T19:36:16"
  }
}
```

#### Interaction Opérateur
```json
{
  "target_pubkey": "7YschDTUmy13KZQzrDzNkvDE43RzK6JtUqPvSuiqoqZi",
  "target_uid": "Cobart31",
  "message_sent": "Bonjour Cobart31...",
  "response_received": "Merci, c'est intéressant...",
  "timestamp": "2025-07-30T12:00:00Z",
  "slot": 0
}
```

#### Messages Personnalisés (🆕 v2.1)
```json
[
  {
    "target": {
      "pubkey": "7YschDTUmy13KZQzrDzNkvDE43RzK6JtUqPvSuiqoqZi",
      "uid": "Cobart31",
      "metadata": {
        "tags": ["developpeur", "crypto", "technologie"]
      }
    },
    "message": "Bonjour Cobart31, en tant que développeur passionné par les technologies décentralisées...",
    "mode": "persona"
  },
  {
    "target": {
      "pubkey": "8ZtchEVVmy24LZQzrEzOkvEF54SzL7KtVqQvTvjvppqZj",
      "uid": "AliceDev",
      "metadata": {
        "tags": ["art", "creativite", "design"]
      }
    },
    "message": "Salut AliceDev, ton approche créative et ton sens du design...",
    "mode": "persona"
  }
]
```

## 🎨 Personnalisation Avancée

### 🎭 Création Automatique de Personas (Recommandé)

#### Méthode 1 : Génération Automatique
```bash
# 1. Lancer l'Agent Analyste
> 1

# 2. Choisir la création automatique
> 5

# 3. Le système détecte et propose d'améliorer l'analyse si nécessaire
# 4. Génération automatique des personas dans les banques 5-9
```

#### Avantages de la Génération Automatique
- **🎯 Représentativité** : Basé sur les thèmes réels de la communauté
- **⚡ Rapidité** : Génération en quelques minutes
- **🔄 Adaptation** : S'adapte à l'évolution de la communauté
- **📊 Données réelles** : Utilise les occurrences réelles des thèmes

### Création Manuelle d'une Banque de Mémoire

1. **Accéder au gestionnaire**
   ```bash
   > 4  # Gérer les Banques de Mémoire
   ```

2. **Configurer la banque**
   ```bash
   > 1  # Créer/Configurer
   > [numéro de banque]  # 0-3, pour banques personnelles, 4 (vide), 5-9 banques automatiques Persona
   ```

3. **Définir l'archétype**
   - Nom : "Votre Personnalité"
   - Description : "Voix pour [type de cible]"
   - Archétype : "Le [Nom de l'Archétype]"

4. **Associer les thèmes**
   ```bash
   > 2  # Associer des thèmes
   > [numéro de banque]
   > [numéros des thèmes séparés par des virgules]
   ```

5. **Remplir le corpus**
   ```bash
   > 3  # Remplir le corpus
   > [numéro de banque]
   ```

### 🔗 Configuration des Liens Externes

Le système gère automatiquement l'injection de liens dans les messages :

#### Liens Configurés par Défaut
- **OpenCollective** : `https://opencollective.com/monnaie-libre`
- **Discord** : `https://ipfs.copylaradio.com/ipns/copylaradio.com/bang.html`
- **Documentation** : `https://github.com/papiche/Astroport.ONE/blob/master/DOCUMENTATION.md`
- **GitHub** : `https://github.com/papiche/Astroport.ONE`
- **Site Web** : `https://copylaradio.com`
- **Blog** : `https://www.copylaradio.com/blog/blog-1`

#### Personnalisation des Liens
```bash
# Dans le gestionnaire des banques de mémoire
> 4  # Gérer les Banques de Mémoire
> 4  # Configurer les liens externes
```

### Configuration des Réponses Automatiques

Le système détecte automatiquement les réponses à traiter :

**Réponses automatiques** (mots-clés positifs) :
- merci, thanks, intéressant, intéressé, oui, yes, ok
- plus d'info, comment, où, quand, combien, participer

**Intervention manuelle** (mots-clés négatifs) :
- non, no, pas intéressé, stop, arrêter
- problème, erreur, plainte, insatisfait

## 🔧 Dépannage

### Problèmes Courants

#### 1. Erreur "Script introuvable"
```bash
# Vérifier les chemins dans main.py
ls ~/.zen/Astroport.ONE/IA/question.py
ls ~/.zen/Astroport.ONE/IA/ollama.me.sh
```

#### 2. Erreur JSON dans l'analyse
```bash
# Supprimer et régénérer la base de connaissance
rm workspace/enriched_prospects.json
# Relancer l'analyse
```

#### 3. Erreur d'authentification Jaklis
```bash
# Vérifier la variable d'environnement
echo $CAPTAINEMAIL
# Vérifier le nœud Cesium
cat ~/.zen/Astroport.ONE/tools/my.sh
```

#### 4. Pas de GPU détecté
```bash
# Normal : ollama.me.sh utilise un serveur GPU de votre constellation
# Vérifier la connexion
~/.zen/Astroport.ONE/IA/ollama.me.sh
```

#### 5. 🎭 Personas avec occurrences faibles
```bash
# Problème : Thèmes avec 1 occurrence chacun
# Solution : Le système détecte automatiquement et propose l'analyse complète
# Choisir 'o' quand proposé pour lancer l'analyse thématique complète
```

#### 6. 🔗 Placeholders non remplacés dans les messages
```bash
# Problème : [URL_OPEN_COLLECTIVE] au lieu de lien fonctionnel
# Solution : Vérifier que links_config.json existe et est configuré
# Le système injecte automatiquement les liens dans tous les modes
```

### Logs et Debug

- **Log principal** : `~/.zen/tmp/astrobot.log`
- **Mode DEBUG** : Activé par défaut pour voir les appels d'outils
- **Logs IA** : Réponses brutes dans les logs DEBUG

## 📈 Optimisation des Campagnes

### Stratégies par Archétype

#### Bâtisseur/Technicien (Banque #0)
- **Focus** : Aspects techniques, protocoles, robustesse
- **Mots-clés** : infrastructure, décentralisation, open-source
- **Call-to-action** : Rejoindre le développement

#### Philosophe/Militant (Banque #1)
- **Focus** : Impact sociétal, bien commun, alternatives
- **Mots-clés** : souveraineté, coopération, écosystème
- **Call-to-action** : Participer au mouvement

#### Créateur/Artisan (Banque #2)
- **Focus** : Valorisation, autonomie, savoir-faire
- **Mots-clés** : création de valeur, circuit court, atelier
- **Call-to-action** : Rejoindre la communauté créative

#### Holistique/Thérapeute (Banque #3)
- **Focus** : Harmonie, bien-être, connexion
- **Mots-clés** : équilibre, conscience, régénération
- **Call-to-action** : Rejoindre une communauté bienveillante

#### 🎭 Personas Auto-générés (Banques #5-9)
- **Focus** : Adaptatif selon les thèmes détectés dans la communauté
- **Mots-clés** : Spécifiques aux thèmes les plus fréquents
- **Call-to-action** : Personnalisé selon l'archétype généré
- **Exemple** : "Le Codeur Libre" pour le thème "developpeur" (1247 occurrences)

### Métriques de Succès

1. **Taux de réponse** : % de cibles qui répondent
2. **Qualité des réponses** : % de réponses positives
3. **Conversion** : % qui rejoignent OpenCollective
4. **Engagement** : % qui demandent plus d'informations

## 🔮 Évolutions Futures

### Fonctionnalités Prévues

1. **Interface Web** : Dashboard pour visualiser les campagnes
2. **A/B Testing** : Comparaison de différentes approches
3. **Intégration CRM** : Synchronisation avec d'autres outils
4. **Analytics Avancés** : Métriques détaillées et prédictions
5. **Personnalisation Dynamique** : Adaptation en temps réel
6. **🎭 Personas Individuels** : Personas spécifiques par prospect
7. **🔄 Apprentissage Continu** : Amélioration automatique des personas
8. **📊 A/B Testing de Personas** : Comparaison d'efficacité des archétypes

### Extensions Possibles

1. **Support Multilingue** : Traduction automatique des messages
2. **Intégration Social Media** : Mastodon, Twitter, LinkedIn
3. **Gamification** : Système de points et récompenses
4. **IA Conversationnelle** : Chatbot pour les réponses complexes

## 📞 Support

### Ressources

- **Documentation technique** : Ce guide
- **Logs système** : `~/.zen/tmp/astrobot.log`
- **Configuration** : `workspace/memory_banks_config.json`
- **Base de données** : `workspace/enriched_prospects.json`

### Commandes Utiles

```bash
# Vérifier l'état du système
tail -f ~/.zen/tmp/astrobot.log

# Sauvegarder la configuration
cp workspace/memory_banks_config.json backup/

# Analyser les performances
grep "✅" ~/.zen/tmp/astrobot.log | wc -l

# Vérifier les erreurs
grep "❌" ~/.zen/tmp/astrobot.log

# 🎭 Vérifier les personas auto-générés
cat workspace/memory_banks_config.json | jq '.banks | keys[] as $k | "Banque \($k): \(.[$k].name) (\(.[$k].archetype))"'

# 📊 Vérifier le niveau d'analyse
cat workspace/enriched_prospects.json | jq 'to_entries | map(select(.value.metadata.tags)) | length'

# 🔗 Vérifier la configuration des liens
cat workspace/links_config.json | jq 'keys[] as $k | "\($k): \(.[$k])"'
```

---

**AstroBot** - Transformez vos prospects en bâtisseurs d'UPlanet ! 🚀 