# Blacksad: Under the Skin — base técnica PT-BR

## Estado inicial

- Jogo analisado: Steam Windows x64, build `15955197`.
- Engine: Unity `2021.3.32f1`.
- A instalação original não contém uma tabela de idiomas editável (`.po`, `.csv`, `.json` ou `.locres`).
- Os textos e elementos de interface estão serializados em assets Unity e bundles de `Blacksad_Data`.

## Referência examinada

A pasta `referencia` contém uma localização árabe de terceiros. Ela é compatível com a build instalada e substitui 42 arquivos dentro de `Blacksad_Data`:

- 21 arquivos principais Unity (`level1`, `resources.assets` e `sharedassets*.assets`);
- 20 bundles em `StreamingAssets/assets_data`;
- `Managed/Assembly-CSharp.dll`;
- uma DLL adicional, `B52.Blacksad.Arabic.dll`.

A DLL extra é específica ao árabe: faz escrita RTL, ligação de caracteres e ajustes de fonte. Ela não é necessária nem deve fazer parte da futura versão PT-BR, que usa o conjunto latino já presente no jogo.

## Material de trabalho criado

- `extraido-original/`: exportação dos assets-alvo originais sem todas as dependências de scripts; útil para comparação bruta.
- `extraido-estruturado/`: exportação dos mesmos assets com as 141 bibliotecas gerenciadas originais carregadas; é a base para localizar os campos de texto e seus contextos.

Esses diretórios são derivados da instalação original. Eles não devem ser distribuídos como mod.

## Estratégia de implementação

1. Identificar, na exportação estruturada, os objetos de diálogo, escolhas, legendas e UI que contêm texto em inglês.
2. Extrair esses campos para uma planilha UTF-8 com identificador do asset, contexto e texto-fonte.
3. Traduzir para PT-BR preservando variáveis, tags, quebras de linha e marcadores de controle.
4. Reimportar somente os assets efetivamente alterados em uma cópia de trabalho, sem tocar no diretório Steam.
5. Montar um pacote de instalação com apenas os arquivos alterados e um script de backup/restauração.
6. Validar o menu, escolhas cronometradas, legendas, caderno, deduções e finais no jogo.

## Regras de segurança

- Não editar arquivos em `C:\Program Files (x86)\Steam\...` diretamente.
- Nunca incluir `B52.Blacksad.Arabic.dll` na versão PT-BR.
- Manter a compatibilidade com a build `15955197`; após uma atualização do jogo, repetir a comparação antes de instalar qualquer pacote.
- Não reutilizar textos ou recursos traduzidos de terceiros: a referência serve somente para identificar os arquivos e a arquitetura do mod.
