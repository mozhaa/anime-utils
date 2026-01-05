import tempfile
from pathlib import Path

import pytest

from anime_utils._cache import FileCache


@pytest.fixture
def temp_cache_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def file_cache(temp_cache_dir):
    return FileCache(temp_cache_dir)


@pytest.mark.asyncio
async def test_cache_set_and_get(file_cache):
    key = "source-id-qualifier"
    data = b"<html><body>Test content</body></html>"

    await file_cache.set(key, data)
    retrieved_data = await file_cache.get(key)
    assert retrieved_data == data


@pytest.mark.asyncio
async def test_cache_get_nonexistent(file_cache):
    key = "nonexistent-key-qualifier"

    result = await file_cache.get(key)
    assert result is None


@pytest.mark.asyncio
async def test_cache_file_creation(file_cache):
    key = "anidb-12345-full"
    data = b"<html><body>Anime page content</body></html>"

    await file_cache.set(key, data)

    expected_path = file_cache.cache_dir / f"{key}.html.zlib"
    assert expected_path.exists()


@pytest.mark.asyncio
async def test_cache_compression(file_cache):
    key = "source-id-qualifier"
    data = b"<html><body>" + b"x" * 1000 + b"</body></html>"

    await file_cache.set(key, data)

    cache_path = file_cache._get_cache_path(key)
    assert cache_path.exists()

    assert cache_path.stat().st_size < len(data)


@pytest.mark.asyncio
async def test_cache_overwrite(file_cache):
    key = "source-id-qualifier"
    original_data = b"<html><body>Original content</body></html>"
    new_data = b"<html><body>New content</body></html>"

    await file_cache.set(key, original_data)
    retrieved_original = await file_cache.get(key)
    assert retrieved_original == original_data

    await file_cache.set(key, new_data)
    retrieved_new = await file_cache.get(key)
    assert retrieved_new == new_data
    assert retrieved_new != original_data


@pytest.mark.asyncio
async def test_cache_invalid_characters_in_key(file_cache):
    key = "invalid-character{}here"
    original_data = b"123"

    for invalid_character in ":\\/?><*":
        with pytest.raises(ValueError):
            await file_cache.set(key.format(invalid_character), original_data)
