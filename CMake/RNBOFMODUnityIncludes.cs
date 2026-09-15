using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace RNBOFMOD.UnityBuild
{
    class RNBOFMODUnityIncludes : IPreprocessBuildWithReport
    {
        public int callbackOrder => 0;
        const string MarkerDefine = "RNBO_FMOD_UNITY_RUNTIME";

        public void OnPreprocessBuild(BuildReport report)
        {
            var current = System.Text.RegularExpressions.Regex.Replace(
                PlayerSettings.GetAdditionalIl2CppArgs() ?? "",
                "--compiler-flags=\"[^\"]*" + MarkerDefine + "[^\"]*\"", "").Trim();
            var dirs = new SortedSet<string>();
            foreach (var pattern in new[] { "FMOD_UnityInc.h", "RNBO_UnityBuild.h", "*_unity.cpp" })
                foreach (var marker in Directory.GetFiles(Application.dataPath, pattern, SearchOption.AllDirectories))
                    dirs.Add(Path.GetDirectoryName(marker).Replace('\\', '/'));
            if (dirs.Count == 0)
            {
                PlayerSettings.SetAdditionalIl2CppArgs(current);
                return;
            }

            // Avoid nested path quotes in IL2CPP's command line on Windows.
            // This relative path itself contains no spaces; paths inside are quoted.
            const string response = "Library/RNBOFMOD/includes.rsp";
            Directory.CreateDirectory(Path.GetDirectoryName(response));
            var flags = new List<string>();
            foreach (var dir in dirs)
                flags.Add("-I\"" + dir + "\"");
            File.WriteAllLines(response, flags, new System.Text.UTF8Encoding(false));
            var extra = "--compiler-flags=\"@" + response + " -D" + MarkerDefine + "=1\"";
            PlayerSettings.SetAdditionalIl2CppArgs((current + " " + extra).Trim());
            Debug.Log("[RNBO-FMOD] Refreshed source include paths in " + response);
        }
    }
}
