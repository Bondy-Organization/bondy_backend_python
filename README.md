# Projeto de Chat Distribuído

Este é um projeto desenvolvido para a disciplina de Sistemas Distribuídos, que implementa um sistema de chat em tempo real (estilo WhatsApp).

## Tecnologias Utilizadas

- **Backend**: Python
- **Banco de Dados**: PostgreSQL
- **ORM**: SQLAlchemy
- **Bibliotecas**: python-dotenv, psycopg2-binary

## Pré-requisitos

Antes de começar, garanta que você tem os seguintes softwares instalados:

- Python (versão 3.10 ou superior)
- PostgreSQL (versão 14 ou superior)
- Git

## Instruções de Instalação e Execução

Siga os passos abaixo para configurar e executar o projeto em seu ambiente local.

### 1. Clone o Repositório

```bash
git clone URL_DO_SEU_REPOSITORIO_AQUI
cd nome_da_pasta_do_projeto
```

### ### 2. Crie e Ative um Ambiente Virtual

Este passo isola as dependências do seu projeto. Lembre-se: sempre que for trabalhar no projeto, você deve ativar o ambiente virtual.

```bash
# 1. Criar o ambiente virtual (só precisa fazer uma vez)
python -m venv venv

# 2. Ativar o ambiente (faça isso toda vez que abrir o projeto)
# No Windows (PowerShell):
.\venv\Scripts\activate

# No macOS/Linux:
source venv/bin/activate
```

Após ativar, você verá `(venv)` no início da linha do seu terminal.

### ### 3. Instale as Dependências

Com o ambiente virtual ativo, instale as bibliotecas listadas no requirements.txt.

```bash
pip install -r requirements.txt
```

### 4. Prepare o Banco de Dados no PostgreSQL

O script irá criar as tabelas, mas não o banco de dados. Você precisa criá-lo manualmente.

1. Abra o pgAdmin 4.
2. Conecte-se ao seu servidor de banco de dados.
3. Na árvore à esquerda, clique com o botão direito em Databases e selecione Create -> Database....
4. No campo "Database name", digite o nome exato que está no seu arquivo .env (o padrão é chat_app_db).
5. Clique em "Save".

(Dica: Se você já tinha um banco com esse nome de experimentos anteriores, é uma boa ideia deletá-lo primeiro para garantir um começo limpo.)

### 5. Configure as Variáveis de Ambiente

1. Crie o seu arquivo .env a partir do modelo .env.example.
2. Abra o arquivo .env e adicione sua senha real do PostgreSQL.

### ### 6. Crie as Tabelas no Banco

Este comando executa o script Python que irá criar o esquema de tabelas dentro do banco de dados que você preparou na etapa 4.
Certifique-se de que seu ambiente (venv) está ativo antes de rodar.

```bash
# Estando na pasta raiz do projeto
python database/database.py
```

### 7. Execute a Aplicação Principal

(Esta etapa será válida quando o servidor principal da aplicação for criado)

```bash
# Certifique-se de que o (venv) está ativo
python app.py
```

## Autores

- Seu Nome Completo
- Nome do Colega 1
- Nome do Colega 2