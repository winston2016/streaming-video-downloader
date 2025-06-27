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
# Opcional: cookies para baixar vídeos privados do TikTok
TIKTOK_COOKIES_FILE=<caminho para cookies.txt>
TIKTOK_COOKIES_BROWSER=<navegador ou navegador:perfil>
```

Defina `TIKTOK_COOKIES_FILE` ou `TIKTOK_COOKIES_BROWSER` caso o TikTok
exija autenticação para baixar o vídeo.

Essas informações são utilizadas pelos módulos de upload em `uploader/`.
- Defina `VIDEO_HWACCEL=1` para habilitar exportação de vídeos utilizando um
  codec de hardware (ex.: `h264_nvenc`). É necessário ter o FFmpeg compilado
  com suporte à aceleração da GPU utilizada.
- Transcrição automática agora utiliza a versão open-source do modelo `whisper`.

Para utilizar a transcrição automática, instale os pacotes listados em `requirements.txt`, em especial o `openai-whisper`.

## Notas

- Os cortes gerados assumem as seguintes resoluções padronizadas: YouTube 1280x720 (16:9), TikTok 720x1280 (9:16) e Instagram Stories 1080x1920 (9:16).
- Pré-visualização das sugestões com possibilidade de ajuste manual e salvamento do corte.
- Para usar `VIDEO_HWACCEL`, o FFmpeg deve ser compilado com o codec
  de aceleração correspondente (ex.: suporte ao NVENC para `h264_nvenc`).

## Desempenho de codificação de vídeo

Os scripts utilizam o MoviePy para gerar os cortes. Por padrão o MoviePy
emprega codecs de CPU fornecidos pelo FFmpeg, o que pode tornar a exportação
mais lenta. Caso a sua instalação do FFmpeg tenha sido compilada com suporte a
NVENC, VAAPI ou tecnologias similares, é possível habilitar a codificação via
GPU definindo a variável de ambiente `VIDEO_HWACCEL=1` antes da execução.

```bash
export VIDEO_HWACCEL=1
python cortarvideo.py
```

Sem esse flag os vídeos continuam sendo processados somente pela CPU.
