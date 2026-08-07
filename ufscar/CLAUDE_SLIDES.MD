# Guia de construção dos slides

Este documento fixa como os slides da dissertação devem ser construídos — estrutura, redação, identidade visual e implementação em Beamer. Vale para todo `.tex` de apresentação do projeto, em qualquer sessão, presente ou futura. Onde uma escolha divergir do que está aqui, o slide está errado, não o guia.

O `CLAUDE_WRITTER.MD` continua valendo para a **dissertação**. Este guia é o seu par para a **apresentação**, e diverge dele deliberadamente em um ponto central: a dissertação é lida em silêncio e precisa ser autossuficiente em prosa; o slide é visto enquanto alguém fala e precisa ser autossuficiente em **evidência visual**. O que na dissertação é um parágrafo, no slide é uma figura — e a prosa correspondente vai para a nota do palestrante, nunca para a tela.

---

## 1. Situação de uso

Trinta minutos, plateia técnica presente, banca acadêmica. A plateia ouve e vê ao mesmo tempo, uma única vez, sem poder voltar. Não há leitura posterior: quem não entendeu no momento não entendeu.

O slide não é o documento. Não é *handout*, não é resumo da dissertação, não é roteiro de fala impresso na parede. É o **canal visual** de uma comunicação que tem dois canais simultâneos — o visual, na tela, e o verbal, na voz do apresentador. Cada canal carrega o que faz melhor.

---

## 2. Metodologia adotada

Duas bases empíricas, não preferência estética.

### 2.1 Assertion-Evidence (Alley, Penn State)

O slide abre com uma **asserção** — uma frase completa que enuncia a conclusão daquele slide — e é sustentado por **evidência visual**: figura, diagrama, gráfico, equação, tabela curta. Nunca por lista de tópicos.

Estudos com estudantes de engenharia mostram que essa estrutura produz compreensão superior, menos concepções equivocadas, carga cognitiva percebida menor e retenção mais forte em teste postergado, comparada à estrutura convencional de título-tópico com *bullets*. O efeito atinge também o apresentador: montar o slide obriga a saber qual é a conclusão.

Consequência prática direta: **o título do slide é uma frase, não um rótulo**. "A demanda triplica entre o vale e o pico" é asserção; "Sazonalidade" é rótulo, e rótulo não comunica nada sozinho.

### 2.2 Teoria cognitiva da aprendizagem multimídia (Mayer)

Quatro princípios governam o corpo do slide:

- **Coerência** — tudo que não serve ao argumento daquele slide sai. Palavra, linha, cor ou ícone decorativo compete por atenção e reduz a compreensão.
- **Multimídia** — palavra somada a imagem ensina mais que palavra sozinha ou imagem sozinha.
- **Contiguidade** — o rótulo fica junto do elemento que ele nomeia, não numa legenda distante nem num slide seguinte.
- **Modalidade e redundância** — o canal auditivo e o visual têm capacidade limitada e independente. Texto na tela **compete** com a fala; narração acompanhada de figura ensina mais que narração acompanhada da mesma narração escrita. Ler o próprio slide em voz alta é o pior caso possível.

O princípio da modalidade é o fundamento técnico da regra de texto mínimo: a explicação **não está sendo cortada**, está sendo **movida** para o canal onde ela funciona melhor — a fala, registrada em `\note{}`.

---

## 3. Anatomia do slide

```
┌──────────────────────────────────────────────┐
│ ASSERÇÃO — frase completa, 6 a 12 palavras   │  ← frametitle
├──────────────────────────────────────────────┤
│                                              │
│              EVIDÊNCIA VISUAL                │  ← corpo: figura, gráfico,
│         (ocupa a maior parte do corpo)       │     equação ou tabela curta
│                                              │
│   rótulo   rótulo   número   número          │  ← texto só como rótulo
└──────────────────────────────────────────────┘
```

**Título — a asserção.** Frase completa, com verbo, no presente do indicativo. Entre 6 e 12 palavras; acima disso, a ideia do slide não está clara o bastante. Sem ponto final. Nunca um substantivo solto ("Resultados", "Modelo operacional") a não ser em slide de abertura de seção.

**Corpo — a evidência.** Um objeto visual dominante por slide. A evidência é o que prova a asserção; se não prova, ou a asserção está errada ou a evidência é a errada.

**Rótulos.** Texto no corpo existe para nomear partes da evidência, dar unidade, marcar um número. Nunca para explicar — explicação é fala.

---

## 4. Grau de detalhamento

Orçamentos rígidos, verificáveis por contagem:

| Elemento | Limite |
|---|---|
| Palavras no título (asserção) | 6 a 12 |
| Palavras no corpo, total | **até 25**, contando rótulos de figura |
| Frases completas no corpo | **zero** — a única frase do slide é o título |
| Objetos visuais dominantes | 1 |
| Linhas de uma tabela | até 7 |
| Colunas de dado de uma tabela | até 6 |
| Séries num gráfico | até 4 |
| Itens numa lista, quando houver | até 4, de até 5 palavras cada |

Listas são exceção, não recurso padrão. Uma lista só se justifica quando os itens são genuinamente paralelos e enumeráveis — premissas, contribuições, etapas — e nunca quando cada item é uma frase explicativa disfarçada de tópico.

**Teste de corte.** Antes de manter qualquer trecho de texto no slide, perguntar: *isto eu vou dizer em voz alta?* Se sim, sai da tela e vai para `\note{}`. Texto que duplica a fala é o caso que a pesquisa mostra ser mais prejudicial.

**Teste da asserção.** Cobrir o corpo do slide e ler só o título: a plateia fica sabendo a conclusão. Cobrir o título e olhar só o corpo: a evidência sustenta aquela conclusão. Se qualquer um dos dois falhar, o slide não está pronto.

---

## 5. Identidade visual

### 5.1 Tema — Beamer clássico

`\usetheme{default}`. O layout macro é o Beamer raiz: título de frame alinhado à esquerda, sem barra de navegação, sem cabeçalho de seção repetido, sem logotipo, sem barra de progresso. Cada elemento persistente é ruído somado a **todos** os slides.

Os três ajustes obrigatórios sobre o tema:

```latex
\setbeamertemplate{navigation symbols}{}      % símbolos de navegação nunca aparecem
\setbeamertemplate{footline}[frame number]    % rodapé é só o número do slide
\setbeamertemplate{blocks}[rounded][shadow=false]
```

Proporção `aspectratio=169`, tamanho base `11pt` — o padrão do Beamer, que já é calibrado para projeção.

Abertura de seção usa o idioma clássico: sumário com a seção corrente destacada, via `\AtBeginSection`. Ele orienta sem custar tempo de fala e é gerado uma vez, no preâmbulo — nunca escrito à mão slide a slide.

### 5.2 Tipografia

Latin Modern, com tema de fonte serifado:

```latex
\usepackage{lmodern}
\usefonttheme{serif}
```

Esta é a escolha deliberada: a fonte do LaTeX é reconhecível, e o documento deve se parecer com o que é. Texto e matemática ficam na mesma família, o que elimina o descasamento entre o corpo do slide e as equações — problema real numa apresentação em que a equação é o objeto central.

Hierarquia de tamanho dentro do corpo, em três degraus e não mais: corpo normal para rótulos principais, `\footnotesize` para rótulos secundários, `\scriptsize` para unidades e notas de figura. Nunca `\tiny`: se só cabe em `\tiny`, não cabe.

### 5.3 Paleta

**Laranja Bitcoin como cor primária, cinzas como secundárias — aplicados a elementos gráficos, nunca ao texto.**

| Token | Hex | Papel |
|---|---|---|
| `laranja` | `F7931A` | Destaque primário: o elemento que o slide está afirmando |
| `laranjaEsc` | `B36308` | Ênfase forte, ou o extremo mais granular de uma rampa |
| `laranjaCla` | `FBC77E` | Preenchimento leve, ou o extremo menos granular de uma rampa |
| `cinzaEsc` | `3A3A3A` | Traço principal, texto de figura |
| `cinza` | `7A7A7A` | Elemento padrão, eixo, seta, borda |
| `cinzaCla` | `D5D5D5` | Preenchimento neutro, grade, contexto |

**Regra de aplicação.** Todo elemento gráfico é cinza por padrão. Vira laranja apenas quando é o objeto da asserção daquele slide — o dado que prova, a decisão que muda, a restrição que morde. Um slide em que tudo é laranja não destaca nada.

**Rampa para hierarquia ordenada.** Quando três coisas ordenadas precisam ser distinguidas ao mesmo tempo — os três níveis de decisão, três níveis de agregação, três cores de composto —, usa-se a rampa `laranjaCla → laranja → laranjaEsc`. A intensidade carrega a ordem: mais escuro é mais granular. Nunca resolver isso introduzindo uma quarta matiz.

**Texto não recebe cor.** Corpo do slide é preto. A identidade visual vive nos elementos: `structure` (título de frame, marcadores, título de bloco) é laranja por definição de tema, e figuras seguem a tabela acima. Texto colorido no corpo é ruído e está na lista negativa.

`\alert{}` destaca **uma** expressão por slide, no máximo. Dois destaques por slide anulam-se.

### 5.4 Densidade

Margem generosa. Um slide cheio até a borda lê-se como parede de informação, independentemente do conteúdo. Figura grande e centrada vale mais que figura pequena cercada de texto.

### 5.5 Pragmatismo do visual

O layout macro é conservador; o visual específico pode ser trabalhado. Essa assimetria é intencional: a moldura não deve chamar atenção, a evidência sim.

O critério para elaborar uma figura é sempre funcional, nunca decorativo. Um Gantt existe porque a alocação no tempo é o objeto da asserção; uma matriz sombreada existe porque a assimetria é o objeto da asserção. Se a figura pode ser substituída por um número sem perda, ela deve ser o número. Sombra, gradiente, ícone, moldura tridimensional e efeito de profundidade não têm função e não entram.

---

## 6. Diretrizes técnicas do Beamer

### 6.1 Preâmbulo canônico

Ordem fixa: `documentclass` → tema, tema de fonte e templates → codificação e idioma → fontes → matemática → tabelas → gráficos (`pgfplots`, `pgfgantt`, `tikz` com bibliotecas) → `appendixnumberbeamer` → bibliografia → cores → ajustes de `beamercolor` → `\AtBeginSection`. Todo pacote novo entra no bloco correspondente, nunca no fim do arquivo.

### 6.2 Padrões de frame

- **Abertura de seção**: `\section{}` sozinho no corpo; a página é gerada pelo `\AtBeginSection` definido no preâmbulo, com `\tableofcontents[currentsection,hideallsubsections]`. Nunca escrever esse frame à mão.
- **Fechamento**: `\begin{frame}[plain]` com o conteúdo centrado por `\vfill` — o tema `default` não tem `standout`.
- **Referências**: `\begin{frame}[allowframebreaks]`, com `\scriptsize`.
- **Anexos**: depois de `\appendix`, que desliga a numeração nos apêndices via `appendixnumberbeamer`.

### 6.3 Figuras que precisam caber

Dimensionar figura TikZ **pela altura**, não pela largura, sempre que ela for mais alta que larga:

```latex
\resizebox{!}{0.70\textheight}{% correto para figura alta
```

`\resizebox{\textwidth}{!}` numa figura alta produz transbordamento silencioso — a figura sai do slide pela base sem nenhum erro de compilação. Este defeito já ocorreu na figura de arquitetura de decisão deste projeto e só apareceu na inspeção visual do PDF.

Valor de referência: `0.70\textheight` cabe com folga sob um `frametitle` de uma linha. `0.84\textheight` **não** cabe.

### 6.4 Gráficos e diagramas

`pgfgantt` para escala de tempo e alocação de máquina — janelas do tático, subdivisão por cor, cronograma. Estilo fixo: `bar/.append style={draw=none}`, `vgrid={*1{draw=cinzaCla}}`, `canvas/.append style={draw=cinza!50}`, rótulos em `\scriptsize`. Barra em cinza quando é contexto, na rampa laranja quando é o objeto da asserção.

`pgfplots` para dado quantitativo, com `compat=1.18`, `axis lines*=left`, `ymajorgrids` em `cinzaCla`, `draw=none` nas barras, legenda sem moldura acima do eixo. Série de destaque em `laranja`, séries de comparação em cinza. Sem eixo secundário, sem 3D, sem sombra.

`tikz` para diagrama conceitual, com as bibliotecas `shapes.geometric`, `arrows.meta`, `positioning`, `calc`. Setas sempre `-{Stealth[length=3mm]}` em `cinza`; caixa padrão com borda `cinza` e fundo branco, caixa de destaque com borda `laranja` e fundo `laranja!12`. Fluxo de cima para baixo ou da esquerda para a direita, nunca ambos no mesmo diagrama sem eixo declarado.

### 6.5 Notas do palestrante

Toda explicação cortada do slide vive num `\note{}` imediatamente após o conteúdo do frame, dentro do próprio `\begin{frame}`. A nota é escrita em prosa corrida, na primeira pessoa do plural ou impessoal, como o texto será falado — não em tópicos.

O arquivo mantém as notas desligadas por padrão. Para gerar a versão com notas, alterna-se uma única linha no preâmbulo:

```latex
% \setbeameroption{show notes}                      % notas em página alternada
% \setbeameroption{show notes on second screen=right} % projeção com monitor duplo
```

Nota que não existe é fala não preparada. Todo slide cujo corpo foi enxugado ganha `\note{}` no mesmo movimento — nunca depois.

### 6.6 Compilação e verificação

Pipeline obrigatório, do zero, apagando auxiliares antes. O diretório de trabalho é a **raiz do repositório**, não `ufscar/` — é de lá que o `referencias.bib` é encontrado, e é a mesma convenção do `ModelagemAlgebrica.tex`:

```bash
rm -f ufscar/apresentacao.aux ufscar/apresentacao.bbl ufscar/apresentacao.blg \
      ufscar/apresentacao.nav ufscar/apresentacao.out ufscar/apresentacao.snm \
      ufscar/apresentacao.toc
pdflatex -interaction=nonstopmode -output-directory=ufscar ufscar/apresentacao.tex
bibtex ufscar/apresentacao
pdflatex -interaction=nonstopmode -output-directory=ufscar ufscar/apresentacao.tex
pdflatex -interaction=nonstopmode -output-directory=ufscar ufscar/apresentacao.tex
```

O `.bib` é o da raiz do repositório, referenciado como `\bibliography{referencias}` — nome puro, sem caminho e sem extensão, o que faz o mesmo `.tex` compilar no Overleaf com o projeto plano. Nunca duplicar o arquivo dentro de `ufscar/`.

`\bibliographystyle{abntex2-alf}` pode ser declarado ou omitido, desde que **depois** do `\usepackage[alf]{abntex2cite}`. O pacote redefine `\bibliographystyle` para escrever o `\bibstyle` uma única vez no `.aux` e já o chama por conta própria. Declará-lo **antes** do pacote usa o comando do kernel, que escreve na hora: saem dois `\bibstyle`, o BibTeX aborta com `Illegal, another \bibstyle command` e a lista de referências sai vazia.

**Verificação de transbordamento**, que a compilação não acusa como erro:

```bash
grep -a "Overfull \\\\vbox" ufscar/apresentacao.log
```

Acima de 20 pt o corte é visível na projeção e precisa ser corrigido; abaixo disso, conferir visualmente antes de aceitar.

**Inspeção visual obrigatória** antes de considerar a apresentação pronta — o código-fonte de um slide transbordado parece perfeitamente correto:

```bash
pdftoppm -png -r 55 ufscar/apresentacao.pdf pagina
```

E olhar as imagens, todas. Nenhum slide é dado como pronto por ter compilado.

### 6.7 Citações

`\cite{}` no corpo do slide, sempre parentético e sempre curto. `\citeonline{}` é para prosa da dissertação e raramente cabe num slide.

O comando `\citeonline{}` já renderiza o nome do autor sozinho — precedê-lo do nome digitado à mão duplica o sobrenome no PDF sem gerar erro de compilação. Defeito já ocorrido neste projeto, detectável apenas lendo o PDF renderizado.

---

## 7. Lógica e coesão entre slides

### 7.1 Arco narrativo

A sequência de slides responde, nesta ordem, a cinco perguntas — e nenhuma outra:

1. **Qual é o problema?** — contexto, processo físico, o que torna a decisão difícil
2. **O que já se sabe?** — literatura, e o que ela não cobre
3. **O que se propõe?** — a formulação matemática, que é a contribuição científica
4. **Como isso virou produto?** — arquitetura da solução e implementação, que são **decorrência** da formulação, não premissa dela
5. **Funciona?** — resultados, limitações, próximos passos

A ordem entre 3 e 4 é deliberada e não deve ser invertida. A arquitetura de decisão e a arquitetura de software são **etapa de produto tecnológico**: elas mostram como os modelos foram montados num sistema que roda. Apresentá-las antes da formulação inverte a hierarquia do trabalho — sugere que a decomposição veio de conveniência de engenharia, quando ela vem da estrutura física do problema (dois *setups* em escalas distintas) e é justificada pela literatura de planejamento hierárquico.

O que a plateia precisa saber **antes** das formulações é apenas que existem três níveis, e isso se resolve com uma faixa visual de três bandas rotuladas, sem anotação — não com o diagrama completo.

### 7.2 Regra de continuidade

Cada slide retoma o anterior por um elemento **visual** concreto: a mesma cor, a mesma figura ampliada, o mesmo eixo, o mesmo símbolo. Nunca por conectivo verbal escrito na tela.

O caso exemplar deste projeto: o Gantt das janelas táticas e o Gantt da subdivisão por cor compartilham eixo de dias e escala — o segundo é literalmente o primeiro ampliado. A plateia enxerga o acoplamento entre os níveis sem que uma palavra o explique.

### 7.3 Uma ideia por slide

Se o título precisa de "e" para ligar duas afirmações independentes, são dois slides. Se a evidência tem dois objetos visuais que não se comentam, são dois slides.

O inverso também vale: dois slides que sustentam a mesma asserção com evidências parciais são um slide só, mal dividido.

### 7.4 Notação

Um símbolo aparece na tela **depois** de ter sido apresentado numa tabela de Conjuntos, Parâmetros e Variáveis, nesta ordem, exatamente como na dissertação (regra 6 do `CLAUDE_WRITTER.MD`, que continua valendo integralmente para notação). Slide de equação nunca introduz símbolo novo sem tabela anterior.

Símbolo em equação é sempre letra — nunca nome descritivo. A tabela de notação é evidência visual legítima e conta como corpo do slide.

### 7.5 Densidade ao longo do tempo

Trinta minutos comportam entre 25 e 35 slides quando eles seguem este guia, porque slide de evidência visual consome menos tempo de fala que slide de texto. Slides de abertura de seção, capa e fechamento consomem segundos.

Slide de equação é a exceção: consome de 60 a 90 segundos e não deve haver mais de um a cada três slides, nem dois consecutivos sem uma figura entre eles.

---

## 8. Lista negativa — o que nunca aparece num slide

- Título que é rótulo em vez de asserção ("Resultados", "Modelo tático"), fora de abertura de seção.
- Frase completa no corpo do slide.
- Parágrafo explicativo, em qualquer tamanho de fonte — pertence a `\note{}`.
- Lista de tópicos em que cada item é uma oração.
- Texto que o apresentador vai ler em voz alta.
- Rodapé persistente, logotipo repetido, barra de navegação.
- Mais de um `\alert{}` por slide.
- Texto de corpo colorido — cor vive nos elementos gráficos, não nas palavras.
- Matiz fora da paleta laranja/cinza, ou laranja aplicado a algo que não é o objeto da asserção.
- Sombra, gradiente, ícone decorativo, efeito de profundidade.
- Figura em `\tiny`, ou reduzida a ponto de exigir aproximação para ler.
- Tabela transposta da dissertação sem cortar colunas.
- Slide que existe só porque o conteúdo está na dissertação.
- Animação ou transição decorativa.
- Emoji.

---

## 9. Checklist antes de considerar a apresentação pronta

- Todo título é uma frase completa com verbo, entre 6 e 12 palavras?
- Nenhum corpo de slide passa de 25 palavras?
- Nenhum corpo contém frase completa?
- Cada slide tem exatamente um objeto visual dominante que sustenta a asserção do título?
- O teste de corte foi aplicado: nada na tela duplica o que será falado?
- Toda explicação removida foi para `\note{}`, e não simplesmente descartada?
- Todo elemento gráfico é cinza, exceto o que é objeto da asserção, que é laranja?
- Nenhum texto de corpo está colorido?
- Cada slide retoma o anterior por um elemento visual, não por conectivo escrito?
- A formulação matemática vem **antes** da arquitetura da solução?
- Todo símbolo apareceu numa tabela de notação antes do primeiro uso em equação?
- O `.tex` foi compilado do zero, com `bibtex` no meio, sem erro?
- `grep "Overfull \vbox"` foi rodado e nenhum transbordamento passa de 20 pt?
- O PDF renderizado foi inspecionado **página por página**, em imagem, e não só compilado?
