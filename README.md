# 🕷️ Robo Spider (Telegram Scraper)

Ferramenta avançada construída com **FastAPI** e **Telethon** para extração (scraping) e adição de membros em grupos do Telegram.

![Python](https://img.shields.io/badge/Python-FastAPI-blue)
![Telethon](https://img.shields.io/badge/Telegram-Telethon-blue)
![Scraper](https://img.shields.io/badge/Bot-Spider-red)

## 🚀 Funcionalidades

*   **API REST**: Interface HTTP para controlar o bot.
*   **Extração de Membros**: Coleta ID, Username e Telefone de membros de grupos públicos/privados.
*   **Adição em Massa**: Importa membros extraídos para um grupo alvo.
*   **Gerenciamento de Sessão**: Suporta múltiplas contas/sessões.
*   **Exportação**: Gera CSV com os dados coletados.

## 🛠️ Endpoints Principais

*   `POST /process`: Inicia o processo de scraping/adição.
*   `POST /code`: Envia o código de verificação (2FA) se necessário.

## ⚙️ Configuração

1.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
2.  Obtenha suas credenciais (`api_id` e `api_hash`) em [my.telegram.org](https://my.telegram.org).
3.  Execute o servidor:
    ```bash
    uvicorn main:app --reload
    ```

## ⚠️ Aviso Legal
O uso de ferramentas de automação (userbots) pode violar os Termos de Serviço do Telegram. Use com responsabilidade e moderação para evitar banimentos de conta.

Desenvolvido por [Gleisson Santos](https://github.com/gleisson-santos).
