from argparse import ArgumentParser
from pathlib import Path

from PIL import Image


PACKAGE_SIZES = {
    "StoreLogo.png": (50, 50),
    "Square44x44Logo.png": (44, 44),
    "Square150x150Logo.png": (150, 150),
    "Square310x310Logo.png": (310, 310),
    "Wide310x150Logo.png": (310, 150),
}


def render_logo(source: Image.Image, size: tuple[int, int]) -> Image.Image:
    width, height = size
    margin = max(2, round(min(width, height) * 0.08))
    available = (width - (margin * 2), height - (margin * 2))
    logo = source.copy()
    logo.thumbnail(available, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    position = ((width - logo.width) // 2, (height - logo.height) // 2)
    canvas.alpha_composite(logo, position)
    return canvas


def main() -> None:
    parser = ArgumentParser(description="Generate Microsoft Store PNG assets.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--package-output", required=True, type=Path)
    parser.add_argument("--listing-output", required=True, type=Path)
    args = parser.parse_args()

    args.package_output.mkdir(parents=True, exist_ok=True)
    args.listing_output.mkdir(parents=True, exist_ok=True)
    with Image.open(args.source) as image:
        source = image.convert("RGBA")
        for filename, size in PACKAGE_SIZES.items():
            render_logo(source, size).save(args.package_output / filename, optimize=True)
        render_logo(source, (300, 300)).save(
            args.listing_output / "DevSnapshot-StoreLogo-300x300.png",
            optimize=True,
        )


if __name__ == "__main__":
    main()
