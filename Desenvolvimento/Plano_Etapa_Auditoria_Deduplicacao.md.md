# Plano - Auditoria e Deduplicação da Base

Diário de bordo / plano de desenvolvimento. Organização revisada conforme as Etapas 0 a 3. Regras técnicas da versão de 04/09/2026 preservadas (correções em relação à primeira versão: split `val` removido da auditoria, BK-Tree retirado do escopo, checkpoint ajustado ao tamanho real da base, e regra de rótulos conflitantes trocada de "reclassificar" para "documentar e excluir").

## Etapa 0 - Ambiente e PoC

**Ambiente Python: concluído.** Ambiente virtual criado e bibliotecas `pillow`, `imagehash`, `pandas`, `networkx` e `matplotlib` instaladas. O uso de `pyarrow` é opcional, apenas se for usar Parquet.

**Prova de Conceito (PoC): concluída nas 100 imagens.** Foi desenvolvido o script `poc_auditoria.py` com 100 imagens de uma única classe do conjunto de treino, validando a leitura e integridade das imagens, a extração de metadados, o cálculo de SHA-256, pHash e dHash, a organização dos dados com pandas e o salvamento do arquivo de saída.

## Etapa 1 - Auditoria da Base

### Auditoria extensiva e geração do manifesto

**Objetivo:** garantir a integridade física de cada arquivo, coletar metadados fundamentais e criar a fonte da verdade da base.

**Metadados obrigatórios por imagem:**
- `file_path`: caminho absoluto; `relative_path`: caminho relativo ao dataset.
- `split_assigned`: split de origem (`train`/`test`) — a base bruta não tem `val`; o split de validação só existe depois do resplit 70/15/15, que é uma etapa posterior, não da auditoria.
- `class_label`: subpasta ou rótulo atribuído.
- `file_size_bytes`: tamanho no disco em bytes.
- `width` e `height`: largura e altura em colunas separadas no CSV.
- `aspect_ratio`: razão de aspecto `(width / height)`.
- `color_mode`: modo de cor lido via Pillow (`RGB`, `L`, `RGBA`, `CMYK`).
- `channels`: número de canais (ex.: 3 para RGB, 1 para escala de cinza).
- `file_extension`: extensão do arquivo de origem (ex.: `.png`, `.jpg`).
- `is_valid`: booleano indicando sucesso do processamento implementado; não certifica ausência de duplicatas nem correção de rótulos.
- `error_flag`: mensagem tratada de erro (ex.: "Truncated file", "Cannot identify image file").

**Tratamento de exceções & tolerância a falhas:**
- Envolver o carregamento de cada imagem em um bloco `try/except` refinado (`PIL.UnidentifiedImageError`, `OSError`).
- Ativar `ImageFile.LOAD_TRUNCATED_IMAGES = True` com aviso, para identificar imagens parcialmente corrompidas.
- Checkpoint de progresso: **opcional** nessa base — o processamento completo das ~7.200 imagens leva ~1-2 minutos, então salvar a cada 5.000 imagens não cumpre função real (dispararia só uma vez, perto do fim). Se quiser essa proteção mesmo assim, use um intervalo bem menor (ex.: a cada 500).

## Etapa 2 - Deduplicacao e Sensibilidade

### Deduplicação e análise de vazamento de dados

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
  - *Data Leakage Pairs*: candidatos entre `train` e `test`; vazamento ainda não confirmado visualmente.
  - *Label Mismatch Pairs*: pares sinalizados pelo hash com classes diferentes; semelhança e conflito precisam de inspeção.
- **Critério de decisão para o T final** (faltava na primeira versão): definir a regra a priori, por exemplo — maior T tal que a taxa de pares "classes diferentes" não ultrapasse um limite aceitável, sinal de que o hash ainda não está capturando ruído/falso positivo. Documentar a justificativa escolhida na metodologia.

**Agrupamento em componentes conexos:**
- Modelar as similaridades como um grafo não-dirigido (imagens = vértices, similaridade ≤ T = aresta).
- Usar busca em largura/profundidade (BFS/DFS) — por exemplo `networkx.connected_components` — para agrupar duplicatas em componentes conexos, não apenas pares isolados.
- Exemplo: se A é quase igual a B, e B é quase igual a C, então A, B e C formam um único cluster de duplicatas.

## Etapa 3 - Curadoria Visual e Decisao

### Curadoria visual e protocolo de exclusão

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

### Etapa 0 - Ambiente e PoC
- [X] Criar ambiente virtual Python e instalar `pillow`, `imagehash`, `pandas`, `networkx`, `matplotlib` (`pyarrow` só se for usar Parquet — opcional para este tamanho de base).
- [X] Escrever script PoC em 100 imagens de uma única classe do conjunto de treino para validar leitura e integridade das imagens, extração de metadados, SHA-256, pHash/dHash, organização com pandas e salvamento do arquivo de saída.

### Etapa 1 - Auditoria da Base
- [X] Rodar o script de auditoria no dataset completo (`train` e `test`).
- [X] Exportar o manifesto consolidado (`manifesto_base_dados.csv` ou `.parquet`).
- [X] Gerar relatório sumário de erros (imagens corrompidas, arquivos sem dimensão válida, modos de cor atípicos).

### Etapa 2 - Deduplicacao e Sensibilidade
- [X] Calcular SHA-256 para todas as entradas do manifesto e agrupar duplicatas exatas.
- [X] Calcular `pHash` e `dHash` para todas as imagens válidas.
- [X] Rodar a matriz de sensibilidade com limiares T ∈ {0, 3, 5, 8, 10} e exportar os relatórios de Data Leakage e Label Mismatch.
- [ ] Definir e documentar o critério de decisão para o T final.
- [ ] Implementar o agrupamento por componentes conexos (`networkx.connected_components`) para consolidar clusters de duplicatas.

### Etapa 3 - Curadoria Visual e Decisao
- [ ] Desenvolver notebook de inspeção visual focado em clusters com conflito de split (`train` x `test`) e de classe.
- [ ] Gerar arquivo de log/decisão final (`exclusoes_e_ajustes.csv`) contendo os caminhos a remover/remanejar e o motivo de cada decisão.
- [ ] Executar o expurgo definitivo e gerar o manifesto final higienizado.

---

*Board Trello correspondente: [TCC - Classificação de Tumores Cerebrais](https://trello.com/b/OJmQifd0/tcc-classifica%C3%A7%C3%A3o-de-tumores-cerebrais)*

## Como interpretar os resultados atuais

- Grupo SHA-256: conjunto de arquivos com o mesmo hash exato. Não confundir com pares.
- Par candidato: combinação de duas imagens sinalizada por hash perceptual.
- Par sem repetição: A-B aparece uma vez, mesmo se pHash e dHash sinalizarem o par. Não significa imagem sem duplicação.
- T=0: igualdade do hash perceptual, não confirmação de duplicação.
- Os limiares são cumulativos; não somar suas contagens. Classes diferentes não equivalem a falsos positivos confirmados.
- O relatório T=0 usa (pHash igual OU dHash igual) E (split diferente OU classe diferente).
- O script calcula candidatos; inspeção humana, T final e componentes conexos continuam pendentes.

Nota de implementação: o código atual usa a leitura estrita padrão do Pillow, sem ativar LOAD_TRUNCATED_IMAGES. A regra histórica acima não está implementada; ativar leitura tolerante não equivale a detectar corrupção. Esta revisão de clareza não alterou esse comportamento.

A sensibilidade já foi explorada. Qualquer escolha futura de T deve documentar essa exploração; não deve ser descrita retroativamente como uma regra a priori.
