# Use uma imagem base oficial do Python 3.8 (compatível com seu código)
FROM python:3.8-slim-buster

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo requirements.txt para o contêiner
COPY requirements.txt .

# Instala as dependências Python
# --no-cache-dir: Evita o cache de pacotes para manter a imagem menor
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do seu código para o contêiner
# Certifique-se de que seu arquivo principal (ex: manual_http_server.py) está na raiz do seu repo
COPY . .

# Expõe a porta que seu servidor HTTP está escutando
# É CRUCIAL que esta porta corresponda à porta que seu script Python usa (8080)
EXPOSE 8080

# Comando para iniciar sua aplicação quando o contêiner for executado
# Substitua 'manual_http_server.py' pelo nome real do seu arquivo principal
CMD ["python", "main.py"]