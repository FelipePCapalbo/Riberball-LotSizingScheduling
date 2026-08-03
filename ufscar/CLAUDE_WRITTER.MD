# Guia de estilo de escrita da dissertação

Este documento fixa como a dissertação deve ser escrita, do ponto de vista estilístico. Vale para todo `.tex` do projeto, em qualquer sessão de escrita, presente ou futura — não há margem para desvio nem para redescobrir o estilo a cada sessão nova. Onde uma escolha de redação divergir do que está aqui, o texto está errado, não o guia.

O padrão codificado abaixo foi extraído do que já funciona no `ModelagemAlgebrica.tex` (especialmente as seções "Modelo de demanda" e "Modelo de otimização") e complementado pela leitura de Camargo, Toledo e Almada-Lobo (2014) — artigo sobre um problema de dois estágios sincronizados na indústria de fiação, estruturalmente próximo do problema desta dissertação, usado como referência de estilo para a Seção 10. Deve ser aplicado retroativamente sempre que uma seção nova for escrita ou uma seção antiga for revisada.

---

## 1. Leitor-alvo

O leitor não tem memória de nenhuma conversa anterior com um assistente, nem acesso a este guia — só ao texto final. Ele é tecnicamente competente em termos gerais (sabe o que é um modelo de otimização, uma variável de decisão, uma restrição) mas não tem nenhuma exposição prévia a este problema específico, a esta notação específica, a esta indústria específica.

Toda informação particular a esta dissertação — símbolo, termo de indústria, escolha de modelagem — é definida no primeiro uso, exatamente uma vez, e nunca presumida conhecida de um capítulo anterior sem uma referência explícita de volta a onde foi definida. Escreve-se para quem lê linearmente, capítulo a capítulo, pela primeira vez — não para quem já sabe a resposta.

## 2. Arquitetura da frase

Uma frase carrega uma afirmação (mais, quando necessário, sua qualificação direta). Duas afirmações sem relação lógica direta não dividem a mesma frase.

Orações fortemente relacionadas se juntam com ponto e vírgula ou travessão, em vez de se fragmentarem em frases curtas e desconectadas que perdem o elo causal entre elas. O travessão (`---`) é reservado para um aparte dentro da frase — uma clarificação, um exemplo, uma reformulação em outros termos —, nunca um substituto decorativo do ponto final, e nunca duas vezes na mesma frase para dois apartes sem relação entre si.

Evitar perguntas retóricas e endereçamento direto ao leitor ("você verá que", "note que", "perceba que"). Evitar ressalvas que não acrescentam informação — "pode-se dizer que", "de certa forma", "em certo sentido", "não é incomum que": se a afirmação é verdadeira, ela é feita diretamente, sem cerca. Evitar narrar o próprio ato de escrever — "nesta seção, discutiremos", "este capítulo tem como objetivo", "como veremos a seguir": diz-se a coisa; não se anuncia que vai dizê-la.

## 3. Arquitetura do parágrafo

Um parágrafo carrega uma ideia, enunciada na primeira frase; as frases seguintes desenvolvem, qualificam ou exemplificam essa ideia — nunca introduzem uma segunda ideia sem relação com a primeira.

Cada parágrafo retoma o fio que o parágrafo anterior deixou — pelo mesmo termo, pelo mesmo símbolo, ou por um conectivo que nomeia a relação ("essa fronteira", "esse padrão", "essa combinação") —, nunca por um conectivo genérico e vazio usado como muleta de abertura ("além disso", "outrossim", "nesse sentido", "cabe destacar que").

Parágrafos são curtos: de duas a cinco frases. Um parágrafo que precisa de uma sexta frase para fechar a ideia deve ser quebrado na junta natural, com a segunda metade abrindo no conectivo que nomeia a relação com a primeira.

## 4. Fluxo linear — sem loops

Definir antes de usar, sempre: um símbolo, uma sigla, um termo de indústria aparece numa tabela, num glossário ou numa frase que o define antes do primeiro uso em prosa ou em equação, sem exceção.

Nunca reintroduzir um conceito sob outro nome. Uma vez escolhido o termo — "balão", "período", "setup" —, ele é o único nome para esse conceito pelo resto do documento; um sinônimo introduz dúvida sobre se é a mesma coisa ou não.

Nunca explicar a mesma coisa duas vezes por ênfase. Uma seção de síntese pode retomar conteúdo anterior somente quando acrescenta um ângulo novo — comparação, consolidação, quantificação; uma retomada que não acrescenta nada é um loop e deve ser cortada.

Referências para frente são permitidas apenas dentro do mesmo capítulo e apenas via `\ref`/`\label` explícito, apontando para onde a promessa é cumprida — nunca um "veremos mais adiante" vago e sem âncora.

## 5. Terminologia

Um termo canônico por conceito, fixo do início ao fim: balão (nunca alternando com "produto" sem necessidade), período (nunca alternando com "intervalo" ou "etapa" como sinônimos, a menos que a distinção esteja fazendo trabalho real no argumento), máquina, *setup*, formato, acabamento, cor.

Termos técnicos em outro idioma (*setup*, *forecast*, *features*, *backorder*, *holding cost*, *block planning*...) são apresentados uma vez em itálico, com o correspondente em português ao lado se necessário, e permanecem nessa mesma forma itálica em todo o resto do texto — nunca traduzidos num lugar e deixados em inglês em outro.

Siglas são escritas por extenso no primeiro uso, com a sigla entre parênteses logo em seguida; depois disso, só a sigla.

## 6. Notação algébrica

Todo conjunto, parâmetro e variável é uma letra — possivelmente acentuada, grega, ou com um acento diacrítico (chapéu, til, sobrescrito) — nunca um nome descritivo. Esta é a convenção da literatura de *lot sizing*/*scheduling* citada na dissertação, e é a única forma aceita aqui.

**Índices**: letra minúscula itálica, uma só — $i$ (balão), $j$ (máquina), $t$ (período), $d$ (dia), $f$ (formato), $k$ (*feature*/mês). Reutilizar exatamente este conjunto em todo capítulo novo; não introduzir uma segunda letra para o mesmo papel.

**Conjuntos**: letra maiúscula correspondente ao índice — $I$, $J$, $T$, $D$, $F$, $K$ —, com notação de subconjunto quando necessário ($I_f \subseteq I$).

**Parâmetros**: letra minúscula, subscrita pelos índices dos quais depende ($d_{it}$, $c_i$, $p_{ij}$, $h_{jd}$, $t^s_j$); letra grega para escalar sem índice ($\alpha$, $\lambda$).

**Variáveis**: uma letra reservada por papel, mantida constante no documento inteiro uma vez fixada ($s$ para estado de *setup*, $\delta$ para ocorrência de *setup*, $I$ para estoque — a sobreposição com o conjunto $I$ já existe no modelo atual e é resolvida pelo contexto: $I$ é conjunto só sob $\sum_{i \in I}$ ou equivalente; $I_{it}$ é sempre a variável de estoque).

Antes de introduzir uma letra nova, checar que ela não está presa a outro significado em outro lugar do documento. Se a colisão for inevitável entre modelos independentes (um escalar de um capítulo e um parâmetro subscrito de outro compartilhando a mesma letra), sinalizar isso explicitamente numa nota — nunca deixar em silêncio.

Todo símbolo aparece numa tabela — nesta ordem: Conjuntos, Parâmetros, Variáveis — antes do primeiro uso, uma linha por símbolo, descrição terminada em ponto final, unidade entre parênteses quando o símbolo tiver uma.

## 7. Equações e restrições

Uma frase curta de entrada, terminada em dois-pontos, nomeia o que a equação computa imediatamente antes do display — nunca uma equação nua, sem introdução. Isso vale para toda equação derivada, intermediária ou de apoio dentro de um argumento em prosa (as etapas de uma cascata de estimação, por exemplo).

**Exceção explícita**: a equação que define o modelo inteiro — a função objetivo e o bloco de restrições de um MILP — usa cabeçalho curto em negrito (`Minimizar`, `Sujeito a`) em vez de frase de entrada, seguindo a convenção universal da literatura de otimização citada nesta dissertação. Essa equação não é uma etapa intermediária de um argumento; é o objeto que o capítulo inteiro existe para apresentar, e o cabeçalho já cumpre o papel de nomeá-la. Fora desse caso — objetivo e restrições de um modelo formal —, a frase de entrada terminada em dois-pontos é obrigatória.

Toda equação não trivial é seguida de exatamente um parágrafo de prosa (nunca mais, nunca uma simples reformulação em palavras do que a equação já diz) cobrindo: seu papel no modelo, seu comportamento nos casos-limite, e sua interação com as demais equações ao redor. Uma equação genuinamente autoevidente a partir da frase de entrada dispensa esse parágrafo — mas esse julgamento deve ser raro e deliberado, não um atalho para não escrever.

Restrições do mesmo modelo são agrupadas num único bloco `\begin{align}`, cada uma com seu próprio `\label` e seu próprio domínio (`\forall...`) alinhado à direita — nunca dispersas em displays separados sem agrupamento lógico.

## 8. Tabelas

**Regra concreta de tamanho**: uma tabela com mais de 6 colunas de dado (sem contar a coluna de rótulo) não cabe em `\small` numa página A4 com margens de 1 polegada — dividir, transpor, ou eliminar colunas redundantes antes de inserir. *(Incidente real já identificado neste documento: a Tabela `tab:fc_i21`, no Apêndice, excede a largura do texto em compilação — corrigir ao aplicar este guia.)*

Preferir transpor quando a dimensão "larga" é tempo (períodos, meses): períodos em linha, uma métrica por coluna — não o inverso.

Tabelas de duas colunas tipo glossário (símbolo | descrição) usam o formato `tabularx` L/R já definido no preâmbulo; tabelas numéricas usam `booktabs` (`\toprule`/`\midrule`/`\bottomrule`), `\small`, colunas numéricas alinhadas à direita.

A legenda (`\caption`) de toda tabela diz o que ela contém e seu escopo (qual subconjunto de dados, qual cenário) em uma linha; o rótulo (`\label`) segue o padrão `tab:<slug>`.

Uma tabela que precisa de legenda para ser lida (cabeçalhos abreviados, símbolos como ✓/--/parcial) explica essa legenda uma vez, na legenda da tabela ou no parágrafo que a introduz — nunca deixa um símbolo sem explicação.

## 9. Citações

`\citeonline{}` quando o autor é o sujeito gramatical da frase; `\cite{}` para referência parentética ao final de uma afirmação.

**Erro recorrente a nunca repetir**: `\citeonline{}` já renderiza "Nome do Autor (Ano)" sozinho — o comando não precisa (e não pode) ser precedido do nome do autor digitado manualmente. Escrever "Hax e Meal \citeonline{haxmeal1975}" compila sem erro mas renderiza "Hax e Meal Hax e Meal (1975)", duplicando o nome — esse bug já aconteceu neste documento, em toda a Revisão de Literatura, e só foi pego numa auditoria visual do PDF compilado, não pela compilação em si (que não acusa erro nenhum). A forma correta é `\citeonline{haxmeal1975} formalizam...`, deixando o comando sozinho no lugar onde o nome do autor entraria na frase. `\citeonline{}` aceita múltiplas chaves separadas por vírgula quando dois ou mais trabalhos dos mesmos autores são citados juntos como sujeito (`\citeonline{ferreira2009,ferreira2010}` renderiza "Ferreira, Morabito e Rangel (2009, 2010)").

Uma citação nunca aparece sem a frase explicar, na mesma respiração, o que o trabalho citado contribui para o argumento em construção — nunca um amontoado de citações sem diferenciação (`\cite{a,b,c,d}` sem dizer o que cada uma traz).

**Verificação obrigatória antes de considerar uma seção com citações pronta**: compilar do zero (apagar `.aux`/`.bbl`/`.blg` antes de rodar `pdflatex`→`bibtex`→`pdflatex`×2, nunca compilar incremental em cima de auxiliares antigos) e **ler o PDF renderizado**, não só o `.tex` fonte — o código-fonte de uma citação quebrada parece perfeitamente correto; o defeito só aparece no texto renderizado. Sobrenomes compostos sem hífen (como "Fatemi Ghomi") precisam de chaves protetoras no `.bib` (`{Fatemi Ghomi}, S. M. T.`) para não serem truncados ao primeiro nome — o efeito colateral é que esse sobrenome específico deixa de ficar em caixa alta na lista de Referências (`abntex2-alf` aplica maiúsculas via um mecanismo que as chaves protetoras bloqueiam); é uma imperfeição cosmética conhecida e aceitável, não um novo bug a perseguir.

## 10. Descrição do problema — técnicas adicionais

Extraídas da Seção 2 ("The production system") de Camargo, Toledo e Almada-Lobo (2014): um problema de dois estágios sincronizados (mistura de fibras → fiação) estruturalmente muito próximo do problema dos balões, usado aqui como modelo de como descrever o problema *antes* de formalizá-lo.

Nomear explicitamente qual estágio é o gargalo do processo, e dizer por quê um estágio anterior ou posterior *não* restringe a produção, em vez de deixar isso implícito. Camargo et al. afirmam logo na descrição do processo que a fiação é o gargalo, porque a capacidade dos estágios anteriores é suficiente para sustentá-la; a afirmação é retomada mais adiante, já com a evidência de que o *setup* de troca de mistura é nulo, fechando o argumento com um dado novo — uma retomada que confirma, não uma repetição vazia (compatível com a Regra 4: retomar só quando acrescenta ângulo).

Toda decisão de modelagem não óbvia — por que existe *backlog*, por que um tipo de *setup* é considerado nulo, por que a demanda é tratada como determinística — recebe uma frase de justificativa física ou de negócio antes da equação correspondente, não só depois: a equação formaliza o que a prosa já motivou.

Índices e conjuntos podem ser introduzidos de forma narrativa, em prosa corrida, antes da tabela formal de notação (Camargo et al.: "consider $N$ yarns to be scheduled on $M$ parallel machines over a horizon $T$"), para que o leitor já reconheça os símbolos quando a tabela aparecer. Essa exposição em prosa não substitui a tabela formal — a Regra 6 continua obrigatória —; é uma segunda apresentação, mais suave, que a antecede.

Ao adaptar um modelo de outro trabalho, declarar a proveniência numa frase explícita — "esta seção descreve uma formulação adaptada de [modelo], introduzida em [referência]" — nunca apresentar uma formulação herdada como se tivesse surgido do zero.

Um exemplo ilustrativo pequeno e concreto (poucos itens, poucas máquinas, poucos períodos) pertence ao capítulo de descrição do problema, não só ao apêndice final — ele ancora a formalização abstrata que vem a seguir, antes que o leitor precise segurá-la só na cabeça. O apêndice numérico desta dissertação (previsão de demanda) já segue esse espírito; a seção de "Descrição do problema"/"Processo produtivo" pode ganhar tratamento equivalente para o modelo de otimização.

Restrições que, juntas, implementam um único mecanismo (por exemplo, uma cadeia de três restrições que define o *carryover* de estado) podem compartilhar um único parágrafo de explicação, desde que esse parágrafo cubra as três e diga como se encaixam — em vez de uma explicação isolada por restrição. Isso complementa a Regra 7: "uma equação, um parágrafo" é o piso, não o teto; um grupo de restrições fortemente acopladas é tratado como uma unidade.

## 11. Lista negativa — o que nunca aparece no texto

- Transições de preenchimento sem conteúdo: "é importante notar que", "vale ressaltar que", "cabe destacar que", "além disso" usado como muleta de abertura de parágrafo.
- Perguntas retóricas e endereçamento direto ao leitor.
- Referência ao próprio ato de escrever ("neste texto/capítulo/seção, vamos explorar...").
- Listas de três adjetivos para dizer uma coisa só.
- Ressalvas que não comprometem nem informam ("pode-se dizer", "de certa forma", "em certo sentido").
- Travessão como substituto de ponto final, ou mais de um aparte por frase.
- Repetição de um fato recém-afirmado, sem ângulo novo, só por ênfase.
- Dois parágrafos consecutivos abrindo com o mesmo conectivo.
- Nome descritivo em notação algébrica (nada de `estoque_i` — é $I_i$).
- Sinônimo para um termo já fixado (Seção 5).

## 12. Checklist antes de considerar uma seção pronta

- Todo símbolo usado já apareceu antes numa tabela de Conjuntos/Parâmetros/Variáveis?
- Todo termo técnico e toda sigla foram definidos no primeiro uso?
- Cada parágrafo retoma o fio do anterior, sem conectivo vazio?
- Nenhuma explicação se repete sem acrescentar ângulo novo?
- Toda equação tem frase de entrada e (quando não trivial) parágrafo de prosa depois?
- Nenhuma tabela excede 6 colunas de dado sem justificativa de que cabe na página?
- Nenhum item da lista negativa (Seção 11) aparece no texto?
- Toda decisão de modelagem não óbvia tem justificativa física antes da equação (Seção 10)?
- O `.tex` foi recompilado do zero (aux/bbl apagados antes) e o PDF renderizado foi lido — não só o código-fonte — para conferir se as citações aparecem corretas?
