"""Unit tests for extract, with mocked HTTP.

To prove:
- paging stops on a short page
- offsets advance by page_size
- an HTTP error is raised, not swallowed
"""
