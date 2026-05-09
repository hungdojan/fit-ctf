# Upload SSH key

SSH is a encrypted network protocol designed for operating network services over unsecure networks.
Most popular usages of SSH protocol are login and command-line execution on a remote machine/server.

Most CTF projects will require you to log into a remote login node using SSH. There two primary ways to
authenticate against the server: either with your **login credentials** (username + password) or using a pair
of **asymmetric cryptographic keys**.

This page describes a set of instruction on the **Linux** system on how to create a pair of
key and how to upload it to the server,


## Prerequisites
Firstly, make sure that your system has **OpenSSH client** software installed. Run the following command
to see, if it print a help/usage.

```sh
ssh
```

If you get error `command not found: ssh` that means that you system does not have OpenSSH installed.
Depending on your system, download the OpenSSH client.

```sh
# Ubuntu/Debian
sudo apt update
sudo apt install openssh-client

# Fedora
sudo dnf install openssh-clients

# Arch
sudo pacman -S openssh
```

## Generate keys
We use utility `ssh-keygen` for generating a pair of SSH keys. More information can be found
here: https://www.ssh.com/academy/ssh/keygen. This tutorial uses a new algorithm ED25519.

```sh
ssh-keygen -t ed25519 -c "your@email.com"
# will prompt a key filename, can be empty
# will prompt for a passphrase (aka a new password), can be empty
```

If you have not specify the key file location, 2 new files should be created in `$HOME/.ssh/id_ed25519*`.
File with `*.pub` suffix is a **public key** and can be shared with anyone.
The second file is a **private key** and **MUST NOT BE SHARED WITH ANYONE**.

## Upload key
There are two-way how to upload the **public key** to the server for authentication. Either use
utility `ssh-copy-id` to copy it to server, you will be prompted to log in to your server using your existing credentials.
Validate that the key was successfully uploaded by login to the login node. It should not ask you for you password.
Note that your instance **MUST BE RUNNING** when you run `ssh-copy-id` command.

```sh
ssh-copy-id -i <path_to_private_key> -p <port> <user>@<server>
# should ask for password
ssh -p <port> <user>@<server>
# should not ask for password
```

Other option is to copy a **public key** content and paste it in the input field *Public key* and
click the button *Upload Key*. If you get a green notification that means that the key was successfully uploaded.
