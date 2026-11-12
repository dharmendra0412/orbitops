"""Destination and mission-archetype catalogue for the multi-planetary scope."""
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class PlanetId(StrEnum):
    MERCURY = "mercury"
    VENUS = "venus"
    EARTH = "earth"
    MARS = "mars"
    JUPITER = "jupiter"
    SATURN = "saturn"
    URANUS = "uranus"
    NEPTUNE = "neptune"


class MissionArchetype(StrEnum):
    FLYBY = "flyby"
    ORBITER = "orbiter"
    ATMOSPHERIC_PROBE = "atmospheric_probe"
    ENTRY_DESCENT_LANDING = "entry_descent_landing"
    LANDER = "lander"
    ROVER = "rover"
    SAMPLE_RETURN = "sample_return"


class PlanetDestination(BaseModel):
    model_config = ConfigDict(frozen=True)

    planet_id: PlanetId
    display_name: str
    planetary_class: str
    mission_archetypes: tuple[MissionArchetype, ...]
    feasibility_status: str = "not_assessed"


class MissionArchetypeInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    archetype: MissionArchetype
    display_name: str
    description: str


class MissionCatalogResponse(BaseModel):
    scope: str
    destinations: tuple[PlanetDestination, ...]
    mission_archetypes: tuple[MissionArchetypeInfo, ...]
    exclusions: tuple[str, ...]


MISSION_ARCHETYPES = (
    MissionArchetypeInfo(archetype=MissionArchetype.FLYBY, display_name="Flyby", description="A spacecraft passes a target body without entering orbit."),
    MissionArchetypeInfo(archetype=MissionArchetype.ORBITER, display_name="Orbiter", description="A spacecraft enters and operates in orbit around a target body."),
    MissionArchetypeInfo(archetype=MissionArchetype.ATMOSPHERIC_PROBE, display_name="Atmospheric probe", description="A probe samples atmospheric properties during descent or flight."),
    MissionArchetypeInfo(archetype=MissionArchetype.ENTRY_DESCENT_LANDING, display_name="Entry, descent and landing", description="A mission architecture for atmospheric or airless-body arrival and landing analysis."),
    MissionArchetypeInfo(archetype=MissionArchetype.LANDER, display_name="Lander", description="A stationary surface spacecraft; feasibility depends on the destination environment."),
    MissionArchetypeInfo(archetype=MissionArchetype.ROVER, display_name="Rover", description="A mobile surface mission; requires a solid surface and validated mobility constraints."),
    MissionArchetypeInfo(archetype=MissionArchetype.SAMPLE_RETURN, display_name="Sample return", description="A mission that collects material and returns it to a designated destination."),
)

_PLANETS = (
    ("mercury", "Mercury", "terrestrial"),
    ("venus", "Venus", "terrestrial"),
    ("earth", "Earth", "terrestrial"),
    ("mars", "Mars", "terrestrial"),
    ("jupiter", "Jupiter", "gas_giant"),
    ("saturn", "Saturn", "gas_giant"),
    ("uranus", "Uranus", "ice_giant"),
    ("neptune", "Neptune", "ice_giant"),
)

DESTINATIONS = tuple(
    PlanetDestination(
        planet_id=PlanetId(planet_id),
        display_name=display_name,
        planetary_class=planetary_class,
        mission_archetypes=tuple(item.archetype for item in MISSION_ARCHETYPES),
    )
    for planet_id, display_name, planetary_class in _PLANETS
)


def get_mission_catalog() -> MissionCatalogResponse:
    """Return the destination taxonomy without asserting mission feasibility."""
    return MissionCatalogResponse(
        scope="eight_planets",
        destinations=DESTINATIONS,
        mission_archetypes=MISSION_ARCHETYPES,
        exclusions=(
            "Natural satellites (including Earth's Moon) are not yet catalogued as destinations.",
            "Dwarf planets and small bodies are not yet catalogued as destinations.",
            "Mission-archetype compatibility and physical feasibility have not been assessed.",
            "No trajectory, environment, propulsion, thermal, power, communications or landing model is implied by this catalogue.",
        ),
    )
