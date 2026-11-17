# Money App — Instruções para agentes

## 1. Objetivo

O Money App permite pesquisar ações da B3, consultar dados e gráficos
de ativos, acompanhar rankings e notícias e acessar uma área pessoal.

O projeto também é um ambiente de aprendizagem do proprietário,
que está se preparando para seu primeiro emprego como programador.

Use o código atual como fonte de verdade. Este documento orienta
o trabalho, mas não substitui a investigação dos arquivos.

## 2. Tecnologias e arquitetura

- Backend: Python e FastAPI.
- Páginas: Jinja2 e HTML renderizado no servidor.
- Interface: CSS e JavaScript sem framework frontend.
- Gráficos: ECharts, carregado por CDN.
- Persistência: SQLite com Peewee.
- Autenticação: pwdlib/Argon2 e sessões assinadas do Starlette.
- Dados externos: Brapi, yfinance e RSS da Agência Brasil.
- Testes: unittest, unittest.mock, TestClient e SQLite temporário.

A aplicação é montada em `app/main.py`.
O fluxo principal é rota → serviço → template ou resposta JSON.
Os modelos e a conexão com o banco ficam em `app/database.py`.

Preserve essa arquitetura enquanto ela atender ao problema.
Não acrescente frameworks, camadas ou ferramentas sem necessidade
concreta e autorização para a mudança.

## 3. Responsabilidades dos arquivos e diretórios

- `app/main.py`: configuração do FastAPI, middlewares, routers,
  arquivos estáticos, filtros Jinja e rota da home.
- `app/routes/`: rotas das páginas e autenticação.
- `app/routes/api/`: endpoints JSON.
- `app/services/`: autenticação, segurança, consultas externas,
  cache, rankings e regras de negócio.
- `app/services/utils/formatar.py`: formatação de números,
  moedas, percentuais e tickers usados nas consultas.
- `app/database.py`: conexão SQLite, modelos e normalização
  de tickers persistidos.
- `app/migrations/`: CLI, runner e migrações versionadas.
- `app/templates/`: páginas Jinja2.
- `app/static/css/`: estilos compartilhados e específicos das páginas.
- `app/static/js/`: busca, autenticação, rankings e gráficos.
- `tests/`: testes automatizados e verificações de frontend.
- `docs/ui-references/`: referências de experiência e organização visual.
- `requirements.txt`: dependências com versões declaradas.
- `money.db`: banco local real; não usar como banco de testes.
- `.venv/`: ambiente Python do projeto.

Não presuma que uma referência em `docs/` representa uma funcionalidade
implementada ou uma autorização para desenvolvê-la.

## 4. Padrões de desenvolvimento

- Faça mudanças pequenas, com responsabilidade clara e dentro do escopo.
- Siga os nomes, estilo e organização do arquivo que estiver alterando.
- Preserve contratos das rotas, respostas JSON, contextos Jinja,
  identificadores HTML e atributos usados pelo JavaScript.
- Coloque regras reutilizáveis em serviços, evitando duplicação nas rotas.
- Valide entradas no backend mesmo quando houver validação no navegador.
- Diferencie entrada inválida, dado inexistente e falha de serviço externo.
- Preserve timeouts, cache e tratamento de indisponibilidade.
- Considere que o catálogo pode devolver dados antigos após falha
  de atualização; não trate isso automaticamente como confirmação atual.
- Confira a unidade de cada dado financeiro antes de converter
  moedas, percentuais ou volumes.
- Distinga `normalizar_ticker()` de persistência e `formatar_ticker()`
  de consulta; elas têm finalidades diferentes.
- Preserve estados de carregamento, vazio, sucesso e erro.
- Use HTML semântico, labels, navegação por teclado, foco visível,
  atributos ARIA coerentes e layouts responsivos.
- Preserve o escape do Jinja e use DOM seguro para dados externos.
- Não introduza controles visuais que aparentem funcionar sem funcionar.
- Evite refatorações, reformatações e mudanças visuais fora da tarefa.

## 5. Fluxo de trabalho e autorização

1. Leia as instruções aplicáveis e confira o estado do Git.
2. Investigue os arquivos e o fluxo realmente envolvidos.
3. Apresente o diagnóstico e, quando houver mudança, um plano proporcional,
   com arquivos afetados, riscos e forma de validação.
4. Respeite a modalidade do pedido:
   análise ou proposta não autoriza edição;
   uma implementação explicitamente autorizada permite executar
   as alterações necessárias dentro daquele escopo.
5. Implemente somente o trabalho autorizado.
6. Execute as validações pertinentes e revise o diff final.
7. Entregue o resultado, as evidências e as pendências.

Não implemente funcionalidades por antecipação.
Uma autorização para uma etapa não autoriza automaticamente a seguinte.

Antes de ampliar o escopo, explique o motivo e obtenha autorização.
Não peça novamente uma autorização já concedida para o mesmo trabalho.

## 6. Segurança e proteção de dados

### Banco e migrações

- Não altere `money.db`, seus dados ou seu schema sem aprovação específica.
- Trate `money.db-wal` e `money.db-shm` como partes do banco em uso:
  não remova, edite ou versione esses arquivos.
- Não execute `--apply`, DDL ou migrações reais por outros caminhos
  sem essa aprovação.
- Consultas ao banco real devem usar conexão explicitamente de leitura.
  Para verificar migrações, prefira a CLI com `--status`.
- Testes de persistência devem usar bancos temporários ou em memória.
  Reassocie os modelos corretamente e restaure o estado ao final.
- Antes de testar inicialização, examine os efeitos do startup.
  Atualmente, `criar_tabelas()` cria a tabela de usuários.
- Não acrescente execução automática de migrações ao startup.
- Preserve transações, chaves estrangeiras, unicidade e validação
  do histórico de migrações.
- Não reescreva migrações já aplicadas para alterar o histórico.
- Uma aplicação real de migração deve ter banco-alvo, plano de backup,
  recuperação e validação apresentados antes da aprovação.

### Autenticação e informações privadas

- Use `app/services/auth.py` e `app/services/security.py`.
- Em APIs privadas, obtenha a identidade por `exigir_usuario_api`.
  Nunca confie em `user_id` enviado pelo navegador para definir o dono.
- Escritas privadas devem validar CSRF com `exigir_csrf`
  e o cabeçalho `X-CSRF-Token`.
- Preserve a validação do campo `csrf_token` no logout.
- Preserve a renovação da sessão e do token após login.
- Mantenha a distinção entre falha de autenticação (401),
  falha de CSRF (403) e redirecionamento de páginas HTML.
- Filtre operações privadas pelo usuário autenticado.
- Nunca exponha senhas, hashes, cookies, tokens ou segredos
  em templates, respostas ou relatórios.
- Cookies de sessão são assinados, não criptografados;
  não coloque informações sensíveis neles.
- Preserve HttpOnly, SameSite=Lax e Secure em produção.
- Não adicione uma SECRET_KEY padrão ao código.

### Arquivos sensíveis e configuração pessoal

- Proteja `.env`, `.env.local` e outros arquivos locais com segredos,
  credenciais, dados pessoais ou parâmetros privados.
- Proteja configurações pessoais do editor, como `.vscode/settings.json`,
  e configurações locais de serviços e ferramentas.
- Não leia esses conteúdos sem necessidade da tarefa nem os reproduza
  em logs, diffs compartilhados ou relatórios. Oculte valores sensíveis.
- Não altere, sobrescreva ou exclua configurações pessoais sem autorização.
- Não versione arquivos sensíveis, bancos, seus arquivos auxiliares,
  backups com dados reais ou configurações pessoais.
- Não presuma que o `.gitignore` protege todos esses arquivos;
  confira o conteúdo selecionado antes de preparar um commit.
- Não instale, atualize ou remova dependências sem autorização.
- Não exclua nem recrie ambientes virtuais sem autorização.

## 7. Comandos de execução e validação

Execute os comandos a partir da raiz, usando o Python da `.venv`.

### Testes completos

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

### Testes específicos de migrações ou segurança

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_migrations.py" -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_security.py" -v
```

Os testes de migração devem continuar restritos aos bancos temporários.

### Integridade das dependências instaladas

```powershell
.\.venv\Scripts\python.exe -B -m pip check
```

Esse comando não instala pacotes nem comprova sozinho a execução
de todas as funcionalidades.

### Sintaxe JavaScript

Quando Node.js estiver disponível:

```powershell
node --check app/static/js/home.js
node --check app/static/js/ativo.js
node --check app/static/js/auth.js
node --check app/static/js/mercado.js
```

### Estado das migrações, somente leitura

```powershell
.\.venv\Scripts\python.exe -B -m app.migrations --status
```

### Inicialização local

Somente quando a inicialização e seus efeitos no banco estiverem
autorizados:

```powershell
$env:SECRET_KEY = "chave-apenas-para-desenvolvimento-local"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Acesso: `http://127.0.0.1:8000`. Encerramento: `Ctrl+C`.
A chave de exemplo é exclusiva de desenvolvimento local.

### Revisão das alterações

```powershell
git status --short --branch
git diff
git diff --cached
git diff --check
```

`git diff --check` verifica problemas de whitespace;
não substitui testes nem revisão de comportamento.

Execute primeiro os testes relacionados à mudança.
Amplie para a suíte completa quando houver impacto compartilhado.

Não apresente testes de conteúdo HTML/CSS/JS como validação completa
em navegador. Mudanças de interface também exigem conferir,
quando possível, responsividade, teclado, foco e estados de erro.

Se uma ferramenta falhar ou estiver indisponível, registre a limitação.
Não instale ferramentas para contornar o problema sem autorização.
Nunca invente resultados de testes.

## 8. Git e aprovação

- Registre mudanças staged, unstaged e arquivos não rastreados
  antes de trabalhar.
- Preserve alterações locais do usuário e identifique as suas separadamente.
- Não descarte, sobrescreva ou incorpore mudanças alheias silenciosamente.
- Não faça commit, push ou deploy sem aprovação explícita.
- Não faça reset destrutivo, limpeza de arquivos ou reescrita
  de histórico sem autorização específica.
- Prepare os commits com arquivos selecionados e revisão do conteúdo;
  evite incluir arquivos locais, segredos, bancos e ambientes virtuais.
- Contagens de commits à frente ou atrás dependem da referência local
  do remoto. Informe se houve atualização dessa referência.
- Não declare que algo foi publicado com base apenas no Git local.

## 9. Modo mentor de programação

Em sessões de aprendizagem, priorize as tentativas do usuário:

- Comece pelo objetivo e por um exemplo concreto.
- Mostre os arquivos, funções e fluxo existentes.
- Explique os conceitos de Python, JavaScript, FastAPI e SQL
  necessários para entender aquela parte.
- Divida o exercício em passos pequenos e deixe o usuário tentar primeiro.
- Ofereça pistas graduais, começando por perguntas e indicações
  de onde investigar, antes de mostrar trechos de solução.
- Revise a tentativa antes de oferecer uma solução completa;
  explique a causa, o efeito e a correção dos erros.
- Dê oportunidade para o usuário aplicar a correção e tentar novamente.
- Apresente uma solução completa quando solicitada ou quando o usuário
  concordar em recebê-la após as pistas e a revisão.
- Proponha um exercício curto ou uma pergunta para verificar o aprendizado.
- Se o usuário não entender, simplifique e use outro exemplo.

Não assuma que todo pedido de ajuda autoriza escrever código.
Quando houver pedido explícito de implementação, execute o escopo
autorizado e explique as decisões relevantes.

## 10. Relatórios e manutenção destas instruções

Adapte o tamanho do relatório ao trabalho, incluindo:

1. Resultado ou diagnóstico principal.
2. Arquivos e funções relevantes.
3. Alterações realizadas ou proposta, conforme a autorização.
4. Comandos executados e resultados reais, incluindo falhas
   e testes ignorados.
5. Riscos, limitações, verificações manuais e pendências.
6. Estado final do Git e próximo passo que depende de aprovação.

Diferencie fatos observados, hipóteses e comportamento ainda não validado.

Não fixe neste documento contagens de testes, commits locais,
estado momentâneo de etapas como B2.2 ou pendências do banco.
Confira esses dados no código, no Git e nas validações de cada sessão.

A existência de um modelo, migração, botão ou proposta não comprova
que todo o fluxo está implementado nem autoriza desenvolver a etapa
seguinte ou migrar o banco real.
