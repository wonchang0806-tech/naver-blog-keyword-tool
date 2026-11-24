import os
from pathlib import Path
from PIL import Image, ImageOps

def batch_optimize_images(
    input_dir: str = "./raw_images",
    output_dir: str = "./optimized_images",
    max_width: int = 860,
    quality: int = 85
):
    """폴더 내 이미지를 일괄 리사이징하고 용량을 최적화"""
    in_path = Path(input_dir)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    files = [f for f in in_path.iterdir() if f.suffix.lower() in valid_exts]

    if not files:
        print(f"'{input_dir}' 폴더에 변환할 이미지가 없습니다.")
        return

    for file in files:
        try:
            with Image.open(file) as img:
                # 스마트폰 촬영 사진의 EXIF 회전 정보 자동 보정
                img = ImageOps.exif_transpose(img)

                # 투명 배경(RGBA/P)인 경우 JPG 저장을 위해 RGB로 변환
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # 가로 폭이 max_width보다 큰 경우에만 비율 유지 축소
                width, height = img.size
                if width > max_width:
                    new_height = int(height * (max_width / width))
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                # 결과물 저장 (JPG 포맷 통일 및 최적화)
                save_file = out_path / f"{file.stem}_opt.jpg"
                img.save(save_file, "JPEG", quality=quality, optimize=True)
                print(f"완료: {file.name} -> {save_file.name} ({img.size[0]}x{img.size[1]})")

        except Exception as e:
            print(f"실패 ({file.name}): {e}")

if __name__ == "__main__":
    batch_optimize_images(
        input_dir="./raw_images",
        output_dir="./optimized_images",
        max_width=860,
        quality=85
    )