"""
Etapa 1 - Auditoria da Base.

Percorre as classes de Training e Testing, coleta metadados e calcula
SHA-256, pHash e dHash. Registra falhas de leitura sem interromper
o processamento das demais imagens.

Nesta etapa, são utilizados apenas os splits train e test.
"""

import hashlib
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

        print(f"\nConjunto: {split_name}")

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

            print(
                f"  Classe: {class_dir.name} "
                f"| Arquivos: {len(image_paths)}"
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
        print(f"Erro ao processar a imagem {image_path}: {error}")
        record["error_flag"] = str(error)

    return record

def run() -> None:
    # Coleta os arquivos das classes de Training e Testing.
    image_entries = collect_image_entries(DATASET_DIR)
    total_entries = len(image_entries)

    print(f"\nTotal de arquivos de imagem: {total_entries}")

    if not image_entries:
        raise ValueError(
            "Nenhum arquivo com extensão aceita foi encontrado "
            "nas pastas de classes."
        )

    # Processa cada arquivo e preserva os registros de falha.
    records = []

    for index, entry in enumerate(image_entries, start=1):
        record = build_record(
            image_path=entry["image_path"],
            split_assigned=entry["split_assigned"],
            class_label=entry["class_label"],
        )
        records.append(record)

        # Apenas exibe o progresso; não salva um checkpoint.
        if index % 500 == 0 or index == total_entries:
            print(f"Processados: {index}/{total_entries}")

    valid_count = sum(record["is_valid"] for record in records)
    invalid_count = len(records) - valid_count

    print(f"\nRegistros gerados: {len(records)}")
    print(f"Válidos: {valid_count}")
    print(f"Inválidos: {invalid_count}")

    # Exporta o manifesto completo e os registros com falha.
    df = pd.DataFrame(records)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_path = OUTPUT_DIR / "manifesto_base_dados.csv"
    errors_path = OUTPUT_DIR / "relatorio_erros.csv"

    df.to_csv(manifest_path, index=False, encoding="utf-8-sig")

    errors_df = df.loc[~df["is_valid"]]
    errors_df.to_csv(errors_path, index=False, encoding="utf-8-sig")

    print(f"\nManifesto salvo em: {manifest_path}")
    print(f"Relatório de erros salvo em: {errors_path}")
    print(f"Registros no relatório de erros: {len(errors_df)}")

    # Reabre o manifesto preservando os hashes como texto.
    hash_columns = ["sha256_hash", "phash", "dhash"]

    loaded_df = pd.read_csv(
        manifest_path,
        encoding="utf-8-sig",
        dtype={column: "string" for column in hash_columns},
    )

    print(f"\nDimensões do manifesto reaberto: {loaded_df.shape}")

    print("Hashes ausentes:")
    print(loaded_df[hash_columns].isna().sum())

    hashes_preserved = (
        df[hash_columns]
        .astype("string")
        .equals(loaded_df[hash_columns])
    )

    print(f"Hashes preservados: {hashes_preserved}")

    if loaded_df.shape != df.shape or not hashes_preserved:
        raise ValueError("Falha na conferência do manifesto exportado.")

    # Confere a distribuição das imagens no arquivo exportado.
    print("\nQuantidade por split e classe:")
    print(
        loaded_df.groupby(
            ["split_assigned", "class_label"],
            dropna=False,
        ).size()
    )

    print("\nQuantidade por modo de cor e canais:")
    print(
        loaded_df.groupby(
            ["color_mode", "channels"],
            dropna=False,
        ).size()
    )

    print("\nDimensões mais frequentes:")
    print(
        loaded_df.groupby(["width", "height"], dropna=False)
        .size()
        .sort_values(ascending=False)
        .head(10)
    )

    invalid_dimensions = (
        loaded_df[["width", "height"]].isna().any(axis=1)
        | (loaded_df["width"] <= 0)
        | (loaded_df["height"] <= 0)
    )

    print(
        "\nRegistros sem dimensões válidas:",
        int(invalid_dimensions.sum()),
    )

    # Separa os modos P e RGBA para inspeção posterior.
    # Esse relatório não exclui nem converte os arquivos.
    color_review_df = loaded_df.loc[
        loaded_df["color_mode"].isin(["P", "RGBA"])
    ].copy()

    color_review_path = OUTPUT_DIR / "revisao_modos_cor.csv"
    color_review_df.to_csv(
        color_review_path,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nImagens com modo P ou RGBA:")
    print(
        color_review_df[
            ["file_path", "split_assigned", "class_label", "color_mode"]
        ].to_string(index=False)
    )
    print(f"\nRelatório salvo em: {color_review_path}")

        # Compara a extensão com o formato identificado pelo Pillow.
    expected_formats = {
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
        ".png": "PNG",
    }

    expected_format = loaded_df["file_extension"].map(expected_formats)

    format_mismatch_df = loaded_df.loc[
        loaded_df["image_format"].notna()
        & loaded_df["image_format"].ne(expected_format)
    ].copy()

    format_report_path = OUTPUT_DIR / "divergencias_formato.csv"
    format_mismatch_df.to_csv(
        format_report_path,
        index=False,
        encoding="utf-8-sig",
    )

    print("\nQuantidade por extensão e formato:")
    print(
        loaded_df.groupby(
            ["file_extension", "image_format"],
            dropna=False,
        ).size()
    )

    print(
        "\nArquivos com divergência entre extensão e formato:",
        len(format_mismatch_df),
    )
    print(f"Relatório salvo em: {format_report_path}")

    print(df[["relative_path", "split_assigned", "class_label"]].head())

if __name__ == "__main__":
    run()