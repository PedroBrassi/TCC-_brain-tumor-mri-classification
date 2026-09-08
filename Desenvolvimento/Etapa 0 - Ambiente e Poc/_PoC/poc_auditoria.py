"""
PoC (Prova de Conceito) - Etapa 0.

Valida, em 100 imagens de uma única classe, a extração de metadados,
o cálculo de SHA-256 e dos hashes perceptuais pHash/dHash, além da
exportação e reabertura do manifesto CSV.

A comparação dos hashes para identificar duplicatas será feita depois.
"""

import hashlib
from pathlib import Path

import imagehash
import pandas as pd
from PIL import Image, UnidentifiedImageError


# --- Configuração ------------------------------------------------------------

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}
SAMPLE_SIZE = 100
HASH_COLUMNS = ["sha256_hash", "phash", "dhash"]

SCRIPT_DIR = Path(__file__).resolve().parent

# Para a localização atual do script:
# parents[0] = _PoC
# parents[1] = Etapa 0 - Ambiente e Poc
# parents[2] = Desenvolvimento
# parents[3] = TCC 1
# Ajuste se mover o script para outra profundidade.
PROJECT_ROOT = Path(__file__).resolve().parents[3]

CLASS_DIR = (
    PROJECT_ROOT
    / "Brain Tumor MRI Dataset"
    / "Training"
    / "meningioma"
)

OUTPUT_DIR = SCRIPT_DIR / "resultados"
OUTPUT_PATH = OUTPUT_DIR / "manifesto_poc.csv"


# --- Funções -----------------------------------------------------------------

def list_sample_images(class_dir: Path, sample_size: int) -> list[Path]:
    """
    Seleciona os primeiros arquivos de imagem, ordenados pelo nome.

    A seleção é reprodutível enquanto os arquivos da pasta permanecerem
    os mesmos. Não é uma amostra aleatória.
    """
    if not class_dir.is_dir():
        raise NotADirectoryError(
            f"Pasta da classe não encontrada ou inválida: {class_dir}"
        )

    if sample_size <= 0:
        raise ValueError("O tamanho da amostra deve ser maior que zero.")

    images = [
        item
        for item in class_dir.iterdir()
        if item.is_file() and item.suffix.lower() in VALID_EXTENSIONS
    ]

    return sorted(images)[:sample_size]


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
    }


def build_record(image_path: Path) -> dict:
    """
    Monta o registro da imagem.

    Registra falhas capturadas como UnidentifiedImageError ou OSError,
    preservando as informações obtidas antes da falha.
    """
    record = {
        "file_path": str(image_path),
        "class_label": image_path.parent.name,
        "file_extension": image_path.suffix.lower(),
        "split_assigned": "train",  # Fixo: esta PoC usa apenas Training.
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
        print(f"Erro ao processar a imagem {image_path.name}: {error}")
        record["error_flag"] = str(error)

    return record


def verify_round_trip(df: pd.DataFrame, csv_path: Path) -> bool:
    """Confere os hashes após salvar e reabrir o CSV."""
    # A leitura como texto preserva possíveis zeros à esquerda.
    reloaded = pd.read_csv(
        csv_path,
        encoding="utf-8-sig",
        dtype={column: "string" for column in HASH_COLUMNS},
    )

    print(f"Dimensões da tabela reaberta: {reloaded.shape}")
    print("Hashes ausentes após reabrir o CSV:")
    print(reloaded[HASH_COLUMNS].isna().sum())

    preserved = (
        df[HASH_COLUMNS]
        .astype("string")
        .equals(reloaded[HASH_COLUMNS])
    )

    print(f"Hashes preservados: {preserved}")
    return preserved


def run() -> None:
    sample_paths = list_sample_images(CLASS_DIR, SAMPLE_SIZE)

    # Evita continuar com uma amostra menor que a planejada ou vazia.
    if len(sample_paths) != SAMPLE_SIZE:
        raise ValueError(
            f"Esperadas {SAMPLE_SIZE} imagens, "
            f"mas foram selecionadas {len(sample_paths)} em {CLASS_DIR}."
        )

    records = [build_record(path) for path in sample_paths]
    df = pd.DataFrame(records)

    print(f"Quantidade de registros: {len(df)}")
    print("Resultado do processamento:")
    print(df["is_valid"].value_counts())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Substitui o manifesto anterior de mesmo nome.
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"Manifesto salvo em: {OUTPUT_PATH}")

    if not verify_round_trip(df, OUTPUT_PATH):
        raise ValueError(
            "Os hashes do CSV não correspondem aos valores antes da exportação."
        )


if __name__ == "__main__":
    run()