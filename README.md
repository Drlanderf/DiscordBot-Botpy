<h1 align=center>🤖 Discord Bot 🤖</h1>
<h3 align="center">

![](https://komarev.com/ghpvc/?username=Drlanderf&color=lightgrey&style=social) [![Youtube](https://img.shields.io/badge/Youtube_Tech-red?/&style=social/&logo=youtube)](https://www.youtube.com/@LanderfTech) [![Youtube](https://img.shields.io/badge/Youtube_Gaming-red?/&style=social/&logo=youtube)](https://www.youtube.com/@LanderfGaming) [![Discord](https://img.shields.io/badge/Discord-5865F2?/&style=social/&logo=discord&logoColor=f5f5f5)](https://discord.gg/rqNgRkvZsq) [![twitter](https://img.shields.io/twitter/follow/LanderfCorp?&label=twitter&style=social)](https://twitter.com/intent/follow?screen_name=LanderfCorp) [![twitch](https://img.shields.io/twitch/status/doc_landerf?&style=social)](https://www.twitch.tv/doc_landerf) ![github](https://img.shields.io/github/followers/DrLanderf?&label=Follow&style=social)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/landerf0311)

[![Discord Bot RELEASE CI/CD](https://github.com/Drlanderf/DiscordBot-Botpy/actions/workflows/Discord-Bot_Release_docker-image.yml/badge.svg)](https://github.com/Drlanderf/DiscordBot-Botpy/actions/workflows/Discord-Bot_Release_docker-image.yml)
</h3>

## 🧰 Technologies & Tools used for this project
![PyCharm](https://img.shields.io/badge/pycharm-143?style=for-the-badge&logo=pycharm&logoColor=black&color=black&labelColor=yellow)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)
![GitHub](https://img.shields.io/badge/github-%23121011.svg?style=for-the-badge&logo=github&logoColor=white)
![Unraid](https://img.shields.io/badge/unraid-%23F15A2C.svg?style=for-the-badge&logo=unraid&logoColor=white)



## ⚖️ Rules of good conduct in order to contribute to the project

- Always start by work on a copy branch of release
    - Name your PR explicit (like: release.My_awsomewNewFeature) that will help me a lot.
	- Detailed changelog of what you did (using emoji please that will be more clean).
	- every PR **MUST** be tested before making a PR.

- Be sure to follow the versioning syntax already in place using gitmoji.dev

## 📝 Documentation :

- This discord bot actualy don't have wiki, it will be done later...

## ⬇️ Deploy

### Docker / Unraid

```bash
docker run -d --name botpy \
  --restart unless-stopped \
  --env-file .env \
  -v /path/to/botpy-data:/data \
  landerf/botpy:latest
```

On Unraid, map the container path `/data` to `/mnt/user/appdata/botpy/`.
On first start, the bot creates `/data/config.yaml` from `config.example.yaml`.
Edit that file, then use `/reload` in Discord (no restart needed).
The SQLite database (`bot.db`) is stored in the same folder.

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `DISCORD_TOKEN` | ✅ | Bot token |
| `GUILD_ID` | | Server ID: slash commands sync instantly (dev) |
| `DATA_DIR` | | Data folder (`/data` in Docker) |
| `TWITCH_CLIENT_ID` / `TWITCH_CLIENT_SECRET` | | Twitch live notifications |
| `YOUTUBE_API_KEY` | | YouTube notifications |
| `BOT_VERSION` / `BOT_COMMIT` | | Set by the CI, shown by `/status` |

### Discord setup

- Enable the privileged intents in the Developer Portal (the bot currently uses `Intents.all()`).
- Invite the bot with the `bot` and `applications.commands` scopes.
- Permissions: Manage Roles, Ban Members, Manage Channels, Manage Messages, View Channels, Send Messages, Embed Links.
- The bot's role must be **above** the roles it manages.

### Run locally

```bash
python -m venv .venv
pip install -r requirements.txt
cp .env.example .env   # then fill it in
python bot.py
```

Python 3.12 is recommended (same as the Dockerfile).

## 🕹️ Commands

| Command | Description |
|---|---|
| `/ping` | Check that the bot responds |
| `/say` | Send a message as the bot (form) |
| `/reload` | Reload `config.yaml` and refresh sent embeds |
| `/reseaux` | Send the social networks embed |
| `/roles <group>` | Send a role picker (buttons) |
| `/botban` | Send the honeypot warning |
| `/status` | Version, latency, notification status |
| `/debug_twitch`, `/debug_youtube`, `/debug_botban` | Test notifications without going live |

All commands except `/ping` are admin-only.

## 🗺️ RoadMap :
- [X] Twitch Notification
- [X] Youtube Notification
- [X] Honeypot channel (botban)
- [X] Bot Status command (/status)
- [X] Talk as bot command (/say)
- [X] Reloading configuration (/reload)
- [X] Member counter
- [X] Role Picker with dynamic update (/roles)
- [X] Logging for few element (more element in the future)
- [ ] Basic moderation command (ban/kick/clear/timeout)
- [ ] Easter Egg ?
- [ ] Make a Wiki
- [ ] Ticket Management
- [ ] Twitter Notification
- [ ] TikTok Notification
- [ ] Instagram Notification (?)
- [ ] Embed Command
- [ ] Rules in embed
- [ ] Join/Leave Logging
- [ ] Giveway managment
- [ ] Survey managment



---

<h3 align="center">
  <a href="https://polyformproject.org/licenses/noncommercial/1.0.0/">
    <img
      alt="Licence PolyForm Noncommercial"
      style="border-width:0"
      src="https://img.shields.io/badge/License-PolyForm%20Noncommercial-blue.svg"
    />
  </a>
  <br />
  This project is made available under the terms of the
  <a href="https://polyformproject.org/licenses/noncommercial/1.0.0/">
    Licence PolyForm Noncommercial 1.0.0
  </a>.
</h3>
