# Validação da entrega — 07/11/2026

Projeto final: S:\estacao-meteorologica-inteligente. ZIP original e firmware não foram alterados.

## Ambiente corrigido

- Usuário liberou espaço no C:. A instalação incompleta do WSL 2.1.5 foi reparada com o instalador oficial WSL 3.0.3, cuja assinatura Microsoft foi verificada. Instalação concluída com código 0, sem reiniciar o Windows.
- Docker Desktop 4.30.0 / Engine 26.1.1 funcionando com discos virtuais em S:\DockerDesktop\wsl\data e S:\DockerDesktop\wsl\main.
- Backup da configuração anterior em S:\DockerDesktop\backups\settings-20261107-154944.json.

## Verificações concluídas

- `docker compose up -d --build` concluiu. MySQL 8.4, API e frontend NGINX estão saudáveis. Somente a porta 8080 do NGINX é publicada.
- 13 testes automatizados passaram em Python 3.12 local e dentro do container. Cobrem autenticação, limites/tipos, nulos, UTC, cadastro/edição, duplicidade, status, paginação, filtros, agregação, resumo e CSV. Esses testes usam SQLite isolado em memória.
- Integração adicional com MySQL real: migrations aplicadas; estação estacao-01 criada sem dados reais; 2880 registros históricos gerados em demo-01; dois POSTs HTTP autenticados enviados pelo simulador; total de 2882 registros confirmado.
- Dashboard HTML, Swagger e CSV responderam HTTP 200 pelo NGINX. Série agregada retornou 288 pontos e resumo respondeu corretamente. Identificação de demonstração preservada e estação real permaneceu sem comunicação simulada.
- Backup MySQL executado pelo script scripts/backup.ps1 e salvo em backups/weather-20261107-161022.sql. Restauração não executada, para não substituir os dados em execução.
- MySQL reiniciado; API voltou a responder e os 2882 registros permaneceram armazenados.
- Build de produção React/Vite concluído localmente e no Docker.
- Sintaxe dos arquivos Python, scripts PowerShell e configuração Vite verificada.

## Limitações restantes

Não houve inspeção visual em navegador nem integração com ESP32 físico. Build emite aviso sobre bundle principal maior que 500 kB; bibliotecas emitem avisos de depreciação (datetime.utcnow, AnyIO/TestClient e linha Recharts 2). Não impediram compilação ou execução.

## Acesso

- Frontend: http://localhost:8080
- Swagger: http://localhost:8080/docs
- Selecione Estação de demonstração para ver os dados fictícios. Ela fica offline após 90 segundos sem novos envios; o histórico continua disponível.

```powershell
Set-Location S:\estacao-meteorologica-inteligente
docker compose ps
docker compose exec -T backend python -m pytest -q
docker compose exec -T backend python simulate.py --url http://frontend --count 10 --interval 30
```
## Atualização: ingestão sem chave de API

Por solicitação do usuário, POST /api/measurements agora é público. A variável de chave foi removida da configuração, Compose, .env, simulador, setup e exemplos. Cadastro e edição de estações continuam exigindo HTTP Basic administrativo.

Os 13 testes atualizados passaram, incluindo POST sem chave e conferência do OpenAPI sem segurança no endpoint de medições. A API foi reconstruída e recriada no Docker, preservando o banco. O simulador enviou uma medição de demonstração por HTTP sem chave com sucesso (201). A administração continua declarada como autenticada no OpenAPI.

## Atualização: estação única, filtros e regras de alarmes

- Interface reduzida a Visão geral e Estação, sem seletor/cadastro de múltiplas estações ou página de histórico. Bloco lateral solicitado removido.
- Períodos de 1, 2, 3, 4, 5, 6 e 24 horas, além de 7/30 dias e personalizado.
- Regras persistidas em alarm_rules (Alembic 002), com nome, sensor, condição, limite, classificação aviso/alarme e habilitação. Salvamento administrativo transacional com os dados da estação.
- Painel abaixo dos gráficos avalia a leitura mais recente; cobre chuva booleana, leituras nulas, regras desabilitadas, estação offline e ausência de dados. Dados de demonstração não são selecionados como estação principal.
- 24 testes passaram localmente e no container. Build de produção concluído. Backup anterior à migração: backups/weather-20261107-175724.sql.
- MySQL atualizado em 002 (head); todos os containers saudáveis. Endpoints de estação/alarmes e filtros de 1 a 6 horas responderam HTTP 200 pelo NGINX. Bundle servido conferido sem o bloco lateral, histórico ou cadastro de estação anteriores.
- Os limites começam sem regras, para o usuário definir os valores. Nenhuma medição foi apagada ou substituída por testes. Inspeção visual em navegador não realizada.

## Atualização: home com prévia dos dados

Página Início definida como entrada, com seis indicadores usando a última medição real, status, localização e horário de coleta. Botões direcionam para Monitoramento (gráficos e alarmes). Consultas de leituras foram separadas das consultas históricas, mantendo atualização a cada dez segundos na home e evitando buscar séries até abrir os detalhes.

Build de produção passou localmente e no Docker. Frontend atualizado e saudável; home/JavaScript e endpoints de leitura/alarmes responderam HTTP 200. Nenhuma alteração no backend ou banco nesta atualização. Não houve inspeção visual automatizada em navegador.
## Atualização: home pública sem barra lateral

- Home com foto local da publicação fornecida, temperatura em destaque e demais leituras centralizadas, com botão Ver mais detalhes abaixo. Configuração de alarmes preservada.
- Build de produção concluído localmente e no Docker. Atualizado somente o frontend; backend e banco mantidos.
- Home, foto e última leitura responderam HTTP 200. Captura desktop em Chrome headless inspecionada; captura mobile gerada. Nenhum dado fictício inserido nesta etapa.
- A imagem principal disponível no link é de outro enquadramento da captura do usuário. Usada a foto da própria publicação e mantido crédito no rodapé.
- Capturas locais: .tmp/public-home-desktop.png e .tmp/public-home-mobile.png.
Conferência adicional no Chrome com emulação de celular de 390px: sem rolagem horizontal, home sem sidebar, botão Ver mais detalhes abriu os gráficos e alarmes, e navegação Início retornou à home sem sidebar. Captura mobile final inspecionada. Perfil de teste isolado e navegador de teste encerrado.
Classificação de luminosidade e lua noturna implementadas: 11 verificações de limites passaram; build Docker concluído; conferência Chrome confirmou status, lux com fonte menor e lua na home e no monitoramento quando Noite, sem inserir dados artificiais.

Atualização de apresentação: chuva exibe Céu limpo/Chovendo; home sem botão Monitoramento no topo e sem Observatório Ambiental; identificação Estação UNIP abaixo do título. Build Docker concluído, frontend saudável e arquivos servidos HTTP 200. A leitura booleana do sensor permanece inalterada.

## Atualização: avisos públicos fixos

Editor e links de configuração da estação removidos do frontend; PUT /api/station removido. Critérios fixos no backend: umidade <40% (aviso com orientação de hidratação), umidade >75% (alarme sem observação), temperatura >30 °C (aviso de dia quente e hidratação), temperatura <15 °C (aviso de dia frio e agasalho) e chuva detectada (aviso de abrigo e atenção se for dirigir). Limites estritos; regras antigas no banco não interferem na avaliação.

29 testes passaram localmente e no container, incluindo fronteiras exatas, mensagens, tipos, sensores nulos, offline e isolamento da demonstração. Build Docker passou; API publicada confirmou cinco critérios fixos; todos os containers saudáveis. Chrome em 390px confirmou navegação pública sem editor ou configuração e acesso ao painel abaixo dos gráficos. Nenhuma medição real foi substituída nem dados de teste inseridos no MySQL nesta alteração.