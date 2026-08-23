#!/usr/bin/env python3
"""Emit a Unity IL2CPP static-plugin source folder from an RNBO FMOD wrap."""

from __future__ import annotations

import argparse
import re
import shutil
import stat
import textwrap
import uuid
from pathlib import Path

INCLUDE_RE = re.compile(r'(#\s*include\s*")([^"]+)(")')
SOURCE_SUFFIXES = {".cpp", ".c", ".cc", ".cxx", ".mm"}
HEADER_SUFFIXES = {".h", ".hpp", ".hh", ".inl"}


def _guid() -> str:
    return uuid.uuid4().hex


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _plugin_meta(enabled: bool) -> str:
    any_enabled = "1" if enabled else "0"
    return textwrap.dedent(
        f"""\
        fileFormatVersion: 2
        guid: {_guid()}
        PluginImporter:
          serializedVersion: 2
          iconMap: {{}}
          executionOrder: {{}}
          defineConstraints: []
          isPreloaded: 0
          isOverridable: 0
          isExplicitlyReferenced: 0
          validateReferences: 1
          platformData:
          - first:
              : Any
            second:
              enabled: {any_enabled}
              settings: {{}}
          userData:
          assetBundleName:
          assetBundleVariant:
        """
    )


def _unity_build_header(legacy_factory: bool) -> str:
    legacy = "#define RNBO_LEGACY_PATCHER_FACTORY 1\n" if legacy_factory else ""
    return textwrap.dedent(
        f"""\
        #pragma once

        #ifndef RNBO_NO_PATCHERFACTORY
        #define RNBO_NO_PATCHERFACTORY
        #endif

        #ifndef RNBO_SIMPLEENGINE
        #define RNBO_SIMPLEENGINE
        #endif

        #ifndef RNBO_STATIC_BUILD
        #define RNBO_STATIC_BUILD 1
        #endif

        #ifndef RNBO_NO_CLANG
        #define RNBO_NO_CLANG
        #endif

        #ifndef RNBO_NO_JUCE
        #define RNBO_NO_JUCE
        #endif

        {legacy}"""
    )


def _readme(plugin_name: str, amalg_name: str) -> str:
    return textwrap.dedent(
        f"""\
        # {plugin_name} — Unity static FMOD plugin

        Drop this folder anywhere under `Assets/` (e.g. `Assets/Plugins/RNBO_FMOD/{plugin_name}/`).
        Not under `Assets/Plugins/FMOD/platforms/.../lib`.

        Only `{amalg_name}` should be ticked. In FMOD Settings, add
        `{plugin_name}_GetDSPDescription` to **Static Plugins**. Keep the dynamic
        plugin on **Dynamic Plugins** for the Editor.

        If `fmod_hpp.h` / `fmod.h` are missing, copy FMOD Engine `api/core/inc` into
        this folder (headers are flattened next to the compile unit).
        """
    )


def _editor_script(plugin_name: str) -> str:
    return textwrap.dedent(
        f"""\
        using System.Collections.Generic;
        using System.IO;
        using UnityEditor;
        using UnityEditor.Build;
        using UnityEditor.Build.Reporting;
        using UnityEngine;

        namespace RNBOFMOD.UnityBuild.{plugin_name}
        {{
            class RNBOFMODUnityIncludes : IPreprocessBuildWithReport
            {{
                public int callbackOrder => 0;

                const string MarkerDefine = "RNBO_FMOD_UNITY_{plugin_name}";

                public void OnPreprocessBuild(BuildReport report)
                {{
                    var dirs = FindIncludeDirs();
                    if (dirs.Count == 0)
                        return;

                    var flags = new List<string>();
                    foreach (var dir in dirs)
                        flags.Add("-I" + Quote(dir));
                    flags.Add("-D" + MarkerDefine + "=1");

                    var extra = "--compiler-flags=\\"" + string.Join(" ", flags) + "\\"";
                    var current = PlayerSettings.GetAdditionalIl2CppArgs() ?? "";
                    if (current.Contains(MarkerDefine))
                        return;

                    PlayerSettings.SetAdditionalIl2CppArgs((current + " " + extra).Trim());
                    Debug.Log("[RNBO-FMOD] IL2CPP include paths added for {plugin_name}");
                }}

                static List<string> FindIncludeDirs()
                {{
                    var result = new List<string>();
                    var assets = Application.dataPath;
                    if (!Directory.Exists(assets))
                        return result;

                    foreach (var marker in Directory.GetFiles(assets, "RNBO_UnityBuild.h", SearchOption.AllDirectories))
                    {{
                        var root = Path.GetDirectoryName(marker);
                        if (string.IsNullOrEmpty(root))
                            continue;
                        AddDir(result, root);
                        AddDir(result, Path.Combine(root, "3rdparty"));
                        AddDir(result, Path.Combine(root, "3rdparty", "json"));
                        AddDir(result, Path.Combine(root, "3rdparty", "cppcodec"));
                        AddDir(result, Path.Combine(root, "3rdparty", "concurrentqueue"));
                        AddDir(result, Path.Combine(root, "3rdparty", "readerwriterqueue"));
                        AddDir(result, Path.Combine(root, "3rdparty", "MPark_variant"));
                    }}
                    return result;
                }}

                static void AddDir(List<string> list, string dir)
                {{
                    if (Directory.Exists(dir) && !list.Contains(dir))
                        list.Add(dir);
                }}

                static string Quote(string path)
                {{
                    return path.Replace("\\\\", "/");
                }}
            }}
        }}
        """
    )


def _dest_name(rel: str, used_h: set[str]) -> str:
    """Map a source-relative path to a flattened Unity filename."""
    rel_u = rel.replace("\\", "/")
    if rel_u.startswith("3rdparty/"):
        if rel_u.endswith(".hpp"):
            return rel_u[:-4] + ".h"
        if Path(rel_u).suffix.lower() in SOURCE_SUFFIXES:
            return str(Path(rel_u).with_suffix(".inc.h"))
        return rel_u

    name = Path(rel_u).name
    suffix = Path(name).suffix.lower()
    stem = Path(name).stem
    if suffix in SOURCE_SUFFIXES:
        return f"{stem}.inc.h"
    if suffix == ".hpp":
        candidate = f"{stem}.h"
        if candidate in used_h or candidate == name:
            return f"{stem}_hpp.h"
        return candidate
    return name


def _rewrite_include(inc: str, used_h: set[str]) -> str:
    inc_u = inc.replace("\\", "/")
    if "3rdparty/" in inc_u:
        return inc_u[:-4] + ".h" if inc_u.endswith(".hpp") else inc_u
    if inc_u.startswith("../externals/"):
        return _dest_name(inc_u, used_h)
    # Keep relative 3rdparty paths (detail/..., ../data/..., internal/...).
    if inc_u.startswith(("../", "./")) or (
        "/" in inc_u and not inc_u.startswith(("src/", "common/", "externals/"))
    ):
        return inc_u[:-4] + ".h" if inc_u.endswith(".hpp") else inc_u
    return _dest_name(inc_u, used_h)


def _rewrite_file_text(text: str, used_h: set[str]) -> str:
    def repl(match: re.Match[str]) -> str:
        prefix, inc, suffix = match.group(1), match.group(2), match.group(3)
        return f"{prefix}{_rewrite_include(inc, used_h)}{suffix}"

    return INCLUDE_RE.sub(repl, text)


def _collect_flat_files(rnbo_root: Path) -> list[Path]:
    files: list[Path] = []
    files.append(rnbo_root / "RNBO.cpp")
    files.append(rnbo_root / "RNBO.h")
    for sub in ("common", "externals"):
        folder = rnbo_root / sub
        if folder.is_dir():
            files.extend(p for p in folder.iterdir() if p.is_file())
    src = rnbo_root / "src"
    if src.is_dir():
        for p in src.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(src).as_posix()
            if rel.startswith("3rdparty/") or p.parent == src:
                files.append(p)
            elif rel.startswith("platforms/stdlib/") and p.suffix.lower() in HEADER_SUFFIXES:
                files.append(p)
    return [p for p in files if p.is_file()]


def export_bundle(args: argparse.Namespace) -> None:
    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    rnbo_src = Path(args.rnbo_src).resolve()
    rnbo_root = rnbo_src / "rnbo"
    if not (rnbo_root / "RNBO.cpp").is_file():
        raise SystemExit(f"RNBO.cpp not found under {rnbo_root}")

    patcher_files = list(rnbo_src.glob("*.cpp"))
    if not patcher_files:
        raise SystemExit(f"No patcher .cpp in {rnbo_src}")

    extras: list[tuple[Path, str]] = []
    for patcher in patcher_files:
        extras.append((patcher, patcher.name))
    extras.append((Path(args.wrapper_dir) / "RNBOWrapper.cpp", "RNBOWrapper.cpp"))
    extras.append((Path(args.wrapper_dir) / "RNBOWrapper.hpp", "RNBOWrapper.hpp"))
    extras.append((Path(args.generated), "RNBO_FMOD.cpp"))
    decoder_dir = Path(args.decoder_dir)
    for name in ("dr_wav.h", "dr_mp3.h"):
        src = decoder_dir / name
        if src.is_file():
            extras.append((src, name))

    fmod_files: list[Path] = []
    fmod_inc_src = Path(args.fmod_inc)
    if fmod_inc_src.is_dir():
        fmod_files = [
            p for p in fmod_inc_src.iterdir()
            if p.is_file() and p.suffix.lower() in {".h", ".hpp"}
        ]

    used_h = {p.name for p in fmod_files if p.suffix.lower() == ".h"}
    used_h.update({"RNBO_UnityBuild.h"})

    jobs: list[tuple[Path, str]] = []
    for src in _collect_flat_files(rnbo_root):
        if src.parent == rnbo_root:
            rel = src.name
        elif (rnbo_root / "src") in src.parents:
            rel = src.relative_to(rnbo_root / "src").as_posix()
        else:
            rel = src.name
        jobs.append((src, rel))
    for src, rel in extras:
        jobs.append((src, rel))
    for src in fmod_files:
        jobs.append((src, src.name))

    dest_used: set[str] = set()
    planned: list[tuple[Path, str, str]] = []
    for src, rel in jobs:
        dest = _dest_name(rel, used_h)
        if dest in dest_used and not rel.startswith("3rdparty/"):
            raise SystemExit(f"Flatten collision: {rel} -> {dest}")
        dest_used.add(dest)
        planned.append((src, rel, dest))

    for src, rel, dest in planned:
        dst = out / dest
        dst.parent.mkdir(parents=True, exist_ok=True)
        raw = src.read_text(encoding="utf-8", errors="replace")
        _write(dst, _rewrite_file_text(raw, used_h))

    plugin = args.plugin_name
    amalg_name = f"{plugin}_unity.cpp"
    patcher_inc = Path(patcher_files[0].name).stem + ".inc.h"
    _write(out / "RNBO_UnityBuild.h", _unity_build_header(args.legacy_factory))
    _write(
        out / amalg_name,
        textwrap.dedent(
            f"""\
            #include "RNBO_UnityBuild.h"
            #include "RNBOWrapper.inc.h"
            #include "RNBO.inc.h"
            #include "{patcher_inc}"
            #include "RNBO_FMOD.inc.h"
            """
        ),
    )
    _write(out / f"{amalg_name}.meta", _plugin_meta(enabled=True))
    _write(out / "README.md", _readme(plugin, amalg_name))

    editor = out / "Editor"
    editor.mkdir()
    _write(editor / "RNBOFMODUnityIncludes.cs", _editor_script(plugin))

    for f in out.rglob("*"):
        if f.is_file():
            mode = f.stat().st_mode
            f.chmod(mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)

    print(f"Unity static source bundle written to {out}")
    print(f"Tick only: {amalg_name}")
    print(f"Register in FMOD Static Plugins: {plugin}_GetDSPDescription")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--plugin-name", required=True)
    parser.add_argument("--generated", required=True)
    parser.add_argument("--rnbo-src", required=True)
    parser.add_argument("--wrapper-dir", required=True)
    parser.add_argument("--decoder-dir", required=True)
    parser.add_argument("--fmod-inc", required=True)
    parser.add_argument("--legacy-factory", action="store_true")
    export_bundle(parser.parse_args())


if __name__ == "__main__":
    main()
