"""Secret storage."""

import os
from typing import Optional

path = os.path

import click
from keyring import get_password, set_password

from fediplug.dirs import DIRS


SERVICE_NAME: str = "fediplug"
CREDENTIAL_CLIENT_ID: str = "client_id"
CREDENTIAL_CLIENT_SECRET: str = "client_secret"
CREDENTIAL_ACCESS_TOKEN: str = "access_token"


def build_username(instance: str, credential_kind: str) -> str:
    return credential_kind + "@" + instance


def set_credential(instance: str, credential_kind: str, credential: str) -> None:
    set_password(SERVICE_NAME, build_username(instance, credential_kind), credential)


def get_credential(instance: str, credential_kind: str) -> Optional[str]:
    return get_password(SERVICE_NAME, build_username(instance, credential_kind))


def has_credential(instance: str, credential_kind: str) -> bool:
    return get_credential(instance, credential_kind) is not None


def migrate_client_credentials(instance: str) -> None:
    def migrate_and_unlink(filename: str) -> None:
        if path.exists(filename):
            click.echo("==> Migrating client credentials to keyring from " + filename)

            with open(filename, "r", encoding="utf-8") as infile:
                client_id = infile.readline().strip()
                client_secret = infile.readline().strip()

            set_credential(instance, CREDENTIAL_CLIENT_ID, client_id)
            set_credential(instance, CREDENTIAL_CLIENT_SECRET, client_secret)

            os.unlink(filename)

    migrate_and_unlink("clientcred.secret")
    migrate_and_unlink(path.join(DIRS.user_config_dir, instance + ".clientcred.secret"))


def migrate_access_token(instance: str) -> None:
    def migrate_and_unlink(filename: str) -> None:
        if path.exists(filename):
            click.echo("==> Migrating access token to keyring from " + filename)

            with open(filename, "r", encoding="utf-8") as infile:
                access_token: str = infile.readline().strip()

            set_credential(instance, CREDENTIAL_ACCESS_TOKEN, access_token)

            os.unlink(filename)

    migrate_and_unlink("usercred.secret")
    migrate_and_unlink(path.join(DIRS.user_config_dir, instance + ".usercred.secret"))
