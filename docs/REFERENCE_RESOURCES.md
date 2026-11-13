# ORBITOPS Reference Resources

**Reviewed:** 2026-11-13

This register records external technical and educational resources supplied for the ORBITOPS roadmap. It does not claim endorsement, partnership, integration, certification, or validation by any listed agency.

## NASA and JPL

| Resource | Intended use in ORBITOPS | Boundary |
|---|---|---|
| [Design and Develop Science Missions](https://www.nasa.gov/wp-content/uploads/2025/04/250323-design-and-develop-science-mission.pdf?emrc=a454cf) | Mission lifecycle and launch/space/ground/user segment reference | Process guidance; not a software API |
| [GMAT — NASA Software Catalog](https://software.nasa.gov/software/GSC-19468-1) | Reference implementation and possible external tool interoperability study | Separate open-source software; no internal GMAT execution is claimed |
| [JPL Concept Maturity Levels paper](https://dataverse.jpl.nasa.gov/dataset.xhtml?persistentId=hdl:2014/44299) | Mission concept maturity assessment, particularly CML 1–4 | Assessment framework; not a certification label |
| [NASA Goddard Mission Design Lab](https://etd.gsfc.nasa.gov/capabilities/integrated-design-center/mission-design-lab/) | Concept development, feasibility, risk, trade studies and point-design process | Describes NASA's collaborative capability; ORBITOPS is not the NASA MDL |
| [NASA Mission Viz](https://nasa.github.io/mission-viz/) | Study of web-based orrery and mission visualisation examples | External examples; do not claim its propagator or outputs as ORBITOPS results |
| [Webb Build It Yourself](https://science.nasa.gov/mission/webb/game-build-it-yourself/) | Educational inspiration for linking science objectives to instruments | Educational game, not engineering analysis |
| [CubeSat 101](https://www3.nasa.gov/sites/default/files/atoms/files/nasa_csli_cubesat_101_508.pdf) | CubeSat development lifecycle and first-time developer reference | Guidance must be checked against current launch-provider and regulatory requirements |
| [NASA Space Apps VR mission visualisation challenge](https://www.spaceappschallenge.org/2023/challenges/visualize-a-space-mission-using-virtual-reality/) | User-experience reference for mission concept, trajectory, timeline and 3D exploration | Challenge brief, not a validated dynamics specification |

## Space agency partner learning resources

- [Canadian Space Agency — Digital Games and Activities](https://www.asc-csa.gc.ca/eng/youth-educators/digital-games-and-activities.asp): educational games, activities, e-books and learning materials.

## Non-fabrication and credibility requirements

1. Never invent telemetry, ephemerides, observations, spacecraft states, mission events, trajectories, or numerical results.
2. Clearly distinguish source data, user-entered assumptions, derived calculations, and illustrative artwork.
3. Every computed engineering result must disclose its algorithm/equation and version, units, input provenance, assumptions, limitations, and validation status.
4. Do not call a chart, animation, or static planetary illustration a simulation unless it is generated from a documented, tested model and time-tagged input/state data.
5. If data or a required solver is unavailable, show an explicit unavailable/unsupported state rather than substituting sample values.
6. Preserve source attribution, data-use restrictions, licences, and version/date metadata when importing external material.
7. NASA, JPL, CSA and other agency references do not imply endorsement, partnership, certification, or approval of ORBITOPS.

## Current implementation boundary

The existing ideal rocket-equation and constant-average-power tools are preliminary calculators/prototypes. They are not full mission simulations. The current mission catalogue is a taxonomy, not a feasibility determination. External GMAT and Mission Viz links are references only; no native integration is claimed by this register.
