# streaming-video-downloader
Cross-platform streaming video downloader built with Python and Kivy.

## Funcionalidades

- Download de vídeos do YouTube, TikTok e Instagram.
- Corte manual de vídeos informando o tempo de início e fim no formato `HH:MM:SS`.
- Tela de configuração para salvar a chave da API do ChatGPT.
- Geração automática de sugestões de cortes utilizando o ChatGPT a partir de uma transcrição.
- Transcrição automática de vídeos usando o modelo `whisper` da OpenAI.

Para utilizar a transcrição automática, instale os pacotes listados em `requirements.txt`, em especial o `openai`.
