# Avisos do runtime distribuído com o AMADO

Os binários e bibliotecas padrão do runtime foram redistribuídos sem alterações pelo projeto MADO. As licenças destes componentes permanecem válidas independentemente das condições de disponibilização da pesquisa.

## Componentes e textos preservados

- Pyodide 314.0.7: [Mozilla Public License 2.0](PYODIDE-MPL-2.0.txt).
- StackFrame / ErrorStackParser incorporados ao Pyodide: [licença MIT](PYODIDE-STACKFRAME-LICENSE.txt).
- CPython 3.14.2: [licença PSF e histórico](PYTHON-3.14.2-LICENSE.txt); [avisos adicionais no formato original](PYTHON-3.14.2-THIRD-PARTY.rst).
- Emscripten 5.0.3: [licenças e aviso de Node.js](EMSCRIPTEN-5.0.3-LICENSE.txt).
- musl, na distribuição do Emscripten: [copyright e avisos](MUSL-COPYRIGHT.txt).
- LLVM compiler-rt, na distribuição do Emscripten: [licença](LLVM-COMPILER-RT-LICENSE.txt).
- LLVM libc++, na distribuição do Emscripten: [licença](LLVM-LIBCXX-LICENSE.txt).

Os avisos foram copiados fielmente das versões oficiais em 06/10/2026. O arquivo de avisos do CPython abrange seu projeto de origem; sua presença não significa que todos os módulos descritos estejam carregados no AMADO.

## Código-fonte correspondente

- [Pyodide 314.0.7](https://github.com/pyodide/pyodide/tree/314.0.7).
- [CPython 3.14.2](https://github.com/python/cpython/tree/v3.14.2).
- [Emscripten 5.0.3](https://github.com/emscripten-core/emscripten/tree/5.0.3).

O pacote de dados `../../assets/base.zip` contém também os diretórios de licença de RDFLib 7.1.4 (BSD-3-Clause), pyparsing 3.3.2 (MIT) e html5rdf 1.2.1 (MIT). O AMADO não altera as condições concedidas pelos autores dessas bibliotecas.
