import discord


def construire_embed(section: dict) -> discord.Embed:
    """Construit un embed à partir d'une section du config.yaml."""
    couleur = discord.Color.blurple()  # couleur par défaut
    if section.get("couleur"):
        try:
            couleur = discord.Color.from_str(str(section["couleur"]))
        except ValueError:
            print(f"[EMBED] couleur invalide : {section['couleur']}")

    embed = discord.Embed(
        title=section.get("titre"),
        description=section.get("description"),
        color=couleur,
    )

    if section.get("miniature"):
        embed.set_thumbnail(url=section["miniature"])
    if section.get("image"):
        embed.set_image(url=section["image"])

    for champ in section.get("champs", []):
        nom, valeur = champ.get("nom"), champ.get("valeur")
        if not nom or not valeur:  # on saute un champ incomplet
            continue
        embed.add_field(name=str(nom), value=str(valeur), inline=champ.get("inline", True))

    return embed