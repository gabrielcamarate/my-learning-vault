# My Learning Vault

#### Video Demo:  https://youtu.be/f7ReU5I-7tU

#### Descricao:
My Learning Vault e uma aplicacao web para organizar materiais de estudo de forma estruturada, navegavel e pesquisavel. A ideia nasceu de um problema real: ao fazer cursos longos, com modulos, aulas, anotacoes em markdown e arquivos complementares, o conteudo costuma ficar espalhado em muitas pastas locais. O objetivo do projeto foi transformar esse fluxo em uma experiencia unica, mais bonita e mais pratica de usar no navegador.

O modelo da aplicacao segue uma hierarquia opinativa e simples. Cada curso possui modulos, cada modulo possui aulas e cada aula possui uma anotacao principal em markdown, alem de um anexo opcional. Essa decisao foi intencional. Em vez de tentar reproduzir um editor universal e totalmente livre logo na primeira versao, o projeto escolhe um formato claro que combina diretamente com a forma como cursos e treinamentos costumam ser estudados na pratica. Isso reduz friccao, facilita a navegacao e deixa o produto mais facil de entender.

A tela inicial funciona como uma biblioteca de cursos. Nela, o usuario pode criar um curso manualmente ou importar uma pasta completa com a estrutura local ja existente. Esse importador aceita uma organizacao baseada em diretorios, na qual a pasta principal representa o curso, as subpastas de primeiro nivel representam os modulos, as subpastas seguintes representam as aulas, e cada aula pode conter um arquivo `anotacoes.md`. Esse recurso foi pensado para reaproveitar um metodo de estudo real, em vez de obrigar o usuario a reconstruir tudo manualmente dentro do sistema. O processo de importacao tambem ignora caminhos ocultos e tecnicos, como `.git`, para evitar lixo estrutural no conteudo final.

Ao entrar em um curso, o usuario nao navega por varias paginas separadas de modulo e aula. Toda a experiencia principal acontece em uma unica tela. Na lateral esquerda ficam os modulos em formato de accordion, e dentro de cada modulo aparecem as aulas correspondentes. Ao clicar em uma aula, o conteudo e exibido imediatamente no painel principal da direita, sem recarregar a pagina. Isso torna a navegacao mais parecida com uma plataforma de estudos ou um caderno digital do que com um painel administrativo tradicional.

O conteudo das aulas e baseado em markdown. No modo de visualizacao, as anotacoes sao renderizadas de forma mais legivel; no modo de edicao, o usuario continua escrevendo em markdown puro. Esse formato foi escolhido porque ele e simples, portavel, duravel e combina bem com anotacoes tecnicas. Alem disso, a aplicacao suporta um anexo opcional por aula, com upload real de arquivo. O anexo aparece em um card visual proprio, pensado para funcionar como material complementar da aula.

Outro ponto importante do projeto e a busca. Existe uma busca global capaz de localizar termos em titulos de cursos, modulos, aulas e tambem no conteudo das anotacoes. Quando o usuario abre um resultado, a interface leva a aula correta para o painel principal, destaca o termo pesquisado no texto e posiciona a leitura perto da primeira ocorrencia. Isso elimina a necessidade de procurar manualmente por um termo dentro de uma anotacao longa e melhora bastante o valor real da aplicacao como ferramenta de consulta.

Tambem foi implementada reordenacao por arrastar e soltar. Os modulos podem ser reorganizados com drag and drop, e as aulas tambem podem ser reordenadas dentro do proprio modulo. Essa funcionalidade faz sentido porque a ordem do estudo muda com o tempo, e um sistema desse tipo precisa permitir ajustes sem obrigar o usuario a apagar e recriar conteudo. A interface de configuracoes visiveis foi removida em favor de menus de contexto com clique direito, o que ajuda a manter a tela mais limpa sem perder acoes importantes como adicionar modulo, adicionar aula e excluir itens.

Do ponto de vista tecnico, o projeto foi construido com Flask no backend e SQLite como banco de dados local. Flask e responsavel pelas rotas, templates, formularios e logica de importacao. SQLite armazena a estrutura principal da aplicacao: cursos, modulos e aulas. O frontend usa templates Jinja renderizados no servidor e uma camada de JavaScript para interacoes que precisam acontecer sem reload, como abrir accordions, alternar entre visualizacao e edicao, salvar anotacoes inline, abrir modais de confirmacao e reorganizar itens com drag and drop.

Arquivos principais do projeto:

- `app.py`: contem a aplicacao Flask, a configuracao do banco, as rotas, a logica de importacao, upload de anexos, busca, reordenacao e acoes inline.
- `schema.sql`: define as tabelas principais do banco de dados.
- `requirements.txt`: lista as dependencias Python necessarias.
- `templates/layout.html`: estrutura base compartilhada pelas paginas.
- `templates/index.html`: tela inicial com a biblioteca de cursos e o modal de criacao/importacao.
- `templates/course_detail.html`: tela principal do curso, com modulos, aulas, leitura, edicao, contexto e drag and drop.
- `templates/search.html`: resultados da busca global.
- `static/styles.css`: identidade visual, layout, responsividade, estados e componentes.

## Como executar localmente

Para clonar o projeto:

```bash
git clone <URL_DO_REPOSITORIO>
cd my-learning-vault
```

Para criar o ambiente virtual e instalar as dependencias:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para iniciar a aplicacao em ambiente local:

```bash
flask --app app --debug run
```

Depois disso, basta abrir o navegador em:

```text
http://127.0.0.1:5000
```

Ao iniciar, a aplicacao cria e utiliza o arquivo `vault.db` localmente. Os anexos enviados pelo usuario ficam armazenados na pasta `uploads/`.

Uma das decisoes de design mais importantes foi evitar a cara padrao de SaaS ou dashboard generico. A interface foi refinada para se aproximar mais de uma area de membros ou plataforma de estudos escura, com foco em leitura, organizacao e consulta. Outra decisao importante foi trocar confirmacoes nativas do navegador por modais consistentes com o resto da aplicacao, o que melhora a percepcao de qualidade e evita interrupcoes visuais feias.

Ainda ha varias possibilidades de evolucao para o produto, como suporte a multiplos anexos por aula, tags, filtros mais avancados, progresso de estudo e sincronizacao mais inteligente com fontes externas. Mas para esta versao do projeto, o foco foi entregar um MVP forte e util: um caderno digital de cursos com estrutura real, busca funcional, importacao de pastas, leitura em markdown e navegacao fluida dentro de uma unica tela.

Em resumo, My Learning Vault nao foi pensado apenas como um exercicio academico. Ele foi desenhado para ser o inicio de uma ferramenta realmente util para organizar conhecimento adquirido em cursos, treinamentos e trilhas de estudo longas. Esse objetivo influenciou tanto as escolhas tecnicas quanto as escolhas de interface ao longo de todo o desenvolvimento.
