# Empréstimo de slots para English

Este teste não aumenta o `GameScript`. Ele parte da estrutura fixa validada,
mantém as traduções PT-BR normais no slot English e, apenas para textos que não
cabem, grava o texto no maior espaço já reservado em outro idioma e troca os
IDs dos dois slots naquela tabela.

Os testes de `RESOLUTION` e `DYNAMIC RESOLUTION` foram validados no jogo: ele
chegou ao menu e exibiu `RESOLUÇÃO` e `RESOLUÇÃO DINÂMICA` ao selecionar
**English**, inclusive com os caracteres `Ç`, `Ã` e `Â`.

O modo `hybrid` agora é o gerador padrão da opção **English** no editor. Ele
avalia cada ocorrência: usa English quando o texto couber e, quando necessário,
empresta o maior campo de outro idioma daquela tabela. Por exemplo,
`DIMINUIR ZOOM` tem 13 bytes e usa Italiano, pois Español oferece apenas 12.
Se nenhum campo suportar o texto inteiro, mantém o English original em vez de
gravar uma tradução truncada.

Para gerar manualmente todo o catálogo, sem alterar o jogo:

```powershell
.\ferramentas\empacotar_ptbr_uabea.ps1 `
  -BundleOrigem 'C:\caminho\para\Blacksad_Data\StreamingAssets\assets_data\2172dc1d-d264-45aa-a94c-231bf3de6baa' `
  -PastaSaida .\saida-teste\ptbr-hybrid `
  -Modo hybrid
```

O editor cria um backup do arquivo atual e aplica esse mesmo modo automaticamente
ao usar **Gerar e aplicar PT-BR no jogo** com English selecionado.
