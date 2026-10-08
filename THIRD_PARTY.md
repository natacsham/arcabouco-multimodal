# Componentes de terceiros

Este aviso se aplica às dependências distribuídas com o projeto, não concede uma licença para a ontologia, os dados ou os textos autorais da pesquisa. A ausência de licença aberta para esses materiais **não restringe os direitos concedidos pelas licenças das dependências**.

Os avisos abaixo foram conferidos em 06/10/2026. Os textos de licença foram copiados de seus projetos de origem, sem alteração. Esta página não substitui os textos completos nem representa endosso dos projetos citados à MADO.

## Runtime do navegador

O AMADO distribui o runtime Pyodide para executar Python no navegador. Os arquivos de runtime não foram modificados por este projeto. As mudanças do AMADO estão no motor, na ponte de comunicação, nos dados e na interface próprios.

| Componente | Versão ou origem | Licença e aviso incluído |
| --- | --- | --- |
| Pyodide | 314.0.7 | [Mozilla Public License 2.0](web/amado/runtime/licenses/PYODIDE-MPL-2.0.txt) |
| CPython | 3.14.2, conforme `pyodide-lock.json` | [Licença PSF e avisos históricos](web/amado/runtime/licenses/PYTHON-3.14.2-LICENSE.txt); [avisos adicionais de componentes](web/amado/runtime/licenses/PYTHON-3.14.2-THIRD-PARTY.rst) |
| Emscripten | 5.0.3, conforme `pyodide-lock.json` | [MIT / University of Illinois NCSA, incluindo aviso de Node.js](web/amado/runtime/licenses/EMSCRIPTEN-5.0.3-LICENSE.txt) |
| StackFrame / ErrorStackParser incorporados ao Pyodide | `src/js/vendor/stackframe` da versão 314.0.7 | [Aviso MIT de Eric Wendelin e colaboradores](web/amado/runtime/licenses/PYODIDE-STACKFRAME-LICENSE.txt) |
| musl | Distribuição de Emscripten 5.0.3 | [Copyright e avisos das partes](web/amado/runtime/licenses/MUSL-COPYRIGHT.txt) |
| LLVM compiler-rt | Distribuição de Emscripten 5.0.3 | [Licença do projeto LLVM e exceções](web/amado/runtime/licenses/LLVM-COMPILER-RT-LICENSE.txt) |
| LLVM libc++ | Distribuição de Emscripten 5.0.3 | [Licença do projeto LLVM, exceções e avisos históricos](web/amado/runtime/licenses/LLVM-LIBCXX-LICENSE.txt) |

O documento de avisos do CPython é preservado em seu formato original reStructuredText; ele descreve componentes do projeto CPython e não deve ser lido como inventário de todos os módulos efetivamente carregados pelo AMADO. O catálogo de pacotes em `pyodide-lock.json` também não significa que todos esses pacotes tenham sido baixados ou incorporados ao instrumento.

### Como obter o código-fonte correspondente

- [Código-fonte do Pyodide 314.0.7](https://github.com/pyodide/pyodide/tree/314.0.7), incluindo sua construção e modificações de integração.
- [Código-fonte do CPython 3.14.2](https://github.com/python/cpython/tree/v3.14.2).
- [Código-fonte do Emscripten 5.0.3](https://github.com/emscripten-core/emscripten/tree/5.0.3).

Esses endereços identificam versões específicas. A fonte modificável do software coberto pela MPL está disponível no projeto Pyodide indicado; o AMADO não exige licença própria para exercer os direitos previstos na licença daquele componente.

## Pacotes Python da aplicação e da verificação

Os diretórios `*.dist-info` preservam metadados e licenças fornecidos pelas distribuições instaladas. O pacote do navegador inclui RDFLib, pyparsing e html5rdf; os demais componentes abaixo dão suporte à verificação local quando empregados pelos testes.

| Pacote | Versão incluída | Licença conforme a distribuição | Texto preservado |
| --- | --- | --- | --- |
| RDFLib | 7.1.4 | BSD-3-Clause | [LICENSE](vendor/rdflib-7.1.4.dist-info/LICENSE) |
| pyparsing | 3.3.2 | MIT | [LICENSE](vendor/pyparsing-3.3.2.dist-info/licenses/LICENSE) |
| html5rdf | 1.2.1 | MIT | [LICENSE](vendor/html5rdf-1.2.1.dist-info/LICENSE), [autores](vendor/html5rdf-1.2.1.dist-info/AUTHORS.rst) |
| pySHACL | 0.30.1 | Apache License | [LICENSE.txt](vendor/pyshacl-0.30.1.dist-info/LICENSE.txt) |
| OWL-RL | 7.1.4 | W3C Software and Document Notice and License | [LICENSE.txt](vendor/owlrl-7.1.4.dist-info/LICENSE.txt) |
| packaging | 26.3 | Apache-2.0 ou BSD-2-Clause | [LICENSE](vendor/packaging-26.3.dist-info/licenses/LICENSE), [Apache](vendor/packaging-26.3.dist-info/licenses/LICENSE.APACHE), [BSD](vendor/packaging-26.3.dist-info/licenses/LICENSE.BSD) |
| PrettyTable | 3.18.0 | BSD-3-Clause | [LICENSE](vendor/prettytable-3.18.0.dist-info/licenses/LICENSE) |
| wcwidth | 0.8.3 | MIT | [LICENSE](vendor/wcwidth-0.8.3.dist-info/licenses/LICENSE) |

## Origem das cópias do runtime

Os arquivos em `web/amado/runtime/licenses/` foram obtidos destes endereços oficiais:

- `https://raw.githubusercontent.com/pyodide/pyodide/314.0.7/LICENSE`
- `https://raw.githubusercontent.com/pyodide/pyodide/314.0.7/src/js/vendor/stackframe/LICENSE`
- `https://raw.githubusercontent.com/python/cpython/v3.14.2/LICENSE`
- `https://raw.githubusercontent.com/python/cpython/v3.14.2/Doc/license.rst`
- `https://raw.githubusercontent.com/emscripten-core/emscripten/5.0.3/LICENSE`
- `https://raw.githubusercontent.com/emscripten-core/emscripten/5.0.3/system/lib/libc/musl/COPYRIGHT`
- `https://raw.githubusercontent.com/emscripten-core/emscripten/5.0.3/system/lib/compiler-rt/LICENSE.TXT`
- `https://raw.githubusercontent.com/emscripten-core/emscripten/5.0.3/system/lib/libcxx/LICENSE.TXT`

Ao atualizar uma dependência, conferir novamente versão, conteúdo distribuído, avisos e origem. Não reutilizar este inventário como certificação jurídica geral nem substituir as condições específicas das fontes científicas pelos termos das bibliotecas de software.
