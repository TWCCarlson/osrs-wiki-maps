package wiki.runescape.oldschool.maps;

import net.runelite.cache.definitions.MapSquareDefinition;
import net.runelite.cache.definitions.ZoneDefinition;
import net.runelite.cache.region.Position;

import java.util.HashSet;
import java.util.Set;

public class WikiWorldMapDefinition {
    int fileId;
    String name;
    Position position;
    Set<MapSquareDefinition> mapSquareDefinitions;
    Set<ZoneDefinition> zoneDefinitions;

    public WikiWorldMapDefinition(int fileId, String name, Position position, Set<MapSquareDefinition> mapSquareDefinitions, Set<ZoneDefinition> zoneDefinitions) {
        this.fileId = fileId;
        this.name = name;
        this.position = position;
        this.mapSquareDefinitions = mapSquareDefinitions;
        this.zoneDefinitions = zoneDefinitions;
    }
}
