# Etapa 1 — Preparação dos dados

Esta etapa lê os arquivos originais, verifica sua integridade, associa cada caso ao artigo e salva os grupos usados nos experimentos. Ainda não extrai entidades nem resolve temporalidade.

## Executar

Requer Python 3.10 ou superior. Esta etapa utiliza somente a biblioteca padrão; não é necessário instalar pacotes.

Na raiz `MC896---NLP`:

```powershell
python -m src.prepare_data
python -m unittest discover -s tests -v
```

Se o Windows disponibilizar o comando `py`, use `py -3` no lugar de `python`. Se nenhum estiver disponível, instale Python ou execute pelo caminho completo de um interpretador existente.

As entradas padrão são `Projeto 1/sample/cases.csv` e `Projeto 1/sample/metadata.csv`. Os arquivos originais e a documentação existente permanecem no local atual. `data_dictionary.csv` é documentação e não participa da associação entre casos e artigos.

## Saídas

```text
data/prepared/
├── manifest.json
├── validation_report.json
├── splits/
│   ├── development.csv
│   └── evaluation.csv
└── records/
    ├── development.jsonl
    └── evaluation.jsonl
```

- `splits/*.csv`: listas de `case_id` e `article_id` para reutilizar a mesma divisão.
- `records/*.jsonl`: um caso por linha, com dois objetos: `case` contém os campos originais do caso e `article` contém todos os campos do artigo correspondente. Quebras de linha do relato são escapadas no JSON e recuperadas ao ler com `json.loads`.
- `validation_report.json`: contagens, campos vazios, duplicidades, referências ausentes, avisos e tamanhos dos grupos.
- `manifest.json`: parâmetros, IDs dos artigos de cada grupo e hashes SHA-256 dos CSVs de entrada. Permite conferir exatamente a versão dos dados usada.

Os valores originais continuam como strings, incluindo idade, listas de metadados e campos vazios. A ausência de idade não é convertida em zero; zero já possui significado no dataset (menos de um ano). Nesta etapa não tentamos interpretar listas MeSH por vírgulas, pois termos individuais também podem conter vírgulas.

## Divisão reproduzível e prevenção de vazamento

O padrão reserva 20% dos **artigos** para avaliação (arredondando para cima), com semente 42. Todos os casos de um artigo ficam no mesmo grupo. Assim, a proporção de casos pode ser diferente de 80/20. O algoritmo ordena os artigos por um hash de semente e ID; reorganizar as linhas dos CSVs não muda os grupos.

É uma divisão por artigo, sem estratificação por doença, idade ou gênero. O relatório descreve os dados, mas não garante representatividade clínica.

Construir `lexicon_metadata.csv` apenas com metadados dos registros de desenvolvimento. Construir os acréscimos do segundo dicionário apenas com textos de desenvolvimento. Ambos os experimentos devem usar exatamente a mesma avaliação reservada. Não selecionar casos de avaliação para ajustar vocabulário ou regras.

Para experimentar outra configuração, escolher uma nova pasta:

```powershell
python -m src.prepare_data --evaluation-fraction 0.2 --seed 42 --output-dir data/prepared_v2
```

Reexecutar com os mesmos dados e parâmetros conserva os arquivos existentes. Se os dados, parâmetros ou resultados mudarem, o programa recusa substituir uma saída incompatível; use outra pasta para uma nova versão. Isso evita alterar silenciosamente a divisão após começar os experimentos.

## Validações

Erros que bloqueiam a preparação: colunas obrigatórias ausentes, CSV malformado ou vazio, IDs duplicados, ID/texto obrigatório vazio, espaços nas extremidades dos IDs ou caso sem artigo correspondente. O programa termina com código 1 e explica o problema antes de gerar saídas.

Avisos que não excluem casos: campos opcionais vazios, idade inválida, artigo sem casos e divergência entre `case_amount` e a quantidade observada. Campos vazios e `Unknown` são preservados. Não há imputação nem exclusão silenciosa de linhas.

## Organização do código

| Arquivo | Responsabilidade |
|---|---|
| `src/data_io.py` | Leitura CSV e hash das entradas |
| `src/validation.py` | Validações e relatório |
| `src/splitting.py` | Divisão determinística por artigo |
| `src/prepare_data.py` | Coordenação, associação caso/artigo, exportação e CLI |
| `tests/test_preparation.py` | Testes de integridade, separação, preservação e reexecução |

## Próxima etapa

Escolher cerca de cinco casos de `development.csv`, ler seus registros associados e anotar a saída esperada. Depois construir o primeiro léxico com os metadados de desenvolvimento. Os arquivos gerados nesta etapa são dados preparados; `nodes.csv` e `edges.csv` serão produzidos pelo futuro extrator.
