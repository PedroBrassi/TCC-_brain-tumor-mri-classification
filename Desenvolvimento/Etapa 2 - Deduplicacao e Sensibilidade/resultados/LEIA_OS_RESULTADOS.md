# Como interpretar os relatórios

Os nomes de arquivos e colunas foram mantidos para compatibilidade.

| Arquivo | Uma linha representa | Como interpretar |
|---|---|---|
| duplicatas_exatas.csv | Um arquivo em grupo SHA-256 repetido | 340 arquivos, não 340 exclusões. |
| resumo_grupos_exatos.csv | Um grupo SHA-256 | 153 grupos; file_count conta arquivos, não pares. |
| analise_sensibilidade.csv | Um hash e um limiar | Contagens cumulativas de pares candidatos. |
| pares_t0_para_revisao.csv | Um par candidato A-B | 1.236 combinações sem repetição; não imagens livres de duplicação. |

## Colunas da sensibilidade

- hash_type: pHash ou dHash, avaliados separadamente.
- threshold: distância máxima em bits (0, 3, 5, 8, 10).
- total_pairs: pares sinalizados, incluindo eventuais duplicatas exatas presentes na base.
- cross_split_pairs: pares com uma imagem em train e outra em test; suspeita perceptual, não vazamento confirmado.
- different_class_pairs: pares com rótulos diferentes; sujeitos à inspeção.
- different_class_pct: 100 × different_class_pairs / total_pairs. Não é uma taxa de erro confirmada.

## Colunas da fila de revisão

- relative_path_a/b: caminhos das duas imagens em relação ao dataset.
- split_a/b e class_a/b: origem e classe de cada imagem.
- phash_distance e dhash_distance: quantidades de bits diferentes; uma delas pode ser maior que zero porque a seleção usa OU.
- cross_split e different_class: indicadores que podem ser verdadeiros simultaneamente.

Os totais 1.233 entre splits e 6 entre classes se sobrepõem em 3 pares.
Categorias exclusivas: 1.230 só split; 3 só classe; 3 ambos.
Cada A-B aparece uma vez mesmo se os dois hashes o sinalizarem. A pode aparecer em A-C também.

O SHA-256 não encontrou grupos atravessando splits nem classes. Isso não exclui candidatos perceptuais ou outras formas de vazamento, como imagens diferentes do mesmo paciente.

Nenhum CSV é uma autorização de exclusão. A revisão humana e o agrupamento em componentes conexos ainda estão pendentes.
