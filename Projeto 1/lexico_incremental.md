# Construção incremental do léxico

Documento de método para a montagem do `lexicon.csv` do projeto de extração de casos clínicos.
Todos os números abaixo foram medidos sobre os arquivos `cases.csv` e `metadata.csv` da amostra.

---

## 1. O que os dados realmente contêm

### Corpus

| Medida | Valor |
|---|---|
| Artigos (`metadata.csv`) | 50 |
| Casos (`cases.csv`) | 56 |
| Tokens alfabéticos (soma de `case_text`) | 26.105 |
| Tipos distintos | 5.049 |
| Tipos com frequência ≥ 2 | 2.420 |
| Tipos com frequência ≥ 5 | 899 |
| Bigramas com frequência ≥ 2 | 3.136 |
| Trigramas com frequência ≥ 2 | 1.535 |

O corpus é pequeno. Isso é uma vantagem: curadoria manual do léxico é viável dentro do prazo, e o pipeline inteiro roda em segundos, o que permite iterar muito.

> **Divergência a conferir:** o README do enunciado descreve a amostra como tendo 246 casos. O `cases.csv` entregue tem 56 linhas, e a soma da coluna `case_amount` do `metadata.csv` também dá 56. Vale confirmar com o professor se recebemos um recorte menor ou se o número do README está desatualizado. O plano abaixo vale para os dois cenários; só muda o volume de triagem.

### Metadados — números corrigidos

A versão anterior deste plano continha erros. Segue a medição:

| Campo | Situação real | O que havia sido dito antes |
|---|---|---|
| `keywords` | **15 dos 50 artigos** sem keywords; 35 têm | "30 sem keywords" — **errado** |
| `keywords` (total de termos) | 161 termos; **69 (42,9%)** aparecem literalmente no `case_text` | 43% — confere |
| `major_mesh_terms` | **43 dos 50** vazios (`[]`) | 43 — confere |
| `mesh_terms` | 8 dos 50 vazios; o descritor mais comum é `Case Reports` (41 artigos) | confere |
| `mesh_terms` (aderência ao texto) | ~13% dos descritores aparecem literalmente no `case_text` | confere |

A contagem manual da equipe apontou 14 artigos sem keywords; a medição dá **15** (`PMC5137649`, `PMC7102447`, `PMC6354154`, `PMC4835621`, `PMC8627357`, `PMC3917415`, `PMC9529523`, `PMC6949661`, `PMC7519975`, `PMC6083636`, `PMC7086412`, `PMC3557982`, `PMC3859158`, `PMC3897989`, `PMC2817501`). A diferença provavelmente é uma linha contada a mais ou a menos; vale reconferir antes de citar o número no relatório.

**Consequência da correção:** as keywords são um recurso melhor do que a versão anterior dava a entender. 69 termos clínicos já validados contra o texto, de graça, é comparável a uma sessão inteira de anotação manual. Elas deixam de ser o último estágio e sobem para o começo do processo.

Já os termos MeSH continuam fracos aqui: `major_mesh_terms` está vazio na maioria dos artigos, e boa parte do que sobra em `mesh_terms` não é clínico (`Humans`, `Female`, `Case Reports`). Além disso, o campo é uma lista serializada como texto e vários descritores contêm vírgula interna (`'Diagnosis, Differential'`), o que quebra qualquer *split* ingênuo por vírgula. Se formos usar MeSH, tem que ser com parser cuidadoso — ou direto do vocabulário da NLM, não deste CSV.

---

## 2. Princípio de organização

Duas inversões em relação ao plano original.

**O corpus é a fonte primária do léxico; os metadados são fonte auxiliar e instrumento de validação.** O `case_text` é o que vamos processar, então é ele que define o vocabulário que precisamos cobrir.

**O incremento é por método de descoberta de termos, não por fonte de dados.** Cada método encontra um tipo diferente de termo: frequência pega o vocabulário do meio da distribuição, padrões pegam termos já tipados, sufixos pegam a cauda longa. Organizar as versões assim permite medir separadamente a contribuição de cada técnica — o que, além de ser bom método, rende resultado de avaliação para os slides.

---

## 3. Decisão que vem antes de tudo: separação dev/eval

Fazer **agora**, antes de qualquer colheita de termos.

- Split **por artigo**, não por caso: casos do mesmo artigo compartilham autor, estilo e vocabulário, e cairiam nos dois lados.
- Sugestão: **35 artigos dev / 15 artigos eval**, com sorteio de semente fixa registrada no repositório.
- Toda colheita automática (frequência, padrões, abreviações) roda **só sobre o dev**. As keywords também: usar as keywords de um artigo de avaliação é vazamento, porque são metadados do próprio texto que vamos medir.
- O `eval` só é aberto para anotação manual e medição final.

Sem isso, o recall medido é ficção: o léxico terá sido construído olhando as respostas.

---

## 4. Esquema do `lexicon.csv`

Mais colunas do que as três originais:

```csv
term,type,canonical,match,source,version,notes
fever,Symptom,fever,exact,manual,v0,
dyspnoea,Symptom,dyspnea,exact,variant,v4,grafia britanica
CT,Exam,computed tomography,cased,abbrev,v4,
CA,Lab,carbohydrate antigen,cased,abbrev,v4,nao casar com "ca" minusculo
carcinoembryonic antigen,Lab,carcinoembryonic antigen,exact,abbrev,v4,
amoxicillin,Treatment,amoxicillin,exact,suffix,v5,-cillin
```

| Coluna | Função |
|---|---|
| `term` | forma como pode aparecer no texto |
| `type` | tipo de nó (`Symptom`, `Exam`, `Condition`, `Treatment`, ...) |
| `canonical` | forma padronizada para deduplicação |
| `match` | `exact` (case-insensitive), `cased` (sensível a maiúsculas), `regex` |
| `source` | `manual`, `keyword`, `freq`, `pattern`, `abbrev`, `variant`, `suffix`, `mesh` |
| `version` | estágio em que o termo entrou |
| `notes` | justificativa, casos de erro conhecidos |

`source` e `version` são o que permite responder "quanto cada método contribuiu para o recall final" — é resultado experimental, não burocracia. `match = cased` é o que evita que a sigla `CA` (*carbohydrate antigen*, presente no corpus) case com qualquer "ca" minúsculo.

---

## 5. Estágios

### v0 — Semente manual (~60 termos, 1 sessão)

**Objetivo:** fechar o pipeline de ponta a ponta, não cobertura.

Escolher 3 casos do dev e anotar à mão tudo que aparece: sintomas, exames, condições, tratamentos. Rodar o pipeline completo (ler caso → segmentar → casar termos → gerar `nodes.csv`/`edges.csv`) com um léxico que a equipe conhece de cor.

**Por que primeiro:** a maior parte do tempo do projeto vai ser gasta em problemas de *matching*, não de dicionário. Descobrir isso na primeira semana, com 60 termos, é muito mais barato do que descobrir depois com 800.

**Critério de saída:** os 3 casos produzem grafo, e a equipe consegue explicar cada nó e cada aresta gerados.

---

### v1 — Keywords do metadata, filtradas pelo texto

**Rendimento medido:** 161 keywords no total, das quais **69 aparecem literalmente no `case_text`** (restringindo ao dev, o número cai proporcionalmente).

**Procedimento:** para cada artigo do dev, ler as keywords, verificar presença no texto do caso correspondente, e triar manualmente as que passaram — só falta atribuir `type` e `canonical`. Descartar as que não aparecem no texto (a regra do plano original está certa: nenhum termo vira nó sem ocorrer no `case_text`).

**Por que subiu de posição:** é o melhor retorno por hora de trabalho de todo o processo. Os termos já são clínicos, já foram escolhidos por um autor humano, e a taxa de 43% de presença no texto é alta o suficiente para valer a triagem.

**Limitação a registrar:** 15 artigos não têm keywords nenhuma, e os que têm são justamente os mais bem indexados. O léxico resultante é enviesado para esse subconjunto — motivo pelo qual este estágio complementa a colheita por frequência em vez de substituí-la.

---

### v2 — Colheita por frequência

**Volume medido no dev (35 artigos, 15.971 tokens), após remover n-gramas com stop-words e com dígitos:**

| Faixa | Candidatos |
|---|---|
| Unigramas com freq ≥ 4 | 683 |
| Bigramas com freq ≥ 3 | 220 |
| Trigramas com freq ≥ 2 | 135 |
| **Total** | **~1.038** |

Aproximadamente 200 a 250 candidatos por integrante, em uma planilha com colunas: `aceitar/rejeitar`, `type`, `canonical`, `notas`. Com limiares mais baixos o volume explode (bigramas ≥ 2 sem stop-word já são 956), então os limiares acima são o ponto de equilíbrio.

**O que este estágio pega que os outros não pegam:** o vocabulário do meio da distribuição — termos frequentes no corpus que nenhum autor listou como keyword e que o MeSH não indexa.

**Cuidado:** trigramas antes de bigramas antes de unigramas na triagem, para reconhecer expressões multipalavra (`abdominal pain`, `upper gastrointestinal series`) antes de aceitar as partes isoladas.

---

### v3 — Colheita por padrão (*bootstrapping*)

Os mesmos padrões que vamos usar para extrair **relações** servem para extrair **candidatos já tipados**. Ocorrências medidas no corpus completo:

| Padrão | Ocorr. | Tipo sugerido do que vem depois |
|---|---|---|
| `showed` | 128 | achado / `Condition` |
| `revealed` | 87 | achado / `Condition` |
| `was performed` | 42 | `Exam` |
| `underwent` | 39 | `Exam` / procedimento |
| `history of` | 30 | `Condition` (histórico) |
| `consistent with` | 22 | `Condition` |
| `initiated` | 17 | `Treatment` |
| `presented with` | 14 | `Symptom` |
| `diagnosed with` | 13 | `Condition` |
| `treated with` | 13 | `Treatment` |
| `was admitted` | 11 | marco temporal |
| `started on` | 9 | `Treatment` |

`revealed` e `showed` são de longe os mais frequentes e não estavam na lista original da equipe — vale adicioná-los. Em compensação são mais ambíguos (`CT showed a mass` vs. `the patient showed improvement`), então entram com precisão menor.

**Vantagem:** a tipagem sai de graça. **Limitação:** cobertura baixa, porque só pega o que está imediatamente adjacente a um gatilho. Complementa v2, não substitui.

---

### v4 — Abreviações e variantes

**Abreviações.** O padrão `forma longa (SIGLA)` — algoritmo de Schwartz & Hearst — encontra **158 ocorrências** no corpus. Exemplos reais extraídos:

```
carcinoembryonic antigen (CEA)
carbohydrate antigen (CA)
Computed tomography (CT)
upper gastrointestinal (UGI)
esophagogastroduodenoscopy (EGD)
postoperative day (POD)
electrocardiogram (EKG)
acute coronary syndrome (ACS)
```

Cada par gera duas linhas no léxico apontando para a mesma `canonical`, sem trabalho manual. As siglas entram com `match = cased`.

**Variantes.** Geradas a partir dos termos já aceitos: plural, `-ing`/`-ed`, hífen opcional (`CT scan` / `CT-scan`), grafia britânica/americana (`dyspnoea` / `dyspnea`, `tumour` / `tumor`).

Este é o estágio de melhor custo-benefício depois da v1: é automático e o retorno é imediato.

---

### v5 — Sufixos como heurística de tipo (*fallback*)

Com 5.049 tipos distintos e cauda longa, escrever tudo à mão não escala. Ocorrências medidas:

| Sufixo | Ocorrências | Termos distintos | Tipo |
|---|---|---|---|
| `-osis` | 93 | 20 | `Condition` |
| `-graphy` | 47 | 12 | `Exam` |
| `-scopy` | 38 | 11 | `Exam` |
| `-oma` | 35 | 10 | `Condition` |
| `-itis` | 29 | 19 | `Condition` |
| `-emia` | 19 | 10 | `Condition` |
| `-ectomy` | 17 | 11 | procedimento |
| `-pathy` | 9 | 4 | `Condition` |
| `-cillin`, `-mycin`, `-azole`, `-sone`, `-statin` | 15 | 15 | `Treatment` |

Os sufixos de fármaco cobrem `amoxicillin`, `ampicillin`, `methicillin`, `piperacillin`, `clarithromycin`, `clindamycin`, `vancomycin`, `carbimazole`, `methimazole`, `omeprazole`, `pantoprazole`, `cortisone`, `dexamethasone`, `prednisone`, `atorvastatin`.

**Falso positivo real e documentado:** a regra `-pril` (inibidores da ECA: *lisinopril*, *enalapril*) casa com **`april`**, que ocorre no corpus como data. Nenhum inibidor da ECA aparece no texto, ou seja, a regra tem precisão 0% aqui. Este é um ótimo exemplo para os slides: mostra concretamente o custo de uma heurística morfológica e por que ela precisa ser marcada e medida separadamente.

Por isso: termos vindos de sufixo entram com `source = suffix` e passam por revisão humana antes de virar nó. A métrica interessante é quanto recall a regra adiciona e a que custo de precisão.

---

### v6 — MeSH e fontes externas

Último estágio, com expectativa baixa. Serve principalmente como **checagem de recall**: dos descritores que o artigo declara, quantos o nosso léxico pega?

Se sobrar tempo e alguém quiser ir além, a alternativa é baixar o MeSH direto da NLM (não usar o campo do CSV): os *Entry Terms* trazem sinônimos prontos e os *tree numbers* dão a hierarquia, o que habilitaria consultas do tipo "recuperar casos de doenças cardiovasculares" a partir de menções específicas. É um diferencial legítimo, mas é escopo adicional — só depois de v0 a v5 fecharem.

---

## 6. Regras de casamento

Independentes do estágio, valem para todo o léxico:

1. **Termo mais longo primeiro.** Sem isso, `pain` casa antes e `abdominal pain` nunca é encontrado.
2. **Normalização antes do casamento:** minúsculas (exceto termos `cased`), plural, lematização leve.
3. **Autômato de Aho-Corasick** para casar milhares de termos em uma passada. Com 56 casos a performance nem importa, mas a implementação é limpa e rende slide.
4. **Guardar offsets de caractere** de cada casamento. São necessários depois para negação (escopo), para associação temporal e para a evidência textual.

---

## 7. Como medir a contribuição de cada estágio

Ao fim de cada versão, rodar o pipeline sobre o **dev** e registrar:

| Métrica | Como obter |
|---|---|
| Tamanho do léxico | linhas por `type` e por `source` |
| Menções casadas | total de casamentos no corpus dev |
| Cobertura de tokens | % dos tokens do dev cobertos por algum termo |
| Novos termos únicos do estágio | termos que nenhum estágio anterior tinha |
| Precisão da tipagem | amostra de 30 termos por `source`, verificada à mão |

A tabela final "contribuição por método" é um dos melhores slides possíveis para esta etapa, porque mostra exatamente o que o enunciado pede: entendimento do impacto de cada algoritmo na geração do grafo.

---

## 8. Observação sobre o diferencial temporal

O léxico de entidades e o léxico temporal são arquivos separados e devem ser construídos em paralelo. Ocorrências medidas no corpus:

| Construção | Ocorrências |
|---|---|
| `<número> <dia/semana/mês/ano>` (algarismo ou por extenso) | 163 |
| `<unidade> later / prior / before / after` | 48 |
| Nome de mês (datas explícitas, ex. `on January 22, 2020`) | 48 |
| `postoperative day` | 9 |
| `on admission` | 6 |
| `the next day` / `the following day` | 3 |
| `twice daily` / `once daily` / `every N hours` | 18 |

Duas leituras importantes:

- Há material temporal suficiente para o diferencial funcionar — 163 deslocamentos explícitos em 56 casos é uma densidade boa.
- As 18 ocorrências de frequência de administração (`twice daily`) **não** são posições na linha do tempo. Elas casam com regex temporal ingênua e precisam de regra explícita de exclusão. Como o plano da equipe já previa isso, vale medir quantos falsos positivos a exclusão evita e reportar.

`on admission` aparece em só 6 ocorrências, o que significa que ancorar tudo na internação vai resolver poucos casos. As datas explícitas (48) e os deslocamentos relativos (163) são as ancoragens mais produtivas. Vale reconsiderar a escolha do dia 0.

---

## 9. Ordem de trabalho

| Etapa | Entrega | Paralelizável |
|---|---|---|
| Split dev/eval por artigo | lista de PMCIDs, semente registrada | não, é pré-requisito |
| v0 semente manual | pipeline rodando ponta a ponta | 1 pessoa + revisão |
| v1 keywords | ~69 candidatos triados | 1 pessoa |
| v2 frequência | ~1.038 candidatos triados | toda a equipe, ~250 cada |
| v3 padrões | script de bootstrapping | 1 pessoa |
| v4 abreviações e variantes | script + 158 pares | 1 pessoa |
| v5 sufixos | regras + medição de precisão | 1 pessoa |
| Léxico temporal | em paralelo, a partir da v0 | 1 pessoa |
| v6 MeSH | checagem de recall | ao final |

v1 a v5 podem rodar em paralelo depois que a v0 fechar o pipeline, porque todas escrevem no mesmo `lexicon.csv` com `source` diferente. O conflito é resolvido na deduplicação por `canonical`.
