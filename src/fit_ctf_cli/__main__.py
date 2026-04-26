import os

from dotenv import load_dotenv

from fit_ctf.components.data_parser.yaml_parser import YamlParser
from fit_ctf_cli.cli import cli


def main():
    # Skip initialization during shell completion for performance
    if "_FIT_CTF_COMPLETE" in os.environ:
        cli()
        return

    load_dotenv()

    # initialize validators
    YamlParser.init_parser()

    # start cli commands
    cli()


if __name__ == "__main__":
    main()
