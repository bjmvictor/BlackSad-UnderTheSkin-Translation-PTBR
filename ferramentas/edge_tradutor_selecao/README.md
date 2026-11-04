# Tradutor de Seleção PT-BR para Edge

Extensão local para traduzir uma seleção com `Ctrl+Espaço`, sem cadastrar chave
de API. O texto selecionado é enviado ao serviço do Google Tradutor e a resposta
volta ao navegador.

## Instalação no Edge

1. Abra `edge://extensions`.
2. Ative **Modo do desenvolvedor**.
3. Clique em **Carregar sem pacote**.
4. Escolha esta pasta: `ferramentas\edge_tradutor_selecao`.
5. Abra `edge://extensions/shortcuts` e confirme ou ajuste o atalho
   **Traduzir seleção para português brasileiro**. `Ctrl+Espaço` pode estar em
   uso pelo Windows, pelo método de entrada ou por outro programa; nesse caso,
   escolha outro atalho, por exemplo `Ctrl+Shift+Space`.

## Uso

- Em qualquer caixa de texto editável, selecione um trecho em inglês e use
  `Ctrl+Espaço`. A seleção é substituída pela tradução.
- No **Editor de catálogo PT-BR**, selecione o texto inglês no painel
  **English · origem** e use o atalho. A extensão preenche automaticamente o
  campo **Português (Brasil) · editável** e dispara a alteração pendente. A
  gravação continua dependendo do botão **Salvar no CSV** do editor.
- Para uma seleção de texto que não tenha campo editável de destino, a tradução
  é copiada para a área de transferência para colar onde quiser.

O botão da extensão executa o mesmo fluxo para quem preferir clicar nele.

## Limites e privacidade

Esta é uma integração sem chave que consulta um endpoint público de tradução;
ela não usa a API Cloud Translation configurada por chave. O Google não oferece
esse uso como API oficial/documentada, portanto pode mudar, aplicar limites ou
parar de responder a qualquer momento. Não selecione conteúdo sensível, pois o
texto é enviado ao Google para ser traduzido.

Tradução automática deve ser revisada, especialmente em trocadilhos, humor,
gírias e termos recorrentes do jogo. A extensão não lê nem grava o CSV e não
armazena os textos traduzidos.
