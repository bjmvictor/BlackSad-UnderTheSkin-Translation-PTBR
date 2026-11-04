// Ponte de linha de comando para a mesma escrita de bundle usada pelo UABEA.
// Este arquivo e compilado localmente pelo empacotar_ptbr_uabea.ps1.
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Runtime.Loader;
using AssetsTools.NET;
using AssetsTools.NET.Extra;

public static class UabeaRawPatcher
{
    // args: <bundle-origem> <raw-textasset> <path-id> <bundle-saida>
    public static int Main(string[] args)
    {
        // O executavel compilado fica fora da pasta do UABEA; instrui o runtime
        // a encontrar as DLLs que ja acompanham o editor.
        string uabeaLibraries = Environment.GetEnvironmentVariable("UABEA_LIB_DIR");
        if (!string.IsNullOrWhiteSpace(uabeaLibraries) && Directory.Exists(uabeaLibraries))
        {
            AssemblyLoadContext.Default.Resolving += (context, name) =>
            {
                string candidate = Path.Combine(uabeaLibraries, name.Name + ".dll");
                return File.Exists(candidate) ? context.LoadFromAssemblyPath(candidate) : null;
            };
        }

        if (args.Length != 4)
        {
            Console.Error.WriteLine("Uso: <bundle-origem> <raw-textasset> <path-id> <bundle-saida>");
            return 2;
        }

        string inputBundle = Path.GetFullPath(args[0]);
        string rawAsset = Path.GetFullPath(args[1]);
        if (!long.TryParse(args[2], out long pathId))
        {
            Console.Error.WriteLine("Path ID invalido.");
            return 2;
        }
        string outputBundle = Path.GetFullPath(args[3]);
        if (!File.Exists(inputBundle) || !File.Exists(rawAsset))
        {
            Console.Error.WriteLine("O bundle de origem ou o Raw TextAsset nao foi encontrado.");
            return 2;
        }
        if (string.Equals(inputBundle, outputBundle, StringComparison.OrdinalIgnoreCase))
        {
            Console.Error.WriteLine("A saida deve ser diferente da origem.");
            return 2;
        }

        byte[] replacementRaw = File.ReadAllBytes(rawAsset);
        AssetBundleFile bundle;
        Stream bundleStream;
        try
        {
            bundleStream = File.OpenRead(inputBundle);
            bundle = new AssetBundleFile();
            bundle.Read(new AssetsFileReader(bundleStream));
            if (bundle.Header.GetCompressionType() != 0)
            {
                var unpacked = new MemoryStream();
                using (var writer = new AssetsFileWriter(unpacked))
                    bundle.Unpack(writer);
                bundleStream.Close();
                unpacked.Position = 0;
                bundle = new AssetBundleFile();
                bundle.Read(new AssetsFileReader(unpacked));
                bundleStream = unpacked;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Nao foi possivel abrir o bundle: " + ex.Message);
            return 1;
        }

        try
        {
            int targetIndex = -1;
            byte[] patchedAsset = null;
            for (int index = 0; index < bundle.BlockAndDirInfo.DirectoryInfos.Length; index++)
            {
                byte[] assetData = BundleHelper.LoadAssetDataFromBundle(bundle, index);
                try
                {
                    using (var input = new MemoryStream(assetData, false))
                    using (var reader = new AssetsFileReader(input))
                    {
                        var assetFile = new AssetsFile();
                        assetFile.Read(reader);
                        AssetFileInfo info = assetFile.GetAssetInfo(pathId);
                        if (info == null)
                            continue;
                        ushort monoId = assetFile.GetScriptIndex(info);
                        var replacer = new AssetsReplacerFromMemory(
                            pathId, info.TypeId, monoId, replacementRaw);
                        using (var output = new MemoryStream())
                        using (var writer = new AssetsFileWriter(output))
                        {
                            assetFile.Write(writer, 0, new List<AssetsReplacer> { replacer });
                            patchedAsset = output.ToArray();
                        }
                        targetIndex = index;
                        break;
                    }
                }
                catch
                {
                    // Nem toda entrada de um bundle e um arquivo serialized Unity.
                }
            }

            if (targetIndex < 0 || patchedAsset == null)
            {
                Console.Error.WriteLine("TextAsset com o Path ID informado nao foi encontrado no bundle.");
                return 1;
            }

            string entryName = bundle.BlockAndDirInfo.DirectoryInfos[targetIndex].Name;
            using (var patchedStream = new MemoryStream(patchedAsset, false))
            using (var output = File.Open(outputBundle, FileMode.CreateNew, FileAccess.Write))
            using (var writer = new AssetsFileWriter(output))
            {
                var replacers = new List<BundleReplacer>
                {
                    new BundleReplacerFromStream(entryName, entryName, true,
                        patchedStream, 0, patchedStream.Length)
                };
                bundle.Write(writer, replacers);
            }

            Console.WriteLine("Bundle gerado: " + outputBundle);
            Console.WriteLine("Entrada alterada: " + entryName + "; Path ID: " + pathId);
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("Falha ao gravar o bundle: " + ex);
            return 1;
        }
        finally
        {
            bundle.Close();
            bundleStream.Close();
        }
    }
}
