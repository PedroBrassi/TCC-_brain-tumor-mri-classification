# Etapa 1 — Auditoria e Deduplicação da Base

Diário de bordo / plano de desenvolvimento. Versão revisada em 04/09/2026 (correções em relação à primeira versão: split `val` removido da auditoria, BK-Tree retirado do escopo, checkpoint ajustado ao tamanho real da base, e regra de rótulos conflitantes trocada de "reclassificar" para "documentar e excluir").

## Parte 1: Auditoria Extensiva e Geração do Manifesto

**Objetivo:** garantir a integridade física de cada arquivo, coletar metadados fundamentais e criar a fonte da verdade da base.

**Metadados obrigatórios por imagem:**
- `file_path`: caminho relativo e absoluto.
- `split_assigned`: split de origem (`train`/`test`) — a base bruta não tem `val`; o split de validação só existe depois do resplit 70/15/15, que é uma etapa posterior, não da auditoria.
- `class_label`: subpasta ou rótulo atribuído.
- `file_size_bytes`: tamanho no disco em bytes.
- `dimensions`: tupla `(width, height)`.
- `aspect_ratio`: razão de aspecto `(width / height)`.
- `color_mode`: modo de cor lido via Pillow (`RGB`, `L`, `RGBA`, `CMYK`).
- `channels`: número de canais (ex.: 3 para RGB, 1 para escala de cinza).
- `file_extension`: extensão do arquivo de origem (ex.: `.png`, `.jpg`).
- `is_valid`: booleano indicando se o arquivo está saudável.
- `error_flag`: mensagem tratada de erro (ex.: "Truncated file", "Cannot identify image file").

**Tratamento de exceções & tolerância a falhas:**
- Envolver o carregamento de cada imagem em um bloco `try/except` refinado (`PIL.UnidentifiedImageError`, `OSError`).
- Ativar `ImageFile.LOAD_TRUNCATED_IMAGES = True` com aviso, para identificar imagens parcialmente corrompidas.
- Checkpoint de progresso: **opcional** nessa base — o processamento completo das ~7.200 imagens leva ~1-2 minutos, então salvar a cada 5.000 imagens não cumpre função real (dispararia só uma vez, perto do fim). Se quiser essa proteção mesmo assim, use um intervalo bem menor (ex.: a cada 500).

## Parte 2: Deduplicação e Análise de Vazamento de Dados

**Deduplicação exata:**
- Calcular o hash SHA-256 diretamente no buffer de bytes do arquivo de cada imagem no manifesto.
- Mapear conflitos exatos dentro do mesmo split e, prioritariamente, entre os splits de `train` e `test`.

**Deduplicação perceptual (quase-duplicatas):**
- Gerar hashes perceptuais usando `imagehash.phash()` e `imagehash.dhash()`.
- Comparar pares por distância de Hamming usando uma matriz de distância vetorizada (`scipy.spatial.distance.pdist`, métrica `hamming`).
  - **Nota sobre escala:** com ~7.200 imagens (~26 milhões de pares), essa abordagem resolve em segundos. Uma estrutura de indexação como BK-Tree não é necessária aqui — só valeria a pena se a base crescesse para centenas de milhares de imagens. Manter fora do escopo por ora.

**Análise de sensibilidade de limiares:**
- Testar múltiplos limiares de distância de Hamming (T ∈ {0, 3, 5, 8, 10}).
- Para cada limiar, tabular:
  - Total de pares detectados.
  - *Data Leakage Pairs*: pares com uma imagem em `train` e outra em `test`.
  - *Label Mismatch Pairs*: pares com aparência muito semelhante, mas rótulos de classe divergentes.
- **Critério de decisão para o T final** (faltava na primeira versão): definir a regra a priori, por exemplo — maior T tal que a taxa de pares "classes diferentes" não ultrapasse um limite aceitável, sinal de que o hash ainda não está capturando ruído/falso positivo. Documentar a justificativa escolhida na metodologia.

**Agrupamento em componentes conexos:**
- Modelar as similaridades como um grafo não-dirigido (imagens = vértices, similaridade ≤ T = aresta).
- Usar busca em largura/profundidade (BFS/DFS) — por exemplo `networkx.connected_components` — para agrupar duplicatas em componentes conexos, não apenas pares isolados.
- Exemplo: se A é quase igual a B, e B é quase igual a C, então A, B e C formam um único cluster de duplicatas.

## Parte 3: Curadoria Visual e Protocolo de Exclusão

**Módulo de inspeção visual:**
- Visualizador (Matplotlib/Plotly) para renderizar todos os elementos de um cluster conexo lado a lado.
- Exibir sobre cada imagem: caminho, split, classe e hash (SHA-256/pHash).
- Destacar visualmente (ex.: borda vermelha) qualquer par que viole a regra de split (`train` vs `test`) ou de classe.

**Diretrizes de exclusão manual (human-in-the-loop):**
- Nenhuma imagem é deletada via script automatizado sem confirmação manual do inspetor.
- Regras de decisão:
  - **Vazamento de dados (train x test):** remover a versão de `test` ou descartar a duplicata do `train`.
  - **Duplicata interna no mesmo split:** manter apenas a imagem de maior resolução/melhor qualidade.
  - **Rótulos conflitantes** (revisado): **não** reclassificar a imagem por conta própria — não há base clínica para corrigir um diagnóstico de um dataset curado. Em vez disso, **documentar o caso e excluir o par do conjunto por ambiguidade**.

---

## Lista de Tarefas Ordenada (ToDo)

### Etapa 0: Ambiente & Prova de Conceito (PoC)
- [X] Criar ambiente virtual Python e instalar `pillow`, `imagehash`, `pandas`, `networkx`, `matplotlib` (`pyarrow` só se for usar Parquet — opcional para este tamanho de base).
- [ ] Escrever script PoC em 100 imagens de uma única classe para validar extração de metadados, pHash e salvamento do arquivo de saída.

### Etapa 1: Execução da Auditoria da Base Completa
- [ ] Rodar o script de auditoria no dataset completo (`train` e `test`).
- [ ] Exportar o manifesto consolidado (`manifesto_base_dados.csv` ou `.parquet`).
- [ ] Gerar relatório sumário de erros (imagens corrompidas, arquivos sem dimensão válida, modos de cor atípicos).

### Etapa 2: Pipeline de Deduplicação e Análise de Sensibilidade
- [ ] Calcular SHA-256 para todas as entradas do manifesto e agrupar duplicatas exatas.
- [ ] Calcular `pHash` e `dHash` para todas as imagens válidas.
- [ ] Rodar a matriz de sensibilidade com limiares T ∈ {0, 3, 5, 8, 10} e exportar os relatórios de Data Leakage e Label Mismatch.
- [ ] Definir e documentar o critério de decisão para o T final.
- [ ] Implementar o agrupamento por componentes conexos (`networkx.connected_components`) para consolidar clusters de duplicatas.

### Etapa 3: Interface de Inspeção e Tomada de Decisão
- [ ] Desenvolver notebook de inspeção visual focado em clusters com conflito de split (`train` x `test`) e de classe.
- [ ] Gerar arquivo de log/decisão final (`exclusoes_e_ajustes.csv`) contendo os caminhos a remover/remanejar e o motivo de cada decisão.
- [ ] Executar o expurgo definitivo e gerar o manifesto final higienizado.

---

*Board Trello correspondente: [TCC - Classificação de Tumores Cerebrais](https://trello.com/b/OJmQifd0/tcc-classifica%C3%A7%C3%A3o-de-tumores-cerebrais)*
