# Como apresentar o Arcabouço Multimodal à Pesquisa Google

Este procedimento complementa a publicação do site. **Preparar metadados ou enviar um sitemap não garante indexação, posição na busca nem prazo de aparecimento.** As informações abaixo foram conferidas na documentação oficial em 07/10/2026.

## O que está preparado no projeto

- Títulos e descrições próprios para a apresentação da MADO e a página da ontologia.
- URLs canônicos explícitos: `https://natacsham.github.io/arcabouco-multimodal/` e `https://natacsham.github.io/arcabouco-multimodal/ontologia/`.
- Metadados Open Graph e de compartilhamento com o nome completo da autora, sem perfil social, imagem ou identificador inventado.
- JSON-LD que identifica o site, a autora e a ontologia como trabalho autoral, sem avaliação, eficácia ou titulação não comprovada.
- Sitemap com quatro endereços públicos: apresentação, ontologia e as duas visões do AMADO. A visão guiada declara a página principal do AMADO como endereço canônico, por apresentar o mesmo instrumento.

O conteúdo explicativo principal é HTML, acessível sem iniciar o motor Python. Os casos preenchidos e as decisões individuais do AMADO não são páginas públicas, não têm URLs próprias e não entram no sitemap.

## Depois da implantação

1. Confirme que as quatro páginas abrem por HTTPS e que [o sitemap público](https://natacsham.github.io/arcabouco-multimodal/sitemap.xml) retorna o XML, não uma página de erro.
2. Acesse o [Google Search Console](https://search.google.com/search-console/). Adicione uma propriedade de **prefixo de URL** para `https://natacsham.github.io/arcabouco-multimodal/`, com a barra final. Esse tipo de propriedade permite acompanhar especificamente o caminho do projeto, sem exigir controle do domínio `github.io`. [Tipos de propriedade](https://support.google.com/webmasters/answer/34592?hl=pt-BR).
3. Siga o método de verificação oferecido pelo Search Console. Se escolher uma tag HTML, use exatamente o token fornecido para essa propriedade no `head` da página inicial. O projeto não inclui token fictício nem comprovação de propriedade presumida. Publique a alteração antes de solicitar a confirmação. [Verificação de propriedade](https://support.google.com/webmasters/answer/9008080?hl=pt-BR).
4. Na área de sitemaps da propriedade verificada, envie `https://natacsham.github.io/arcabouco-multimodal/sitemap.xml`. Acompanhe erros de leitura e URLs descobertas. O sitemap é um sinal para descoberta, não uma ordem de indexação. [Orientações de sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap?hl=pt-br).
5. Inspecione a URL da página inicial e a da ontologia. Confira o teste publicado e, quando apropriado, solicite indexação. Repetir a solicitação continuamente não acelera o processamento. [Novo rastreamento](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl?hl=pt-br).

O cadastro no Search Console e a solicitação de indexação dependem da conta responsável e não são feitos apenas pela inclusão destes arquivos no repositório.

## Por que não existe robots.txt dentro deste projeto?

O arquivo que rege o host seria `https://natacsham.github.io/robots.txt`, na raiz. Criar `https://natacsham.github.io/arcabouco-multimodal/robots.txt` não cumpre essa função. Esta alteração não assume controle do site raiz da conta nem modifica outros projetos. Para esta implantação, o sitemap pode ser enviado diretamente pelo Search Console. [Localização do robots.txt](https://developers.google.com/crawling/docs/robots-txt/create-robots-txt?hl=pt-br).

## Limites dos metadados

`rel="canonical"` informa a URL preferida, mas o Google pode selecionar outra com base em seus sinais. Mantenha URLs, links internos e sitemap coerentes se o endereço mudar. [Canonização](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls?hl=pt-br).

O JSON-LD usa fatos visíveis no site. Ele não transforma a ontologia em produto avaliado nem assegura um resultado enriquecido. Em particular, o recurso de **nome de site** do Google não é suportado para sites em subdiretórios: o caminho `/arcabouco-multimodal/` não deve ser apresentado como garantia de um nome exclusivo na busca. [Nomes de sites](https://developers.google.com/search/docs/appearance/site-names?hl=pt-br).

Os títulos, descrições e metadados de compartilhamento são sugestões; mecanismos de busca e redes sociais podem compor apresentações diferentes. Não foram adicionados `meta keywords`, avaliações artificiais ou alegações de qualidade para tentar obter classificação. Conteúdo útil, legível e coerente com a pesquisa continua sendo a base da apresentação. [Guia oficial de SEO](https://developers.google.com/search/docs/fundamentals/seo-starter-guide?hl=pt-br).

## Manutenção

Ao mudar uma rota, atualize canonical, Open Graph, JSON-LD, links e sitemap em conjunto. Não adicione datas de modificação fictícias ou URLs de casos pessoais. Após a implantação, registre separadamente a verificação de disponibilidade pública e o estado real de indexação informado pelo Search Console.
