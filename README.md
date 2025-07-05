
# Projeto de Chat Distribuído

## 1. Visão Geral

Este projeto foi desenvolvido para a disciplina de Sistemas Distribuídos e implementa um servidor de chat de alta disponibilidade, utilizando uma arquitetura ativa/passiva para garantir a continuidade do serviço.

O núcleo do sistema é um servidor HTTP multi-threaded construído com a biblioteca `socket` do Python, demonstrando o funcionamento de baixo nível do protocolo. O servidor:

- Gerencia o estado da aplicação (`alive`/`active`);
- Sincroniza-se com um nó par para definir seu papel operacional (ativo ou passivo);
- Utiliza a técnica de **long-polling** para atualizações em tempo real com os clientes.

A interação com o banco de dados PostgreSQL é gerenciada através do ORM **SQLAlchemy**.

## 2. Funcionalidades

- **Alta Disponibilidade**: Cluster ativo/passivo com `SyncManager` monitorando e assumindo o controle em caso de falha.
- **Atualizações em Tempo Real**: Long-polling no endpoint `/subscribe/status`.
- **Notificações por Grupo**: Suporte à comunicação direcionada.
- **Integração com Banco de Dados**: ORM SQLAlchemy com PostgreSQL.
- **Servidor HTTP Customizado**: Baseado em `socket`, para maior controle do protocolo.
- **Arquitetura Multi-threaded**: Cada cliente é tratado em uma thread separada.
- **API de Controle RESTful**: Endpoints como `/health`, `/fall`, `/revive` para gerenciamento.

## 3. Arquitetura

O sistema roda em duas instâncias idênticas:

- **Nó Ativo**: Lida com os clientes (`IS_ACTIVE=true`)
- **Nó Passivo**: Standby, com `SyncManager` monitorando (`IS_ACTIVE=false`)

### Lógica de Failover

1. O `SyncManager` do nó passivo verifica a saúde do ativo via `/health`.
2. Se o ativo falhar, o passivo assume o controle.
3. O estado é gerenciado por flags globais: `_is_alive` e `_is_active`.

### Long-Polling

O servidor mantém a conexão do cliente aberta no endpoint `/subscribe/status`, liberando-a apenas com mudanças de estado ou timeout, utilizando `threading.Condition`.

## 4. Estrutura do Projeto

```
.
├── main.py             # Aplicação principal
├── database/
│   └── database.py     # Modelos e configuração do banco
└── .env                # Variáveis de ambiente
```

## 5. Endpoints da API

| Método | Rota                   | Descrição                                                                 |
|--------|------------------------|---------------------------------------------------------------------------|
| GET    | `/`                    | Verificação básica                                                        |
| GET    | `/health`              | Verifica se o servidor está vivo e ativo                                 |
| POST   | `/fall`                | Define o servidor como inativo (`is_alive = False`)                      |
| POST   | `/revive`              | Define o servidor como vivo (`is_alive = True`)                          |
| GET    | `/subscribe/status`    | Long-polling para mudanças de status                                     |
| POST   | `/notify/{group}`      | Notificação para grupo específico                                        |
| POST   | `/login`               | Login ou criação de usuário (`{'username': 'user'}`)                     |
| GET    | `/chats`               | Lista os grupos de um usuário (`{'userId': 1}`)                          |
| GET    | `/messages`            | Lista mensagens de um grupo (`{'groupId': 1}`)                           |
| POST   | `/messages`            | Envia mensagem para grupo (`{'userId': 1, 'groupId': 1, 'content': ''}`) |
| DELETE | `/messages`            | Deleta mensagem (`{'messageId': 1}`)                                     |
| GET    | `/group-users`         | Lista usuários de um grupo (`{'groupId': 1}`)                            |

## 6. Instruções de Instalação e Execução

### Pré-requisitos

- Python 3.7+
- PostgreSQL 14+
- Git

### Passos

#### 1. Clone o Repositório

```bash
git clone https://github.com/Bondy-Organization/bondy_backend_python.git
cd bondy_backend_python
```

#### 2. Crie e Ative um Ambiente Virtual

```bash
# Criar o ambiente
python -m venv venv

# Ativar o ambiente
# Windows:
.\venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate
```

#### 3. Instale as Dependências

```bash
pip install requests python-dotenv SQLAlchemy psycopg2-binary
```

(Opcional: use `requirements.txt` para automatizar)

#### 4. Configure o Banco de Dados

1. Crie o banco no **pgAdmin** com o nome `chat_distribuido_db`.
2. No projeto, crie um arquivo `.env`:

```env
DB_USER=seu_usuario_postgres
DB_PASSWORD=sua_senha_postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chat_distribuido_db

PORT=8080
IS_ACTIVE=true
PEER_URL=http://localhost:8081
```

#### 5. Crie as Tabelas

```bash
python database/database.py
```

#### 6. Execute a Aplicação

```bash
python main.py
```

## 7. Executando em Modo de Alta Disponibilidade

### Instância 1 (Ativa)

```env
PORT=8080
IS_ACTIVE=true
PEER_URL=http://localhost:8081
```

```bash
python main.py
```

### Instância 2 (Passiva)

#### Linux/macOS:

```bash
export PORT=8081
export IS_ACTIVE=false
export PEER_URL=http://localhost:8080
python main.py
```

#### Windows (PowerShell):

```powershell
$env:PORT=8081
$env:IS_ACTIVE="false"
$env:PEER_URL="http://localhost:8080"
python main.py
```

## 8. Como Testar (com cURL)

### Verificar saúde:

```bash
curl http://localhost:8080/health
```

### Long-polling (aguarda alteração de status):

```bash
curl http://localhost:8080/subscribe/status
```

### Simular falha:

```bash
curl -X POST http://localhost:8080/fall
```

### Enviar mensagem:

```bash
curl -X POST -H "Content-Type: application/json" \
-d '{"userId": 1, "groupId": 1, "content": "Olá do cURL!"}' \
http://localhost:8080/messages
```

## 9. Autores

- Emanuel Silva
- Emily Salum  
- Gabriel Marques  
