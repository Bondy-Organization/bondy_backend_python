Projeto de Chat Distribuído
1. Visão Geral
Este projeto foi desenvolvido para a disciplina de Sistemas Distribuídos e implementa um servidor de chat de alta disponibilidade, utilizando uma arquitetura ativa/passiva para garantir a continuidade do serviço.

O núcleo do sistema é um servidor HTTP multi-threaded construído com a biblioteca socket do Python, demonstrando o funcionamento de baixo nível do protocolo. O servidor gerencia o estado da aplicação (alive/active), sincroniza-se com um nó par para definir seu papel operacional (ativo ou passivo) e utiliza a técnica de long-polling para atualizações em tempo real com os clientes. A interação com o banco de dados PostgreSQL é gerenciada através do ORM SQLAlchemy.

2. Funcionalidades
Alta Disponibilidade: Opera em um cluster ativo/passivo. Um SyncManager no nó passivo monitora continuamente a saúde do nó ativo e está pronto para assumir em caso de falha.

Atualizações em Tempo Real: Implementa um mecanismo de long-polling (/subscribe/status) que permite aos clientes receberem notificações imediatas sobre mudanças de estado do servidor sem a necessidade de polling constante.

Notificações por Grupo: Suporta o envio de notificações direcionadas para grupos específicos de clientes, otimizando a comunicação.

Integração com Banco de Dados: Utiliza o SQLAlchemy ORM para mapear objetos Python para um banco de dados PostgreSQL, gerenciando usuários, grupos e mensagens.

Servidor HTTP Customizado: Construído do zero usando a biblioteca socket para uma compreensão profunda do parse de requisições e formatação de respostas HTTP.

Arquitetura Multi-threaded: Cada conexão de cliente é tratada em uma thread separada, permitindo que o servidor gerencie múltiplas requisições concorrentes.

API de Controle RESTful: Fornece endpoints simples (/health, /fall, /revive) para monitorar e controlar o estado do servidor para fins de teste e gerenciamento.

3. Arquitetura
O sistema foi projetado para rodar em duas instâncias idênticas: uma ativa e uma passiva.

Nó Ativo: Lida com todo o tráfego dos clientes. Sua variável de ambiente IS_ACTIVE é definida como true.

Nó Passivo: Permanece em standby. Sua variável de ambiente IS_ACTIVE é false. Ele executa uma thread SyncManager que envia requisições de verificação de saúde para o endpoint /health do nó ativo.

Lógica de Failover:

O SyncManager no nó passivo verifica o nó ativo.

Se o nó ativo não responder ou relatar um status inativo, o SyncManager no nó passivo assume que o nó ativo está fora do ar.

Neste momento, o nó passivo se torna o novo nó ativo para manter o serviço operacional.

Gerenciamento de Estado: O estado operacional do servidor é controlado por duas flags globais, _is_alive e _is_active, que são acessadas de forma segura entre as threads.

Long-Polling: Clientes se conectam ao endpoint /subscribe/status. O servidor mantém essa conexão aberta até que uma mudança de estado ocorra ou um timeout seja atingido, usando uma threading.Condition para esperar eficientemente por mudanças.

4. Estrutura do Projeto
.
├── main.py             # Aplicação principal: Servidor HTTP, gestão de estado e lógica da API.
├── database/
│   └── database.py     # Configuração do banco, modelos SQLAlchemy e funções de acesso a dados.
└── .env                # Variáveis de ambiente para configuração (conexão com BD, etc.).

5. Endpoints da API
Método

Rota

Descrição

GET

/

Rota raiz para uma verificação básica de funcionamento.

GET

/health

Verifica a saúde do servidor. Retorna {'status': 'alive', 'active': true}.

POST

/fall

Define manualmente o estado do servidor para down (is_alive = False).

POST

/revive

Define manualmente o estado do servidor para alive (is_alive = True).

GET

/subscribe/status

Endpoint de long-polling para atualizações de status em tempo real.

POST

/notify/{group}

Dispara uma notificação para um grupo de clientes específico.

POST

/login

Faz login de um usuário ou cria um novo. Corpo: {'username': 'user'}.

GET

/chats

Lista os grupos aos quais um usuário pertence. Corpo: {'userId': 1}.

GET

/messages

Lista as mensagens de um grupo. Corpo: {'groupId': 1}.

POST

/messages

Envia uma mensagem para um grupo. Corpo: {'userId': 1, 'groupId': 1, 'content': 'Olá'}.

DELETE

/messages

Deleta uma mensagem pelo ID. Corpo: {'messageId': 1}.

GET

/group-users

Lista todos os usuários de um grupo. Corpo: {'groupId': 1}.

6. Instruções de Instalação e Execução
Pré-requisitos
Python (versão 3.7 ou superior)

PostgreSQL (versão 14 ou superior)

Git

Passos de Instalação
Clone o Repositório

git clone <URL_DO_SEU_REPOSITORIO>
cd <nome_da_pasta_do_projeto>

Crie e Ative um Ambiente Virtual
Isso isola as dependências do seu projeto. Lembre-se de ativar o ambiente sempre que for trabalhar no projeto.

# 1. Criar o ambiente virtual (só precisa fazer uma vez)
python -m venv venv

# 2. Ativar o ambiente (faça isso toda vez que abrir o projeto)
# No Windows (PowerShell):
.\venv\Scripts\activate

# No macOS/Linux:
source venv/bin/activate

Instale as Dependências
Com o ambiente virtual ativo, instale as bibliotecas necessárias.

pip install requests python-dotenv SQLAlchemy psycopg2-binary

(Você também pode criar um arquivo requirements.txt com essas dependências)

Prepare o Banco de Dados no PostgreSQL
O script criará as tabelas, mas o banco de dados precisa ser criado manualmente.

Abra o pgAdmin 4.

Conecte-se ao seu servidor de banco de dados.

Na árvore à esquerda, clique com o botão direito em Databases e selecione Create -> Database....

No campo "Database name", digite o nome que será usado no seu arquivo .env (ex: chat_distribuido_db).

Clique em Save.

Configure as Variáveis de Ambiente
Crie um arquivo chamado .env na raiz do projeto e adicione suas credenciais do PostgreSQL.

# .env file
DB_USER=seu_usuario_postgres
DB_PASSWORD=sua_senha_postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chat_distribuido_db # O mesmo nome criado no passo 4

# Configuração do Servidor
PORT=8080
IS_ACTIVE=true
PEER_URL=http://localhost:8081

Crie as Tabelas no Banco
Este comando executa o script que criará o esquema de tabelas dentro do banco de dados.

python database/database.py

Execute a Aplicação Principal

python main.py

O servidor estará rodando na porta definida na sua variável de ambiente (ex: http://localhost:8080).

7. Executando em Modo de Alta Disponibilidade
Para testar a arquitetura ativa/passiva, você precisará de duas instâncias rodando.

Instância 1 (Nó Ativo)
Configure seu arquivo .env:

PORT=8080
IS_ACTIVE=true
PEER_URL=http://localhost:8081 # URL do nó passivo

Inicie o servidor em um terminal:

python main.py

Instância 2 (Nó Passivo)
Abra um novo terminal.

Configure as variáveis de ambiente para esta instância (pode ser via export ou um segundo arquivo .env carregado manualmente):

# Exemplo para Linux/macOS
export PORT=8081
export IS_ACTIVE=false
export PEER_URL=http://localhost:8080 # URL do nó ativo

No Windows, use set em vez de export.

Inicie o segundo servidor neste novo terminal:

python main.py

8. Como Testar (com cURL)
Verificar a Saúde:

curl http://localhost:8080/health

Inscrever-se para Mudanças de Status (Long-Polling):
Este comando ficará aguardando até que uma mudança de status ocorra ou o timeout de 25 segundos seja atingido.

curl http://localhost:8080/subscribe/status

Simular uma Falha:
Em outro terminal, envie uma requisição para o endpoint /fall. Você verá o comando curl acima receber uma atualização imediatamente.

curl -X POST http://localhost:8080/fall

Enviar uma Mensagem:

curl -X POST -H "Content-Type: application/json" -d '{"userId": 1, "groupId": 1, "content": "Olá do cURL!"}' http://localhost:8080/messages

9. Autores
Seu Nome Completo

Nome do Colega 1

Nome do Colega 2