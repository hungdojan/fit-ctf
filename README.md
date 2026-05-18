# CTF Framework at FIT BUT

Container-oriented CTF framework built on Podman. **fit-ctf** is the operator CLI (projects, users, scenarios, clusters). **fit-rendezvous** is the participant TUI for login and managing personal instances.

## Requirements

- Python 3.10+
- [Poetry](https://python-poetry.org/)
- Podman and [podman-compose](https://github.com/containers/podman-compose) (`inv db-start` and challenge containers)

## Installation

```sh
git clone https://github.com/hungdojan/fit-ctf.git
cd fit-ctf
poetry install --only main
```

Generate `.env` and start the database with [Invoke](https://www.pyinvoke.org/) tasks from [tasks.py](tasks.py):

```sh
poetry run inv generate-env \
    --db-username=ctf_user \
    --db-password=changeme \
    --db-name=ctf_db

poetry run inv db-start
```

Other useful tasks: `poetry run inv --list` (e.g. `db-stop`, `db-shell`, `db-deploy`, `setup-sshd`).

Run the tools via Poetry or activate the virtualenv:

```sh
poetry run fit-ctf --help
poetry run fit-rendezvous

# or
poetry shell
fit-ctf
fit-rendezvous
```

## Quickstart

Minimal local setup (scenarios and clusters are covered in the docs):

```sh
poetry run inv db-start

fit-ctf project create --project-name demo_project
fit-ctf user create -u user1 --generate-password
fit-ctf enrollment enroll -u user1 --project-name demo_project

fit-rendezvous
```

Project data defaults to `~/.local/share/fit-ctf/` unless overridden in `.env`.

## Deployment

To deploy the **full CTF architecture** (VM, networking, port forwarding, production layout), use the separate **[fit-ctf-virt](https://github.com/hungdojan/fit-ctf-virt)** repository.

For local Rendezvous SSH configuration, run `poetry run inv setup-sshd --user=... --rdz-port=... --fitctf-dirpath=...` and see the documentation below.

## Documentation

Guides (tutorial, scenarios, clusters, CLI reference, deployment details) are built with Sphinx:

```sh
cd docs/sphinx
make html
# open _build/html/index.html
```

Hosted docs: [hungdojan.github.io/fit-ctf](https://hungdojan.github.io/fit-ctf/)

## Contributing

Issues and pull requests are welcome on [GitHub](https://github.com/hungdojan/fit-ctf).
