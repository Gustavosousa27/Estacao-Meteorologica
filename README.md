
# Estação Meteorológica Inteligente

Projeto desenvolvido para a disciplina de **Projeto e Desenvolvimento II**, com o objetivo de construir uma estação meteorológica utilizando ESP32 e sensores ambientais.

A estação realiza a coleta de informações de temperatura, umidade relativa do ar, pressão atmosférica, luminosidade, qualidade do ar e presença de chuva.

Os dados são enviados pelo ESP32 para um servidor, onde são armazenados em um banco de dados MySQL e disponibilizados por meio de um dashboard web.

## Tecnologias Utilizadas

- ESP32
- Python (FastAPI)
- React e JavaScript
- MySQL
- Docker
- Nginx

## Sensores Utilizados

- **DHT22:** Temperatura e umidade relativa do ar.
- **BMP180:** Pressão atmosférica.
- **BH1750:** Luminosidade.
- **MQ-135:** Leitura analógica relacionada à presença de gases.
- **Sensor de chuva:** Detecção de água.

## Estrutura do Projeto

```text
Estacao-Meteorologica/
├── esp32/
│   └── Estacao_meteorologica/
│       └── Estacao_meteorologica.ino
├── backend/
├── frontend/
├── deployment/
├── docker-compose.yml
└── README.md
```

### Descrição das Pastas

- `esp32/` – Código responsável pela leitura dos sensores e envio das medições.
- `backend/` – API Python responsável por receber e armazenar os dados.
- `frontend/` – Interface web para visualização dos dados.
- `deployment/` – Configuração do servidor Nginx.
- `docker-compose.yml` – Configuração dos serviços Docker.

## Funcionamento

O ESP32 realiza as leituras dos sensores e envia as informações ao servidor a cada 30 segundos.

O backend recebe os dados e os armazena no banco MySQL.

O dashboard consulta essas informações e apresenta as medições atuais, gráficos históricos e avisos relacionados às condições ambientais.

## Informações Acadêmicas

**Disciplina:** Projeto e Desenvolvimento II

**Projeto:** Estação Meteorológica Inteligente

**Ano:** 2026
