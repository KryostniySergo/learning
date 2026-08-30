from uuid import UUID


def build_root_path(node_id: UUID) -> str:
    """Строит path для корневого узла оргструктуры (без родителя).

    Args:
        node_id (UUID): id самого узла.

    Returns:
        str: ltree-путь вида 'n_<node_hex>'.
    """
    return f"n_{node_id.hex}"


def build_child_path(parent_path: str, node_id: UUID) -> str:
    """Строит path для дочернего узла, добавляя сегмент к родительскому пути.

    Args:
        parent_path (str): ltree-путь родительского узла.
        node_id (UUID): id создаваемого дочернего узла.

    Returns:
        str: ltree-путь вида '<parent_path>.n_<node_hex>'.
    """
    return f"{parent_path}.n_{node_id.hex}"
