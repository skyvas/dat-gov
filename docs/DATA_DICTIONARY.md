# Data Dictionary

The data dictionary is generated, not hand-maintained: run the
pipeline and read [catalog.md](catalog.md).

```bash
.venv/bin/python -m dat_gov.cli catalog
```

`src/dat_gov/catalog.py` builds `docs/catalog.md` from
`governance/catalog/*.yaml` and `governance/contracts/*.yaml`,
merged with the actual Silver Parquet schemas (so the types shown
are the types in the files, not the types someone remembered).
`docs/catalog.md` and `data/lineage.json` are generated artefacts;
edit the YAML, not the output.
