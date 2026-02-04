"""Base adapter for REST APIs with pagination support.

This module provides a reusable foundation for API adapters that implement
pagination. Any backend (GitHub, GitLab, etc.) that needs to paginate through
REST API results should inherit from this class.

The pagination implementation is backend-agnostic - it works with any REST API
that follows standard pagination patterns (page number, per_page, Link headers).
"""

from typing import Any

from structlog import get_logger

logger = get_logger(__name__)


class BasePaginatedAdapter:
    """Base class for REST API adapters with pagination support.

    Provides a reusable `_paginate_request()` method that handles pagination
    for any REST API endpoint. Backends should inherit from this class to
    automatically get pagination capability.

    Subclasses must implement `_make_request()` to perform actual API calls.
    """

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make a request to the API (must be implemented by subclass).

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments (params, json, headers, etc.)

        Returns:
            Response object with .json() method and .headers dict

        Raises:
            Subclass-specific exception on error
        """
        raise NotImplementedError("Subclasses must implement _make_request()")

    def _paginate_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        per_page: int = 100,
    ) -> list[dict[str, Any]]:
        """Make a paginated request to a REST API.

        Automatically handles pagination by checking the Link header
        for next page references. Returns all items across all pages.

        This method is backend-agnostic and works with any REST API that:
        1. Supports page and per_page query parameters
        2. Returns a Link header with rel="next" for pagination
        3. Returns an empty list when no more items exist

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters (will add page and per_page)
            per_page: Items per page (backend default is usually 30-100)

        Returns:
            List of all items from all pages (flattened)

        Raises:
            Subclass-specific exceptions if any request fails
        """
        all_items = []
        page = 1
        params = params or {}

        while True:
            # Add pagination params
            page_params = {**params, "page": page, "per_page": per_page}

            response = self._make_request(method, endpoint, params=page_params)
            items_page = response.json()

            if not items_page:
                # No more items on this page
                logger.debug(
                    "pagination_complete",
                    endpoint=endpoint,
                    total_pages=page - 1,
                    total_items=len(all_items),
                )
                break

            all_items.extend(items_page)
            logger.debug(
                "pagination_page_fetched",
                endpoint=endpoint,
                page=page,
                page_count=len(items_page),
                total_so_far=len(all_items),
            )

            # Check if there are more pages by looking at the Link header
            link_header = response.headers.get("Link", "")
            if 'rel="next"' not in link_header:
                # No next page link, we're done
                logger.debug(
                    "pagination_no_next_link",
                    endpoint=endpoint,
                    final_page=page,
                    total_items=len(all_items),
                )
                break

            page += 1

        return all_items
