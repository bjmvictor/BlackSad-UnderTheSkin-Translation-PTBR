# Progresso da traducao PT-BR

## Base validada

- Jogo alvo: Steam Windows x64, build `15955197`.
- Fonte principal: `GameScript/Script.bytes`, no bundle
  `2172dc1d-d264-45aa-a94c-231bf3de6baa`.
- SHA-256 do GameScript original:
  `23972e6ce27b881758d8df24d27167b39ae12c2fd54041890c43c86880c98501`.
- Catalogo extraido: 18.006 ocorrencias, equivalentes a 8.269 textos ingleses
  distintos.

## Traducao em andamento

- Lotes `texto/lotes/abertura-001.csv` a `abertura-004.csv`: 247 textos
  distintos, propagados para 584 ocorrencias.
- Estado dos lotes: `draft`; requer revisao contextual durante os testes no jogo.
- `texto/lotes/correcoes-usuario-002.csv`: corrige a resposta “What pictures?”
  e os avisos de salvamento automático para todas as variantes de plataforma.
- O preview em `saida-teste/ptbr-preview/` contem apenas o bundle de texto para
  teste tecnico. Ele nao e uma versao distribuivel nem deve ser copiado sobre a
  instalacao sem backup.
- O preview atualizado esta em `saida-teste/ptbr-preview-v4/`; ele foi gerado a
  partir do bundle original e inclui as correcoes `correcoes-usuario-002`.

## Ferramentas

- `catalogo_editor.py`: servidor local para pesquisar, comparar idiomas lado a
  lado e editar PT-BR/status/notas com backup automático do CSV; aceita
  tradução automática local opcional via Argos Translate, sem API externa, e
  gera e aplica o bundle de texto com UABEA, sempre criando backup da instalação
  antes da troca.
- `edge_tradutor_selecao/`: extensão local Manifest V3 para Edge; com
  `Ctrl+Espaço`, traduz a seleção e preenche o campo PT-BR no editor, sem
  configurar chave de API.
- `extrair_gamescript.py`: extrai e identifica o catalogo UTF-8 a partir do
  bundle ou do TextAsset bruto.
- `aplicar_lote.py`: propaga um lote revisavel pelo catalogo mestre.
- `gerar_bundle_ptbr.py`: monta o bundle modificado fora da Steam. Sem
  `--allow-partial`, ele se recusa a gerar um pacote com textos faltantes.
- `testar_remontagem.py`: confirma que a remontagem preserva o TextAsset quando
  nenhuma traducao e aplicada.
- `empacotar_ptbr_uabea.ps1`: gera o Raw a partir do CSV e o aplica em uma cópia
  do bundle com as bibliotecas do UABEA, sem remonte UnityPy. A opção
  `-InstalarNoJogo` cria backup e pede confirmação antes de substituir o bundle.
- `EXPERIMENTO_EXPANSAO.md`: roteiro do teste controlado que expande somente
  `Dunn's will` no slot English. O modo experimental bloqueia instalação direta
  e aguarda validação manual no jogo antes de ser ampliado.

O mod PT-BR usara temporariamente a selecao de idioma **English** do jogo: a
estrutura ja existente para ingles e a que recebera os textos portugueses. A
traducao do rotulo de idioma e das telas de interface sera tratada depois, nos
assets de UI identificados pela comparacao com a referencia.
