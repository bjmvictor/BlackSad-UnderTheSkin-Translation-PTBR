# Catálogo de tradução PT-BR

`pt-BR.csv` é gerado a partir do `GameScript.bytes` original por
`ferramentas/extrair_gamescript.py`.

- `id` e `offset` são identificadores estáveis da entrada no arquivo original.
- `en` é o texto-fonte; as outras colunas são referências oficiais já existentes.
  Textos UTF-8 legíveis, incluindo reticências (`…`) e aspas tipográficas,
  também fazem parte do catálogo.
- Preencha somente `pt_br`.
- Preserve comandos iniciados por `$`, tags entre colchetes, variáveis e quebras de linha.
- `status` deve ser `pending`, `draft`, `review` ou `approved`.

O CSV é material de trabalho. A geração do mod final exige reserializar a tabela
e reempacotar o bundle Unity; nunca se deve editar o arquivo instalado diretamente.
