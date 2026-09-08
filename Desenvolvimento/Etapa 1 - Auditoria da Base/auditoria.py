"""
Etapa 1 - Auditoria da Base.

Percorre as classes de Training e Testing, coleta metadados e calcula
SHA-256, pHash e dHash. Registra falhas de leitura sem interromper
o processamento das demais imagens.

Nesta etapa, são utilizados apenas os splits train e test.
"""

import hashlib
from time import perf_counter
from pathlib import Path

import imagehash
from PIL import Image, UnidentifiedImageError

import pandas as pd

# --- Configuração ------------------------------------------------------------

# Localização esperada:
# Projeto do TCC/Desenvolvimento/Etapa 1 - Auditoria da Base/auditoria.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_ROOT / "Brain Tumor MRI Dataset"

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}

SPLIT_MAPPING = {
    "Training": "train",
    "Testing": "test",
}

OUTPUT_DIR = Path(__file__).resolve().parent / "resultados"

# --- Funções -----------------------------------------------------------------

def collect_image_entries(dataset_dir: Path) -> list[dict]:
    """Coleta os caminhos das imagens, junto com seu split e sua classe."""
    if not dataset_dir.is_dir():
        raise NotADirectoryError(
            f"Pasta do dataset não encontrada: {dataset_dir}"
        )

    image_entries = []

    for folder_name, split_name in SPLIT_MAPPING.items():
        split_dir = dataset_dir / folder_name

        if not split_dir.is_dir():
            raise NotADirectoryError(
                f"Pasta do conjunto não encontrada: {split_dir}"
            )



        for class_dir in sorted(split_dir.iterdir()):
            if not class_dir.is_dir():
                continue

            # O filtro considera a extensão, sem validar o conteúdo ainda.
            image_paths = sorted(
                path
                for path in class_dir.iterdir()
                if path.is_file()
                and path.suffix.lower() in VALID_EXTENSIONS
            )



            for image_path in image_paths:
                image_entries.append({
                    "image_path": image_path,
                    "split_assigned": split_name,
                    "class_label": class_dir.name,
                })

    return image_entries


def compute_sha256(path: Path) -> str:
    """Calcula o SHA-256 dos bytes originais do arquivo."""
    with path.open("rb") as image_file:
        return hashlib.sha256(image_file.read()).hexdigest()


def extract_image_metadata(image: Image.Image) -> dict:
    """Extrai metadados e hashes perceptuais da imagem já carregada."""
    return {
        "width": image.width,
        "height": image.height,
        "color_mode": image.mode,
        "aspect_ratio": image.width / image.height,
        "channels": len(image.getbands()),
        "phash": str(imagehash.phash(image)),
        "dhash": str(imagehash.dhash(image)),
        "image_format": image.format,
    }


def build_record(
    image_path: Path,
    split_assigned: str,
    class_label: str,
) -> dict:
    """
    Monta o registro da imagem.

    Registra falhas capturadas como UnidentifiedImageError ou OSError,
    preservando as informações obtidas antes da falha.
    """
    record = {
        "file_path": str(image_path),
        "relative_path": image_path.relative_to(DATASET_DIR).as_posix(),
        "class_label": class_label,
        "file_extension": image_path.suffix.lower(),
        "split_assigned": split_assigned,
        "file_size_bytes": None,
        "sha256_hash": None,
        "width": None,
        "height": None,
        "color_mode": None,
        "aspect_ratio": None,
        "channels": None,
        "phash": None,
        "dhash": None,
        "is_valid": False,
        "error_flag": None,
        "image_format": None,
    }

    try:
        record["file_size_bytes"] = image_path.stat().st_size
        record["sha256_hash"] = compute_sha256(image_path)

        with Image.open(image_path) as image:
            # Força a leitura dos pixels e pode revelar falhas de decodificação.
            image.load()
            record.update(extract_image_metadata(image))

        record["is_valid"] = True

    except (UnidentifiedImageError, OSError) as error:
        print(f"[ERRO] {record['relative_path']}: {error}")
        record["error_flag"] = str(error)

    return record

def print_section(title: str) -> None:
    """Separa os blocos de saída no terminal."""
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def print_table(table: pd.DataFrame) -> None:
    """Exibe a tabela sem índice nem informações internas do pandas."""
    if table.empty:
        print("Nenhum registro.")
    else:
        print(table.to_string(index=False))


def run() -> None:
    started_at = perf_counter()

    print_section("ETAPA 1 - AUDITORIA DA BASE")
    print(f"Dataset: {DATASET_DIR}")
    print("Escopo: train e test | Metadados, SHA-256, pHash e dHash")

    print_section("1. INVENTÁRIO DOS ARQUIVOS")
    image_entries = collect_image_entries(DATASET_DIR)
    total_entries = len(image_entries)

    if not image_entries:
        raise ValueError(
            "Nenhum arquivo com extensão aceita foi encontrado "
            "nas pastas de classes."
        )

    inventory = (
        pd.DataFrame(image_entries)
        .groupby(["split_assigned", "class_label"], sort=False)
        .size()
        .reset_index(name="Arquivos")
        .rename(columns={"split_assigned": "Split", "class_label": "Classe"})
    )
    print_table(inventory)
    print(f"\nTotal de arquivos selecionados: {total_entries}")

    print_section("2. PROCESSAMENTO")
    records = []
    invalid_count = 0
    print(f"Iniciando processamento de {total_entries} arquivos...")

    for index, entry in enumerate(image_entries, start=1):
        record = build_record(
            image_path=entry["image_path"],
            split_assigned=entry["split_assigned"],
            class_label=entry["class_label"],
        )
        records.append(record)
        invalid_count += int(not record["is_valid"])

        # Acompanha o progresso sem imprimir uma linha para cada imagem.
        # Isso não salva um checkpoint.
        if index % 500 == 0 or index == total_entries:
            percentage = 100 * index / total_entries
            print(
                f"  {index:>5}/{total_entries} | {percentage:6.1f}% "
                f"| Falhas: {invalid_count}"
            )

    df = pd.DataFrame(records)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = OUTPUT_DIR / "manifesto_base_dados.csv"
    errors_path = OUTPUT_DIR / "relatorio_erros.csv"

    print_section("3. EXPORTAÇÃO E CONFERÊNCIA DO MANIFESTO")
    df.to_csv(manifest_path, index=False, encoding="utf-8-sig")
    errors_df = df.loc[~df["is_valid"]]
    errors_df.to_csv(errors_path, index=False, encoding="utf-8-sig")

    hash_columns = ["sha256_hash", "phash", "dhash"]
    loaded_df = pd.read_csv(
        manifest_path,
        encoding="utf-8-sig",
        dtype={column: "string" for column in hash_columns},
    )

    shape_preserved = loaded_df.shape == df.shape
    hashes_preserved = (
        df[hash_columns].astype("string").equals(loaded_df[hash_columns])
    )
    print(
        f"Manifesto reaberto: {loaded_df.shape[0]} linhas "
        f"e {loaded_df.shape[1]} colunas"
    )
    print(f"Dimensões da tabela preservadas: {'SIM' if shape_preserved else 'NÃO'}")
    print(f"Valores dos hashes preservados: {'SIM' if hashes_preserved else 'NÃO'}")
    print("\nHashes ausentes após a reabertura:")
    for column in hash_columns:
        print(f"  {column:<12}: {loaded_df[column].isna().sum()}")

    if not shape_preserved or not hashes_preserved:
        raise ValueError("Falha na conferência do manifesto exportado.")

    print_section("4. PERFIL DAS IMAGENS NO MANIFESTO")
    print("Distribuição por split e classe:")
    print_table(
        loaded_df.groupby(["split_assigned", "class_label"], dropna=False)
        .size()
        .reset_index(name="Imagens")
        .rename(columns={"split_assigned": "Split", "class_label": "Classe"})
    )

    print("\nModos de cor e canais:")
    print_table(
        loaded_df.groupby(["color_mode", "channels"], dropna=False)
        .size()
        .reset_index(name="Imagens")
        .rename(columns={"color_mode": "Modo", "channels": "Canais"})
    )

    print("\nDez dimensões mais frequentes (pixels):")
    print_table(
        loaded_df.groupby(["width", "height"], dropna=False)
        .size()
        .sort_values(ascending=False)
        .head(10)
        .reset_index(name="Imagens")
        .rename(columns={"width": "Largura", "height": "Altura"})
    )

    invalid_dimensions = (
        loaded_df[["width", "height"]].isna().any(axis=1)
        | (loaded_df["width"] <= 0)
        | (loaded_df["height"] <= 0)
    )
    invalid_dimensions_count = int(invalid_dimensions.sum())
    print(f"\nRegistros sem dimensões válidas: {invalid_dimensions_count}")

    print("\nExtensão do arquivo e formato identificado:")
    print_table(
        loaded_df.groupby(["file_extension", "image_format"], dropna=False)
        .size()
        .reset_index(name="Arquivos")
        .rename(columns={"file_extension": "Extensão", "image_format": "Formato"})
    )

    # Mantém os relatórios completos; limita apenas os detalhes no terminal.
    color_review_df = loaded_df.loc[
        loaded_df["color_mode"].isin(["P", "RGBA"])
    ].copy()
    color_review_path = OUTPUT_DIR / "revisao_modos_cor.csv"
    color_review_df.to_csv(color_review_path, index=False, encoding="utf-8-sig")

    expected_formats = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG"}
    expected_format = loaded_df["file_extension"].map(expected_formats)
    format_mismatch_df = loaded_df.loc[
        loaded_df["image_format"].notna()
        & loaded_df["image_format"].ne(expected_format)
    ].copy()
    format_report_path = OUTPUT_DIR / "divergencias_formato.csv"
    format_mismatch_df.to_csv(format_report_path, index=False, encoding="utf-8-sig")

    print_section("5. OCORRÊNCIAS PARA REVISÃO")
    print(f"Falhas de processamento: {len(errors_df)}")
    print(f"Arquivos em modo P ou RGBA: {len(color_review_df)}")
    print(f"Divergências entre extensão e formato: {len(format_mismatch_df)}")
    print("As duas últimas categorias podem incluir os mesmos arquivos.")

    # Exibe uma única tabela para evitar repetir arquivos nas duas categorias.
    review_df = loaded_df.loc[
        loaded_df.index.isin(color_review_df.index)
        | loaded_df.index.isin(format_mismatch_df.index)
    ]
    if not review_df.empty:
        print("\nArquivos sinalizados (até 10; detalhes completos nos CSVs):")
        print_table(
            review_df[
                ["relative_path", "color_mode", "file_extension", "image_format"]
            ].head(10).rename(columns={
                "relative_path": "Arquivo relativo ao dataset",
                "color_mode": "Modo",
                "file_extension": "Extensão",
                "image_format": "Formato",
            })
        )
    print("Sinalizações para revisão não são decisões de exclusão.")

    print_section("6. ARQUIVOS GERADOS")
    print(f"Pasta: {OUTPUT_DIR}")
    for path, count in [
        (manifest_path, len(df)),
        (errors_path, len(errors_df)),
        (color_review_path, len(color_review_df)),
        (format_report_path, len(format_mismatch_df)),
    ]:
        print(f"  {path.name:<30} | {count:>5} registros")
    print("Relatórios com zero registros contêm apenas os cabeçalhos.")

    print_section("RESUMO FINAL")
    print(f"Arquivos processados: {len(records)}")
    print(f"Processados sem falha: {len(records) - invalid_count}")
    print(f"Falhas de processamento: {invalid_count}")
    print(f"Registros sem dimensões válidas: {invalid_dimensions_count}")
    print(f"Arquivos únicos sinalizados por modo ou formato: {len(review_df)}")
    print("Conferência da exportação: APROVADA (dimensões da tabela e hashes)")
    print(f"Tempo total: {perf_counter() - started_at:.1f} segundos")
    print("Execução concluída. Os arquivos originais foram preservados.")


if __name__ == "__main__":
    run()