# Oficina PT-BR — editor local de catálogo

Abra um PowerShell na raiz do projeto e execute:

```powershell
python ferramentas\catalogo_editor.py
```

Depois, acesse `http://127.0.0.1:8765` no navegador. A ferramenta funciona
somente no computador local e abre por padrão `texto/catalogo/pt-BR.csv`.

## Como usar

- Digite qualquer trecho no campo de busca.
- Em **Pesquisar em**, marque os idiomas que devem participar da busca. Por
  exemplo, deixe somente **Português (Brasil)** marcado para ignorar resultados
  em inglês, espanhol e os demais idiomas.
- Marque **Apenas acima do limite de bytes** para revisar textos que o
  empacotador preservaria em inglês. No modal, o campo PT-BR fica vermelho e
  informa o uso e o limite seguro de bytes.
- Marque os idiomas que quer comparar lado a lado. English, Português (Brasil)
  e Español já vêm selecionados.
- Cada texto em inglês aparece uma única vez, acompanhado de todos os IDs
  `gamescript:...` que ele representa. Clique no grupo para abrir a comparação
  completa em um modal, sem tirar a tabela da tela. Feche com `Esc`, no `×` ou
  clicando fora do painel; a linha continua destacada. Ao salvar, PT-BR, status
  e notas são aplicados a todas as ocorrências daquele texto; os idiomas de
  referência ficam protegidos contra alteração acidental.
- Clique em **Salvar no CSV** ou use `Ctrl+S`.

## Segurança do salvamento

Antes de cada salvamento, a ferramenta cria uma cópia integral do catálogo em
`texto/backups/`. Em seguida grava um arquivo temporário UTF-8 no mesmo diretório
e o substitui atomicamente. Se outra edição tiver sido gravada desde que a linha
foi aberta, ela bloqueia o salvamento e pede para recarregar a página.

## Aplicar e restaurar no jogo

O menu lateral **Instalação do jogo** procura automaticamente a biblioteca Steam
e a pasta que contém `Blacksad.exe`. Se não localizar, informe o caminho no
campo ou clique em **Escolher…** para abrir o seletor de pastas do Windows.

- **Gerar e aplicar PT-BR no jogo** usa o CSV salvo no editor, gera o bundle com
  as bibliotecas do UABEA e só então o troca de forma atômica. Não usa a
  remontagem UnityPy que o jogo rejeita.
- Escolha o **slot que exibirá o PT-BR** antes de aplicar. **English** usa a
  estrutura de maior cobertura validada; **Español** usa os espaços reservados
  para espanhol e pode acomodar alguns textos mais longos. No jogo, selecione
  o mesmo idioma escolhido no editor.
- Antes de aplicar, restaurar um backup ou restaurar o original, a ferramenta
  salva a versão atual em `backups-jogo/`.
- **Restaurar backup** lista somente cópias da mesma instalação selecionada.
- **Restaurar original** volta o bundle validado da build base. Ele não remove
  saves nem altera outros arquivos do jogo.

Feche o jogo antes da operação. Aplicar, restaurar um backup ou restaurar o
original preserva o arquivo atual antes de substituí-lo; os backups conhecidos
como incompatíveis ficam ocultos da lista.

Para usar outro catálogo, informe o caminho explicitamente:

```powershell
python ferramentas\catalogo_editor.py --catalog texto\catalogo\pt-BR.csv --port 8766
```

## Tradução automática local

O botão **Traduzir do inglês** usa o modelo local **Argos Translate** para
inserir um rascunho no campo PT-BR. Não usa chave, conta, API do Google ou
chamadas externas durante a tradução. O pacote de idiomas `English ->
Portuguese` já precisa estar instalado no computador; caso contrário, o botão
fica desativado e informa o que falta.

O resultado é somente um rascunho: revise tom, contexto, marcadores e tags
antes de salvar. Marcadores como `<1>` e tags como `<BR>` são preservados
durante a tradução.

## Empacotador automático via UABEA

Depois de editar e salvar o CSV, o comando abaixo gera automaticamente um
bundle PT-BR usando as bibliotecas do UABEA. Ele reproduz o fluxo que foi
validado no editor: gera o Raw do `TextAsset` e o grava em uma cópia do bundle,
sem usar o remonte incompatível do UnityPy.

```powershell
.\ferramentas\empacotar_ptbr_uabea.ps1 `
  -BundleOrigem 'C:\caminho\para\Blacksad_Data\StreamingAssets\assets_data\2172dc1d-d264-45aa-a94c-231bf3de6baa'
```

A saída é criada em `saida-teste/uabea-csv/`, com data e hora no nome; o
arquivo original do jogo não é tocado. Na primeira utilização, teste esse
arquivo no jogo. Depois de validado, use o mesmo comando com
`-InstalarNoJogo`: ele pede confirmação, cria um backup ao lado do bundle e só
então instala a cópia gerada. Feche o jogo antes de executar.

O processo requer o .NET 6 Runtime, o UABEA incluído em `ferramentas/uabea-v8`
e o compilador C# que já vem com o componente MSBuild do Visual Studio. A ponte
compilada é criada localmente dentro da pasta do UABEA a cada execução.

## Experimento de expansão

O modo experimental `-Modo expand` tenta aumentar uma string sem reduzir o
texto, recalculando os offsets do `GameScript`. Ele não pode instalar no jogo
automaticamente e deve ser testado em cópia. Consulte
[`EXPERIMENTO_EXPANSAO.md`](EXPERIMENTO_EXPANSAO.md) antes de usá-lo.
