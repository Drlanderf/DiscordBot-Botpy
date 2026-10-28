def formater_membres(nombre: int) -> str:
    """842 -> "842", 1100 -> "1,1k", 12345 -> "12,3k", 1500000 -> "1,5M"."""
    if nombre < 1000:
        return str(nombre)

    if nombre < 1_000_000:
        valeur = (nombre // 100) / 10          # 1 décimale, tronquée : 12345 -> 12.3
        suffixe = "k"
    else:
        valeur = (nombre // 100_000) / 10      # 1 500 000 -> 1.5
        suffixe = "M"

    texte = f"{valeur:.1f}".replace(".", ",")  # virgule à la française

    if texte.endswith(",0"):                   # "10,0" -> "10"
        texte = texte[:-2]

    return texte + suffixe