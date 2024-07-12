package wiki.runescape.oldschool.maps;


import net.runelite.cache.AreaManager;
import net.runelite.cache.IndexType;
import net.runelite.cache.MapImageDumper;
import net.runelite.cache.ObjectManager;
import net.runelite.cache.SpriteManager;
import net.runelite.cache.definitions.AreaDefinition;
import net.runelite.cache.definitions.ObjectDefinition;
import net.runelite.cache.definitions.SpriteDefinition;
import net.runelite.cache.definitions.WorldMapCompositeDefinition;
import net.runelite.cache.definitions.ZoneDefinition;
import net.runelite.cache.definitions.MapSquareDefinition;
import net.runelite.cache.definitions.WorldMapDefinition;
import net.runelite.cache.definitions.loaders.WorldMapCompositeLoader;
import net.runelite.cache.definitions.loaders.WorldMapLoader;
import net.runelite.cache.fs.Archive;
import net.runelite.cache.fs.ArchiveFiles;
import net.runelite.cache.fs.FSFile;
import net.runelite.cache.fs.Index;
import net.runelite.cache.fs.Storage;
import net.runelite.cache.fs.Store;
import net.runelite.cache.region.Location;
import net.runelite.cache.region.Region;
import net.runelite.cache.region.RegionLoader;

import com.google.gson.Gson;
import net.runelite.cache.util.XteaKeyManager;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.FileInputStream;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.HashMap;
import java.util.Map;
import java.util.List;

public class MapExport {
    private static RegionLoader regionLoader;
    private static String version = "2024-05-29_0_a";
    public static void main(String[] args) throws Exception {
        version = args.length > 0 ? args[0] : version;
        Gson gson = new Gson();
        String cache = String.format("./out/mapgen/versions/%s/cache", version);
        String xteas = String.format("./out/mapgen/versions/%s/xteas.json", version);
        Store store = new Store(new File(cache));
        store.load();

        XteaKeyManager xteaKeyManager = new XteaKeyManager();
        try (FileInputStream fin = new FileInputStream(xteas))
        {
            xteaKeyManager.loadKeys(fin);
        }

        regionLoader = new RegionLoader(store, xteaKeyManager);
        regionLoader.loadRegions();

        MapImageDumper dumper = new MapImageDumper(store, regionLoader);
        dumper.setRenderIcons(false);
        dumper.setLowMemory(false);
        dumper.setRenderLabels(false);
        dumper.load();

        // Draw the planes
        for (int plane = 0; plane < 4; plane++) {
            BufferedImage image = dumper.drawMap(plane);
            String dirname = String.format("./out/mapgen/versions/%s/fullplanes/base", version);
            String filename = String.format("plane_%s.png", plane);
            File outputfile = fileWithDirectoryAssurance(dirname, filename);
            System.out.println(outputfile);
            ImageIO.write(image, "png", outputfile);
        }

        // Dump icon data and images
        String dirname = String.format("./out/mapgen/versions/%s", version);
        String filename = "minimapIcons.json";
        File outputfile = fileWithDirectoryAssurance(dirname, filename);
        PrintWriter out = new PrintWriter(outputfile);
        List<MinimapIcon> icons = getMapIcons(store);
        String json = gson.toJson(icons);
        out.write(json);
        out.close();

        // Generate the world map definitions
        filename = "wikiWorldMapDefinitions.json";
        outputfile = fileWithDirectoryAssurance(dirname, filename);
        out = new PrintWriter(outputfile);
        List<WikiWorldMapDefinition> wwmds = getWikiWorldMapDefinitions(store);
        json = gson.toJson(wwmds);
        out.write(json);
        out.close();

        // Output the highest and lowest X and Y values drawn on the plane for coordinate transforms
        regionLoader.calculateBounds();
        dirname = String.format("./", version);
        filename = "coordinateData.json";
        outputfile = fileWithDirectoryAssurance(dirname, filename);
        out = new PrintWriter(outputfile);
        Map<String, Integer> coords = createCoordDataJSON();
        json = gson.toJson(coords);
        out.write(json);
        out.close();
    }

    private static Map<String, Integer> createCoordDataJSON() {
        Map<String, Integer> coords = new HashMap<>();
        coords.put("minTileX", regionLoader.getLowestX().getBaseX());
        coords.put("minSquareX", regionLoader.getLowestX().getRegionX());
        coords.put("minTileY", regionLoader.getLowestY().getBaseY());
        coords.put("minSquareY", regionLoader.getLowestY().getRegionY());
        coords.put("maxTileX", regionLoader.getHighestX().getBaseX());
        coords.put("maxSquareX", regionLoader.getHighestX().getRegionX());
        coords.put("maxTileY", regionLoader.getHighestY().getBaseY());
        coords.put("maxSquareY", regionLoader.getHighestY().getRegionY());
        coords.put("tilePixelLength", 4);
        coords.put("squareTileLength", 64);
        coords.put("squarePixelLength", 256);
        coords.put("squareZoneLength", 8);
        coords.put("zonePixelLength", 32);
        coords.put("zoneTileLength", 8);
        return coords;
    }

    private static List<WikiWorldMapDefinition> getWikiWorldMapDefinitions(Store store) throws Exception {
        Index index = store.getIndex(IndexType.WORLDMAP);
        Storage storage = store.getStorage();

        Archive archiveDetails = index.findArchiveByName("details");
        Archive archiveCompMap = index.findArchiveByName("compositemap");

        byte[] archiveDataDetails = storage.loadArchive(archiveDetails);
        byte[] archiveDataCompMap = storage.loadArchive(archiveCompMap);

        ArchiveFiles filesDetails = archiveDetails.getFiles(archiveDataDetails);
        ArchiveFiles filesCompMap = archiveCompMap.getFiles(archiveDataCompMap);

        WorldMapLoader worldMapLoader =  new WorldMapLoader();
        WorldMapCompositeLoader worldMapCompositeLoader = new WorldMapCompositeLoader();

        List<WikiWorldMapDefinition> definitions = new ArrayList<>();
        for (FSFile file : filesDetails.getFiles()) {
            int fileId = file.getFileId();
            WorldMapDefinition wmd = worldMapLoader.load(file.getContents(), fileId);
            WorldMapCompositeDefinition wmcd = worldMapCompositeLoader.load(
                    filesCompMap.findFile(fileId).getContents()
            );

            WikiWorldMapDefinition wwmd = new WikiWorldMapDefinition(
                    wmd.getFileId(),
                    wmd.getName(),
                    wmd.getPosition(),
                    wmcd.getMapSquareDefinitions(),
                    wmcd.getZoneDefinitions()
            );
            definitions.add(wwmd);
        }
        return definitions;
    }

    private static File fileWithDirectoryAssurance(String directory, String filename) {
        File dir = new File(directory);
        if (!dir.exists()) dir.mkdirs();
        return new File(directory + "/" + filename);
    }

    private static List<MinimapIcon> getMapIcons(Store store) throws Exception {
        List<MinimapIcon> icons = new ArrayList<MinimapIcon>();
        SpriteManager spriteManager = new SpriteManager(store);
        spriteManager.load();
        HashSet<Integer> spriteIds = new HashSet<Integer>();
        ObjectManager objectManager = new ObjectManager(store);
        objectManager.load();
        AreaManager areaManager = new AreaManager(store);
        areaManager.load();
        for (Region region : regionLoader.getRegions()) {
            for (Location location : region.getLocations()) {
                ObjectDefinition od = objectManager.getObject(location.getId());

                if (od.getMapAreaId() != -1) {
                    AreaDefinition area = areaManager.getArea(od.getMapAreaId());
                    icons.add(new MinimapIcon(location.getPosition(), area.spriteId));
                    spriteIds.add(area.spriteId);
                }
            }
        }

        for (int spriteId : spriteIds) {
            SpriteDefinition sprite = spriteManager.findSprite(spriteId, 0);
            BufferedImage iconImage = spriteManager.getSpriteImage(sprite);
            String dirname = String.format("./out/mapgen/versions/%s/icons", version);
            String filename = String.format("%s.png", spriteId);
            File outputfile = fileWithDirectoryAssurance(dirname, filename);
            System.out.println(outputfile);
            ImageIO.write(iconImage, "png", outputfile);
        }
        return icons;
    }
}