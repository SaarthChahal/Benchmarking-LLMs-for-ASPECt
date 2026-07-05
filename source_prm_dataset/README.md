# Source PRM Dataset

This folder contains the real baseline `.prm` inputs used by the refactored `F1` study.

The study now assumes:

1. start from a real source ASPECT `.prm`
2. reverse-engineer it into a prompt
3. regenerate a new `.prm`
4. compare source `.prm` vs regenerated `.prm`
5. optionally compare actual ASPECT run behavior

## Source Pools

Two pools are available:

- `files/`
  Cookbook-focused copied `.prm` set.

- `all_files/`
  Much larger official ASPECT `.prm` pool gathered from cookbooks, benchmarks, and tests.

## Catalogs

Use:

- `catalog.csv`
- `catalog_full.csv`

Main columns:

- `prompt_id`
- `source_type`
- `category`
- `source_hint`
- `file_path`
- `relative_path`
- `original_source`

## Notes

- `catalog.csv` is the smaller cookbook-facing set.
- `catalog_full.csv` is broader and includes many benchmark and test inputs.
- The larger pool is useful for breadth, but not all entries are equally suitable as cheap, research-style benchmark cases.
- Some files may depend on external assets or may be slow to run, so this dataset is a source pool, not yet a curated guaranteed-runnable subset.
