from pathlib import Path
from PIL import Image, UnidentifiedImageError
import hashlib
import imagehash
import pandas as pd

# A PoC utiliza imagens de uma única classe do conjunto de treino.
class_dir = Path(
    r"C:\Users\pedro\Desktop\TCC 1\Brain Tumor MRI Dataset\Training\meningioma"
)

valid_extensions = {".jpg", ".jpeg", ".png"}
image_paths = []

# Usa a localização do script, independentemente da pasta do terminal.
output_dir = Path(__file__).resolve().parent / "resultados"
output_dir.mkdir(exist_ok=True)

output_path = output_dir / "manifesto_poc.csv"
# Filtra por extensão; a leitura com Pillow será verificada depois.
for item in class_dir.iterdir():
    if item.is_file() and item.suffix.lower() in valid_extensions:
        image_paths.append(item)

# Ordena pelos nomes para manter a seleção consistente entre execuções.
# Esta seleção serve à PoC; não é uma amostra aleatória da base.
image_paths = sorted(image_paths)
sample_paths = image_paths[:100]

# Cada imagem terá um registro, inclusive quando houver falha na leitura.
records = []

for image_path in sample_paths:
    file_size_bytes = None
    sha256_hash = None
    try:
        file_size_bytes = image_path.stat().st_size

        # Calcula o SHA-256 dos bytes originais do arquivo.
        with image_path.open("rb") as image_file:
            file_bytes = image_file.read()
            sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        # O with fecha o arquivo automaticamente ao sair do bloco.
        with Image.open(image_path) as image:
            # Carrega os pixels para detectar possíveis falhas de leitura.
            image.load()
            # Calcula os hashes perceptuais e converte os resultados para texto.
            phash_value = str(imagehash.phash(image))
            dhash_value = str(imagehash.dhash(image))

            record = {
                "file_path": str(image_path),
                "dimensions": image.size,  # (largura, altura), em pixels.
                "color_mode": image.mode,
                "is_valid": True,
                "error_flag": None,
                "class_label": image_path.parent.name,
                "file_extension": image_path.suffix.lower(),
                "aspect_ratio": image.width / image.height,
                "channels": len(image.getbands()),
                # Valor fixo porque esta PoC usa apenas Training.
                "split_assigned": "train",
                "file_size_bytes": file_size_bytes,
                "sha256_hash": sha256_hash,
                "phash": phash_value,
                "dhash": dhash_value
            }
            records.append(record)

    except (UnidentifiedImageError, OSError) as error:
        # Registra a falha e permite continuar com a próxima imagem.
        print(f"Erro ao ler a imagem {image_path.name}: {error}")

        # Preserva os dados do caminho e marca como ausentes os metadados
        # que não puderam ser obtidos com uma leitura bem-sucedida.
        record = {
            "file_path": str(image_path),
            "dimensions": None,
            "color_mode": None,
            "is_valid": False,
            "error_flag": str(error),
            "class_label": image_path.parent.name,
            "file_extension": image_path.suffix.lower(),
            "aspect_ratio": None,
            "channels": None,
            "split_assigned": "train",
            "file_size_bytes": file_size_bytes,
            "sha256_hash": sha256_hash,
            "phash": None,
            "dhash": None,
        }
        records.append(record)

# Organiza os registros em uma tabela: uma linha por imagem.
df = pd.DataFrame(records)

# Conta quantas imagens foram processadas com sucesso ou com falha.
print(df["is_valid"].value_counts())

df.to_csv(output_path, index=False, encoding="utf-8-sig")
print(f"Manifesto salvo em: {output_path}")

# Lê os hashes como texto para preservar possíveis zeros à esquerda.
loaded_df = pd.read_csv(
    output_path,
    encoding="utf-8-sig",
    dtype={
        "sha256_hash": "string",
        "phash": "string",
        "dhash": "string",
    },
)

print(f"Dimensões da tabela reaberta: {loaded_df.shape}")

print(loaded_df[["sha256_hash", "phash", "dhash"]].isna().sum())
hash_columns = ["sha256_hash", "phash", "dhash"]

print(
    "Hashes preservados:",
    df[hash_columns].astype("string").equals(loaded_df[hash_columns]),
)