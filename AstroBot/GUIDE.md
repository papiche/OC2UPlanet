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

### 🌍 Traduction Automatique des Messages
- **Détection automatique** de la langue du profil depuis la base de connaissance
- **Génération multilingue** : français, anglais, espagnol, allemand, italien, portugais
- **Personnalisation linguistique** : chaque message est écrit dans la langue du prospect
- **Fallback intelligent** : français par défaut si langue non détectée

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
  - **🌍 Génération multilingue** automatique selon la langue du profil
  - **🔗 Injection automatique de liens** (OpenCollective, Discord, etc.)
  - **🎭 Choix de banque de contexte** même en mode classique
  - Intégration du contexte web (Perplexica)
  - **🔄 Méthode classique améliorée** avec injection de liens
  - Génération de messages ultra-ciblés et localisés
- **Sortie** : Messages de campagne optimisés avec liens fonctionnels dans la langue du prospect

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

### 🎯 Système de Slots de Campagnes (0-11)

AstroBot utilise un **système de 12 slots** pour gérer **jusqu'à 12 campagnes en parallèle** de manière organisée et indépendante.

#### **🏗️ Architecture des Slots**

| Slot | Utilisation | État | Campagne |
|------|-------------|------|----------|
| 0-11 | Campagnes actives | Libre/Occupé | Nom automatique |

**Principe de fonctionnement :**
- **12 slots disponibles** : 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
- **Chaque slot = 1 campagne indépendante**
- **Attribution automatique** du premier slot libre
- **Gestion intelligente** de la capacité (12 campagnes max)

#### **🔄 Workflow d'Attribution des Slots**

```
Nouvelle campagne → Recherche slot libre → Attribution automatique → Nommage
```

**Exemple concret :**
```
🎯 SLOT 0: MULTIPASS - FR, ES - France, Spain (Campagne active)
🎯 SLOT 1: Financement - EN - International (Campagne active)
🎯 SLOT 2: [LIBRE - Prêt pour nouvelle campagne]
🎯 SLOT 3: [LIBRE - Prêt pour nouvelle campagne]
...
🎯 SLOT 11: [LIBRE - Prêt pour nouvelle campagne]
```

#### **📊 Noms de Campagnes Automatiques**

Chaque campagne reçoit un **nom descriptif automatique** basé sur :
- **Thèmes détectés** : MULTIPASS, Financement, Communauté, etc.
- **Langues ciblées** : FR, ES, EN, DE, etc.
- **Pays ciblés** : France, Spain, International, etc.

**Exemples de noms générés :**
- `MULTIPASS - FR, ES - France, Spain`
- `Financement - EN - International`
- `Communauté - DE - Germany`
- `design, technique - ES - Spain, Argentina`

#### **📈 Statistiques Détaillées par Slot**

Chaque slot/campagne fournit des **statistiques complètes** :

```
🎯 SLOT 0: MULTIPASS - FR, ES - France, Spain
   📅 Date: 2025-07-31T07:30:00
   🎯 Cibles initiales: 14
   📊 Interactions: 14
   💬 Réponses: 3
   📈 Taux de réponse: 21.4%
   👥 Conversations actives: 3
   📋 Profils ayant répondu:
      • DsEx1pS33v... (2 réponses)
      • 4Fo3AjhHvWJ... (1 réponse)
      • ... et 1 autres
```

#### **🔍 Consultation et Gestion des Slots**

**Menu Opérateur → État des interactions (Option 3) :**

```
📊 ÉTAT DES CAMPAGNES ET INTERACTIONS
============================================================

🎯 SLOT 0: MULTIPASS - FR, ES - France, Spain
   📅 Date: 2025-07-31T07:30:00
   🎯 Cibles initiales: 14
   📊 Interactions: 14
   💬 Réponses: 3
   📈 Taux de réponse: 21.4%
   👥 Conversations actives: 3

🎯 SLOT 1: Financement - EN - International
   📅 Date: 2025-07-31T08:15:00
   🎯 Cibles initiales: 8
   📊 Interactions: 8
   💬 Réponses: 1
   📈 Taux de réponse: 12.5%
   👥 Conversations actives: 1

📈 RÉSUMÉ GLOBAL
   🎯 Campagnes actives: 2
   📊 Total interactions: 22
   💬 Total réponses: 4
   📈 Taux de réponse global: 18.2%

🔍 Options de consultation:
   1. Voir les détails d'une campagne spécifique
   2. Voir l'historique d'un profil spécifique
   3. Retour
```

#### **🎯 Avantages du Système de Slots**

##### **✅ Campagnes Parallèles**
- **12 campagnes simultanées** possibles
- **Pas de conflit** entre les campagnes
- **Suivi indépendant** de chaque campagne
- **Gestion de la capacité** automatique

##### **✅ Attribution Intelligente**
- **Recherche automatique** du premier slot libre
- **Réutilisation** des slots libérés
- **Gestion de la capacité** (12 max)
- **Nommage automatique** descriptif

##### **✅ Organisation Claire**
- **Nom unique** pour chaque campagne
- **Statistiques séparées** par slot
- **Historique isolé** par campagne
- **Consultation détaillée** disponible

##### **✅ Cas d'Usage Typiques**
- **Campagne A** (Slot 0) : MULTIPASS pour développeurs français
- **Campagne B** (Slot 1) : Financement pour anglophones
- **Campagne C** (Slot 2) : Communauté pour germanophones
- **Campagne D** (Slot 3) : Test pour nouveaux prospects

#### **🔄 Gestion Automatique des Slots**

1. **Nouvelle campagne** → Recherche slot libre (0, 1, 2, 3...)
2. **Attribution** → Premier slot disponible
3. **Sauvegarde** → Informations de campagne dans le slot
4. **Suivi** → Statistiques isolées par slot
5. **Libération** → Slot réutilisable après nettoyage

#### **📋 Mémoire Contextuelle par Slot**

- **Historique automatique** des interactions par cible et par slot
- **Réponses automatiques** basées sur les mots-clés
- **Détection intelligente** des réponses nécessitant une intervention
- **Séparation claire** des conversations par campagne

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

# 🚀 INITIALISATION ET ANALYSE :
# 1. 🌍 Analyse Géo-Linguistique (langue, pays, région) - Profils avec GPS uniquement
# 2. 🏷️  Analyse par Thèmes (compétences, intérêts)
# 3. 🎭 Créer des personas basés sur les thèmes détectés (banques 5-9)
# 
# 🔧 RAFFINAGE ET OPTIMISATION :
# 4. 🔄 Optimiser les Thèmes (consolider et nettoyer le Top 50)
# 5. 🧪 Mode Test (cible unique pour validation)
# 
# 🎯 CIBLAGE ET EXPORT :
# 6. 🎯 Ciblage Avancé Multi-Sélection (Thèmes + Filtres)
# 7. 🌍 Cibler par Langue
# 8. 🌍 Cibler par Pays
# 9. 🌍 Cibler par Région
# 10. 📊 Lancer une campagne à partir d'un Thème

# 2. Choisir l'analyse par thèmes
> 2

# 3. Créer des personas automatiquement
> 3

# 4. Optimiser les thèmes (optionnel)
> 4

# 5. Mode test pour validation
> 5

# 6. Ciblage avancé multi-sélection
> 6

**🎯 Options de Ciblage Avancées**

**6. 🎯 Ciblage Avancé Multi-Sélection** : Sélection multiple de thèmes + filtres croisés
- Multi-sélection de thèmes (ex: developpeur + crypto + open-source)
- Filtres croisés par langue, pays, région
- Base de prospects flexible et personnalisée

**7. 🌍 Cibler par Langue** : Sélectionne les prospects selon leur langue détectée
- Français, Anglais, Espagnol, Allemand, Italien, Portugais, etc.
- Idéal pour des campagnes multilingues ciblées

**8. 🌍 Cibler par Pays** : Sélectionne les prospects selon leur localisation géographique
- France, Espagne, Belgique, Portugal, Allemagne, etc.
- Parfait pour des campagnes régionales

**9. 🌍 Cibler par Région** : Sélectionne les prospects selon leur région spécifique
- Île-de-France, Provence-Alpes-Côte d'Azur, Aragon, etc.
- Excellent pour des campagnes hyper-locales

**10. 📊 Cibler par Thème Simple** : Sélectionne les prospects selon un thème unique
- Thèmes individuels (developpeur, crypto, art, etc.)
- Ciblage simple et direct

### **📋 Nouvelle Organisation du Menu : Workflow Logique**

Le menu a été réorganisé pour suivre un **workflow logique et pratique** :

#### **🚀 INITIALISATION ET ANALYSE (Étapes 1-3)**
- **1. 🌍 Analyse Géo-Linguistique** : Détection langue/pays/région
- **2. 🏷️ Analyse par Thèmes** : Extraction des centres d'intérêt
- **3. 🎭 Création de Personas** : Génération automatique des banques 5-9

#### **🔧 RAFFINAGE ET OPTIMISATION (Étapes 4-5)**
- **4. 🔄 Optimisation des Thèmes** : Nettoyage et consolidation
- **5. 🧪 Mode Test** : Validation avec une cible unique

#### **🎯 CIBLAGE ET EXPORT (Étapes 6-10)**
- **6. 🎯 Ciblage Multi-Sélection** : Thèmes + filtres croisés (recommandé)
- **7-9. 🌍 Ciblage Simple** : Par langue, pays, région
- **10. 📊 Ciblage par Thème** : Thème unique
```

**📍 Note sur l'analyse Géo-Linguistique :**
L'analyse géo-linguistique se concentre uniquement sur les profils ayant des coordonnées GPS valides dans leur profil. Cela permet d'obtenir des informations géographiques fiables et réduit le nombre de profils à analyser pour des résultats plus précis.

**🌍 Géocodage GPS pour les régions :**
Le système propose maintenant d'utiliser Nominatim (OpenStreetMap) pour déterminer automatiquement la région depuis les coordonnées GPS. Cette option améliore considérablement la précision des informations géographiques.
```

#### Étape 2 : Création Automatique de Personas (Recommandé)
```bash
# 3. 🎭 Créer des personas basés sur les thèmes détectés (banques 5-9)
> 3

# Le système détecte automatiquement le niveau d'analyse :
# 📊 Profils analysés : 8269 / 8269
# ✅ Analyse complète détectée

# 🎯 Top 5 des thèmes détectés :
# 1. developpeur (1247 occurrences)
# 2. technologie (892 occurrences)
# 3. crypto (756 occurrences)
# 4. open-source (634 occurrences)
# 5. blockchain (523 occurrences)

# 🎉 Création automatique terminée ! 5 personas créés dans les banques 5-9.
```

#### Étape 3 : Optimisation des Thèmes (Recommandé quand la base augmente)
```bash
# 4. 🔄 Optimiser les Thèmes (consolider et nettoyer le Top 50)
> 4

# Le système analyse les thèmes existants :
# 📊 3343 profils analysés trouvés. Consolidation des thèmes...
# 📊 1247 thèmes uniques détectés dans la base.
# 🎯 523 thèmes conservés (≥ 3 occurrences)
# 🗑️ 724 thèmes supprimés (< 3 occurrences)

# --- Thèmes supprimés (trop peu utilisés) ---
#   ❌ reflexologie        ( 2 occurrences) - Profils: KimVenditti, Elouna
#   ❌ ostéopathie         ( 1 occurrences) - Profils: Elouna
#   ...

# 🔄 Nettoyage pour pupucine : ['bon moment', 'nourriture', 'personne', 'social', 'bien-être'] → ['nourriture', 'social']
# ...

# 🔄 Consolidation terminée. 1247 profils nettoyés. Sauvegarde...

# --- Nouveau Top 50 des thèmes après consolidation ---
#  1. developpeur          (1247 occurrences)
#  2. technologie          ( 892 occurrences)
#  3. crypto               ( 756 occurrences)
#  4. open-source          ( 634 occurrences)
#  5. blockchain           ( 523 occurrences)
#  ...
```

#### Étape 4 : Mode Test (Validation)
```bash
# 5. 🧪 Mode Test (cible unique pour validation)
> 5

# 🧪 MODE TEST - SÉLECTION DE LA CIBLE
# ==================================================
# Choisissez une option pour la cible de test :
# 1. 🎯 Utiliser la cible de test par défaut
# 2. 🔑 Spécifier une clé publique (pubkey)
# 3. 👤 Spécifier un identifiant utilisateur (uid)
# 4. 📋 Voir les prospects disponibles

# Exemple avec une pubkey personnalisée :
> 2
# Entrez la clé publique (pubkey) : 7YschDTUmy13KZQzrDzNkvDE43RzK6JtUqPvSuiqoqZi

# Exemple avec un uid personnalisé :
> 3
# Entrez l'identifiant utilisateur (uid) : Cobart31

# Exemple pour voir les prospects disponibles :
> 4
# 📋 PROSPECTS DISPONIBLES POUR LE MODE TEST
# ============================================================
# Affichage des 20 premiers prospects (uid | pubkey | tags)
# ------------------------------------------------------------
#  1. Cobart31              | 7YschDTUmy13KZQzrDzNkvDE43RzK6JtUqPvSuiqoqZi... | developpeur, crypto, technologie
#  2. AliceDev               | 8ZtchEVVmy24LZQzrEzOkvEF54SzL7KtVqQvTvjvppqZj... | art, creativite, design
#  3. CarlosEsp              | 9AtchFWWnz35MZQzrFzPlvFG65TzM8LtWrRwUwkwqqqAk... | blockchain, open-source
# ...

# 🎯 INFORMATIONS DE LA CIBLE SÉLECTIONNÉE
# ==================================================
# 👤 UID : Cobart31
# 🔑 Pubkey : 7YschDTUmy13KZQzrDzNkvDE43RzK6JtUqPvSuiqoqZi
# 🌍 Langue : fr
# 🌍 Pays : France
# 🌍 Région : Île-de-France
# 🏷️  Tags : developpeur, crypto, technologie
# 📝 Description : Développeur passionné par les technologies décentralisées...
# ==================================================

# Permet de tester le système avec une cible spécifique
# Idéal pour valider les personas et les messages avant une campagne complète
```

#### Étape 5 : Ciblage et Export
```bash
# 6. 🎯 Ciblage Avancé Multi-Sélection (Thèmes + Filtres)
> 6

# Permet de créer des cibles personnalisées avec multi-sélection de thèmes
# et filtres croisés par langue, pays, région
```

#### Étape 6 : Configuration Manuelle des Banques (Optionnel)
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

#### Étape 7 : Rédaction du Message
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
🌍 Langue détectée : fr
🎭 Mode Persona : Banque sélectionnée automatiquement : Le Codeur Libre
🌍 Utilisation du contenu multilingue pour fr
✅ Message personnalisé généré pour Cobart31 (français)

🎯 Génération du message personnalisé pour la cible 2/5 : AliceDev
🌍 Langue détectée : en
🎭 Mode Persona : Banque sélectionnée automatiquement : The Free Coder
🌍 Utilisation du contenu multilingue pour en
✅ Message personnalisé généré pour AliceDev (anglais)

🎯 Génération du message personnalisé pour la cible 3/5 : CarlosEsp
🌍 Langue détectée : es
🎭 Mode Persona : Banque sélectionnée automatiquement : El Codificador Libre
🌍 Utilisation du contenu multilingue pour es
✅ Message personnalisé généré pour CarlosEsp (espagnol)

...

✅ 5 messages personnalisés générés et sauvegardés. Prêt pour validation par l'Opérateur.
```

#### Étape 8 : Envoi de la Campagne
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

#### Étape 9 : Suivi des Interactions et Gestion des Slots
```bash
# 5. Gérer les Interactions de l'Opérateur
> 5

# Menu Opérateur simplifié :
# 1. 📤 ENVOYER - Lancer la campagne
# 2. 📥 RECEVOIR - Consulter la messagerie
# 3. 📊 État des interactions
# 4. Retour au menu principal

# 3. Consulter l'état des campagnes et slots
> 3

# Affichage des statistiques par slot :
📊 ÉTAT DES CAMPAGNES ET INTERACTIONS
============================================================

🎯 SLOT 0: MULTIPASS - FR, ES - France, Spain
   📅 Date: 2025-07-31T07:30:00
   🎯 Cibles initiales: 14
   📊 Interactions: 14
   💬 Réponses: 3
   📈 Taux de réponse: 21.4%
   👥 Conversations actives: 3

🎯 SLOT 1: Financement - EN - International
   📅 Date: 2025-07-31T08:15:00
   🎯 Cibles initiales: 8
   📊 Interactions: 8
   💬 Réponses: 1
   📈 Taux de réponse: 12.5%
   👥 Conversations actives: 1

📈 RÉSUMÉ GLOBAL
   🎯 Campagnes actives: 2
   📊 Total interactions: 22
   💬 Total réponses: 4
   📈 Taux de réponse global: 18.2%

🔍 Options de consultation:
   1. Voir les détails d'une campagne spécifique
   2. Voir l'historique d'un profil spécifique
   3. Retour

# 1. Consulter les détails d'une campagne
> 1

# Affichage des campagnes disponibles :
📋 Campagnes disponibles :
   0. MULTIPASS - FR, ES - France, Spain (2025-07-31)
   1. Financement - EN - International (2025-07-31)

# Sélectionner une campagne pour voir les détails
> 0

# Détails complets de la campagne :
🎯 CAMPAGNE : MULTIPASS - FR, ES - France, Spain
============================================================
📅 Date : 2025-07-31T07:30:00
🎯 Cibles initiales : 14
🏷️ Thèmes : developpeur, crypto, technologie
🌍 Langues : fr, es
🌎 Pays : France, Spain

💬 Message : Bonjour [uid], en tant que développeur passionné...

📊 STATISTIQUES DÉTAILLÉES
----------------------------------------
📊 Total interactions : 14
💬 Total réponses : 3
📈 Taux de réponse : 21.4%

👥 CONVERSATIONS ACTIVES (3)
----------------------------------------
   • DsEx1pS33v... (2 réponses, dernière: 2025-07-31)
   • 4Fo3AjhHvWJ... (1 réponse, dernière: 2025-07-31)
   • 9KtchGXXo... (1 réponse, dernière: 2025-07-31)

# 2. Consulter l'historique d'un profil spécifique
> 2

# Entrer la clé publique du profil
Clé publique du profil : DsEx1pS33v...

# Affichage de l'historique complet :
📋 HISTORIQUE DE DsEx1pS33v...
============================================================

🎯 SLOT 0 (3 interactions)
----------------------------------------

📨 Interaction 1:
   📅 Date : 2025-07-31T07:30:00
   📤 Message envoyé : Bonjour Cobart31, en tant que développeur...
   📥 Réponse reçue : Merci, c'est très intéressant...

📨 Interaction 2:
   📅 Date : 2025-07-31T08:15:00
   📤 Message envoyé : Parfait ! Pour en savoir plus sur MULTIPASS...
   📥 Réponse reçue : Comment puis-je participer au développement ?

# 1. Voir l'historique des interactions (ancien menu)
> 1

# 2. Traiter une réponse reçue (ancien menu)
> 2
```

#### **🎯 Gestion des Slots de Campagnes**

**Principe :** Chaque nouvelle campagne est automatiquement assignée au premier slot libre (0-11).

**Exemple de workflow :**
```bash
# Campagne 1 : MULTIPASS pour développeurs français
# → Attribution automatique au SLOT 0
# → Nom : "MULTIPASS - FR - France"

# Campagne 2 : Financement pour anglophones  
# → Attribution automatique au SLOT 1
# → Nom : "Financement - EN - International"

# Campagne 3 : Communauté pour germanophones
# → Attribution automatique au SLOT 2
# → Nom : "Communauté - DE - Germany"

# Résultat : 3 campagnes en parallèle, chacune dans son slot
```

**Avantages :**
- **12 campagnes simultanées** possibles
- **Suivi indépendant** de chaque campagne
- **Statistiques séparées** par slot
- **Pas de conflit** entre les campagnes
- **Réutilisation** des slots libérés

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

### 🌍 Géocodage GPS pour les Régions (Nouveau)

L'analyse géo-linguistique propose maintenant d'utiliser **Nominatim (OpenStreetMap)** pour déterminer automatiquement la région depuis les coordonnées GPS :

### 🌍 Génération Multilingue des Messages (Nouveau)

L'Agent Stratège détecte automatiquement la langue du profil et génère les messages dans la langue appropriée :

### 🎭 Personas Multilingues (Nouveau)

Les personas auto-générés (banques 5-9) sont maintenant créés dans toutes les langues détectées dans la base de connaissance :

#### **Processus de Création**
1. **Détection des langues** : Analyse de `metadata.language` dans la base
2. **Consolidation des variantes** : Fusion des variantes de pays (ex: "Spain" + "Espagne" → "es")
3. **Fallback intelligent** : Utilisation de l'anglais pour les profils non détectés (`language: "xx"`)
4. **Validation stricte GPS** : Filtrage des données invalides (null, none, unknown)
5. **Génération multilingue** : Création du persona dans chaque langue détectée
6. **Adaptation culturelle** : Contenu adapté aux spécificités de chaque culture
7. **Validation complète** : Vérification de la structure pour toutes les langues

#### **Structure des Personas Multilingues**
```json
{
  "name": "Le Codeur Libre",
  "archetype": "L'Architecte Numérique",
  "description": "Développeur passionné par les technologies open-source...",
  "corpus": {
    "tone": "pragmatique, précis, direct",
    "vocabulary": ["protocole", "infrastructure", "décentralisation"],
    "arguments": ["Le MULTIPASS est une implémentation concrète..."],
    "examples": ["En tant que développeur, tu comprends..."]
  },
  "multilingual": {
    "fr": {
      "name": "Le Codeur Libre",
      "archetype": "L'Architecte Numérique",
      "tone": "pragmatique, précis, direct",
      "vocabulary": ["protocole", "infrastructure", "décentralisation"],
      "arguments": ["Le MULTIPASS est une implémentation concrète..."],
      "examples": ["En tant que développeur, tu comprends..."]
    },
    "en": {
      "name": "The Free Coder",
      "archetype": "The Digital Architect",
      "tone": "pragmatic, precise, direct",
      "vocabulary": ["protocol", "infrastructure", "decentralization"],
      "arguments": ["MULTIPASS is a concrete implementation..."],
      "examples": ["As a developer, you understand..."]
    },
    "es": {
      "name": "El Codificador Libre",
      "archetype": "El Arquitecto Digital",
      "tone": "pragmático, preciso, directo",
      "vocabulary": ["protocolo", "infraestructura", "descentralización"],
      "arguments": ["MULTIPASS es una implementación concreta..."],
      "examples": ["Como desarrollador, entiendes..."]
    }
  }
}
```

#### **Avantages des Personas Multilingues**
- **🎯 Précision maximale** : Contenu spécifiquement rédigé pour chaque langue
- **🌍 Authenticité culturelle** : Adapté aux nuances culturelles
- **🔄 Consolidation intelligente** : Fusion automatique des variantes de pays
- **⚡ Performance optimale** : Pas de traduction à la volée
- **🎭 Cohérence du persona** : Même personnalité dans toutes les langues
- **📊 Efficacité marketing** : Messages plus engageants et naturels
- **🌐 Couverture étendue** : Fallback anglais pour les profils non détectés
- **🛡️ Validation stricte** : Filtrage des données GPS invalides (null, none, unknown)

#### **Langues Supportées**
- **Français (fr)** : Langue par défaut
- **Anglais (en)** : Messages en anglais
- **Espagnol (es)** : Mensajes en español
- **Allemand (de)** : Nachrichten auf Deutsch
- **Italien (it)** : Messaggi in italiano
- **Portugais (pt)** : Mensagens em português

#### **Processus de Détection**
1. **Récupération** : Lit la langue depuis `metadata.language` dans la base de connaissance
2. **Validation** : Vérifie que la langue n'est pas 'xx' (non détectée)
3. **Fallback** : Utilise le français si langue non disponible
4. **Génération** : Ajoute l'instruction de langue au prompt IA

#### **Exemple d'Utilisation**
```bash
# L'Agent Stratège détecte automatiquement :
🌍 Langue détectée pour Cobart31 : fr
🌍 Langue détectée pour AliceDev : en
🌍 Langue détectée pour CarlosEsp : es

# Et génère les messages dans la langue appropriée :
✅ Message personnalisé généré pour Cobart31 (français)
✅ Message personnalisé généré pour AliceDev (anglais)
✅ Message personnalisé généré pour CarlosEsp (espagnol)
```

#### **Consolidation des Variantes de Pays**
Le système consolide automatiquement les variantes de noms de pays :

```bash
# Avant consolidation :
🌍 Langues détectées dans la base :
  • fr : 1754 profils (France)
  • es : 266 profils (Espagne)
  • es : 180 profils (Spain)
  • fr : 170 profils (Belgique)
  • fr : 14 profils (Belgium)
  • en : 6 profils (null/xx)

# Après consolidation :
🌍 Langues consolidées dans la base :
  • fr : 1938 profils (France + Belgique + Belgium + ...)
  • es : 446 profils (Espagne + Spain + ...)
  • en : 20 profils (Canada + États-Unis + fallback xx)
  • de : 27 profils (Allemagne + Germany)
  • it : 8 profils (Italie + Italy)
  • pt : 24 profils (Portugal + Brazil)
```

#### **Fallback Anglais pour les Profils Non Détectés**
Les profils avec `language: "xx"` ou sans informations géographiques utilisent l'anglais par défaut :

```bash
🌍 Fallback anglais pour KimVenditti (langue: xx, pays: null)
🌍 Fallback anglais pour AliceDev (langue: xx, pays: null)
```

#### **Avantages du géocodage GPS**
- **Précision géographique** : Régions déterminées depuis les coordonnées exactes
- **Données fiables** : Basé sur OpenStreetMap, base de données géographiques mondiale
- **Langue française** : Résultats en français quand disponibles
- **Fallback intelligent** : Utilise l'IA si le géocodage échoue

#### **Processus de géocodage**
1. **Extraction des coordonnées** : Récupère lat/lon depuis le profil
2. **Appel Nominatim** : Requête à l'API OpenStreetMap
3. **Extraction de la région** : Priorité : state > region > county > province
4. **Sauvegarde** : Stocke la région dans les métadonnées

#### **Exemple d'utilisation**
```bash
# 1. Lancer l'analyse Géo-Linguistique
> 1

# 📍 Options de géocodage :
# 1. Utiliser le géocodage GPS pour les régions (recommandé)
# 2. Utiliser uniquement l'IA pour l'analyse
# Choisissez une option (1-2, défaut: 1) : 1

# 📊 2347 profils avec GPS valides sur 8269 profils totaux
# 📍 Géocodage GPS activé pour les régions
# Analyse Géo-Linguistique 1/2347 : pupucine
# 📍 Région GPS pour pupucine : Provence-Alpes-Côte d'Azur
# ...
```

### 🔄 Optimisation des Thèmes (Nouveau)

Quand la base de prospects augmente, il est important de maintenir un **Top 50 des thèmes représentatif** en consolidant et nettoyant les tags existants :

#### **Quand utiliser l'optimisation ?**
- **Base qui a augmenté** : Nouveaux prospects ajoutés
- **Thèmes obsolètes** : Certains thèmes ne sont plus pertinents
- **Nouveaux domaines** : Émergence de nouveaux centres d'intérêt
- **Avant une campagne** : S'assurer de la qualité des thèmes
- **Nettoyage nécessaire** : Trop de thèmes uniques peu utilisés

#### **Avantages de l'optimisation**
- **Top 50 actualisé** : Thèmes les plus représentatifs de la communauté actuelle
- **Personas améliorés** : Banques 5-9 basées sur des thèmes optimisés
- **Ciblage précis** : Segmentation plus efficace
- **Détection des changements** : Suivi de l'évolution des centres d'intérêt
- **Nettoyage automatique** : Suppression des thèmes peu utilisés (< 3 occurrences)

#### **Processus d'optimisation**
1. **Analyse des tags existants** : Compte les occurrences de chaque thème
2. **Filtrage intelligent** : Conserve uniquement les thèmes utilisés par ≥ 3 profils
3. **Nettoyage des profils** : Supprime les tags non conservés de chaque profil
4. **Nouveau Top 50** : Affiche les thèmes les plus représentatifs
5. **Sauvegarde** : Met à jour la base de connaissance

### 🌍 Ciblage Avancé par Critères Géographiques et Linguistiques

#### **Nouvelles Options de Ciblage**

AstroBot propose maintenant **4 méthodes de ciblage** pour des campagnes ultra-précises :

##### **1. Ciblage par Thème (Option 4)**
```bash
# 4. Lancer une campagne à partir d'un Thème
> 4

# Exemple de sortie :
# 1. Thème : developpeur (1247 membres)
#    Description : Groupe de 1247 membres partageant l'intérêt ou la compétence 'developpeur'.
# 2. Thème : technologie (892 membres)
#    Description : Groupe de 892 membres partageant l'intérêt ou la compétence 'technologie'.
# ...
```

##### **2. Ciblage par Langue (Option 5)**
```bash
# 5. 🌍 Cibler par Langue
> 5

# Exemple de sortie :
# 1. Langue : Français (1938 membres)
#    Description : Groupe de 1938 membres parlant Français.
# 2. Langue : Anglais (892 membres)
#    Description : Groupe de 892 membres parlant Anglais.
# 3. Langue : Espagnol (446 membres)
#    Description : Groupe de 446 membres parlant Espagnol.
# 4. Langue : Allemand (27 membres)
#    Description : Groupe de 27 membres parlant Allemand.
# ...
```

##### **3. Ciblage par Pays (Option 6)**
```bash
# 6. 🌍 Cibler par Pays
> 6

# Exemple de sortie :
# 1. Pays : France (1754 membres)
#    Description : Groupe de 1754 membres localisés en 'France'.
# 2. Pays : Espagne (266 membres)
#    Description : Groupe de 266 membres localisés en 'Espagne'.
# 3. Pays : Belgique (170 membres)
#    Description : Groupe de 170 membres localisés en 'Belgique'.
# 4. Pays : Portugal (23 membres)
#    Description : Groupe de 23 membres localisés en 'Portugal'.
# ...
```

##### **4. Ciblage par Région (Option 7)**
```bash
# 7. 🌍 Cibler par Région
> 7

# Exemple de sortie :
# 1. Région : Île-de-France, France (234 membres)
#    Description : Groupe de 234 membres localisés en 'Île-de-France, France'.
# 2. Région : Provence-Alpes-Côte d'Azur, France (189 membres)
#    Description : Groupe de 189 membres localisés en 'Provence-Alpes-Côte d'Azur, France'.
# 3. Région : Aragon, Espagne (45 membres)
#    Description : Groupe de 45 membres localisés en 'Aragon, Espagne'.
# 4. Région : Pays de la Loire, France (67 membres)
#    Description : Groupe de 67 membres localisés en 'Pays de la Loire, France'.
# ...
```

##### **5. 🎯 Ciblage Avancé Multi-Sélection (Option 8)**
```bash
# 8. 🎯 Ciblage Avancé Multi-Sélection (Thèmes + Filtres)
> 8

# Étape 1 : Sélection des thèmes
🎯 SÉLECTION DES THÈMES
==================================================
Sélectionnez les thèmes qui vous intéressent (numéros séparés par des virgules)
Exemple : 1,3,5 pour sélectionner les thèmes 1, 3 et 5
Entrée pour annuler

 1. Developpeur           (1247 membres)
 2. Technologie           ( 892 membres)
 3. Crypto                ( 756 membres)
 4. Open-source           ( 634 membres)
 5. Blockchain            ( 523 membres)
...

Sélectionnez les thèmes (ex: 1,3,5) : 1,3,5

# Étape 2 : Filtrage géographique
🌍 FILTRAGE GÉOGRAPHIQUE
==================================================
Prospects des thèmes sélectionnés : 2347

Options de filtrage :
1. Aucun filtre (tous les prospects des thèmes)
2. Filtrer par langue
3. Filtrer par pays
4. Filtrer par région
5. Combinaison de filtres

Choisissez une option (1-5) : 2

# Étape 3 : Sélection des langues
🌍 LANGUES DISPONIBLES :
1. Français (1456 prospects)
2. Anglais (567 prospects)
3. Espagnol (234 prospects)
4. Allemand (90 prospects)

Sélectionnez les langues (ex: 1,2) ou 'all' pour toutes : 1,2

# Étape 4 : Résultats et sauvegarde
🎯 RÉSULTATS DU CIBLAGE MULTI-SÉLECTION
============================================================
Thèmes sélectionnés : developpeur, crypto, blockchain
Nombre de prospects ciblés : 2023

📊 COMPOSITION DE LA CIBLE :
🌍 Langues : fr(1456), en(567)
🌍 Pays : France(1234), Spain(456), Belgium(333)
🌍 Régions : Île-de-France, France(234), Provence-Alpes-Côte d'Azur, France(189)

💾 Sauvegarder cette cible de 2023 prospects ? (o/n) : o
✅ Cible sauvegardée : Multi-developpeur+crypto+blockchain-2023prospects (2023 prospects)
```

#### **Avantages du Ciblage Avancé**

##### **🎯 Précision Maximale**
- **Ciblage linguistique** : Messages dans la langue native du prospect
- **Ciblage géographique** : Campagnes adaptées aux spécificités locales
- **Ciblage thématique** : Contenu aligné sur les centres d'intérêt
- **Multi-sélection** : Combinaison de plusieurs thèmes pour un ciblage ultra-précis

##### **🎯 Flexibilité Totale**
- **Sélection multiple** : Choisir plusieurs thèmes simultanément
- **Filtres croisés** : Combiner langue + pays + région
- **Base personnalisée** : Constituer des cibles sur-mesure
- **Sauvegarde intelligente** : Noms descriptifs automatiques

##### **🌍 Campagnes Multilingues**
- **Français** : 1938 prospects pour des campagnes francophones
- **Anglais** : 892 prospects pour des campagnes internationales
- **Espagnol** : 446 prospects pour des campagnes hispanophones
- **Autres langues** : Allemand, Italien, Portugais, etc.

##### **📍 Campagnes Régionales**
- **France** : 1754 prospects répartis par régions
- **Espagne** : 446 prospects avec régions spécifiques
- **Belgique** : 170 prospects (Flandre, Wallonie, Bruxelles)
- **Autres pays** : Portugal, Allemagne, Suisse, etc.

##### **🎭 Personnalisation Avancée**
- **Combinaison de critères** : Langue + Pays + Thème
- **Messages adaptés** : Contenu culturellement approprié
- **Timing optimal** : Campagnes selon les fuseaux horaires

#### **Exemples d'Utilisation**

##### **Campagne Francophone Technique**
```bash
# 1. Cibler par langue française
> 5
> 1  # Français

# 2. Lancer l'Agent Stratège en mode Persona
> 2
> 1  # Mode Persona

# Résultat : Messages en français pour 1938 prospects francophones
```

##### **Campagne Régionale Espagnole**
```bash
# 1. Cibler par région espagnole
> 7
> 3  # Aragon, Espagne

# 2. Lancer l'Agent Stratège en mode Persona
> 2
> 1  # Mode Persona

# Résultat : Messages en espagnol pour 45 prospects d'Aragon
```

##### **Campagne Thématique Internationale**
```bash
# 1. Cibler par thème technique
> 4
> 1  # developpeur

# 2. Lancer l'Agent Stratège en mode Persona
> 2
> 1  # Mode Persona

# Résultat : Messages multilingues pour 1247 développeurs
```

##### **🎯 Campagne Multi-Sélection Avancée**
```bash
# 1. Ciblage avancé multi-sélection
> 8

# 2. Sélectionner plusieurs thèmes
> 1,3,5  # developpeur, crypto, blockchain

# 3. Filtrer par langue française
> 2  # Filtrer par langue
> 1  # Français

# 4. Lancer l'Agent Stratège en mode Persona
> 2
> 1  # Mode Persona

# Résultat : Messages en français pour développeurs crypto/blockchain francophones
```

### 🎭 Création Automatique de Personas Multilingues (Recommandé)

#### Méthode 1 : Génération Automatique
```bash
# 1. Lancer l'Agent Analyste
> 1

# 2. Choisir la création automatique
> 5

# 3. Le système détecte les langues présentes dans la base
# 4. Génération automatique des personas multilingues dans les banques 5-9
```

#### **Avantages des Personas Multilingues**
- **Contenu localisé** : Chaque persona a son contenu dans toutes les langues détectées
- **Cohérence culturelle** : Adapté aux spécificités culturelles de chaque langue
- **Efficacité maximale** : Plus besoin de traduction à la volée
- **Qualité optimale** : Contenu rédigé par l'IA dans chaque langue

#### **Exemple de Sortie**
```bash
🌍 Langues détectées pour les personas multilingues :
  • fr : 3247 profils
  • en : 892 profils
  • es : 456 profils
  • de : 234 profils

🎭 Création du persona multilingue pour le thème 'developpeur' (banque 5)...
✅ Persona multilingue créé : Le Codeur Libre (L'Architecte Numérique)
🌍 Langues supportées : fr, en, es, de

🎭 Création du persona multilingue pour le thème 'technologie' (banque 6)...
✅ Persona multilingue créé : L'Innovateur Digital (Le Technologue)
🌍 Langues supportées : fr, en, es, de

🎉 Création automatique terminée ! 5 personas multilingues créés dans les banques 5-9.
```

#### Avantages de la Génération Automatique
- **🎯 Représentativité** : Basé sur les thèmes réels de la communauté
- **🌍 Multilingue** : Contenu généré dans toutes les langues détectées
- **⚡ Rapidité** : Génération en quelques minutes
- **🔄 Adaptation** : S'adapte à l'évolution de la communauté
- **📊 Données réelles** : Utilise les occurrences réelles des thèmes
- **🎭 Cohérence culturelle** : Contenu adapté à chaque culture

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