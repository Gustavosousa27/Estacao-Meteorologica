# Estação Meteorológica Inteligente

Aplicação independente de monitoramento ambiental com ESP32. FastAPI, SQLAlchemy, Alembic, React/Vite, Recharts, MySQL 8.4 e NGINX. O ZIP original foi consultado como referência de organização e visual; não foi alterado. Não há funcionalidades de GLPI nem alterações no firmware.

## Estrutura

- `backend/app`: configuração, modelos, validação, autenticação e endpoints.
- `backend/migrations`: migrations Alembic; cria a estação inicial `estacao-01`.
- `backend/tests`: testes automatizados.
- `backend/simulate.py`: simulação HTTP e geração de histórico fictício.
- `frontend/src`: home pública, monitoramento, avisos/alarmes e temas.
- `deployment/nginx.conf`: frontend e proxy reverso para API/Swagger.
- `scripts/setup.ps1`: gera segredos no `.env` sem sobrescrever arquivo existente.
- `scripts/backup.ps1`: backup MySQL compatível com PowerShell.
- `docker-compose.yml`: containers, rede, healthchecks e volume persistente.

## Windows: pré-requisitos e instalação

Use Windows compatível com o Docker Desktop, virtualização habilitada e espaço livre para imagens e banco. Em PowerShell administrativo:

```powershell
wsl --install
wsl --update
wsl --set-default-version 2
```

Reinicie se solicitado. Instale e abra o [Docker Desktop para Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Ative **Use the WSL 2 based engine** e utilize containers Linux. Veja a [documentação do backend WSL 2](https://docs.docker.com/desktop/features/wsl/). `docker version` deve mostrar Client e Server; confira também `docker compose version`.

Na pasta do projeto:

```powershell
Set-Location S:\estacao-meteorologica-inteligente
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
docker compose up -d --build
docker compose ps
docker compose logs -f backend
```

O setup gera senhas aleatórias no `.env`; não imprime os segredos. Alternativamente copie `.env.example` para `.env` e preencha os valores vazios. Não versione esse arquivo. Se editar valores com `$`, use aspas simples no `.env` para impedir interpolação do Compose.

| Variável | Uso |
|---|---|
| HTTP_PORT | Porta HTTP pública, padrão 8080 |
| MYSQL_DATABASE / MYSQL_USER | Banco e usuário da aplicação |
| MYSQL_PASSWORD / MYSQL_ROOT_PASSWORD | Senhas distintas do banco |
| ADMIN_USERNAME / ADMIN_PASSWORD | Administração; senha com mínimo 16 caracteres |
| OFFLINE_SECONDS | Offline sem comunicação: padrão 90s, mínimo 30s |
| INTERFACE_TIMEZONE | Fuso IANA: America/Sao_Paulo por padrão |

O backend também aceita `DATABASE_URL` em execução local/testes; no Compose a conexão é construída com DB_HOST, DB_NAME, DB_USER e DB_PASSWORD. Não é necessário configurá-la no Compose.

Acessos (ajuste a porta se necessário):

- Frontend: http://localhost:8080
- Swagger: http://localhost:8080/docs
- OpenAPI: http://localhost:8080/openapi.json
- Saúde com consulta ao banco: http://localhost:8080/api/health

Somente NGINX publica porta. API e MySQL ficam na rede interna Docker. Healthchecks aguardam banco, migrations e API antes de iniciar o frontend. O volume nomeado `weather_mysql` recebe o prefixo do projeto Compose.

**Disco S:** manter o código no S: não transfere automaticamente os discos virtuais do Docker. Se C: estiver cheio, configure a localização de dados/disco do Docker Desktop para um disco com espaço, conforme a opção disponível em sua versão, antes de construir os containers. Não apague discos virtuais manualmente.

## Interface e autenticação

O dashboard atualiza a cada dez segundos e mostra temperatura, umidade, pressão, lux, MQ-135 e água detectada. Estações sem comunicação por mais de OFFLINE_SECONDS ficam offline. Ausência de leitura aparece como “Indisponível”. A última leitura pode continuar visível enquanto a estação está offline, com horário e status identificados.

Seis gráficos independentes usam agregação no banco. Temperatura, umidade, pressão, luminosidade e ADC mostram médias por intervalo. Chuva indica presença em ao menos uma amostra; não representa milímetros. Não há conversão de MQ-135 para ppm, CO₂ ou índice oficial. Intervalos sem amostras não geram pontos; valores nulos não viram zero.

Selecione uma, duas, três, quatro, cinco ou seis horas, 24 horas, sete dias, trinta dias ou período personalizado. A interface apresenta somente a estação principal; a página de histórico foi removida, preservando os dados e endpoints existentes. Armazenamento é UTC; respostas possuem offset UTC. Horários exibidos usam INTERFACE_TIMEZONE. Seletores personalizados usam o fuso do computador, indicado no formulário, e enviam UTC.

A interface pública apresenta somente Início e Monitoramento. Não há edição de estação ou de limites de avisos no site. As mensagens e limites são definidos no backend, conforme a tabela abaixo.

A administração utiliza HTTP Basic, disponível também no Swagger; consulte os [mecanismos de segurança do FastAPI](https://fastapi.tiangolo.com/reference/security/). Nesta etapa HTTP destina-se à rede local confiável. Para publicar na internet, configure HTTPS e controle de acesso na infraestrutura, pois as credenciais dependem de transporte protegido.

## API

| Método | Endpoint | Acesso |
|---|---|---|
| POST | /api/measurements | Público, sem chave |
| GET | /api/station | Estação principal e regras; público |
| GET | /api/station/alerts | Avisos e alarmes atuais; público |
| GET | /api/stations | Público; compatibilidade e simulador |
| POST | /api/stations | Basic administrativo |
| PUT | /api/stations/{id} | Basic administrativo |
| GET | /api/stations/{id}/latest | Público |
| GET | /api/stations/{id}/measurements | Público |
| GET | /api/stations/{id}/summary | Público |
| GET | /api/stations/{id}/series | Público |
| GET | /api/stations/{id}/export.csv | Público |
| GET | /api/health e /api/config | Público, sem segredos |

`{id}` nas URLs é numérico, retornado na lista de estações. `station_id` no POST é o identificador textual (`estacao-01`). A estação precisa estar cadastrada; desconhecida retorna 404. Sensores aceitam `null` ou omissão. Campos extras são rejeitados; data/hora é sempre atribuída pelo servidor.

Faixas: DHT22 −40 a 80 °C; umidade 0–100%; BMP180 −40 a 85 °C, pressão 300–1100 hPa; luz 0–200000 lux; ADC inteiro 0–4095; GPIO inteiro 0–3300 mV; AO estimado inteiro 0–6600 mV; chuva booleano e digital inteiro 0/1. Ajuste faixas se mudar o hardware. A polaridade digital de chuva depende da montagem; não há equivalência forçada entre os dois campos.

Histórico, resumo, série e CSV aceitam `start` e `end` ISO 8601 **com fuso**, por exemplo `2026-11-01T00:00:00-03:00`. Histórico aceita `page` >= 1, `limit` entre 1 e 1000, `order=asc|desc`. Há desempate por ID e índice composto estação/horário/ID.

Resumo retorna contagem, mínimo, máximo e média de cada variável numérica e contagem de amostras com chuva (não eventos independentes). Nulos são ignorados nos agregados. Série exige início/fim e `bucket_seconds` entre 60 e 86400, com até 1000 intervalos. A interface escolhe aproximadamente 400 pontos. CSV exporta todo o período, independentemente da página atual, limitado a 100000 registros; acima disso reduza o período.

Respostas: 201 para criação, 401 autenticação, 404 estação inexistente, 409 identificador duplicado, 422 validação e 503 falha de banco. Logs não incluem senhas, chaves ou corpo das requisições.

## Simulação sem ESP32

Gere 24 horas de leituras fictícias a cada 30 segundos:

```powershell
docker compose exec -T backend python simulate.py --seed-hours 24
```

A geração histórica usa conexão direta com o banco, exclusivamente em `demo-01`, identificada como demonstração. A API pública de ingestão não aceita datas forjadas. O comando aceita 1 a 720 horas; executá-lo novamente acrescenta registros. Se `demo-01` já existir como estação real, a operação é recusada. A demonstração continua disponível pela API e pelo simulador, mas não aparece no dashboard da estação principal.

Teste o POST HTTP com atualização contínua, sem chave:

```powershell
docker compose exec -T backend python simulate.py --url http://frontend --count 10 --interval 30
```


Fora do Docker, execute `python backend/simulate.py --url http://localhost:8080 --count 10`, sem configurar chave.

### PowerShell

Após criar demo-01, envie dados fictícios sem autenticação:

```powershell
$payload = @{
  station_id = 'demo-01'
  temperature_c = 28.7
  humidity_pct = 71.8
  pressure_hpa = 920.37
  bmp_temperature_c = 28.4
  luminosity_lux = 10.0
  gas_adc_raw = 318
  gas_gpio_mv = 397
  gas_ao_mv_estimated = 794
  rain_detected = $false
  rain_sensor_digital = 1
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://localhost:8080/api/measurements' -ContentType 'application/json' -Body $payload
```

Resposta HTTP 201: `{"success":true,"message":"Medicao registrada com sucesso","measurement_id":1}` (ID varia).

### curl (Bash)

Com demo-01 previamente criada:


```bash
curl --fail-with-body http://localhost:8080/api/measurements \
  -H 'Content-Type: application/json' \
  -d '{"station_id":"demo-01","temperature_c":28.7,"humidity_pct":71.8,"pressure_hpa":920.37,"bmp_temperature_c":28.4,"luminosity_lux":10.0,"gas_adc_raw":318,"gas_gpio_mv":397,"gas_ao_mv_estimated":794,"rain_detected":false,"rain_sensor_digital":1}'
```

## ESP32: próxima etapa

Execute `ipconfig` e identifique o IPv4 do Wi-Fi/Ethernet na mesma rede do ESP32. Use futuramente `http://IP_DO_WINDOWS:8080/api/measurements`, nunca localhost no microcontrolador. Teste `/api/health` de outro aparelho. Se necessário, permita a porta TCP escolhida no Firewall apenas no perfil privado; redes de visitantes podem impedir comunicação local. Não é necessário expor MySQL. I²C separado do BH1750/BMP180, divisor do MQ-135 e firmware permanecem como estão.

## Banco e migrations

```powershell
docker compose exec db mysql -u weather -p weather
```

Digite MYSQL_PASSWORD quando solicitado. Ajuste usuário/banco se alterados.

```sql
SELECT id, identifier, name, is_demo, last_seen FROM stations;
SELECT * FROM measurements ORDER BY received_at DESC LIMIT 10;
SELECT * FROM alembic_version;
```

Migrations são aplicadas antes do servidor iniciar:

```powershell
docker compose exec backend alembic current
docker compose logs --tail 100 db backend frontend
```

## Backup e restauração

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup.ps1
```

Backups em `backups/`; copie para outro disco. O script evita redirecionamento SQL no PowerShell, que pode produzir UTF-16. Para restaurar, faça antes backup do estado atual. Confirme arquivo e ambiente, pois o dump substitui as tabelas existentes:

```powershell
docker compose stop backend frontend
docker compose cp .\backups\SEU_ARQUIVO.sql db:/tmp/restore.sql
docker compose exec db sh
```

Dentro do container:

```sh
MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE" < /tmp/restore.sql
exit
```

De volta ao PowerShell: `docker compose up -d`.

## Parar sem perder dados

```powershell
docker compose stop       # para containers
docker compose start      # inicia os existentes
docker compose restart    # reinicia
docker compose down       # remove containers/rede; preserva volume
docker compose up -d      # recria usando o volume existente
```

**Não use `docker compose down -v` na manutenção normal:** apaga os dados. Alterar MYSQL_PASSWORD no `.env` não altera uma conta já criada em volume persistente. Faça a mudança da conta MySQL e da configuração de forma coordenada.

## Testes e build

```powershell
docker compose exec -T backend python -m pytest -q
docker compose build frontend
```

Sem Docker (Python 3.12, Node 22.12+):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q
Set-Location ..\frontend
npm.cmd install
npm.cmd run build
```

Os testes usam SQLite isolado em memória para autenticação, validação, nulos, UTC, cadastro/edição, paginação, resumo, série e CSV. Não substituem o teste de integração com MySQL. `VALIDATION.md` registra as verificações efetivamente executadas nesta entrega.

Esta versão não inclui alertas externos, retenção automática, cadastro de usuários, TLS embutido ou firmware. Administração usa uma credencial do servidor; o recebimento de medições é público, sem chave de API.

## Avisos públicos fixos

O quadro **Avisos e alarmes atuais**, abaixo dos gráficos, utiliza a última leitura da estação principal. Os critérios foram definidos para este projeto acadêmico e não são apresentados como alertas oficiais de órgãos públicos.

| Condição | Tipo | Mensagem | Observação |
|---|---|---|---|
| Umidade < 40% | Aviso | A umidade do ar está abaixo do normal. | Procure se hidratar mais em tempos muito secos. |
| Umidade > 75% | Alarme | A umidade está acima do esperado. | Sem observação adicional |
| Temperatura > 30 °C | Aviso | É um dia quente, procure se hidratar mais. | Sem observação adicional |
| Temperatura < 15 °C | Aviso | É um dia frio, procure se agasalhar bem. | Sem observação adicional |
| Chuva detectada | Aviso | Chuva detectada. | Procure abrigo. Se você for dirigir, redobre a atenção. |

Os limites são estritos: valores iguais a 40%, 75%, 30 °C ou 15 °C não acionam esses avisos. As regras ficam em backend/app/alarm_service.py. Podem aparecer vários avisos ao mesmo tempo; alarmes são exibidos primeiro. Quando uma nova leitura sai da condição, a mensagem desaparece. Leituras ausentes não viram zero e não acionam aviso. Estação offline não é tratada como situação normal.

O formulário e os links de configuração foram removidos da interface. PUT /api/station foi retirado. Regras armazenadas pelo editor antigo foram preservadas para não apagar dados, mas não afetam a avaliação pública. Não há som, notificações externas ou histórico de eventos nesta versão.

## Página inicial

O sistema abre em **Início**, com uma prévia das seis leituras ambientais da estação principal, status online/offline, localização e horário da última medição. Os dados são atualizados a cada dez segundos. Na ausência de dados aparece Indisponível; quando a estação está offline, os valores são identificados como a última leitura recebida.

Os botões **Ver detalhes e gráficos** e **Acessar monitoramento**, assim como o item **Monitoramento** do menu, abrem os gráficos, filtros de período e alarmes. Os gráficos são consultados ao acessar o monitoramento. A edição da estação e das regras foi removida da interface pública.
## Home com apresentação pública

A página Início agora ocupa toda a largura, sem barra lateral, com foto de fundo, temperatura em destaque e demais leituras centralizadas. O botão **Ver mais detalhes** abre o monitoramento existente com gráficos e alarmes. Os avisos públicos agora seguem os critérios fixos documentados acima.

A imagem local frontend/public/estacao-pantanal.jpeg foi obtida da publicação indicada pelo usuário, com crédito no rodapé. A foto principal disponível no link tem outro enquadramento da captura anexada, embora mostre a mesma estação. Origem: https://agenciadenoticias.ms.gov.br/wp-content/uploads/2025/05/WhatsApp-Image-2025-05-18-at-14.09.31.jpeg (cópia equivalente também disponível na Semadesc). O fundo é ilustrativo e não altera a origem das medições exibidas, que continuam vindo da estação do projeto.

O visual foi preparado para visitantes, mantendo a execução local no Docker. Não houve publicação na internet. Valores ausentes e estação offline continuam identificados.
## Classificação visual da luminosidade

Na home e nos indicadores do monitoramento, o status aparece em destaque e o valor medido em lux logo abaixo, menor. Faixas baseadas na tabela fornecida: abaixo de 400 lux = Noite; de 400 até menos de 1000 = Amanhecer / Entardecer; de 1000 a 5000 = Dia nublado; acima de 5000 e abaixo de 10000 = Dia; a partir de 10000 = Dia pleno. As faixas intermediárias completam as lacunas da tabela. Essa classificação é uma indicação da luz medida, não uma determinação astronômica ou meteorológica. Leituras ausentes continuam indisponíveis. Quando o status é Noite, o ícone de luminosidade muda de sol para lua nas duas telas. Os gráficos continuam exibindo os valores numéricos em lux.