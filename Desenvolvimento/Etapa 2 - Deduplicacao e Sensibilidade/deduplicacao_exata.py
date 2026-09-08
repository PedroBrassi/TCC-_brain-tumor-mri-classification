"""Etapa 2: duplicatas exatas e candidatos perceptuais para inspeção.

O nome do script foi mantido por compatibilidade. Ele executa as duas análises.
Pares sem repetição são combinações A-B listadas uma vez, NÃO imagens únicas
sem duplicatas. Hash perceptual igual NÃO confirma duplicação ou vazamento.
Nenhum arquivo de imagem é modificado por este script.
"""
from pathlib import Path

import imagehash
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist

# As etapas são pastas irmãs, tanto no ZIP extraído quanto em Desenvolvimento.
MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent
    / "Etapa 1 - Auditoria da Base" / "resultados" / "manifesto_base_dados.csv"
)


def print_section(title: str) -> None:
    print(f"\n{'=' * 76}\n{title}\n{'=' * 76}")


def run() -> None:
    print_section("ETAPA 2 - DUPLICAÇÃO EXATA E CANDIDATOS À REVISÃO")
    print("Split: divisão treino/teste. Classe: rótulo, como glioma ou notumor.")
    # Preserva os hashes como texto, incluindo possíveis zeros à esquerda.
    df = pd.read_csv(
        MANIFEST_PATH,
        encoding="utf-8-sig",
        dtype={
            "sha256_hash": "string",
            "phash": "string",
            "dhash": "string",
        },
    )

    print_section("1. MANIFESTO DE ENTRADA")
    print(f"Imagens registradas: {len(df)}")
    print(f"SHA-256 ausentes: {df['sha256_hash'].isna().sum()}")

    if df["sha256_hash"].isna().any():
        raise ValueError("Existem SHA-256 ausentes. Corrija o manifesto antes de agrupar.")
    if df["relative_path"].isna().any() or df["relative_path"].duplicated().any():
        raise ValueError("Cada imagem deve ter um caminho relativo preenchido e exclusivo.")
    if df[["split_assigned", "class_label"]].isna().any().any():
        raise ValueError("Split e classe devem estar preenchidos em todas as linhas.")

    print_section("2. GRUPOS DE ARQUIVOS COM SHA-256 REPETIDO")
    print("Grupo = arquivos com o mesmo SHA-256. Não é uma contagem de pares.")
    # Seleciona todos os integrantes dos grupos com SHA-256 repetido.
    duplicate_mask = df["sha256_hash"].duplicated(keep=False)
    exact_duplicates_df = df.loc[duplicate_mask].copy()

    duplicate_group_count = exact_duplicates_df["sha256_hash"].nunique()

    print(f"Grupos com SHA-256 repetido: {duplicate_group_count}")
    print(f"Arquivos nesses grupos: {len(exact_duplicates_df)}")
    print(
        "Cópias excedentes teóricas (não são exclusões decididas):",
        len(exact_duplicates_df) - duplicate_group_count,
    )

    # Resume cada grupo de arquivos com SHA-256 repetido.
    group_summary = (
        exact_duplicates_df.groupby("sha256_hash")
        .agg(
            file_count=("relative_path", "size"),
            split_count=("split_assigned", "nunique"),
            class_count=("class_label", "nunique"),
        )
        .reset_index()
    )

    group_summary["cross_split"] = group_summary["split_count"] > 1
    group_summary["label_conflict"] = group_summary["class_count"] > 1

    print(
        "Grupos presentes em train e test:",
        int(group_summary["cross_split"].sum()),
    )
    print(
        "Grupos com classes diferentes:",
        int(group_summary["label_conflict"].sum()),
    )
    print(
        "Grupos com ambas as condições:",
        int(
            (
                group_summary["cross_split"]
                & group_summary["label_conflict"]
            ).sum()
        ),
    )

    output_dir = Path(__file__).resolve().parent / "resultados"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Associa as características do grupo a cada arquivo duplicado.
    duplicate_details = exact_duplicates_df.merge(
        group_summary,
        on="sha256_hash",
        how="left",
        validate="many_to_one",
    )

    duplicate_details = duplicate_details.sort_values(
        ["sha256_hash", "relative_path"]
    )

    details_path = output_dir / "duplicatas_exatas.csv"
    summary_path = output_dir / "resumo_grupos_exatos.csv"

    duplicate_details.to_csv(
        details_path, index=False, encoding="utf-8-sig"
    )
    group_summary.to_csv(
        summary_path, index=False, encoding="utf-8-sig"
    )

    print(f"Arquivos no relatório detalhado: {len(duplicate_details)}")
    print(f"Grupos no resumo: {len(group_summary)}")
    print(f"Relatórios salvos em: {output_dir}")


    print_section("3. COMPARAÇÃO VISUAL POR HASHES PERCEPTUAIS")
    print("Par = combinação de duas imagens: A-B e B-A contam uma vez.")
    print("Distância zero significa hash perceptual igual, não duplicata confirmada.")
    valid_hashes_df = df.dropna(subset=["phash", "dhash"])
    print(f"Imagens com ambos os hashes: {len(valid_hashes_df)}")
    print(f"Imagens fora desta comparação por hash ausente: {len(df) - len(valid_hashes_df)}")
    if len(valid_hashes_df) < 2:
        raise ValueError("São necessárias pelo menos duas imagens com ambos os hashes.")
    for column in ["phash", "dhash"]:
        if not valid_hashes_df[column].str.fullmatch(r"[0-9a-fA-F]{16}").all():
            raise ValueError(f"A coluna {column} deve conter hashes de 64 bits (16 caracteres hexadecimais).")

    # Mantém uma posição sequencial para relacionar os hashes aos arquivos.
    valid_hashes_df = valid_hashes_df.reset_index(drop=True)

    # Cada linha representa uma imagem; cada coluna, um bit do hash.
    phash_bits = np.array([
        imagehash.hex_to_hash(value).hash.flatten()
        for value in valid_hashes_df["phash"]
    ])

    dhash_bits = np.array([
        imagehash.hex_to_hash(value).hash.flatten()
        for value in valid_hashes_df["dhash"]
    ])

    # pdist retorna a proporção de bits diferentes.
    # Multiplicamos por 64 para obter a quantidade de bits diferentes.
    phash_distances = pdist(phash_bits, metric="hamming")
    phash_distances *= phash_bits.shape[1]

    # Arredonda e armazena como inteiros de 0 a 64.
    np.rint(phash_distances, out=phash_distances)
    phash_distances = phash_distances.astype(np.uint8)

    print(f"Combinações comparadas por hash: {len(phash_distances)}")


    # Converte a proporção de bits diferentes em quantidade de bits.
    dhash_distances = pdist(dhash_bits, metric="hamming")
    dhash_distances *= dhash_bits.shape[1]

    np.rint(dhash_distances, out=dhash_distances)
    dhash_distances = dhash_distances.astype(np.uint8)

    print("Cálculo de pHash e dHash concluído.")


    # Os rótulos seguem exatamente a ordem das linhas usadas nas matrizes de bits.
    splits = valid_hashes_df["split_assigned"].to_numpy()
    classes = valid_hashes_df["class_label"].to_numpy()
    image_count = len(valid_hashes_df)

    # Uma posição por par, na mesma ordem do vetor retornado por pdist.
    cross_split_mask = np.empty(len(phash_distances), dtype=bool)
    different_class_mask = np.empty(len(phash_distances), dtype=bool)

    offset = 0

    for index in range(image_count - 1):
        pair_count = image_count - index - 1
        end = offset + pair_count

        cross_split_mask[offset:end] = (
            splits[index] != splits[index + 1:]
        )
        different_class_mask[offset:end] = (
            classes[index] != classes[index + 1:]
        )

        offset = end

    sensitivity_records = []

    for hash_name, distances in [
        ("pHash", phash_distances),
        ("dHash", dhash_distances),
    ]:
        for threshold in [0, 3, 5, 8, 10]:
            detected = distances <= threshold
            total_pairs = int(np.count_nonzero(detected))

            cross_split_pairs = int(
                np.count_nonzero(detected & cross_split_mask)
            )
            different_class_pairs = int(
                np.count_nonzero(detected & different_class_mask)
            )

            sensitivity_records.append({
                "hash_type": hash_name,
                "threshold": threshold,
                "total_pairs": total_pairs,
                "cross_split_pairs": cross_split_pairs,
                "different_class_pairs": different_class_pairs,
            })

    sensitivity_df = pd.DataFrame(sensitivity_records)

    # Percentual de pares detectados que possuem classes diferentes.
    sensitivity_df["different_class_pct"] = (
        sensitivity_df["different_class_pairs"]
        .div(sensitivity_df["total_pairs"].replace(0, float("nan")))
        .mul(100)
        .round(2)
    )

    output_dir = Path(__file__).resolve().parent / "resultados"
    output_dir.mkdir(parents=True, exist_ok=True)

    sensitivity_path = output_dir / "analise_sensibilidade.csv"

    sensitivity_df.to_csv(
        sensitivity_path,
        index=False,
        encoding="utf-8-sig",
    )

    print_section("4. SENSIBILIDADE - PARES CANDIDATOS, NÃO CONFIRMADOS")
    print("T = máximo de bits diferentes aceito. As linhas são cumulativas; não somar.")
    print("Entre splits = train/test. Classes diferentes = rótulos distintos.")
    print("Essas categorias podem se sobrepor; o percentual não é taxa de falsos positivos.")
    print(sensitivity_df.rename(columns={
        "hash_type": "Hash", "threshold": "T", "total_pairs": "Pares candidatos",
        "cross_split_pairs": "Entre splits", "different_class_pairs": "Classes diferentes",
        "different_class_pct": "% classes diferentes",
    }).to_string(index=False))
    print(f"\nRelatório salvo em: {sensitivity_path}")

    # Seleciona pares com distância zero em pelo menos um dos hashes
    # e com diferença de split ou classe.
    review_mask = (
        ((phash_distances == 0) | (dhash_distances == 0))
        & (cross_split_mask | different_class_mask)
    )

    relative_paths = valid_hashes_df["relative_path"].to_numpy()
    review_records = []
    offset = 0

    # Percorre os pares na mesma ordem utilizada por pdist.
    for first_index in range(image_count - 1):
        pair_count = image_count - first_index - 1
        end = offset + pair_count

        selected_positions = np.flatnonzero(review_mask[offset:end])

        for position in selected_positions:
            second_index = first_index + 1 + int(position)
            pair_index = offset + int(position)

            review_records.append({
                "relative_path_a": relative_paths[first_index],
                "relative_path_b": relative_paths[second_index],
                "split_a": splits[first_index],
                "split_b": splits[second_index],
                "class_a": classes[first_index],
                "class_b": classes[second_index],
                "phash_distance": int(phash_distances[pair_index]),
                "dhash_distance": int(dhash_distances[pair_index]),
                "cross_split": bool(cross_split_mask[pair_index]),
                "different_class": bool(different_class_mask[pair_index]),
            })

        offset = end

    review_columns = [
        "relative_path_a", "relative_path_b",
        "split_a", "split_b",
        "class_a", "class_b",
        "phash_distance", "dhash_distance",
        "cross_split", "different_class",
    ]

    review_df = pd.DataFrame(review_records, columns=review_columns)

    review_path = output_dir / "pares_t0_para_revisao.csv"
    review_df.to_csv(review_path, index=False, encoding="utf-8-sig")

    print_section("5. FILA DE INSPEÇÃO - CANDIDATOS EM T=0")
    print("Critério: pHash OU dHash igual, com split OU classe diferente.")
    print("Cada combinação A-B aparece uma vez, mesmo se ambos os hashes a sinalizam.")
    print("Não é uma lista de imagens livres de duplicação nem uma lista de exclusões.")
    both = review_df["cross_split"] & review_df["different_class"]
    distinct_images = pd.concat([
        review_df["relative_path_a"], review_df["relative_path_b"]
    ]).nunique()
    print(f"Pares candidatos sem repetição da combinação: {len(review_df)}")
    print(f"Imagens distintas envolvidas nesses pares: {distinct_images}")
    print("Uma imagem pode participar de vários pares.")
    print(f"Entre splits (inclui os casos com ambas as condições): {int(review_df['cross_split'].sum())}")
    print(f"Entre classes (inclui os casos com ambas as condições): {int(review_df['different_class'].sum())}")
    print("Distribuição sem sobreposição:")
    print(f"  Só split diferente: {int((review_df['cross_split'] & ~review_df['different_class']).sum())}")
    print(f"  Só classe diferente: {int((~review_df['cross_split'] & review_df['different_class']).sum())}")
    print(f"  Split e classe diferentes: {int(both.sum())}")
    print_section("6. RELATÓRIOS GERADOS")
    print(f"Pasta: {output_dir}")
    for path, description in [
        (details_path, "uma linha por arquivo em grupo SHA-256 repetido"),
        (summary_path, "uma linha por grupo SHA-256 repetido"),
        (sensitivity_path, "uma linha por hash e limiar"),
        (review_path, "uma linha por par CANDIDATO à revisão"),
    ]:
        print(f"  {path.name}: {description}")
    print("\nAnálise concluída. Nenhuma imagem removida ou reclassificada.")
    print("Próximo passo: inspeção humana. T final e componentes conexos ainda pendentes.")


if __name__ == "__main__":
    run()
