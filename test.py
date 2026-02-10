import requests


URL = "https://picazor.com/pt/kira-pregiato-1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": "https://picazor.com/",
    "Connection": "keep-alive",
}


def main():
    print("Enviando requisição...\n")

    response = requests.get(URL, headers=HEADERS)

    print("Status Code:", response.status_code)
    print("-" * 50)

    print("Primeiros 1000 caracteres da resposta:\n")
    print(response.text[:1000])

    print("\n" + "-" * 50)

    if response.status_code == 403:
        print("🚨 Está sendo bloqueado (403 Forbidden)")
    elif "Attention Required" in response.text:
        print("🚨 Possível bloqueio Cloudflare detectado")
    elif response.status_code == 200:
        print("✅ Página carregada com sucesso!")
    else:
        print("⚠️ Resposta inesperada")


if __name__ == "__main__":
    main()
