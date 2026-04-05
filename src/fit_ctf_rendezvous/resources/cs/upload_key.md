# Nahrání SSH klíče

SSH je šifrovaný síťový protokol určený ke vzdálené správě služeb přes nezabezpečené sítě.
Nejčastěji se používá k přihlášení a spouštění příkazů na vzdáleném počítači nebo serveru.

Většina CTF projektů vyžaduje přihlášení na vzdálený přihlašovací uzel přes SSH. Obvykle existují
dva způsoby ověření: **přihlašovací údaje** (uživatelské jméno a heslo) nebo pár
**asymetrických kryptografických klíčů**.

Tato stránka popisuje na systému **Linux**, jak vytvořit pár klíčů a jak **veřejný klíč**
nahrát na server.

## Požadavky
Nejprve ověřte, že máte nainstalovaného klienta **OpenSSH**. Spusťte příkaz:

```sh
ssh
```

Pokud se zobrazí chyba `command not found: ssh`, OpenSSH nemáte nainstalované.
Podle distribuce nainstalujte balíček s OpenSSH klientem.

```sh
# Ubuntu/Debian
sudo apt update
sudo apt install openssh-client

# Fedora
sudo dnf install openssh-clients

# Arch
sudo pacman -S openssh
```

## Generování klíčů
K vytvoření páru klíčů slouží nástroj `ssh-keygen`. Další informace např. na
[ssh.com academy](https://www.ssh.com/academy/ssh/keygen). Zde používáme algoritmus ED25519.

```sh
ssh-keygen -t ed25519 -C "vas@email.cz"
# zobrazí výzvu k názvu souboru klíče, může zůstat prázdné
# zobrazí výzvu k passphrase (heslu ke klíči), může zůstat prázdné
```

Pokud jste nezměnili cestu, měly by vzniknout soubory v `$HOME/.ssh/id_ed25519*`.
Soubor s příponou `*.pub` je **veřejný klíč** – lze ho sdílet.
Druhý soubor je **soukromý klíč** a **NESMÍTE HO NIKOMU PŘEDÁVAT**.

## Nahrání klíče
**Veřejný klíč** na server dostanete dvěma způsoby. Buď použijte `ssh-copy-id`,
který klíč zkopíruje na server (budete se muset přihlásit stávajícími údaji).
Ověřte přihlášení na přihlašovací uzel – nemělo by se ptát na heslo.
Instance **MUSÍ BĚŽET**, když příkaz `ssh-copy-id` spouštíte.

```sh
ssh-copy-id -i <cesta_k_soukromemu_klici> -p <port> <user>@<server>
# zeptá se na heslo
ssh -p <port> <user>@<server>
# už by se nemělo ptát na heslo
```

Nebo zkopírujte obsah **veřejného klíče** a vložte ho do pole *Veřejný klíč* a
klikněte na **Nahrát klíč**. Zelené oznámení znamená úspěšné nahrání.
