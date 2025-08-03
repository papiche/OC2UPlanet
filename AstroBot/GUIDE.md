# 🚀 AstroBot v2.0 - Guide Complet des Campagnes Marketing Intelligentes
[... more](GUIDE.more.md)

> **📚 Documentation associée :**
> - [📋 Résumé du Mode Persona](MODE_PERSONA_SUMMARY.md) - Fonctionnalités avancées de personnalisation
> - [🎯 Guide Marketing](MARKETING.md) - Stratégies de prospection dans les bases Ğ1 & ğchange
> - [📊 Résumé du Système](../SUMMARY.md) - Architecture du système de prospection unifié
> - [🎯 Guide G1FabLab](GUIDE_G1FABLAB.md) - Utilisation des prompts G1FabLab

## 🎯 Vue d'ensemble - AstroBot v2.0

AstroBot v2.0 est un **système d'agents IA avancé** spécialisé dans la création et l'exécution de campagnes marketing multicanal ultra-personnalisées pour UPlanet. Il combine analyse intelligente, rédaction contextuelle, gestion multicanal et suivi automatisé pour optimiser vos campagnes marketing.

### 🆕 Nouvelles Fonctionnalités v2.0

#### 🎭 **Système de Personas Avancé**
- **12 banques de mémoire** (0-11) pour gérer jusqu'à 12 campagnes en parallèle
- **Personas auto-générés** (banques 5-9) basés sur l'analyse réelle de la communauté
- **Import G1FabLab** : Import et analyse IA automatique des prompts G1FabLab dans la banque 4
- **Personas multilingues** : Contenu adapté à chaque langue détectée (FR, EN, ES, DE, IT, PT)

#### 🌍 **Traduction et Localisation Intelligente**
- **Détection automatique** de la langue du prospect depuis la base de connaissance
- **Génération multilingue** : Messages écrits dans la langue native du prospect
- **Adaptation culturelle** : Contenu adapté aux spécificités de chaque culture
- **Fallback intelligent** : Français par défaut si langue non détectée

#### 🔗 **Injection Automatique de Liens**
- **Placeholders intelligents** : `[Lien vers OpenCollective]` → liens fonctionnels
- **Configuration centralisée** des liens externes dans `workspace/links_config.json`
- **Injection automatique** dans tous les modes de rédaction
- **Liens contextuels** : OpenCollective, Discord, Documentation, GitHub, etc.

#### 🎯 **Trois Modes de Rédaction Optimisés**
- **Mode Persona** : Analyse IA automatique + sélection intelligente de banque
- **Mode Auto** : Sélection automatique basée sur les thèmes + enrichissement web
- **Mode Classique** : Choix manuel avec injection de liens et personnalisation

#### 📊 **Système de Slots de Campagnes (0-11)**
- **12 campagnes simultanées** possibles
- **Attribution automatique** du premier slot libre
- **Nommage descriptif** : "MULTIPASS - FR, ES - France, Spain"
- **Statistiques détaillées** par campagne
- **Suivi indépendant** de chaque campagne

## 🏗️ Architecture des 3 Agents

### 1. 🤖 **Agent Analyste** - Intelligence et Segmentation

#### **Fonctionnalités Principales**
- **Analyse géo-linguistique** : Détection langue/pays/région depuis les coordonnées GPS
- **Analyse thématique** : Extraction des centres d'intérêt et compétences
- **Création automatique de personas** : Génération IA des banques 5-9
- **Optimisation des thèmes** : Consolidation et nettoyage de la base de connaissance
- **Ciblage avancé multi-sélection** : Thèmes + filtres croisés par langue/pays/région

#### **Workflow d'Analyse**
```
1. 🌍 Analyse Géo-Linguistique (GPS → Région via Nominatim)
2. 🏷️ Analyse par Thèmes (compétences, intérêts)
3. 🎭 Création de Personas (banques 5-9 auto-générées)
4. 🔄 Optimisation des Thèmes (consolidation)
5. 🧪 Mode Test (validation avec cible unique)
6. 🎯 Ciblage Avancé Multi-Sélection
```

#### **Nouvelles Capacités v2.0**
- **Géocodage GPS** : Utilisation de Nominatim (OpenStreetMap) pour les régions
- **Détection intelligente** du niveau d'analyse (alerte si < 10% des profils analysés)
- **Analyse automatique** si données insuffisantes
- **Options "Retour"** dans tous les sous-menus pour une navigation fluide

### 2. 🎭 **Agent Stratège** - Personnalisation et Rédaction

#### **Fonctionnalités Principales**
- **12 banques de mémoire** thématiques (0-11)
- **Trois modes de rédaction** : Persona, Auto, Classique
- **Import G1FabLab** : Analyse IA automatique des prompts `.sh`
- **Génération multilingue** automatique selon la langue du prospect
- **Injection automatique de liens** via placeholders intelligents

#### **Système de Banques de Mémoire**

| Banque | Type | Contenu | Utilisation |
|--------|------|---------|-------------|
| 0-3 | Manuel | Personas configurés manuellement | Campagnes spécialisées |
| 4 | G1FabLab | Prompt importé + analyse IA | Campagnes G1FabLab |
| 5-9 | Auto-généré | Personas basés sur l'analyse de la communauté | Campagnes thématiques |
| 10-11 | Libre | Disponibles pour nouvelles campagnes | Campagnes futures |

#### **Import G1FabLab (Banque 4)**
- **Analyse IA automatique** du contenu des prompts `.sh`
- **Génération automatique** : nom, description, archétype, thèmes, vocabulaire
- **Priorité automatique** : Banque 4 apparaît en premier avec icône 🎯
- **Personnalisation IA** : Le persona redraft le message G1FabLab dans son style

#### **Modes de Rédaction**

##### **🎭 Mode Persona (Recommandé)**
- **Analyse IA** automatique du profil du prospect
- **Enrichissement web** via Perplexica pour le contexte
- **Sélection intelligente** de la banque la plus adaptée
- **Scoring automatique** : Correspondance thèmes/archetype
- **Personnalisation maximale** : Messages ultra-ciblés

##### **🔄 Mode Auto**
- **Sélection automatique** basée sur les thèmes des cibles
- **Enrichissement contextuel** via Perplexica
- **Personnalisation élevée** avec injection de liens
- **Fallback intelligent** vers méthode classique si nécessaire

##### **📝 Mode Classique**
- **Choix manuel** de la banque de contexte
- **Injection automatique** de liens
- **Personnalisation variable** selon la banque choisie
- **Sélection unique** : Un persona pour toutes les cibles

### 3. 📡 **Agent Opérateur** - Exécution et Suivi

#### **Fonctionnalités Principales**
- **Envoi multicanal** : Jaklis (Cesium+), Mailjet (Email), Nostr DM
- **Système de slots** : Gestion de 12 campagnes en parallèle
- **Mémoire contextuelle** des interactions par campagne
- **Réponses automatiques** intelligentes basées sur les mots-clés
- **Suivi détaillé** : Statistiques par campagne et par profil

#### **Canaux de Communication**

##### **📱 Jaklis (Cesium+)**
- **Message privé** via l'API Cesium+
- **Authentification** via portefeuille Trésor UPlanet
- **Suivi** des réponses en temps réel
- **Opt-out** automatique sur demande

##### **📧 Mailjet (Email)**
- **Campagnes email** professionnelles
- **Templates** personnalisés par prospect
- **Statistiques** d'ouverture et de clic
- **Gestion** des bounces et désinscriptions

##### **🔗 Nostr DM**
- **Messages directs** pour détenteurs de MULTIPASS
- **Authentification** via clé privée UPlanet
- **Communication** décentralisée
- **Suivi** via réseau Nostr

#### **Système de Slots de Campagnes**

```
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
```

## 🚀 Guide d'Utilisation Complet

### **Installation et Configuration**

#### **1. Prérequis Système**
```bash
# Vérifier les scripts externes
ls ~/.zen/Astroport.ONE/IA/question.py
ls ~/.zen/Astroport.ONE/IA/ollama.me.sh
ls ~/.zen/Astroport.ONE/tools/jaklis/jaklis.py
ls ~/.zen/Astroport.ONE/tools/mailjet.sh
ls ~/.zen/Astroport.ONE/tools/nostr_send_dm.py

# Vérifier la base de prospects
ls ~/.zen/game/g1prospect.json
```

#### **2. Configuration Initiale**
```bash
cd /home/fred/workspace/AAA/OC2UPlanet/AstroBot
python3 main.py
```

#### **3. Configuration du Portefeuille Trésor**
- Le système détecte automatiquement le portefeuille `$UPLANETNAME_G1`
- Vérifier que `~/.zen/Astroport.ONE/tools/keygen` est accessible
- Configuration automatique de la clé publique Trésor

### **Workflow de Campagne Optimisé**

#### **Étape 1 : Analyse et Segmentation (Agent Analyste)**

##### **1.1 Analyse Géo-Linguistique**
```bash
# Menu → 1. Lancer l'Agent ANALYSTE
# Option 1. 🌍 Analyse Géo-Linguistique

# Options de géocodage :
# 1. Utiliser le géocodage GPS pour les régions (recommandé)
# 2. Utiliser uniquement l'IA pour l'analyse

# Résultat : Détection automatique langue/pays/région
🌍 Langue détectée : fr
🌍 Pays détecté : France  
🌍 Région détectée : Île-de-France
```

##### **1.2 Analyse Thématique**
```bash
# Option 2. 🏷️ Analyse par Thèmes
# Le système analyse les profils et extrait les centres d'intérêt
# Résultat : Base de connaissance enrichie avec tags thématiques
```

##### **1.3 Création Automatique de Personas**
```bash
# Option 3. 🎭 Créer des personas basés sur les thèmes détectés
# Le système génère automatiquement les banques 5-9

🌍 Langues détectées pour les personas multilingues :
  • fr : 3247 profils
  • en : 892 profils
  • es : 456 profils
  • de : 234 profils

🎭 Création du persona multilingue pour le thème 'developpeur' (banque 5)...
✅ Persona multilingue créé : Le Codeur Libre (L'Architecte Numérique)
🌍 Langues supportées : fr, en, es, de
```

##### **1.4 Optimisation des Thèmes (Recommandé)**
```bash
# Option 4. 🔄 Optimiser les Thèmes
# Quand la base augmente, consolidation et nettoyage

📊 3343 profils analysés trouvés. Consolidation des thèmes...
📊 1247 thèmes uniques détectés dans la base.
🎯 523 thèmes conservés (≥ 3 occurrences)
🗑️ 724 thèmes supprimés (< 3 occurrences)
```

##### **1.5 Mode Test (Validation)**
```bash
# Option 5. 🧪 Mode Test
# Validation avec une cible unique avant campagne complète

🧪 MODE TEST - SÉLECTION DE LA CIBLE
1. 🎯 Utiliser la cible de test par défaut
2. 🔑 Spécifier une clé publique (pubkey)
3. 👤 Spécifier un identifiant utilisateur (uid)
4. 📋 Voir les prospects disponibles
```

##### **1.6 Ciblage Avancé Multi-Sélection**
```bash
# Option 6. 🎯 Ciblage Avancé Multi-Sélection
# Méthode recommandée pour des campagnes ultra-précises

🎯 SÉLECTION DES THÈMES
Sélectionnez les thèmes (ex: 1,3,5) : 1,3,5

🌍 FILTRAGE GÉOGRAPHIQUE
Options de filtrage :
1. Aucun filtre (tous les prospects des thèmes)
2. Filtrer par langue
3. Filtrer par pays
4. Filtrer par région
5. Combinaison de filtres

🎯 RÉSULTATS DU CIBLAGE MULTI-SÉLECTION
Thèmes sélectionnés : developpeur, crypto, blockchain
Nombre de prospects ciblés : 2023

📊 COMPOSITION DE LA CIBLE :
🌍 Langues : fr(1456), en(567)
🌍 Pays : France(1234), Spain(456), Belgium(333)
🌍 Régions : Île-de-France, France(234), Provence-Alpes-Côte d'Azur, France(189)
```

#### **Étape 2 : Import G1FabLab (Optionnel mais Recommandé)**

##### **2.1 Import d'un Prompt G1FabLab**
```bash
# Menu → 4. Gérer les Mémoires Persona (0-9)
# Option 7. 📥 Importer un prompt G1FabLab dans la banque 4

# Sélection du fichier :
1. 1.sh - "La Ğ1, c'est fait. Et si on construisait le reste ?"
2. 2.sh - "Activez les super-pouvoirs de votre compte Ğ1"
3. 3.sh - "Appel aux bâtisseurs : devenez Capitaine"
4. 4.sh - "Notre but ultime n'est pas le code. C'est la Terre."

# L'IA analyse automatiquement le contenu et génère :
✅ Nom personnalisé : L'Architecte de Confiance
✅ Description : Spécialiste de l'écosystème souverain
✅ Archétype : Le Visionnaire
✅ Thèmes : developpeur, crypto, technologie, open-source
✅ Vocabulaire : écosystème, souveraineté, infrastructure, décentralisation
✅ Arguments : Transformation de la confiance en infrastructure
✅ Ton : inspirant, visionnaire, engageant
```

#### **Étape 3 : Rédaction du Message (Agent Stratège)**

##### **3.1 Choix du Mode de Rédaction**
```bash
# Menu → 2. Lancer l'Agent STRATEGE

🎯 MODE DE RÉDACTION DU MESSAGE
1. Mode Persona : Analyse automatique du profil et sélection de banque
2. Mode Auto : Sélection automatique basée sur les thèmes
3. Mode Classique : Choix manuel du persona
```

##### **3.2 Mode Persona (Recommandé pour Personnalisation Maximale)**
```bash
# Option 1. Mode Persona

🔍 Mode Persona : Analyse du profil du prospect...
🌍 Langue détectée pour Cobart31 : fr
🎯 Correspondance détectée : Ingénieur/Technicien (Score: 25)
🎭 Archetype sélectionné : L'Informaticien
🌍 Utilisation du contenu multilingue pour fr
✅ Message personnalisé généré pour Cobart31 (français)

🔍 Mode Persona : Analyse du profil du prospect...
🌍 Langue détectée pour AliceDev : en
🎯 Correspondance détectée : The Free Coder (Score: 30)
🎭 Archetype sélectionné : The Digital Architect
🌍 Utilisation du contenu multilingue pour en
✅ Message personnalisé généré pour AliceDev (anglais)
```

##### **3.3 Mode Auto (Recommandé pour Campagnes de Masse)**
```bash
# Option 2. Mode Auto

🎯 Sélection automatique basée sur les thèmes des cibles...
🎭 Banque sélectionnée : Le Codeur Libre (L'Architecte Numérique)
🌍 Utilisation du contenu multilingue pour fr
✅ Messages générés pour 1456 prospects francophones
```

##### **3.4 Mode Classique (Recommandé pour Tests)**
```bash
# Option 3. Mode Classique

🎭 CHOIX DU PERSONA DE CONTEXTE
🎯 4. L'Architecte de Confiance - PROMPT G1FabLab (Le Visionnaire)
0. Ingénieur/Technicien (Le Bâtisseur)
1. Philosophe/Militant (Le Militant)
2. Créateur/Artisan (Le Créateur)
3. Holistique/Thérapeute (L'Holistique)
5. Aucun persona (méthode classique pure)

# Sélection unique : Le persona choisi sera utilisé pour toutes les cibles
Choisissez un persona (0-4) ou 5 pour aucune : 4

✅ Banque sélectionnée : L'Architecte de Confiance
🎯 Utilisation du prompt G1FabLab importé
```

#### **Étape 4 : Envoi de la Campagne (Agent Opérateur)**

##### **4.1 Lancement de la Campagne**
```bash
# Menu → 3. Lancer l'Agent OPÉRATEUR
# Option 1. 📤 ENVOYER - Lancer la campagne

📡 Choisissez le canal d'envoi :
1. Jaklis (Message privé Cesium+)
2. Mailjet (Email)
3. Nostr (DM pour les détenteurs de MULTIPASS)

# Attribution automatique du slot
🎯 SLOT 0: MULTIPASS - FR, ES - France, Spain
📅 Date: 2025-07-31T07:30:00
🎯 Cibles initiales: 14
```

##### **4.2 Suivi des Interactions**
```bash
# Option 3. 📊 État des interactions

📊 ÉTAT DES CAMPAGNES ET INTERACTIONS
============================================================

🎯 SLOT 0: MULTIPASS - FR, ES - France, Spain
   📅 Date: 2025-07-31T07:30:00
   🎯 Cibles initiales: 14
   📊 Interactions: 14
   💬 Réponses: 3
   📈 Taux de réponse: 21.4%
   👥 Conversations actives: 3

🔍 Options de consultation:
   1. Voir les détails d'une campagne spécifique
   2. Voir l'historique d'un profil spécifique
   3. Retour
```

##### **4.3 Gestion des Réponses**
```bash
# Option 2. 📥 RECEVOIR - Consulter la messagerie

📥 MESSAGERIE - RÉPONSES REÇUES
============================================================

💬 Réponse de DsEx1pS33v... (Slot 0)
📅 Date : 2025-07-31T08:15:00
📝 Message : "Merci, c'est très intéressant. Comment puis-je participer ?"

🤖 Réponse automatique envoyée :
"Parfait ! Pour en savoir plus sur MULTIPASS et rejoindre le développement..."

✅ Réponse traitée automatiquement
```

## 🎯 Stratégies de Campagnes Optimisées

### **Campagne 1 : MULTIPASS pour Développeurs Francophones**
```bash
# 1. Ciblage
🎯 Ciblage Multi-Sélection : developpeur + crypto + technologie
🌍 Filtre : Langue française
📊 Résultat : 1456 prospects

# 2. Persona
🎭 Mode Persona : Analyse automatique + sélection intelligente
🏗️ Banque sélectionnée : Le Codeur Libre (L'Architecte Numérique)

# 3. Canal
📡 Jaklis (Cesium+) : Messages privés personnalisés

# 4. Résultat attendu
📈 Taux de réponse : 25-30%
🎯 Conversion : 15-20% vers OpenCollective
```

### **Campagne 2 : Financement International**
```bash
# 1. Ciblage
🎯 Ciblage Multi-Sélection : open-source + blockchain
🌍 Filtre : Langue anglaise
📊 Résultat : 567 prospects

# 2. Persona
🎭 Mode Auto : Sélection automatique basée sur les thèmes
🏗️ Banque sélectionnée : The Free Coder (The Digital Architect)

# 3. Canal
📧 Mailjet : Campagne email professionnelle

# 4. Résultat attendu
📈 Taux d'ouverture : 35-40%
🎯 Conversion : 10-15% vers OpenCollective
```

### **Campagne 3 : G1FabLab - Écosystème Souverain**
```bash
# 1. Import G1FabLab
📥 Import du prompt 1.sh dans la banque 4
🤖 Analyse IA automatique du contenu

# 2. Ciblage
🎯 Ciblage par thème : developpeur
🌍 Filtre : France + Espagne
📊 Résultat : 234 prospects

# 3. Persona
🎭 Mode Classique : Banque 4 (G1FabLab)
🏗️ Persona : L'Architecte de Confiance

# 4. Canal
📡 Jaklis + Nostr : Multicanal pour couverture maximale

# 5. Résultat attendu
📈 Taux de réponse : 30-35%
🎯 Conversion : 20-25% vers OpenCollective
```

## 📊 Métriques et Optimisation

### **KPI Principaux**
- **Taux de réponse** : % de cibles qui répondent
- **Taux d'ouverture** : % d'emails ouverts (Mailjet)
- **Taux de conversion** : % qui rejoignent OpenCollective
- **Qualité des réponses** : % de réponses positives
- **Engagement** : % qui demandent plus d'informations

### **Optimisation Continue**
- **A/B Testing** : Comparer différents personas
- **Analyse des réponses** : Adapter les messages selon les retours
- **Optimisation des thèmes** : Nettoyer et consolider régulièrement
- **Personas multilingues** : Améliorer le contenu culturel

## 🔧 Configuration Avancée

### **Personas Multilingues**
```json
{
  "name": "Le Codeur Libre",
  "archetype": "L'Architecte Numérique",
  "multilingual": {
    "fr": {
      "name": "Le Codeur Libre",
      "tone": "pragmatique, précis, direct",
      "vocabulary": ["protocole", "infrastructure", "décentralisation"]
    },
    "en": {
      "name": "The Free Coder",
      "tone": "pragmatic, precise, direct",
      "vocabulary": ["protocol", "infrastructure", "decentralization"]
    }
  }
}
```

### **Configuration des Liens**
```json
{
  "Lien vers OpenCollective": "https://opencollective.com/monnaie-libre",
  "Lien vers Discord": "https://ipfs.copylaradio.com/ipns/copylaradio.com/bang.html",
  "Lien vers Documentation": "https://github.com/papiche/Astroport.ONE/blob/master/DOCUMENTATION.md",
  "Lien vers GitHub": "https://github.com/papiche/Astroport.ONE",
  "Lien vers Site Web": "https://copylaradio.com"
}
```

### **Réponses Automatiques**
- **Positives** : merci, thanks, intéressant, oui, plus d'info
- **Négatives** : non, pas intéressé, stop, arrêter
- **Intervention manuelle** : problème, erreur, plainte

## 🚨 Dépannage et Support

### **Problèmes Courants**

#### **1. Erreur "Script introuvable"**
```bash
# Vérifier les chemins dans main.py
ls ~/.zen/Astroport.ONE/IA/question.py
ls ~/.zen/Astroport.ONE/IA/ollama.me.sh
ls ~/.zen/Astroport.ONE/tools/jaklis/jaklis.py
```

#### **2. Erreur JSON dans l'analyse**
```bash
# Supprimer et régénérer la base de connaissance
rm workspace/enriched_prospects.json
# Relancer l'analyse
```

#### **3. Erreur d'authentification Jaklis**
```bash
# Vérifier la variable d'environnement
echo $CAPTAINEMAIL
# Vérifier le nœud Cesium
cat ~/.zen/Astroport.ONE/tools/my.sh
```

#### **4. Personas avec occurrences faibles**
```bash
# Le système détecte automatiquement et propose l'analyse complète
# Choisir 'o' quand proposé pour lancer l'analyse thématique complète
```

### **Logs et Debug**
- **Log principal** : `~/.zen/tmp/astrobot.log`
- **Mode DEBUG** : Activé par défaut pour voir les appels d'outils
- **Logs IA** : Réponses brutes dans les logs DEBUG

### **Commandes Utiles**
```bash
# Vérifier l'état du système
tail -f ~/.zen/tmp/astrobot.log

# Vérifier les personas auto-générés
cat workspace/memory_banks_config.json | jq '.banks | keys[] as $k | "Banque \($k): \(.[$k].name) (\(.[$k].archetype))"'

# Vérifier le niveau d'analyse
cat workspace/enriched_prospects.json | jq 'to_entries | map(select(.value.metadata.tags)) | length'

# Vérifier la configuration des liens
cat workspace/links_config.json | jq 'keys[] as $k | "\($k): \(.[$k])"'
```

## 🔮 Évolutions Futures

### **Fonctionnalités Prévues**
1. **Interface Web** : Dashboard pour visualiser les campagnes
2. **A/B Testing** : Comparaison de différentes approches
3. **Intégration CRM** : Synchronisation avec d'autres outils
4. **Analytics Avancés** : Métriques détaillées et prédictions
5. **Personnalisation Dynamique** : Adaptation en temps réel
6. **🎭 Personas Individuels** : Personas spécifiques par prospect
7. **🔄 Apprentissage Continu** : Amélioration automatique des personas
8. **📊 A/B Testing de Personas** : Comparaison d'efficacité des archétypes

### **Extensions Possibles**
1. **Support Multilingue** : Traduction automatique des messages
2. **Intégration Social Media** : Mastodon, Twitter, LinkedIn
3. **Gamification** : Système de points et récompenses
4. **IA Conversationnelle** : Chatbot pour les réponses complexes

## 📞 Support et Ressources

### **Ressources**
- **Documentation technique** : Ce guide
- **Logs système** : `~/.zen/tmp/astrobot.log`
- **Configuration** : `workspace/memory_banks_config.json`
- **Base de données** : `workspace/enriched_prospects.json`

### **Contact**
- **Support technique** : Via les logs et la documentation
- **Améliorations** : Suggestions via les issues GitHub
- **Formation** : Guide complet et exemples inclus

---

## ✅ Conclusion

**AstroBot v2.0** transforme la prospection marketing en un processus intelligent, automatisé et ultra-personnalisé. Avec ses 12 campagnes simultanées, ses personas multilingues, son import G1FabLab et son système de slots, il offre une solution complète pour créer des campagnes marketing au top.

**🎭 Prêt pour les campagnes de prospection intelligentes !** 🚀 