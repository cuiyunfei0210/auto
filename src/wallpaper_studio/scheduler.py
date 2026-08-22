from __future__ import annotations

from pathlib import Path

from wallpaper_studio.models import Account, AccountBatch, NetworkSettings, PreparedImage


class ProxyAssignmentError(ValueError):
    """Raised when unique-IP mode cannot give each account its own exit."""


def normalize_proxy(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def proxy_for_account_index(index: int, network: NetworkSettings) -> str | None:
    """Legacy pooled rotation. Used only when unique_ip_per_account is off."""
    if not network.proxy_enabled or not network.proxies:
        return None
    rotate_every = max(1, network.rotate_every_accounts)
    group = index // rotate_every
    return network.proxies[group % len(network.proxies)]


def assign_proxy(
    account: Account,
    index: int,
    network: NetworkSettings,
    used: set[str],
) -> str | None:
    if not network.proxy_enabled:
        return None

    chosen = normalize_proxy(account.proxy)
    if chosen is None:
        if network.unique_ip_per_account:
            for candidate in network.proxies:
                candidate = candidate.strip()
                if candidate and candidate not in used:
                    chosen = candidate
                    break
            if chosen is None:
                raise ProxyAssignmentError(
                    f"账号 {account.username} 没有独立出口。"
                    "请为每个账号准备一个不同的代理，或在该账号行里单独填写。"
                )
        else:
            chosen = normalize_proxy(proxy_for_account_index(index, network))

    if network.unique_ip_per_account and chosen:
        if chosen in used:
            raise ProxyAssignmentError(
                f"账号 {account.username} 与其他账号共用了同一出口：{chosen}"
            )
        used.add(chosen)
    return chosen


def preview_proxy_assignments(
    accounts: list[Account],
    network: NetworkSettings | None = None,
) -> list[dict[str, str | None]]:
    network = network or NetworkSettings()
    used: set[str] = set()
    rows: list[dict[str, str | None]] = []
    for index, account in enumerate(accounts):
        rows.append(
            {
                "username": account.username,
                "proxy": assign_proxy(account, index, network, used),
            }
        )
    return rows


def plan_account_batches(
    images: list,
    accounts: list[Account],
    network: NetworkSettings | None = None,
) -> list[AccountBatch]:
    """Assign images to accounts in order: finish one account, then the next."""
    remaining = [_as_prepared(item) for item in images]
    batches: list[AccountBatch] = []
    network = network or NetworkSettings()
    used: set[str] = set()
    for index, account in enumerate(accounts):
        if not remaining:
            break
        take = remaining[: account.upload_count]
        remaining = remaining[account.upload_count :]
        batches.append(
            AccountBatch(
                account=account,
                images=take,
                proxy=assign_proxy(account, index, network, used),
            )
        )
    return batches


def _as_prepared(item: object) -> PreparedImage:
    if isinstance(item, PreparedImage):
        return item
    path = item if isinstance(item, Path) else Path(str(item))
    return PreparedImage(path=path, title=path.stem)
