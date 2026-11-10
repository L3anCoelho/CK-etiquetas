"""Gera assets/icone.ico (multi-resolução) a partir do logotipo original da CK Autoshop.

Uso:  python empacotamento/gerar_icone.py
"""

from pathlib import Path

from PIL import Image, ImageFilter

RAIZ = Path(__file__).resolve().parent.parent
LOGO = RAIZ / "assets" / "logo_ck.png"
SAIDA = RAIZ / "assets" / "icone.ico"
TAMANHOS = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]


def quadrado(img: Image.Image) -> Image.Image:
    img = img.crop(img.getbbox())  # remove a margem transparente
    lado = max(img.size)
    fundo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    fundo.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2), img)
    return fundo


def main() -> None:
    base = quadrado(Image.open(LOGO).convert("RGBA"))
    imagens = []
    for t in TAMANHOS:
        im = base.resize((t, t), Image.LANCZOS)
        if t <= 48:  # reforça o contorno nos tamanhos pequenos
            im = im.filter(ImageFilter.UnsharpMask(radius=1, percent=80, threshold=2))
        imagens.append(im)
    imagens[-1].save(SAIDA, format="ICO", sizes=[(t, t) for t in TAMANHOS], append_images=imagens[:-1])
    print(f"Ícone gerado: {SAIDA} ({', '.join(map(str, TAMANHOS))} px)")


if __name__ == "__main__":
    main()
