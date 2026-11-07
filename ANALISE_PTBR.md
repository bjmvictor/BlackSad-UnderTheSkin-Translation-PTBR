# Notas técnicas

## Texto do jogo

Os diálogos e parte da interface ficam no `TextAsset` chamado `Script`, dentro
do bundle `2172dc1d-d264-45aa-a94c-231bf3de6baa`. Cada tabela contém oito
campos de idioma e IDs fixos:

| Idioma | ID |
| --- | ---: |
| English | 10 |
| Español | 34 |
| 简体中文 | 40 |
| Français | 14 |
| Deutsch | 15 |
| Italiano | 21 |
| Nederlands | 9 |
| Русский | 30 |

## Empacotamento seguro

Alterar o tamanho do `GameScript` e recalcular seus offsets causou carregamento
infinito no jogo. O fluxo aceito usa **Import Raw do UABEA** e preserva todos
os tamanhos do script.

Quando o PT-BR excede o campo English, o gerador híbrido grava a tradução em
outro campo existente que comporte o texto e troca os IDs desse campo e do
English. A escolha é por tabela; não muda offsets nem o tamanho do bundle.

## Material local

Exports completos de assets, referências de terceiros, bundles gerados e
backups não fazem parte do repositório. Eles são grandes, regeneráveis ou
proprietários. Para reproduzir a base, use o bundle da própria instalação Steam
conforme o [README.md](README.md).
