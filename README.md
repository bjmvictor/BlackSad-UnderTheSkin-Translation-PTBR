# Tradução PT-BR — Blacksad: Under the Skin

Projeto de tradução comunitária para a versão Steam Windows (build-base
`15955197`) de *Blacksad: Under the Skin*. O trabalho é feito no catálogo
UTF-8 em `texto/catalogo/pt-BR.csv`; o editor local permite pesquisar, comparar
idiomas, editar ocorrências repetidas e aplicar o resultado ao jogo com backup.

## Andamento

Estimativa atual: aproximadamente **80% traduzido** e **60% revisado** para
PT-BR. A revisão ainda depende de contexto e validação dentro do jogo.

## O que está no Git

- código do editor, empacotador e extensão opcional do Edge;
- catálogo PT-BR, lotes e documentação;
- histórico técnico suficiente para continuar a tradução.

O repositório **não inclui arquivos do jogo, backups nem UABEA**. Esses itens
são proprietários ou regeneráveis e permanecem ignorados localmente. Cada
colaborador deve usar uma instalação Steam legítima do jogo.

## Preparação inicial

1. Instale Python 3.11+ e o .NET 6 Runtime.
2. Baixe a versão portátil do UABEA usada pelo projeto e extraia-a em
   `ferramentas/uabea-v8/`. Não versione essa pasta.
3. Com o jogo restaurado ao original (ou após verificar a integridade pela
   Steam), copie o bundle original e extraia o Raw necessário ao empacotador:

```powershell
$bundle = 'C:\Program Files (x86)\Steam\steamapps\common\Blacksad - Under the skin\Blacksad_Data\StreamingAssets\assets_data\2172dc1d-d264-45aa-a94c-231bf3de6baa'
New-Item -ItemType Directory -Force .\teste-uabea | Out-Null
Copy-Item -LiteralPath $bundle -Destination .\teste-uabea\2172dc1d-d264-45aa-a94c-231bf3de6baa
python -m pip install UnityPy
python .\ferramentas\extrair_gamescript.py .\teste-uabea\2172dc1d-d264-45aa-a94c-231bf3de6baa .\saida-teste\catalogo-base.csv --dump-raw .\teste-uabea\Script-original.dat
```

O arquivo original e o Raw ficam só na sua máquina, em `teste-uabea/`.

## Editar a tradução

```powershell
python .\ferramentas\catalogo_editor.py
```

Abra `http://127.0.0.1:8765`. Pesquise por qualquer trecho em inglês ou
português, abra o grupo, edite PT-BR e salve. Uma edição unificada atualiza
todas as ocorrências iguais. Veja o guia detalhado em
[README_EDITOR_CATALOGO.md](README_EDITOR_CATALOGO.md).

## Aplicar ao jogo

Feche o jogo. No menu lateral do editor, escolha a pasta que contém
`Blacksad.exe`, mantenha **English — cobertura máxima** e use **Gerar e aplicar
PT-BR no jogo**. O processo cria um backup local antes de trocar o bundle.

O modo English híbrido preserva o tamanho do `GameScript`: quando o campo
English não comporta o PT-BR, ele usa o maior campo já existente naquela mesma
mensagem e o identifica como English. Consulte
[EXPERIMENTO_HIBRIDO.md](EXPERIMENTO_HIBRIDO.md) para os limites e testes.

## Gerar uma release instalável

Para que outra pessoa instale sem Python, UABEA ou Visual Studio, gere um ZIP
de release a partir do CSV revisado:

```powershell
.\ferramentas\gerar_instalador_release.ps1 -Versao 0.1.0
```

O comando cria `dist/Blacksad_PTBR-v0.1.0.zip`. Publique esse ZIP na aba
**Releases** do GitHub, e não o bundle inteiro do jogo. Dentro dele há apenas
o aplicador, o Raw PT-BR e as dependências mínimas; ao executar
`Instalar-PTBR.cmd`, a pessoa usuária:

- confirma a elevação do Windows;
- tem a pasta Steam detectada automaticamente ou pode escolhê-la manualmente;
- recebe um backup do bundle original em
  `Blacksad_PTBR_Backup/` dentro da pasta do jogo;
- inicia o jogo no idioma **English**.

`Desinstalar-PTBR.cmd` restaura exatamente esse backup e mantém a cópia para
auditoria; saves e configurações do jogo não são alterados. A geração da
release exige os mesmos pré-requisitos de desenvolvimento já descritos acima,
inclusive a cópia original local e o UABEA, mas quem baixa o ZIP precisa apenas
do .NET 6 Runtime x64 e de uma instalação legítima do jogo.

O Raw de tradução é produzido a partir de dados do jogo. Antes de publicar ou
redistribuir qualquer release, confira os termos da editora e da loja; o
projeto não concede direitos sobre os arquivos do jogo. O pacote inclui os
avisos de licença de terceiros em `TERCEIROS.txt`.

## Como contribuir

- Faça alterações somente em `pt_br`, `status` e `notes` do CSV pelo editor.
- Preserve tags (`<BR>`, `<1>`), variáveis (`$...`) e a intenção da fala.
- Use `draft` para rascunhos, `review` para textos prontos para revisão e
  `approved` somente após validação no jogo.
- Não versione `teste-uabea/`, `saida-teste/`, `backups-jogo/`, exports de
  assets, UABEA ou backups do CSV.
- Antes de enviar mudanças, confira `git diff --check` e descreva no commit o
  lote ou o trecho revisado.

O estado atual e as decisões técnicas estão em
[PROGRESSO_PTBR.md](PROGRESSO_PTBR.md).
