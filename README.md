# CacheLib

A collection of cache libraries in the same API interface. Extracted from
Werkzeug.

## Pallets Ecosystem

> [!IMPORTANT]\
> This project is part of the Pallets Ecosystem. Pallets is the open source
> organization that maintains Flask; Pallets-Eco enables community maintenance
> of related projects. If you are interested in helping maintain this project,
> please reach out on [the Pallets Discord server][discord].

[discord]: https://discord.gg/pallets

## Installation

Install from [PyPI]:

```sh
pip install cachelib
```

[PyPI]: https://pypi.org/project/cachelib/

## A Minimal Example

```python
from cachelib import SimpleCache

# Create a cache instance
cache = SimpleCache()

# Set a value in the cache
cache.set('my_key', 'my_value')

# Retrieve the value from the cache
value = cache.get('my_key')
print(value)  # Output: my_value

# Delete the value from the cache
cache.delete('my_key')

# Try to retrieve the deleted value
value = cache.get('my_key')
print(value)  # Output: None
```
