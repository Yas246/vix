# Vix

**Vix** est une application Python qui génère des requêtes SQL intelligentes à partir de commandes en langage naturel. Elle utilise **LangChain** et **Google Generative AI (Gemini)**, et prend en charge plusieurs systèmes de gestion de base de données (SGBD).

---

## 🔧 Fonctionnalités

- 💬 Traduction automatique du langage naturel en requêtes SQL.
- 🧠 Intégration avec Google Gemini via LangChain.
- 🗃️ Support de plusieurs SGBD :
  - SQLite
  - PostgreSQL
  - MySQL / MariaDB
  - SQL Server
  - Oracle
- 🔐 Configuration centralisée via un fichier `.env`.
- 🛡️ Détection automatique des permissions et fallback sécurisé.

---

## 🧱 Prérequis

- Python 3.8+
- Une clé API Google valide (Gemini)
- Accès à la base de données à interroger

---

## 🚀 Installation

```bash
git clone https://github.com/tonutilisateur/vix.git
cd vix
python -m venv venv
source venv/bin/activate  # sous Windows : venv\Scripts\activate
pip install -r requirements.txt
```

---

## ⚙️ Configuration

Crée un fichier `.env` à la racine du projet :

```env
GOOGLE_API_KEY=ta_clé_google
DB_TYPE=sqlite  # postgresql, mysql, mariadb, mssql, oracle
DATABASE_URL=sqlite:///chemin/vers/ma_base.db  # ou les infos ci-dessous

DB_USER=utilisateur
DB_PASSWORD=motdepasse
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nom_de_la_base
```

Si `DATABASE_URL` est défini, les autres champs seront ignorés.

---

## ▶️ Utilisation

```bash
python app.py
```

L'application interrogera la base de données en traduisant vos questions en SQL à l’aide du LLM.

---

## 🧰 Technologies

- [LangChain](https://www.langchain.com/)
- [Google Generative AI (Gemini)](https://ai.google.dev/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

---

## 💾 Bases de données supportées

| SGBD       | URL de connexion typique                       |
| ---------- | ---------------------------------------------- |
| SQLite     | `sqlite:///ma_base.db`                         |
| PostgreSQL | `postgresql+psycopg2://user:pass@host/db`      |
| MySQL      | `mysql+pymysql://user:pass@host/db`            |
| MariaDB    | `mariadb+pymysql://user:pass@host/db`          |
| SQL Server | `mssql+pyodbc://user:pass@host/db?driver=ODBC` |
| Oracle     | `oracle+cx_oracle://user:pass@host:port/db`    |

---

## 👤 Auteur

Développé par **Yas246**

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus d'informations.
