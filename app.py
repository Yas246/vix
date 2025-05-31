# --- PARTIE 1: IMPORTS ET CONFIGURATION ---
import os
import re
from dotenv import load_dotenv
from typing import Dict, Any, Optional
import json

# Imports de LangChain
from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from operator import itemgetter
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough

# Charger les variables d'environnement
load_dotenv()

# Vérifier que la clé API est bien chargée
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("Clé API Google manquante...")

# --- PARTIE 2: CONFIGURATION MULTI-BASES DE DONNÉES ---

class DatabaseConfig:
    """Gestionnaire de configuration pour différents types de bases de données"""
    
    # Configurations prédéfinies pour différents types de BDD
    DB_CONFIGS = {
        "sqlite": {
            "driver": "sqlite",
            "port": None,
            "example_uri": "sqlite:///ma_base.db",
            "description": "Base de données SQLite locale",
            "required_env": []
        },
        "postgresql": {
            "driver": "postgresql+psycopg2",
            "port": 5432,
            "example_uri": "postgresql+psycopg2://user:password@localhost:5432/database",
            "description": "Base de données PostgreSQL",
            "required_env": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME"]
        },
        "mysql": {
            "driver": "mysql+pymysql",
            "port": 3306,
            "example_uri": "mysql+pymysql://user:password@localhost:3306/database",
            "description": "Base de données MySQL",
            "required_env": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME"]
        },
        "mariadb": {
            "driver": "mariadb+pymysql",
            "port": 3306,
            "example_uri": "mariadb+pymysql://user:password@localhost:3306/database",
            "description": "Base de données MariaDB",
            "required_env": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME"]
        },
        "mssql": {
            "driver": "mssql+pyodbc",
            "port": 1433,
            "example_uri": "mssql+pyodbc://user:password@server:1433/database?driver=ODBC+Driver+17+for+SQL+Server",
            "description": "Base de données SQL Server",
            "required_env": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME"]
        },
        "oracle": {
            "driver": "oracle+cx_oracle",
            "port": 1521,
            "example_uri": "oracle+cx_oracle://user:password@localhost:1521/xe",
            "description": "Base de données Oracle",
            "required_env": ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME"]
        }
    }
    
    @classmethod
    def list_supported_databases(cls):
        """Affiche la liste des bases de données supportées"""
        print("\n🗄️  Bases de données supportées :")
        print("=" * 50)
        for db_type, config in cls.DB_CONFIGS.items():
            print(f"• {db_type.upper()}: {config['description']}")
            print(f"  Port par défaut: {config['port'] or 'N/A'}")
            print(f"  Exemple URI: {config['example_uri']}")
            print()
    
    @classmethod
    def build_uri_from_env(cls, db_type: str) -> str:
        """Construit l'URI de connexion à partir des variables d'environnement"""
        if db_type not in cls.DB_CONFIGS:
            raise ValueError(f"Type de base de données non supporté: {db_type}")
        
        config = cls.DB_CONFIGS[db_type]
        
        # Pour SQLite, utiliser directement le chemin du fichier
        if db_type == "sqlite":
            db_path = os.getenv("DB_PATH", "ma_base.db")
            return f"sqlite:///{db_path}"
        
        # Pour les autres BDD, construire l'URI complète
        required_vars = config["required_env"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"Variables d'environnement manquantes pour {db_type}: {missing_vars}")
        
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", str(config["port"]))
        database = os.getenv("DB_NAME")
        
        driver = config["driver"]
        
        # Construction de l'URI selon le type de BDD
        if db_type in ["postgresql", "mysql", "mariadb"]:
            return f"{driver}://{user}:{password}@{host}:{port}/{database}"
        elif db_type == "mssql":
            driver_param = os.getenv("ODBC_DRIVER", "ODBC+Driver+17+for+SQL+Server")
            return f"{driver}://{user}:{password}@{host}:{port}/{database}?driver={driver_param}"
        elif db_type == "oracle":
            service_name = os.getenv("DB_SERVICE_NAME", "xe")
            return f"{driver}://{user}:{password}@{host}:{port}/{service_name}"
        
        return f"{driver}://{user}:{password}@{host}:{port}/{database}"

def get_database_connection() -> SQLDatabase:
    """Établit la connexion à la base de données selon la configuration"""
    
    # Méthode 1: URI directe dans .env
    db_uri = os.getenv("DATABASE_URL")
    if db_uri:
        print(f"📡 Connexion via DATABASE_URL...")
        return create_safe_db_connection(db_uri)
    
    # Méthode 2: Configuration par type de BDD
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    print(f"📡 Connexion à une base de données {db_type.upper()}...")
    
    try:
        db_uri = DatabaseConfig.build_uri_from_env(db_type)
        print(f"🔗 URI générée: {db_uri.split('@')[0]}@***" if '@' in db_uri else db_uri)
        return create_safe_db_connection(db_uri)
    except Exception as e:
        print(f"❌ Erreur de configuration pour {db_type}: {e}")
        print("\n💡 Vérifiez votre fichier .env ou utilisez DATABASE_URL directement")
        DatabaseConfig.list_supported_databases()
        raise

def create_safe_db_connection(db_uri: str) -> SQLDatabase:
    """Crée une connexion sécurisée avec gestion des permissions limitées"""
    
    print(f"🔌 Tentative de connexion...")
    
    # Essai 1: Connexion standard
    try:
        db = SQLDatabase.from_uri(db_uri, connect_argrs={"connect_timeout": 10})
        print("✅ Connexion standard réussie")
        return db
    except Exception as e:
        print(f"⚠️  Connexion standard échouée: {str(e)[:100]}...")
        
        # Essai 2: Connexion avec paramètres restreints
        if "permission denied" in str(e).lower() or "insufficient" in str(e).lower():
            print("🔄 Tentative en mode restreint...")
            try:
                db = SQLDatabase.from_uri(
                    db_uri,
                    sample_rows_in_table_info=1,
                    max_string_length=100,
                    lazy_table_reflection=True  
                )
                print("✅ Connexion restreinte réussie")
                return db
            except Exception as e2:
                print(f"⚠️  Mode restreint échoué: {str(e2)[:100]}...")
        
        # Essai 3: Connexion SQLAlchemy directe
        print("🔄 Tentative avec SQLAlchemy direct...")
        try:
            import sqlalchemy
            from sqlalchemy import create_engine
            
            engine = create_engine(db_uri)
            
            # Test de connexion basique
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            
            # Créer l'objet SQLDatabase manuellement
            db = SQLDatabase(engine=engine)
            print("✅ Connexion SQLAlchemy directe réussie")
            return db
            
        except Exception as e3:
            print(f"❌ Toutes les tentatives ont échoué")
            print(f"Dernière erreur: {str(e3)[:200]}...")
            
            # Diagnostic plus détaillé
            if "could not connect" in str(e3).lower():
                print("🔍 Problème de connectivité réseau ou de serveur")
            elif "authentication" in str(e3).lower() or "password" in str(e3).lower():
                print("🔍 Problème d'authentification (login/mot de passe)")
            elif "database" in str(e3).lower() and "does not exist" in str(e3).lower():
                print("🔍 La base de données spécifiée n'existe pas")
            elif "driver" in str(e3).lower():
                print("🔍 Driver de base de données manquant")
                db_type = os.getenv("DB_TYPE", "").lower()
                if db_type == "postgresql":
                    print("💡 Installez: pip install psycopg2-binary")
                elif db_type == "mysql":
                    print("💡 Installez: pip install pymysql")
                elif db_type == "mssql":
                    print("💡 Installez: pip install pyodbc")
            
            raise Exception(f"Impossible de se connecter: {str(e3)}")

# --- PARTIE 3: PROMPTS ADAPTÉS PAR TYPE DE BDD ---

def get_database_specific_prompt(db_type: str) -> str:
    """Retourne un prompt adapté au type de base de données"""
    
    base_prompt = """Tu es un expert en bases de données. Génère une requête SQL pour répondre à la question de l'utilisateur.
    
Règles importantes:
- Utilise uniquement les tables et colonnes qui existent dans le schéma fourni
- La requête doit être syntaxiquement correcte pour {db_type}
- Limite les résultats à 100 lignes maximum avec LIMIT
- Pour les recherches textuelles, utilise la syntaxe appropriée à {db_type}
- N'utilise que SELECT, pas de modification de données
"""
    
    # Ajouts spécifiques par type de BDD
    db_specifics = {
        "sqlite": "- Utilise LIKE pour les recherches textuelles (sensible à la casse)\n- Date/time avec strftime() si nécessaire",
        "postgresql": "- Utilise ILIKE pour les recherches insensibles à la casse\n- Fonctions PostgreSQL natives disponibles",
        "mysql": "- Utilise LIKE (insensible à la casse par défaut)\n- Fonctions MySQL disponibles",
        "mssql": "- Utilise LIKE avec COLLATE pour contrôler la casse\n- Fonctions SQL Server disponibles",
        "oracle": "- Utilise UPPER() avec LIKE pour recherches insensibles à la casse\n- Fonctions Oracle disponibles"
    }
    
    specific_rules = db_specifics.get(db_type, "- Utilise la syntaxe SQL standard")
    
    return base_prompt.format(db_type=db_type.upper()) + "\n" + specific_rules

# --- PARTIE 4: CONNEXION ET CONFIGURATION DU MODÈLE ---

try:
    # Connexion à la base de données
    db = get_database_connection()
    
    # Détecter le type de BDD à partir de l'URI
    try:
        # Essayer différentes façons d'accéder à l'URL de la BDD selon la version de LangChain
        if hasattr(db, 'engine'):
            db_uri_lower = str(db.engine.url).lower()
        elif hasattr(db, '_engine'):
            db_uri_lower = str(db._engine.url).lower()
        elif hasattr(db, 'database_uri'):
            db_uri_lower = str(db.database_uri).lower()
        else:
            # Fallback : essayer de récupérer l'URI depuis les variables d'environnement
            env_uri = os.getenv("DATABASE_URL") or DatabaseConfig.build_uri_from_env(os.getenv("DB_TYPE", "sqlite"))
            db_uri_lower = env_uri.lower()
    except Exception as e:
        print(f"⚠️  Impossible de détecter le type de BDD automatiquement: {e}")
        # Fallback basé sur la configuration
        db_uri_lower = os.getenv("DB_TYPE", "sqlite").lower()
    if "sqlite" in db_uri_lower:
        detected_db_type = "sqlite"
    elif "postgresql" in db_uri_lower:
        detected_db_type = "postgresql"
    elif "mysql" in db_uri_lower or "mariadb" in db_uri_lower:
        detected_db_type = "mysql"
    elif "mssql" in db_uri_lower:
        detected_db_type = "mssql"
    elif "oracle" in db_uri_lower:
        detected_db_type = "oracle"
    else:
        detected_db_type = "unknown"
    
    print(f"✅ Connexion réussie ! Type détecté: {detected_db_type.upper()}")
    
    # Test de connexion sécurisé
    try:
        test_result = db.run("SELECT 1")
        print(f"🔍 Test de connexion: OK")
        
        # Essayer d'obtenir des infos sur le schéma de manière sécurisée
        try:
            table_info = db.get_table_info()
            if table_info and len(table_info) > 10:
                table_count = len([line for line in table_info.split('\n') if 'CREATE TABLE' in line.upper()])
                print(f"📊 Nombre de tables détectées: {table_count}")
            else:
                print("📊 Schéma: Accès limité aux métadonnées")
        except Exception as schema_error:
            print(f"📊 Schéma: Accès restreint ({str(schema_error)[:50]}...)")
            
            # Pour les BDD avec permissions limitées, on essaie une approche manuelle
            if detected_db_type == "postgresql":
                try:
                    # Requête basique pour lister les tables publiques
                    tables_result = db.run("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        LIMIT 10
                    """)
                    print(f"📋 Tables publiques trouvées: {len(tables_result.split()) if tables_result else 0}")
                except Exception as e:
                    print(f"📋 Impossible de lister les tables: accès très restreint")
        
    except Exception as e:
        print(f"⚠️  Attention: Test de connexion échoué: {e}")
        # On continue quand même, la connexion de base fonctionne peut-être

except Exception as e:
    print(f"❌ Impossible de se connecter à la base de données: {e}")
    print("\n🔧 Solutions possibles:")
    print("1. Vérifiez vos identifiants de connexion")
    print("2. Vérifiez que l'utilisateur a les permissions nécessaires")
    print("3. Pour des BDD publiques, essayez avec des permissions limitées")
    print("\nExemple de fichier .env:")
    print("""
# Pour SQLite:
DB_TYPE=sqlite
DB_PATH=ma_base.db

# Pour PostgreSQL avec permissions limitées:
DB_TYPE=postgresql
DB_USER=reader
DB_PASSWORD=motdepasse
DB_HOST=serveur.com
DB_PORT=5432
DB_NAME=database_name

# Ou directement:
DATABASE_URL=postgresql://user:pass@host:port/db
    """)
    exit(1)

# Configuration du modèle LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

# --- PARTIE 5: CRÉATION DE LA CHAÎNE LANGCHAIN ADAPTÉE ---

# Chaîne pour écrire la requête SQL avec prompt adapté
write_query_chain = create_sql_query_chain(llm, db)

# Outil pour exécuter la requête SQL
execute_query_tool = QuerySQLDataBaseTool(db=db)

# Prompt pour la réponse finale adapté au type de BDD
answer_prompt = PromptTemplate.from_template(
    f"""Tu es un assistant expert en bases de données {detected_db_type.upper()}.
    Réponds à la question de l'utilisateur en français de manière claire et structurée.
    
    Si aucun résultat n'est trouvé, explique pourquoi de façon constructive.
    Si les résultats sont nombreux, présente-les de manière organisée.
    Si la requête a des limites, mentionne-le à l'utilisateur.

Question: {{question}}
Requête SQL ({detected_db_type.upper()}): {{query}}
Résultat: {{result}}

Réponse détaillée: """
)

# Assemblage de la chaîne complète
answer_chain = (
    RunnablePassthrough.assign(query=write_query_chain).assign(
        result=itemgetter("query") | execute_query_tool
    )
    | answer_prompt
    | llm
    | StrOutputParser()
)

# --- PARTIE 6: VALIDATION DE SÉCURITÉ ---

def validate_sql_query(query: str, db_type: str) -> bool:
    """Valide la requête SQL pour éviter les opérations dangereuses"""
    dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE', 'TRUNCATE', 'REPLACE']
    query_upper = query.upper()
    
    for keyword in dangerous_keywords:
        if keyword in query_upper:
            raise ValueError(f"❌ Requête non autorisée détectée: {keyword}")
    
    # Vérifications spécifiques par type de BDD
    if db_type == "mssql" and any(cmd in query_upper for cmd in ['EXEC', 'EXECUTE', 'SP_']):
        raise ValueError("❌ Exécution de procédures stockées non autorisée")
    
    return True

# --- PARTIE 7: INTERFACE UTILISATEUR AMÉLIORÉE ---

print(f"""
🤖 Assistant SQL IA Multi-Bases de Données
Base de données: {detected_db_type.upper()}
Connexion: ✅ Active

💡 Exemples de questions:
   • 'Combien de lignes dans chaque table ?'
   • 'Montre-moi les 10 premiers enregistrements de [table]'
   • 'Quelles sont les colonnes de la table [nom] ?'
   • 'Cherche tous les enregistrements contenant [terme]'

📝 Tapez 'quitter' pour arrêter
📋 Tapez 'schema' pour voir la structure des tables
""")

while True:
    question = input(f"\n[{detected_db_type.upper()}] Posez votre question : ")
    
    if question.lower() == 'quitter':
        print("👋 Au revoir !")
        break
    
    if question.lower() == 'schema':
        print("\n📋 Structure de la base de données:")
        print("=" * 50)
        try:
            schema_info = db.get_table_info()
            if schema_info and len(schema_info) > 10:
                print(schema_info[:2000] + "..." if len(schema_info) > 2000 else schema_info)
            else:
                print("ℹ️  Informations de schéma limitées. Essayons une approche alternative...")
                
                # Pour PostgreSQL avec permissions limitées
                if detected_db_type == "postgresql":
                    try:
                        tables_query = """
                        SELECT table_name, column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        ORDER BY table_name, ordinal_position
                        LIMIT 50
                        """
                        result = db.run(tables_query)
                        print("Tables et colonnes disponibles:")
                        print(result)
                    except Exception as e:
                        print(f"Impossible d'accéder au schéma: {e}")
                        print("💡 Essayez de poser des questions directement sur les données")
        except Exception as e:
            print(f"Erreur d'accès au schéma: {e}")
            print("💡 Permissions insuffisantes. Essayez des requêtes directes comme:")
            print("   • 'Montre-moi quelques lignes de la première table'")
            print("   • 'Liste les tables disponibles'")
        continue
    
    if not question.strip():
        continue

    try:
        print(f"\n🔍 [DÉBOGAGE] Analyse de la question pour {detected_db_type.upper()}...")
        
        # Génération de la requête SQL
        generated_query = write_query_chain.invoke({"question": question})
        print(f"📝 Requête générée:\n{generated_query}")
        
        # Nettoyage de la requête
        cleaned_query = re.sub(r"```(?:\w+)?\s*", "", generated_query).replace("```", "").strip()
        
        # Validation de sécurité
        validate_sql_query(cleaned_query, detected_db_type)
        
        # Exécution de la requête
        print(f"⚡ Exécution sur {detected_db_type.upper()}...")
        query_result = execute_query_tool.invoke({"query": cleaned_query})
        print(f"📊 Résultat obtenu: {len(str(query_result))} caractères")
        
        # Génération de la réponse finale
        final_prompt_input = {
            "question": question,
            "query": cleaned_query,
            "result": query_result
        }
        
        final_chain_part = answer_prompt | llm | StrOutputParser()
        response = final_chain_part.invoke(final_prompt_input)
        
        print(f"\n✅ Réponse finale:")
        print("=" * 50)
        print(response)

    except ValueError as e:
        print(f"\n🚫 {e}")
    except Exception as e:
        print(f"\n❌ Erreur lors du traitement: {e}")
        if "syntax" in str(e).lower():
            print(f"💡 Cette erreur peut être liée aux spécificités du dialecte SQL {detected_db_type.upper()}")