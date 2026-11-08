# Bibliotecas locais do mapa

O mapa usa as distribuições oficiais, sem modificações, de **Leaflet 1.9.4**
(BSD-2-Clause) e **Leaflet.draw 1.0.4** (MIT). JavaScript, CSS, imagens relativas
e licenças estão nas pastas correspondentes. Esses assets são servidos pela
aplicação; o carregamento do editor não depende de CDN externa.

`mapa-dependencias.json` registra URL do pacote npm oficial, versão, integridade
SHA-512 do arquivo de distribuição e SHA-256/tamanho de cada arquivo incluído.
A licença do Leaflet.draw foi conferida também no arquivo `MIT-LICENSE.md` do
tag oficial `v1.0.4`, cuja origem está registrada no manifesto. Os hashes foram
verificados antes de copiar os arquivos para este diretório.

Ao atualizar uma biblioteca, verificar a integridade do pacote oficial,
preservar as licenças e arquivos relativos, atualizar o manifesto e executar
os testes de mapas e de navegador. Não editar os arquivos minificados.

Os tiles de fundo continuam vindo de OpenStreetMap, com atribuição visível.
Se estiverem indisponíveis, as geometrias locais e a lista textual continuam
acessíveis; não se trata de um pacote offline de mapas de fundo.
