# Ideia inicial — Extração de informação de casos clínicos

## Objetivo

O projeto transformará o texto de cada caso clínico em um grafo de conhecimento. A primeira versão será simples, baseada em dicionários, expressões regulares e regras. Não será necessário treinar um modelo.

## Nós do grafo

Teremos cinco tipos de nós:

| Tipo | O que representa | Exemplo |
|---|---|---|
| `Case` | O caso clínico | `case_17` |
| `Symptom` | Sintoma ou sinal apresentado | `fever` |
| `Exam` | Exame realizado | `computed tomography` |
| `Condition` | Doença ou diagnóstico | `pneumonia` |
| `Treatment` | Medicamento, procedimento ou terapia | `amoxicillin` |

O nó `Case` será criado diretamente com as informações do `cases.csv`. Os outros quatro tipos serão encontrados no texto.

## Relações

Usaremos inicialmente estas relações:

| Origem | Relação | Destino |
|---|---|---|
| `Case` | `HAS_SYMPTOM` | `Symptom` |
| `Case` | `UNDERWENT_EXAM` | `Exam` |
| `Case` | `DIAGNOSED_WITH` | `Condition` |
| `Case` | `RECEIVED_TREATMENT` | `Treatment` |
| `Exam` | `INDICATES` | `Condition` |
| `Treatment` | `TREATS` | `Condition` |

As relações `INDICATES` e `TREATS` só serão criadas quando houver evidência suficiente no texto.

## Léxico principal

O arquivo `lexicon.csv` reunirá os dicionários de sintomas, exames, condições e tratamentos. Vai ser o nosso dicionário principal, a maneira que vamos encontrar as palavras dentro dos textos. Cada linha informará:

- o termo que pode aparecer no texto;
- o tipo de nó;
- sua forma padronizada.

Exemplo:

```csv
term,type,canonical
fever,Symptom,fever
shortness of breath,Symptom,dyspnea
dyspnoea,Symptom,dyspnea
CT,Exam,computed tomography
CT scan,Exam,computed tomography
pneumonia,Condition,pneumonia
amoxicillin,Treatment,amoxicillin
```

Sinônimos e abreviações aparecem em linhas diferentes, mas apontam para a mesma forma padronizada. O léxico será global: o mesmo arquivo será usado em todos os casos.

O léxico inicial será montado manualmente com termos frequentes, `keywords` e termos MeSH. Os metadados serão usados como fonte de candidatos, mas nenhum termo será transformado automaticamente em nó sem aparecer também no `case_text`.

## Métodos de extração

**Como a nossa criatividade vai ser julgada, é nessa parte da extração que temos que caprichar, então se tiverem novas ideias de coisas e maneira que podemos usar para extrair informação no texto avisem no grupo para adicionár-mos. Essas foram as ideias iniciais que pensei em fazer.**

Além do léxico, utilizaremos:

1. **Separação em frases:** ponto final, interrogação, exclamação e quebra de parágrafo indicarão possíveis finais de frase. Vírgulas não separarão frases.
2. **Tokenização por palavras:** cada frase será tokenizada, mantendo a posição dos tokens e a frase à qual pertencem. Expressões com várias palavras, como `abdominal pain`, formarão um único nó.
3. **Expressões regulares:** para doses (`500 mg`), frequências, valores de exames, unidades e medidas.
4. **Expressões indicadoras:** padrões como `presented with`, `diagnosed with`, `underwent` e `treated with` ajudarão a interpretar as entidades.
5. **Negação:** expressões como `no evidence of`, `without` e `ruled out` impedirão a criação da entidade na primeira versão.
6. **Regras de relação:** padrões linguísticos conectarão as entidades encontradas. Se aparecer a palavra diagnosed, já sabemos que é a relação DIAGNOSED_WITH. Ou seja, vamos definir as reações pelas palavras que aparecem ao redor.
7. **Normalização e deduplicação:** sinônimos receberão o mesmo nome e uma entidade repetida no mesmo caso gerará apenas um nó. Será feito a partir do arquivo dicionário. 
8. **Evidência:** cada extração guardará a frase original que a originou, facilitando a conferência dos resultados (para nós mesmos).

## Fluxo do programa

```text
cases.csv e metadata.csv
        ↓
leitura de um caso
        ↓
separação em frases e tokens
        ↓
busca de entidades no lexicon.csv
        ↓
regex para doses, valores e unidades
        ↓
verificação de contexto, negação e incerteza
        ↓
normalização e remoção de duplicatas
        ↓
criação dos nós e identificação das relações
        ↓
nodes.csv e edges.csv
```

## Exemplo

Texto:

> The patient presented with fever. A chest CT was performed. Pneumonia was diagnosed and treatment with amoxicillin was initiated.

Nós:

```text
Case: case_17
Symptom: fever
Exam: computed tomography
Condition: pneumonia
Treatment: amoxicillin
```

Relações:

```text
case_17 --HAS_SYMPTOM--------> fever
case_17 --UNDERWENT_EXAM-----> computed tomography
case_17 --DIAGNOSED_WITH-----> pneumonia
case_17 --RECEIVED_TREATMENT-> amoxicillin
amoxicillin --TREATS---------> pneumonia
```

## Saída e avaliação

O resultado será exportado em duas tabelas:

- `nodes.csv`: nós e seus atributos;
- `edges.csv`: relações entre os nós.

Depois, alguns casos serão revisados manualmente para identificar extrações corretas, informações não encontradas e falsos positivos. Por fim, os grafos poderão ser visualizados de forma interativa, exibindo a frase original associada a cada entidade.
