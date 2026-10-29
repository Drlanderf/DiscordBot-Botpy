import discord


def construire_embed_log(
    titre: str,
    couleur: discord.Color,
    membre: discord.Member,
    salon,
    texte: str,
    nb_pieces_jointes: int,
    resultat: str,
) -> discord.Embed:
    embed = discord.Embed(title=titre, color=couleur, timestamp=discord.utils.utcnow())
    embed.set_author(name=str(membre), icon_url=membre.display_avatar.url)
    embed.set_thumbnail(url=membre.display_avatar.url)

    embed.add_field(name="Membre", value=f"{membre.mention} (`{membre.id}`)", inline=True)
    embed.add_field(name="Salon", value=salon.mention, inline=True)
    embed.add_field(name="Résultat", value=resultat, inline=False)

    # L'ancienneté du compte aide à repérer les comptes jetables
    embed.add_field(name="Compte créé", value=discord.utils.format_dt(membre.created_at, "R"), inline=True)
    arrivee = discord.utils.format_dt(membre.joined_at, "R") if membre.joined_at else "inconnu"
    embed.add_field(name="A rejoint", value=arrivee, inline=True)

    # Le message est mis dans un bloc de code : les liens du spam ne sont ainsi ni cliquables ni aperçus
    contenu = texte.replace("```", "'''")[:900] or "(aucun texte)"
    if nb_pieces_jointes:
        contenu += f"\n[+ {nb_pieces_jointes} pièce(s) jointe(s)]"
    embed.add_field(name="Message", value=f"```\n{contenu}\n```", inline=False)

    embed.set_footer(text="Botban")
    return embed