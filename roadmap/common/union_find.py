"""Union-Find (Disjoint Set Union) data structure with path compression.

Provides O(α(n)) ≈ O(1) operations for union and find operations,
where α is the inverse Ackermann function (effectively constant).
"""

from typing import Any


class UnionFind:
    """Efficient disjoint set data structure with path compression and union by rank."""

    def __init__(self, items: list[Any]) -> None:
        """Initialize union-find with given items.

        Args:
            items: List of hashable items to track
        """
        self.parent: dict[Any, Any] = {item: item for item in items}
        self.rank: dict[Any, int] = dict.fromkeys(items, 0)

    def find(self, item: Any) -> Any:
        """Find the canonical representative of item's set with path compression.

        Args:
            item: Item to find representative for

        Returns:
            Canonical representative of item's set
        """
        if self.parent[item] != item:
            # Path compression: point directly to root
            self.parent[item] = self.find(self.parent[item])
        return self.parent[item]

    def union(self, item1: Any, item2: Any) -> bool:
        """Union the sets containing item1 and item2.

        Args:
            item1: First item
            item2: Second item

        Returns:
            True if union occurred, False if already in same set
        """
        root1 = self.find(item1)
        root2 = self.find(item2)

        if root1 == root2:
            return False  # Already in same set

        # Union by rank: attach smaller tree under larger
        if self.rank[root1] < self.rank[root2]:
            self.parent[root1] = root2
        elif self.rank[root1] > self.rank[root2]:
            self.parent[root2] = root1
        else:
            # Same rank: pick one and increment its rank
            self.parent[root2] = root1
            self.rank[root1] += 1

        return True

    def get_canonical(self, item: Any) -> Any:
        """Get canonical representative (alias for find)."""
        return self.find(item)

    def get_representatives(self) -> set[Any]:
        """Get all canonical representatives (roots of each set).

        Returns:
            Set of canonical representatives
        """
        return {self.find(item) for item in self.parent.keys()}

    def get_groups(self) -> dict[Any, list[Any]]:
        """Get mapping of representative -> list of items in that group.

        Returns:
            Dict mapping canonical representative to list of items
        """
        groups: dict[Any, list[Any]] = {}
        for item in self.parent.keys():
            rep = self.find(item)
            if rep not in groups:
                groups[rep] = []
            groups[rep].append(item)
        return groups
