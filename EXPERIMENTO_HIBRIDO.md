# Experimento: empréstimo Español para English

Este teste não aumenta o `GameScript`. Ele parte da estrutura fixa validada,
mantém as traduções PT-BR normais no slot English e, apenas para textos que não
cabem, grava o texto no espaço já reservado para Español e troca os IDs dos dois
slots naquela tabela.

O primeiro teste altera as quatro ocorrências de `RESOLUTION`. No jogo
configurado em **English**, elas devem aparecer como `RESOLUÇÃO`, incluindo `Ç`
e `Ã`, mesmo que o espaço English normal tenha apenas 10 bytes.

O modo `hybrid` não permite instalação automática. Feche o jogo, restaure antes
um bundle conhecido como funcional e substitua manualmente o arquivo por esta
cópia de teste, sempre mantendo um backup recuperável:

```powershell
.\ferramentas\empacotar_ptbr_uabea.ps1 `
  -BundleOrigem .\teste-uabea\2172dc1d-d264-45aa-a94c-231bf3de6baa `
  -PastaSaida .\saida-teste\experimentos\english-hybrid-resolution `
  -Modo hybrid `
  -SomenteFonte RESOLUTION `
  -TextoHibrido RESOLUÇÃO
```

Se o jogo chegar ao menu e **RESOLUTION** aparecer como **RESOLUÇÃO** em
English, a técnica estará validada. O passo seguinte será aplicá-la somente aos
textos que excedem o limite do slot English e ainda cabem no slot Español.
