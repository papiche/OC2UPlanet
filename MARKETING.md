# Marketing Strategy - A Practical Guide to Prospecting in the Unified Ğ1 & ğchange Databases

## 🎯 **Vue d'ensemble**

Ce document est un **guide opérationnel** pour exploiter notre système de prospection unifié. Il fournit des exemples concrets de requêtes `jq` pour segmenter nos bases de données (`g1prospect.json` et `gchange_prospect.json`) et lancer des campagnes marketing hyper-ciblées pour OC2UPlanet et le **G1FabLab**.

### **Rappel de nos deux actifs de données**
1.  **`g1prospect.json`** : Contient tous les utilisateurs de la Ğ1 découverts, qu'ils soient **membres certifiés** (source: `g1_wot_*`) ou **simples utilisateurs de portefeuille** (source: `g1_wallet_*`). C'est notre référentiel d'identité et de localisation.
2.  **`gchange_prospect.json`** : Contient les utilisateurs **actifs sur la place de marché**. C'est notre indicateur de l'activité économique et des besoins commerciaux.

---

## 🚀 **Catalogue de stratégies de segmentation marketing**

### 1. **Ciblage par activité économique (via `gchange_prospect.json`)**

C'est notre segment le plus qualifié pour des offres commerciales.

#### **a) Par catégorie de produit/service**
*Idéal pour proposer des services spécifiques à un secteur (ex: un site vitrine pour artisans).*
```bash
# Extraire les vendeurs de la catégorie "Alimentation"
jq '.members[] | select(.discovery_ad.category.name? == "Alimentation")' gchange_prospect.json

# Extraire les artisans (catégorie "Artisanat")
jq '.members[] | select(.discovery_ad.category.name? == "Artisanat")' gchange_prospect.json
```

#### **b) Par mots-clés dans les annonces**
*Très puissant pour un ciblage fin sur des produits spécifiques.*
```bash
# Trouver les vendeurs de miel
jq '.members[] | select((.discovery_ad.title? // "") | test("miel"; "i"))' gchange_prospect.json

# Trouver ceux qui proposent des "massages"
jq '.members[] | select((.discovery_ad.description? // "") | test("massage"; "i"))' gchange_prospect.json
```

---

### 2. **Ciblage par besoin en souveraineté numérique (via `g1prospect.json`)**

Parfait pour proposer les services du **G1FabLab**.

#### **a) Par besoin technique exprimé**
*Cible les personnes qui ont probablement des problèmes à résoudre.*
```bash
# Utilisateurs mentionnant des problèmes avec leurs outils (chemin de profil normalisé)
jq '.members[] | select((.profile._source.description? // .profile.description? // "") | test("PC|smartphone|ordinateur|problème|lent|aide"; "i"))' g1prospect.json
```

#### **b) Par intérêt pour le Logiciel Libre**
*Notre cœur de cible pour les ateliers "Dégooglisation" et "Installation Linux".*
```bash
# Utilisateurs intéressés par le Libre (chemin de profil normalisé)
jq '.members[] | select((.profile._source.description? // .profile.description? // "") | test("Linux|libre|dégoogliser|open source|privacy|vie privée"; "i"))' g1prospect.json
```

---

### 3. **Ciblage par synergie Ğ1 / ğchange (la vraie puissance)**

Ici, on croise les données pour trouver les prospects les plus stratégiques.

#### **a) Acteurs économiques et membres de confiance**
*Ce sont les piliers de la communauté. Idéal pour des partenariats, des ambassadeurs.*
```bash
# Étape 1: Extraire les pubkeys des membres actifs sur ğchange
jq -r '.members[].profile.pubkey | select(. != null)' gchange_prospect.json > gchange_pubkeys.txt

# Étape 2: Filtrer la base Ğ1 pour ne garder que les membres certifiés qui sont aussi sur ğchange
jq --slurpfile keys gchange_pubkeys.txt \
  '.members[] | select(.source | startswith("g1_wot")) | select(.pubkey | IN($keys[]))' g1prospect.json
```

#### **b) Vendeurs locaux pour un événement**
*Permet d'animer un marché local en invitant les bonnes personnes.*
```bash
# Scénario : Marché à Toulouse (31)

# Étape 1: Extraire les pubkeys des membres Ğ1 de la région de Toulouse (requête robuste)
jq -r '.members[] | select((.profile._source.city? // .profile.city? // "") | contains("31")) | .pubkey' g1prospect.json > toulouse_pubkeys.txt

# Étape 2: Filtrer la base ğchange pour trouver les vendeurs de cette région
jq --slurpfile keys toulouse_pubkeys.txt \
  '.members[] | select(.profile.pubkey | IN($keys[]))' gchange_prospect.json
```

---

### 4. **Ciblage par profil démographique (via `g1prospect.json`)**

Utile pour adapter le ton de la communication.

#### **a) Par ville ou code postal**
*Pour des campagnes hyper-locales. C'est la requête qui a été corrigée.*
```bash
# Trouver les membres à Nantes (requête robuste qui gère les profils sans ville)
jq '.members[] | select((.profile._source.city? // .profile.city? // "") | test("Nantes|44000|44100|44200|44300"; "i"))' g1prospect.json
```

#### **b) Par présence sur les réseaux sociaux**
*Pour identifier des relais d'opinion.*
```bash
# Trouver les membres ayant un profil Facebook (requête robuste)
jq '.members[] | select( (.profile._source.socials? // .profile.socials? // [])[] | .type == "facebook" )' g1prospect.json

# Trouver les membres ayant un site web (requête robuste)
jq '.members[] | select( (.profile._source.socials? // .profile.socials? // [])[] | .type == "website" )' g1prospect.json
```

## 📈 **Plan d'action et outils**

Le plan d'action reste valide, mais nos outils de segmentation doivent être mis à jour pour refléter ces nouvelles capacités.

### **`segment_gchange.sh` (Script unifié et robuste)**
```bash
#!/bin/bash
# Script de segmentation avancé pour la base ğchange
# Usage: ./segment_gchange.sh category "Alimentation"
#        ./segment_gchange.sh title "miel"

FIELD=$1
QUERY=$2
# Utilise les arguments jq pour la sécurité et la robustesse
jq --arg field "$FIELD" --arg query "$QUERY" \
  '.members[] | select((.discovery_ad[$field]? // "") | test($query; "i"))' gchange_prospect.json
```

### **`find_trusted_sellers.sh` (Script stratégique)**
```bash
#!/bin/bash
# Identifie les membres de confiance qui sont actifs sur ğchange
jq -r '.members[].profile.pubkey | select(. != null)' gchange_prospect.json > gchange_pubkeys.txt
jq --slurpfile keys gchange_pubkeys.txt \
  '.members[] | select(.source | startswith("g1_wot")) | select(.pubkey | IN($keys[]))' g1prospect.json
```

---
*Document mis à jour le 25 juillet 2025 - Version 3.0* 