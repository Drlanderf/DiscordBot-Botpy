import discord


class RoleButton(
    discord.ui.DynamicItem[discord.ui.Button],
    template=r"role:(?P<groupe>[a-z0-9_]+):(?P<role_id>[0-9]+)",
):
    def __init__(self, groupe: str, role_id: int, label: str | None = None, emoji: str | None = None):
        super().__init__(
            discord.ui.Button(
                label=label,
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                custom_id=f"role:{groupe}:{role_id}",  # le groupe ET le rôle sont dans l'identifiant
            )
        )
        self.groupe = groupe
        self.role_id = role_id

    @classmethod
    async def from_custom_id(cls, interaction, item, match):
        # Appelé après un redémarrage : retrouve groupe et rôle à partir de "role:jeux:123..."
        return cls(match["groupe"], int(match["role_id"]))

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if role is None:
            await interaction.response.send_message("❌ Ce rôle n'existe plus.", ephemeral=True)
            return

        try:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                ajoute = False
                message = f"❌ Rôle **{role.name}** retiré."
            else:
                await interaction.user.add_roles(role)
                ajoute = True
                message = f"✅ Rôle **{role.name}** ajouté."
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Je n'ai pas la permission de gérer ce rôle.", ephemeral=True
            )
            return

        # On réécrit les boutons de CE groupe avec les compteurs à jour
        section = interaction.client.config.get("groupes_roles", self.groupe)
        if section and section.get("roles"):
            vue = construire_vue(
                interaction.guild, self.groupe, section,
                (self.role_id, interaction.user.id, ajoute),
            )
            await interaction.response.edit_message(view=vue)
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


def construire_vue(guild, groupe: str, section: dict, modif=None):
    """Construit la vue d'un groupe, avec un compteur par bouton.
    modif = (role_id, user_id, ajoute) corrige tout de suite le rôle qui vient de changer."""
    view = discord.ui.View(timeout=None)
    for jeu in section["roles"]:
        role = guild.get_role(jeu["role_id"])
        ids = {m.id for m in role.members} if role else set()

        if modif and modif[0] == jeu["role_id"]:
            _, user_id, ajoute = modif
            if ajoute:
                ids.add(user_id)
            else:
                ids.discard(user_id)

        view.add_item(RoleButton(groupe, jeu["role_id"], f"{jeu['nom']} ({len(ids)})", jeu.get("emoji")))
    return view