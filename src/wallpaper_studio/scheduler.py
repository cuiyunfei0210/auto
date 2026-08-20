from __future__ import annotations

from wallpaper_studio.models import Account, AccountBatch, NetworkSettings


def proxy_for_account_index(index: int, network: NetworkSettings) -> str | None:
    if not network.proxy_enabled or not network.proxies:
        return None
    rotate_every = max(1, network.rotate_every_accounts)
    group = index // rotate_every
    return network.proxies[group % len(network.proxies)]


def plan_account_batches(
    images: list,
    accounts: list[Account],
    network: NetworkSettings | None = None,
) -> list[AccountBatch]:
    """Assign images to accounts in order: finish one account, then the next."""
    remaining = list(images)
    batches: list[AccountBatch] = []
    network = network or NetworkSettings()
    for index, account in enumerate(accounts):
        if not remaining:
            break
        take = remaining[: account.upload_count]
        remaining = remaining[account.upload_count :]
        batches.append(
            AccountBatch(
                account=account,
                images=take,
                proxy=proxy_for_account_index(index, network),
            )
        )
    return batches
