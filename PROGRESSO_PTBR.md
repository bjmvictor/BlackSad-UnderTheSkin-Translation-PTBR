# Progresso da tradução PT-BR

## Base atual

- Jogo-alvo: Steam Windows x64, build-base `15955197`.
- Bundle de texto: `Blacksad_Data/StreamingAssets/assets_data/2172dc1d-d264-45aa-a94c-231bf3de6baa`.
- SHA-256 do `GameScript` original: `23972e6ce27b881758d8df24d27167b39ae12c2fd54041890c43c86880c98501`.
- Catálogo: 18.008 ocorrências físicas, agrupadas em 8.270 textos English.
- Todas as linhas possuem um texto PT-BR; a maior parte ainda é
  `machine-draft` e requer revisão contextual.

## Fluxo validado

1. O editor salva o CSV em UTF-8 de modo atômico e agrupa textos repetidos.
2. O empacotador usa Import Raw do UABEA; remontagem UnityPy não deve ser usada
   para instalar o bundle no jogo.
3. Em **English — cobertura máxima**, o gerador mantém o tamanho do
   `GameScript`. Se PT-BR não couber no campo English, usa o maior campo de
   idioma existente na mesma tabela e troca somente os IDs dos dois campos.
4. Os testes no jogo validaram caracteres acentuados em `RESOLUÇÃO` e
   `RESOLUÇÃO DINÂMICA`. `DIMINUIR ZOOM` usa o campo Italiano, pois o Español
   possui apenas 12 bytes para uma tradução de 13 bytes.

## Itens de revisão prioritária

- diálogos com `machine-draft`;
- textos que permanecem em inglês por excederem todos os campos existentes;
- escolhas cronometradas, caderno de detetive, deduções e telas de opções;
- tags, variáveis e marcadores como `<1>`, `<BR>` e `$...`.

## Arquivos principais

- `texto/catalogo/pt-BR.csv`: fonte de verdade da tradução.
- `ferramentas/catalogo_editor.py`: editor e aplicação com backup.
- `ferramentas/empacotar_ptbr_uabea.ps1`: geração manual por UABEA.
- `README.md`: preparação de uma máquina nova e contribuição.
- `README_EDITOR_CATALOGO.md`: uso diário do editor.

Arquivos do jogo, UABEA, backups e saídas de teste são locais/ignorados. Veja
o [README.md](README.md) antes de tentar aplicar o mod em outra instalação.
