package wiki.runescape.oldschool.maps;


import net.runelite.cache.*;
import net.runelite.cache.definitions.WorldMapCompositeDefinition;
import net.runelite.cache.definitions.ZoneDefinition;
import net.runelite.cache.definitions.MapSquareDefinition;
import net.runelite.cache.definitions.loaders.WorldMapCompositeLoader;
import net.runelite.cache.fs.*;
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
import java.util.*;

public class MapExport {
    private static RegionLoader regionLoader;
    private static String version = "2024-05-29_a";
    public static void main(String[] args) throws Exception {
        version = args.length > 0 ? args[0] : version;
        Gson gson = new Gson();
        String cache = "./data/cache";
        Store store = new Store(new File(cache));
        store.load();

        XteaKeyManager xteaKeyManager = new XteaKeyManager();
        try (FileInputStream fin = new FileInputStream("./data/xteas.json"))
        {
            xteaKeyManager.loadKeys(fin);
        }

        MapImageDumper dumper = new MapImageDumper(store, xteaKeyManager);
        dumper.setRenderIcons(false);
        dumper.setLowMemory(false);
        dumper.setRenderLabels(false);
        dumper.load();

        // Draw the planes
//        for (int plane = 0; plane < 4; plane++) {
//            BufferedImage image = dumper.drawMap(plane);
//            String dirname = String.format("./out/mapgen/versions/%s/fullplanes/base", version);
//            String filename = String.format("plane_%s.png", plane);
//            File outputfile = fileWithDirectoryAssurance(dirname, filename);
//            System.out.println(outputfile);
//            ImageIO.write(image, "png", outputfile);
//        }

        // Dump icon data and images
        String dirname = String.format("./out/mapgen/versions/%s", version);
        String filename = "minimapIcons.json";
        File outputfile = fileWithDirectoryAssurance(dirname, filename);
        PrintWriter out = new PrintWriter(outputfile);
        List<MinimapIcon> icons = getMapIcons(store);
        String json = gson.toJson(icons);
        out.write(json);
        out.close();

        // Dump Jagex mapID data
        filename = "worldMapDefinitions.json";
        outputfile = fileWithDirectoryAssurance(dirname, filename);
        out = new PrintWriter(outputfile);
        List<WorldMapDefinition> wmds = getWorldMapDefinitions(store);
        json = gson.toJson(wmds);
        out.write(json);
        out.close();

        // Output the highest and lowest X and Y values drawn on the plane for coordinate transforms
        regionLoader.calculateBounds();
        dirname = String.format("./", version);
        filename = "coordinateData.json";
        outputfile = fileWithDirectoryAssurance(dirname, filename);
        out = new PrintWriter(outputfile);
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
        json = gson.toJson(coords);
        out.write(json);
        out.close();
    }

    private static File fileWithDirectoryAssurance(String directory, String filename) {
        File dir = new File(directory);
        if (!dir.exists()) dir.mkdirs();
        return new File(directory + "/" + filename);
    }

    private static List<WorldMapDefinition> getWorldMapDefinitions(Store store) throws Exception {
        Index index = store.getIndex(IndexType.WORLDMAP);
        Archive archive = index.getArchive(1);
        Storage storage = store.getStorage();
        byte[] archiveData = storage.loadArchive(archive);
        ArchiveFiles files = archive.getFiles(archiveData);

        WorldMapCompositeLoader loader = new WorldMapCompositeLoader();

        for (FSFile file : files.getFiles()) {
            WorldMapCompositeDefinition wmd = loader.load(file.getContents());
            int mapid = file.getFileId();

            List<MapSquareDefinition> mapSquareDefinitions = new ArrayList<>(wmd.getMapSquareDefinitions());
            List<ZoneDefinition> zoneDefinitions = new ArrayList<>(wmd.getZoneDefinitions());

            String msFilename = String.format("mapSquareDefinitions_%s.json", mapid);
            outputfile = fileWithDirectoryAssurance(dirname, msFilename);
            out = new PrintWriter(outputfile);
            json = gson.toJson(mapSquareDefinitions);
            out.write(json);
            out.close();

            String zFilename = String.format("zoneDefinitions_%s.json", mapid);
            outputfile = fileWithDirectoryAssurance(dirname, zFilename);
            out = new PrintWriter(outputfile);
            json = gson.toJson(zoneDefinitions);
            out.write(json);
            out.close();
        }
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