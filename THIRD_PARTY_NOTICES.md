# Third-party software notices

AstroAI uses the following software in its astrology-calculation runtime. This file records the source locations and license routes relevant to the deployed application. Preserve upstream copyright and license notices when redistributing these components.

## Swiss Ephemeris

Swiss Ephemeris is a third-party astronomy library and ephemeris-data set under a dual-licensing model. AstroAI elects the AGPL route for its use of Swiss Ephemeris. The upstream copyright and licensing notice is preserved verbatim in [`THIRD_PARTY_LICENSES/Swiss-Ephemeris-LICENSE.txt`](THIRD_PARTY_LICENSES/Swiss-Ephemeris-LICENSE.txt).

- Official project and source repository: <https://github.com/aloistr/swisseph>
- Official licensing information: <https://www.astro.com/swisseph/swephinfo_e.htm>
- Official code/data download information: <https://www.astro.com/swisseph/swedownload_e.htm>
- Ephemeris data source directory: <https://github.com/aloistr/swisseph/tree/master/ephe>

Preserve the upstream notice with redistributed Swiss Ephemeris components. No endorsement of AstroAI is implied.

## swisseph-ffi Python runtime binding

AstroAI pins `swisseph-ffi==1.0.0`. The package metadata declares `AGPL-3.0-or-later` and the distribution includes platform-specific Swiss Ephemeris shared libraries.

- Published package: <https://pypi.org/project/swisseph-ffi/1.0.0/>
- Source repository at the publishing commit recorded by the PyPI provenance attestation: <https://github.com/jayeshmepani777/Swiss-Ephemeris-Python/tree/6c4ec75308070cb2b95a2b5a78d68b85cbf2b179>
- Source distribution: linked from the PyPI release page above.

The source distribution and source repository are part of the source materials needed to build the FFI wrapper. The Swiss Ephemeris C library and ephemeris data remain subject to the Swiss Ephemeris licensing terms described above.
