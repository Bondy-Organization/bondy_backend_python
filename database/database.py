# database_orm.py
# Importações de bibliotecas padrão e de terceiros
import os
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import quote_plus

# Importações do SQLAlchemy para ORM
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import sessionmaker, relationship, declarative_base, joinedload

# --- Configuração do banco de dados ---
load_dotenv()  # Carrega variáveis do .env
db_user = os.getenv("DB_USER")
raw_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_name = os.getenv("DB_NAME")
db_password = quote_plus(raw_password)  # Codifica a senha para uso na URL
DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

DATABASE_URL = os.getenv("DATABASE_URL", DATABASE_URL)  # Permite sobrescrever via .env
 
# Cria o engine de conexão e a fábrica de sessões
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()  # Classe base para os modelos ORM

# --- Definição dos Modelos ---

# Tabela de associação para relacionamento muitos-para-muitos entre User e Grupo
user_group_association = Table(
    "user_group_association",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("group_id", Integer, ForeignKey("grupos.id"), primary_key=True),
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    
    # Um usuário pode enviar muitas mensagens (um-para-muitos)
    sent_messages = relationship("Message", back_populates="sender")
    # Um usuário pode participar de vários grupos (muitos-para-muitos)
    groups = relationship("Grupo", secondary=user_group_association, back_populates="members")

class Grupo(Base):
    __tablename__ = "grupos"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.now)

    # Um grupo pode ter vários membros (muitos-para-muitos)
    members = relationship("User", secondary=user_group_association, back_populates="groups")
    # Um grupo pode ter várias mensagens (um-para-muitos)
    messages = relationship("Message", back_populates="group")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    
    # Cada mensagem tem um remetente (usuário) - muitos-para-um
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender = relationship("User", back_populates="sent_messages")

    # Cada mensagem pertence a um grupo - muitos-para-um
    group_id = Column(Integer, ForeignKey("grupos.id"), nullable=False)
    group = relationship("Grupo", back_populates="messages")

# --- Funções de Operação Seguras ---

def create_tables():
    """Cria as tabelas no banco de dados conforme os modelos definidos."""
    Base.metadata.create_all(bind=engine)
    print("Tabelas verificadas/criadas com sucesso.")

def add_user(session, username, password_hash):
    """Verifica se o usuário existe e adiciona se não existir."""
    existing_user = session.query(User).filter(User.username == username).first()
    if existing_user:
        print(f"Usuário '{username}' já existe.")
        return existing_user
    
    new_user = User(username=username, password_hash=password_hash)
    session.add(new_user)
    session.commit()
    print(f"Usuário '{username}' adicionado.")
    return new_user

def add_group(session, name):
    """Verifica se o grupo existe e adiciona se não existir."""
    existing_group = session.query(Grupo).filter(Grupo.name == name).first()
    if existing_group:
        print(f"Grupo '{name}' já existe.")
        return existing_group
        
    new_group = Grupo(name=name)
    session.add(new_group)
    session.commit()
    print(f"Grupo '{name}' adicionado.")
    return new_group

def add_user_to_group(session, user, group):
    """Adiciona um usuário a um grupo se ele ainda não for membro."""
    if user not in group.members:
        group.members.append(user)
        session.commit()
        print(f"Usuário '{user.username}' adicionado ao grupo '{group.name}'.")
    else:
        print(f"Usuário '{user.username}' já é membro do grupo '{group.name}'.")

def add_message(session, user, group, content):
    """Adiciona uma nova mensagem a um grupo."""
    new_message = Message(sender_id=user.id, group_id=group.id, content=content)
    session.add(new_message)
    session.commit()
    print(f"Mensagem de '{user.username}' adicionada ao grupo '{group.name}'.")

def populate_initial_data():
    """Popula o banco com dados iniciais de exemplo."""
    with SessionLocal() as session:
        print("\n--- Populando dados iniciais ---")
        
        # 1. Cria os usuários
        user_ana = add_user(session, 'ana_orm', 'senha123')
        user_bruno = add_user(session, 'bruno_orm', 'senha456')
        
        # 2. Cria um grupo
        grupo_geral = add_group(session, 'Grupo Geral')
        
        # 3. Adiciona os usuários ao grupo
        add_user_to_group(session, user_ana, grupo_geral)
        add_user_to_group(session, user_bruno, grupo_geral)
        
        # 4. Adiciona mensagens ao grupo (apenas se o grupo estiver vazio)
        if not grupo_geral.messages:
             add_message(session, user_ana, grupo_geral, "Oi pessoal, bem-vindos ao novo grupo!")
             add_message(session, user_bruno, grupo_geral, "Olá, Ana! Que legal que agora temos grupos.")
        else:
            print("O grupo já possui mensagens. Nenhuma mensagem de exemplo foi adicionada.")

# --- Script de Demonstração ---
if __name__ == '__main__':
    create_tables()
    populate_initial_data()