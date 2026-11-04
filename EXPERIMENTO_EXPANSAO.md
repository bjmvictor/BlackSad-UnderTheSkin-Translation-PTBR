# Experimento: expansão do slot English

Este teste tenta ultrapassar o tamanho originalmente reservado para uma string
sem remontar o bundle com UnityPy. Ele aumenta somente o `TextAsset/Script`,
recalcula os offsets internos e usa o mesmo Import Raw via UABEA que já foi
aceito pelo jogo.

O modo `expand` é deliberadamente bloqueado de instalar no jogo. Gere sempre
uma cópia fora da Steam e só substitua o arquivo manualmente depois de guardar
o original e fechar o jogo.

O primeiro teste altera somente as duas ocorrências de `Dunn's will` para o
PT-BR atual do CSV. Essa tradução passa de 11 bytes no English original para
15 bytes, portanto confirma se o aumento real de tamanho funciona.

```powershell
.\ferramentas\empacotar_ptbr_uabea.ps1 `
  -BundleOrigem .\teste-uabea\2172dc1d-d264-45aa-a94c-231bf3de6baa `
  -PastaSaida .\saida-teste\experimentos\english-expand-dunn `
  -Modo expand `
  -SomenteFonte "Dunn's will"
```

O jogo deve ser configurado em **English** nesse experimento. Se abrir e o
texto aparecer em PT-BR, o próximo passo será testar um lote pequeno de textos
maiores antes de considerar a expansão para todo o catálogo.
