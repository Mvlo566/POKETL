
# POKETL

POKETL est une suite d’outils Python pour automatiser le scraping, l’analyse et l’injection de données de tournois Pokémon Pocket (LimitlessTCG) dans une base PostgreSQL.
Le projet propose une interface terminal avec menu animé (ASCII/Pikachu) pour lancer tous les scripts de traitement en 1 clic.

## 🚀 Fonctionnalités principales

- Scraping automatisé des tournois Pokémon sur LimitlessTCG : decklists, joueurs, résultats, etc.
- Transformation des données brutes en fichiers JSON structurés, exploitables par les scripts d’insertion.
- Injection PostgreSQL optimisée et séquentielle (cartes, joueurs, tournois, matches, decklists, résultats).
- Interface terminal stylée et animée pour gérer tous les traitements.
- Logs détaillés et suivi en temps réel pour chaque étape.
- Organisation modulaire : chaque script est indépendant, relançable séparément ou via le launcher.

---

## 📦 Structure du projet

```
.
├── launcher.py           # Lancement de l’interface terminal animée (menu principal)
├── scripts/              # Tous les scripts d’insertion et utilitaires
│   ├── scraping_tournaments.py     # Scraping LimitlessTCG → JSON
│   ├── insert_wrk_cards.py         # Insertion cartes dans PostgreSQL
│   ├── insert_wrk_players.py       # Insertion joueurs
│   ├── insert_wrk_tournaments.py   # Insertion tournois
│   ├── insert_wrk_matches.py       # Insertion matches
│   ├── insert_wrk_decklists.py     # Insertion decklists
│   ├── insert_wrk_results.py       # Insertion résultats
│   └── export_railway.py           # Export de la base (optionnel, ex : Railway)
├── GIF/                  # Animations ASCII/GIF pour l’UI
│   └── pikachu_loading.gif, folder.gif, etc.
├── sample_output/        # Exemples de fichiers JSON générés
├── requirements.txt      # Dépendances Python
└── .env                  # Variables d’environnement (connexion PostgreSQL)
```

---

## 🚦 Utilisation rapide

1. **Cloner le repo**
    ```bash
    git clone https://github.com/Mvlo566/POKETL.git
    cd POKETL
    ```

2. **Installer les dépendances**
    ```bash
    pip install -r requirements.txt
    ```

3. **Configurer la connexion PostgreSQL**  
    Remplir le fichier `.env` avec tes paramètres (hôte, user, mdp…).

4. **Lancer l’interface terminal**
    ```bash
    python launcher.py
    ```

5. **Ou exécuter un script spécifique**
    ```bash
    python scripts/insert_wrk_players.py
    ```

---

## 💾 Dépendances principales

- psycopg2
- python-dotenv
- Pillow
- xlwings, openpyxl (pour extraction Excel, si besoin)
- requests, beautifulsoup4
- blessed (interface terminal animée)
- (voir `requirements.txt` pour tout)

---

## 📝 Notes & recommandations

- **L’ordre des scripts d’insertion** :  
  `insert_wrk_cards.py` → `insert_wrk_decklists.py` → `insert_wrk_tournaments.py` → `insert_wrk_players.py` → `insert_wrk_matches.py` → `insert_wrk_results.py`
- **Tout est loggé** : chaque script affiche les erreurs et étapes en temps réel.
- **Modulaire** : chaque script peut être relancé séparément, relance = maj incrémentale (pas d’écrasement).
- **Le launcher.py** gère tout avec menu ASCII stylé et animation Pikachu en bonus 😎

---

## 👤 Auteur

- [Mvlo](https://github.com/Mvlo566)
- Contact : malo.leniniven@proton.me

---
