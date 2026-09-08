# Revisão de clareza — 08/09/2026

## O que mudou

- `Etapa 2 - Deduplicacao e Sensibilidade/deduplicacao_exata.py`: saída em seções; glossário de split, classe, grupo e par; substituição de “pares únicos” por “pares candidatos sem repetição da combinação”; contagem de imagens distintas envolvidas (1.039); categorias exclusivas (1.230 só split, 3 só classe, 3 ambos); tabela de sensibilidade sem impressão duplicada; nomes de colunas amigáveis apenas no terminal. Importações organizadas e execução dentro de run().
- O script da Etapa 2 encontra o manifesto na pasta irmã da Etapa 1. Também valida caminhos relativos preenchidos e exclusivos, rótulos preenchidos, SHA-256 não ausente, ao menos duas imagens comparáveis e hashes perceptuais de 64 bits. Entradas inválidas interrompem a análise com mensagem, em vez de produzir contagens enganosas.
- `Etapa 0 - Ambiente e Poc/_PoC/poc_auditoria.py` e `Etapa 1 - Auditoria da Base/auditoria.py`: comentário e mensagem explicando que is_valid representa sucesso do processamento, não ausência de duplicatas ou rótulo correto.
- `README.md`: estrutura e status atualizados; glossário com exemplos; instruções para usar este pacote. Texto salvo em UTF-8.
- `Plano_Etapa_Auditoria_Deduplicacao.md.md`: status da PoC e análises executadas atualizado; nomes dos campos atuais; esclarecimentos sobre candidatos, limiares e interpretação. Link do Trello preservado.
- `Etapa 2 - Deduplicacao e Sensibilidade/resultados/LEIA_OS_RESULTADOS.md`: novo guia de interpretação de cada CSV e de suas colunas.
- `ALTERACOES.md`: este registro.

## Comportamento técnico preservado

SHA-256, pHash, dHash, comparação por Hamming em bits, limiares 0/3/5/8/10 e critério T=0 com OU foram mantidos. Os nomes e colunas dos quatro CSVs da Etapa 2 foram preservados; eles foram regenerados durante a verificação. Nada foi excluído ou reclassificado. Diários históricos, relatório consolidado, PDF, requirements e CSVs da PoC/auditoria foram mantidos na cópia.

O plano histórico pede LOAD_TRUNCATED_IMAGES=True, mas o código usa a leitura estrita padrão do Pillow. Essa diferença foi explicitada no plano; o processamento não foi alterado nesta revisão. Não confundir tolerância a truncamento com detecção de corrupção.

## Verificação realizada

- Sintaxe dos três scripts verificada.
- Etapa 2 executada no manifesto de 7.200 linhas do pacote, sem acessar imagens.
- Reproduzidos: 153 grupos SHA-256, 340 arquivos e todas as dez linhas de contagens de sensibilidade informadas na conversa.
- Reproduzidos: 1.236 pares candidatos, 1.233 entre splits, 6 entre classes, 3 com ambas as condições.
- Verificados: ausência de repetição A-B/B-A e cumprimento do critério de seleção em todas as linhas.
- Identificadas 1.039 imagens distintas nesses pares.
- PoC e auditoria não foram reexecutadas no dataset; suas alterações são apenas explicativas.

## Como aplicar

Faça uma cópia de segurança dos arquivos que deseja substituir. Copie os arquivos alterados para os locais correspondentes do seu projeto, com as pastas das etapas dentro de Desenvolvimento. Não mova as etapas para outro nível: PoC e auditoria dependem da estrutura existente para localizar o dataset.

O ZIP revisado é uma cópia independente. Não houve edição direta nos arquivos originais do projeto. T final, componentes conexos e inspeção humana continuam pendentes.
