# Prospect Database Builder - Résumé du Système Unifié

## 🎯 **Objectif atteint : Un système de prospection à double source**

Nous avons créé un **écosystème de prospection avancé** qui unifie les données des deux principales plateformes de la Monnaie Libre : la **Ğ1 (via Cesium)** et **ğchange**. Ce système ne se contente plus de collecter des données, il les **croise et les enrichit mutuellement**.

### **Le système accomplit désormais :**
1.  **Prospection Ğ1** : Il récupère et enrichit les profils des membres de la toile de confiance via `g1prospect_final.sh`.
2.  **Prospection ğchange** : Il scanne l'activité sur ğchange via `gchange_prospect.sh` pour découvrir de nouveaux utilisateurs et suivre l'activité des anciens.
3.  **Enrichissement Croisé (Cross-Enrichment)** : C'est la fonctionnalité clé. Quand `gchange_prospect.sh` trouve un utilisateur ğchange qui a lié son compte Ğ1, il **vérifie et met à jour automatiquement** la base de données `g1prospect.json`, créant ainsi un pont entre les deux écosystèmes.

## 📁 **Architecture des fichiers**

### **Scripts principaux**
-   `g1prospect_final.sh` : Le collecteur dédié à la toile de confiance Ğ1.
-   `gchange_prospect.sh` : Le collecteur dédié à la place de marché ğchange, qui **déclenche aussi** l'enrichissement de la base Ğ1.
-   `test_g1prospect.sh` : Script de test pour le collecteur Ğ1.

### **Bases de données générées**
-   `~/.zen/game/g1prospect.json` : La base de données des membres de la toile Ğ1, enrichie par les deux scripts.
-   `~/.zen/game/gchange_prospect.json` : La base de données des utilisateurs actifs sur ğchange, avec un historique de leurs annonces.

## 🔧 **Fonctionnalités du système unifié**

### ✅ **Collecte de données multi-sources**
-   **Ğ1 WoT API** (`g1.duniter.org`) : Pour la liste des membres Ğ1.
-   **Cesium API** (`g1.data.e-is.pro`) : Pour les profils Ğ1 détaillés.
-   **ğchange API** (`data.gchange.fr`) : Pour les annonces et les profils ğchange.

### ✅ **Enrichissement des données**
-   **Profils complets** : Les deux bases contiennent les profils détaillés des utilisateurs.
-   **Historique d'activité** : La base ğchange conserve la trace de toutes les annonces détectées pour un utilisateur (`detected_ads`).
-   **Contexte de découverte** : Chaque prospect ğchange est lié à l'annonce qui a permis de le découvrir (`discovery_ad`).

### ✅ **Robustesse et efficacité**
-   **Écriture progressive** : Les données sont sauvegardées en temps réel, garantissant aucune perte en cas d'interruption.
-   **Détection des doublons** : Le système ne traite jamais deux fois la même information.
-   **Optimisation des requêtes** : Les téléchargements lourds sont évités grâce au filtrage des images et à des requêtes ciblées.

## �� **Exemple de données enrichies**

### **`gchange_prospect.json`**
```json
{
  "uid": "7fJPzRzGidkTAr48415kmK7yKV3FT6r235BudnwCTYUx",
  "profile": {
    "pubkey": "K66QRvCQNUvYgbPF5D1v72sPKSus4KweERemDrPeHzb" 
  },
  "discovery_ad": { /* ... détails de la 1ère annonce ... */ },
  "detected_ads": [ "AXb4aa7iaml2THvBAH4B", "AYc5..."]
}
```
*Ici, la `pubkey` est le pont qui permet de déclencher l'enrichissement de l'autre base.*

### **`g1prospect.json`**
```json
{
  "pubkey": "K66QRvCQNUvYgbPF5D1v72sPKSus4KweERemDrPeHzb",
  "uid": "Fern",
  "profile": { /* Données Cesium complètes */ },
  "source": "g1_wot_discovered_via_gchange"
}
```
*Ce membre Ğ1 a été découvert grâce à son activité sur ğchange, une information marketing précieuse.*

## 🚀 **Utilisation du système**

### **Lancer la prospection Ğ1 seule**
```bash
./g1prospect_final.sh
```

### **Lancer la prospection ğchange (qui enrichit aussi la base Ğ1)**
```bash
./gchange_prospect.sh
```

## 🔄 **Synergie avec OC2UPlanet**

Ce système unifié ouvre des possibilités marketing bien plus vastes :
1.  **Identifier les acteurs économiques** : Repérer les membres Ğ1 qui sont aussi actifs sur la place de marché.
2.  **Cibler par activité commerciale** : Contacter les utilisateurs en se basant sur les produits ou services qu'ils proposent sur ğchange.
3.  **Comprendre les ponts communautaires** : Identifier les personnes qui font le lien entre les différents écosystèmes.

## ✅ **Validation**

Le système a été **entièrement testé** et validé sur ses deux volets. Il est prêt pour une utilisation en production pour alimenter des stratégies marketing avancées. 🎉 