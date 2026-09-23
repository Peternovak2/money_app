# Referencia de UX: pagina de ativo

## Objetivo

Este documento registra aprendizados obtidos ao estudar uma pagina publica de ativo financeiro do TradingView como referencia de arquitetura de informacao e experiencia de uso.

O objetivo nao e reproduzir a interface observada. Os conceitos abaixo devem ser reinterpretados para as necessidades, a identidade visual e as fontes de dados do Money App. Textos, codigo, branding, logotipos, iconografia proprietaria e outros elementos de identidade visual da referencia estao fora do escopo.

## Estrutura identificada na referencia

A pagina organiza a informacao em camadas, partindo do contexto geral para dados progressivamente mais detalhados.

### Navegacao global e contexto

- Cabecalho global com busca, navegacao principal e controles de conta.
- Trilha de navegacao indicando mercado, pais, classe do ativo, setor e ativo atual.
- Contexto suficiente para o usuario entender onde o ativo se encontra dentro do mercado.

### Cabecalho do ativo

- Identidade da empresa e do ativo apresentada antes dos dados analiticos.
- Nome, ticker e bolsa agrupados visualmente.
- Preco atual em forte destaque.
- Variacao absoluta e percentual posicionadas junto ao preco.
- Moeda, estado do mercado e horario da ultima cotacao tratados como metadados.
- Acoes relacionadas ao ativo colocadas proximas desse contexto.

### Navegacao do ativo

- Navegacao horizontal especifica para o ativo.
- Separacao entre visao geral, informacoes financeiras, noticias e outras categorias.
- Indicacao clara da secao ativa.
- A navegacao permanece visualmente ligada ao cabecalho do ativo.

### Grafico e desempenho

- Grafico como elemento dominante da primeira area de conteudo.
- Pouca decoracao ao redor do grafico, preservando espaco para leitura dos dados.
- Controles secundarios mantidos compactos e proximos ao grafico.
- Retornos de diferentes periodos apresentados como uma faixa comparativa.
- A leitura imediata responde tanto ao movimento recente quanto ao desempenho de longo prazo.

### Metricas e fundamentos

- Metricas resumidas antes das demonstracoes mais detalhadas.
- Indicadores apresentados como pares de rotulo e valor.
- Agrupamento por assunto, evitando uma unica lista indiferenciada.
- Ajuda contextual para indicadores que podem nao ser conhecidos pelo usuario.
- Unidades, periodos de referencia e moedas exibidos junto aos valores.
- Graficos financeiros usam alternancia entre visoes anual e trimestral quando aplicavel.

### Informacoes da empresa

- Setor, industria, lideranca, sede, fundacao, site e identificadores corporativos.
- Descricao da atividade da empresa em uma secao propria.
- Informacoes resumidas primeiro, com possibilidade de expansao.

### Noticias e conteudo relacionado

- Noticias agrupadas em uma secao posterior aos dados do ativo.
- Cada item prioriza titulo, fonte e recencia.
- A lista inicial e limitada e oferece continuidade para quem deseja aprofundamento.

### Hierarquia, espacamento e agrupamento

- Nome e preco usam maior peso visual; metadados aparecem de forma secundaria.
- Variacao fica perto do preco por possuir relacao semantica direta.
- Espacamentos maiores separam assuntos completos, enquanto elementos do mesmo assunto ficam mais proximos.
- Linhas e divisores discretos ajudam a estruturar a pagina sem transformar cada secao em um card.
- Cards aparecem principalmente quando ha itens repetidos ou unidades independentes.
- A pagina usa divulgacao progressiva: resumo e grafico primeiro, fundamentos depois, contexto corporativo e noticias em seguida.

## Padroes de UX que podemos adaptar

### Contexto financeiro completo

O preco nunca deve aparecer isolado. Deve ser acompanhado de variacao, moeda, estado do mercado e horario de atualizacao. Isso reduz ambiguidades e aumenta a confianca nos dados.

### Leitura em camadas

A pagina deve atender dois comportamentos:

1. Consulta rapida de preco e variacao.
2. Analise mais profunda de desempenho, fundamentos, empresa e noticias.

A informacao deve ficar progressivamente mais detalhada conforme o usuario avanca pela pagina.

### Agrupamento por intencao

As metricas devem ser agrupadas pelo tipo de pergunta que respondem:

- negociacao e preco;
- desempenho historico;
- valor de mercado e valuation;
- dividendos;
- crescimento e rentabilidade;
- saude financeira.

Esse modelo e mais facil de escanear do que uma grade plana com indicadores de naturezas diferentes.

### Grafico como ferramenta principal

O grafico deve ser uma area de trabalho clara, com dimensoes estaveis e selecao de periodo. Controles extras devem ser adicionados apenas quando tiverem utilidade real no Money App.

### Navegacao contextual simples

Uma barra de navegacao interna pode apontar para secoes da propria pagina antes de justificar rotas independentes. Isso preserva simplicidade tecnica e melhora a orientacao em paginas longas.

### Ajuda no momento certo

Indicadores como P/L, EPS e dividend yield devem possuir explicacoes curtas, acessiveis por tooltip ou acao equivalente, sem ocupar permanentemente a interface.

### Tratamento explicito de dados

- Exibir a unidade ou moeda aplicavel.
- Informar o periodo de referencia.
- Diferenciar mercado aberto e fechado.
- Usar um estado neutro para dados indisponiveis.
- Informar quando os dados foram atualizados.
- Evitar apresentar previsoes como fatos observados.

### Responsividade por prioridade

No mobile, a ordem deve preservar preco, variacao, grafico e metricas essenciais. Conteudos secundarios devem vir depois, em uma unica coluna, sem comprimir tabelas ou grades de forma ilegivel.

## Componentes sugeridos

Os nomes abaixo representam responsabilidades e podem ser adaptados ao padrao de templates do projeto.

### Estrutura e navegacao

- `AssetBreadcrumb`: contexto de navegacao e retorno.
- `AssetHeader`: identidade, nome, ticker, bolsa e metadados.
- `AssetTabs`: navegacao entre as secoes da pagina.
- `SectionHeader`: titulo de secao e acao secundaria opcional.

### Cotacao

- `AssetPrice`: preco atual e moeda.
- `PriceChange`: variacao absoluta e percentual com estado positivo, negativo ou neutro.
- `MarketStatus`: estado do mercado e horario da cotacao.
- `DataFreshness`: fonte e momento de atualizacao dos dados.

### Grafico e desempenho

- `AssetChart`: area principal do grafico.
- `ChartPeriodSelector`: selecao de intervalo temporal.
- `PerformanceStrip`: retorno por periodo.
- `TradingSnapshot`: abertura, maxima, minima, fechamento anterior e volume.

### Metricas e fundamentos

- `MetricGroup`: agrupamento semantico de indicadores.
- `MetricItem`: rotulo, valor, unidade, periodo e ajuda contextual.
- `FinancialHighlights`: resumo de receita, lucro, margens, divida e fluxo de caixa.
- `FinancialPeriodToggle`: alternancia entre dados anuais e trimestrais.
- `EmptyMetricState`: apresentacao consistente de valores indisponiveis.

### Empresa e noticias

- `CompanySummary`: descricao curta da atividade da empresa.
- `CompanyFacts`: setor, industria, sede, site e demais dados corporativos.
- `NewsList`: lista de noticias relacionadas.
- `NewsItem`: titulo, fonte, data e indicacao de link externo.

## Elementos que deliberadamente nao vamos copiar

- Identidade visual, marca, logotipos, cores e tipografia do TradingView.
- Textos, descricoes, rotulos proprietarios e conteudo editorial.
- Codigo-fonte, estrutura de estilos ou implementacao dos componentes da referencia.
- Ferramentas avancadas de desenho e terminal profissional de graficos.
- Integracao com corretoras e execucao de ordens.
- Comunidade, comentarios e publicacao de ideias de negociacao.
- Linguagem de scripts, marketplace de indicadores e widgets incorporaveis.
- Abas de opcoes, titulos, sazonalidade e documentos enquanto nao houver suporte de dados e necessidade comprovada.
- Previsoes, recomendacoes ou precos-alvo sem fonte confiavel e metodologia explicita.
- Navegacao global extensa para produtos que nao fazem parte do Money App.
- Replicacao imediata de todos os graficos financeiros da referencia.
- Comparacao com ativos semelhantes na primeira entrega da nova pagina.

## Proposta para a pagina de ativo do Money App

### 1. Cabecalho global

Manter a identidade do Money App, os controles de conta e o acesso a busca.

### 2. Contexto do ativo

Exibir retorno ou breadcrumb, identidade propria do ativo quando disponivel, nome da empresa, ticker canonico, bolsa e categoria.

### 3. Cotacao principal

Apresentar preco, variacao absoluta, variacao percentual, moeda, estado do mercado e horario da cotacao em um unico grupo semantico.

### 4. Navegacao interna

Usar inicialmente ancoras para as secoes:

- Visao geral;
- Grafico;
- Fundamentos;
- Empresa;
- Noticias.

Rotas independentes so devem ser criadas quando o volume ou a complexidade do conteudo justificar.

### 5. Grafico e desempenho

Exibir o grafico principal em largura dominante, seguido por seletor de periodos e retornos acumulados. Em telas amplas, o resumo de negociacao pode ocupar uma coluna lateral. No mobile, deve aparecer abaixo do grafico.

### 6. Resumo do mercado

Agrupar abertura, maxima, minima, fechamento anterior, volume e valor de mercado. Esses dados formam um resumo operacional e nao devem ser misturados com indicadores fundamentalistas.

### 7. Fundamentos

Organizar indicadores em grupos:

- valuation;
- rentabilidade;
- dividendos;
- crescimento;
- saude financeira.

Valores ausentes devem usar um estado neutro, sem remover o item nem alterar a estrutura da pagina.

### 8. Destaques financeiros

Exibir receita, lucro e margens com historico visual somente quando a fonte oferecer series consistentes. A alternancia anual e trimestral deve ser adicionada depois que ambas as granularidades estiverem disponiveis.

### 9. Sobre a empresa

Apresentar descricao curta, setor, industria, pais, sede, site e outros fatos corporativos relevantes. A descricao pode ser expandida sob demanda.

### 10. Noticias

Exibir uma lista curta com titulo, fonte e horario. Links externos devem ser claramente identificados e a pagina deve evitar reproduzir integralmente conteudo editorial de terceiros.

## Prioridades de implementacao

### Prioridade 1: base de informacao e confianca

- Reorganizar o cabecalho do ativo.
- Formatar ticker, numeros, moedas e percentuais de forma consistente.
- Exibir variacao absoluta e percentual com estados positivo, negativo e neutro.
- Mostrar moeda, estado do mercado e horario de atualizacao.
- Tratar valores ausentes com um componente neutro.
- Tornar a pagina de ativo responsiva.
- Separar resumo de mercado de indicadores fundamentalistas.

### Prioridade 2: grafico e navegacao

- Adicionar grafico historico com dimensoes estaveis.
- Implementar selecao de periodos essenciais.
- Calcular ou obter retornos por periodo.
- Adicionar navegacao interna por ancoras.
- Preservar preco e grafico como conteudo prioritario no mobile.

### Prioridade 3: fundamentos e empresa

- Ampliar a fonte de dados fundamentalistas.
- Criar grupos de metricas por intencao.
- Exibir industria, que ja e obtida pelo servico atual.
- Adicionar descricao e fatos corporativos.
- Incluir ajuda contextual para indicadores financeiros.

### Prioridade 4: historico financeiro e noticias

- Adicionar series anuais confiaveis de receita, lucro, margens, divida e caixa.
- Criar visualizacoes financeiras simples e legiveis.
- Integrar noticias com fonte, data e link externo.
- Avaliar visualizacao trimestral apos validar a cobertura dos dados.

### Prioridade 5: evolucoes opcionais

- Comparacao com ativos semelhantes.
- Paginas ou rotas dedicadas para secoes que crescerem demais.
- Indicadores adicionais orientados por uso real e disponibilidade de dados.

## Criterio de sucesso

A nova pagina deve permitir que o usuario responda, nesta ordem:

1. Qual e o ativo e qual e o preco atual?
2. Como ele esta se movimentando agora e em diferentes periodos?
3. Quais sao seus principais numeros de mercado e fundamentos?
4. O que a empresa faz?
5. Quais eventos recentes podem afetar o ativo?

Se essas respostas forem encontradas rapidamente, com dados contextualizados e sem sobrecarga visual, a arquitetura estara cumprindo seu objetivo.
