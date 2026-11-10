# Swiss Ephemeris data for Vercel

Place the Swiss Ephemeris `.se1` data files required by your birth-date coverage in this directory. The Vercel configuration explicitly bundles `ephe/*.se1` into the FastAPI function.

For typical modern birth dates, start with the official Swiss Ephemeris files for 1800–2399:

- `sepl_18.se1` — planetary data
- `semo_18.se1` — lunar data

Download them from the official Swiss Ephemeris source repository:

```bash
mkdir -p backend/ephe
curl -fL https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/sepl_18.se1 -o backend/ephe/sepl_18.se1
curl -fL https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/semo_18.se1 -o backend/ephe/semo_18.se1
```

The two files above cover 1800–2399 only. Add the matching `sepl_*.se1` and `semo_*.se1` pairs for other date ranges from the official distribution when you need them. Do not substitute files from unofficial mirrors. Check Astrodienst's current licensing and file notices before distributing the files.

Configure the Vercel backend project's `SWISSEPH_EPHE_PATH` environment variable as `ephe`. Relative paths are resolved against the `backend/` project root, not the process working directory. Commit the `.se1` files under `backend/ephe/`; the repository `.gitignore` now permits them in this specific directory.
