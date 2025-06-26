# streaming-video-downloader
Cross-platform streaming video downloader built with Python and Kivy.

## Funcionalidades

- Download de vídeos do YouTube, TikTok e Instagram.
- Corte manual de vídeos informando o tempo de início e fim no formato `HH:MM:SS`.
- Tela de configuração para salvar a chave da API do ChatGPT.
- Geração automática de sugestões de cortes utilizando o ChatGPT a partir de uma transcrição.
- Upload automático dos cortes para YouTube, TikTok e Instagram após a geração.

## Configuração

Crie um arquivo `.env` com as seguintes variáveis:

```
OPENAI_API_KEY=<sua chave>
YOUTUBE_CLIENT_SECRETS=<caminho client_secrets.json>
INSTAGRAM_USER=<usuario>
INSTAGRAM_PASSWORD=<senha>
TIKTOK_USER=<usuario>
TIKTOK_PASSWORD=<senha>
```

Essas informações são utilizadas pelos módulos de upload em `uploader/`.
- Transcrição automática de vídeos usando o modelo `whisper` da OpenAI.

Para utilizar a transcrição automática, instale os pacotes listados em `requirements.txt`, em especial o `openai`.

## Notas

- Os cortes gerados assumem as seguintes resoluções padronizadas: YouTube 1280x720 (16:9), TikTok 720x1280 (9:16) e Instagram Stories 1080x1920 (9:16).
- Pré-visualização das sugestões com possibilidade de ajuste manual e salvamento do corte.
