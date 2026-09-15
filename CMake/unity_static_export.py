#!/usr/bin/env python3
"""Emit Unity IL2CPP static-plugin folders: shared RNBO runtime + slim plugin."""

from __future__ import annotations

import argparse
import posixpath
import re
import shutil
import stat
import textwrap
import uuid
from pathlib import Path

INCLUDE_RE = re.compile(r'(#\s*include\s*")([^"]+)(")')
SOURCE_SUFFIXES = {".cpp", ".c", ".cc", ".cxx", ".mm"}
HEADER_SUFFIXES = {".h", ".hpp", ".hh", ".inl"}

RUNTIME_AMALG = "RNBO_runtime_unity.cpp"
FMOD_INC_MARKER = "FMOD_UnityInc.h"


def _guid() -> str:
    return uuid.uuid4().hex


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _strip_exec(root: Path) -> None:
    for f in root.rglob("*"):
        if f.is_file():
            mode = f.stat().st_mode
            f.chmod(mode & ~stat.S_IXUSR & ~stat.S_IXGRP & ~stat.S_IXOTH)


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


def _runtime_readme() -> str:
    return textwrap.dedent(
        f"""\
        # RNBO FMOD — Unity runtime

        Drop this folder **once** under `Assets/` (e.g. `Assets/Plugins/RNBO_FMOD/Runtime/`).
        Not under `Assets/Plugins/FMOD/platforms/.../lib`.

        Tick only `{RUNTIME_AMALG}`. Do not add this folder to FMOD Static Plugins.

        Also drop `FMOD_unity_inc/` under `Assets/` once (shared by all wrappers).
        Each audio plugin is a separate `*_unity_static` folder. All RNBO plugins must
        use the same RNBO export version as this runtime.
        """
    )


def _fmod_readme() -> str:
    return textwrap.dedent(
        """\
        # FMOD headers — Unity IL2CPP

        Drop this folder **once** under `Assets/` (e.g. `Assets/Plugins/FMOD_unity_inc/`).
        Not under `Assets/Plugins/FMOD/platforms/.../lib`.

        Shared by RNBO, HeavyPd, and Cmajor static plugins. Do not tick any
        compile unit here, and do not add this folder to FMOD Static Plugins.

        If `fmod_hpp.h` / `fmod.h` are missing, copy FMOD Engine `api/core/inc`
        into this folder (headers are flattened next to the marker).
        """
    )


def _plugin_readme(plugin_name: str, amalg_name: str) -> str:
    return textwrap.dedent(
        f"""\
        # {plugin_name} — Unity static FMOD plugin

        Also drop `FMOD_unity_inc/` and `RNBO_FMOD_runtime/` under `Assets/` (once
        each). This folder is plugin-only and needs those two for FMOD / RNBO headers.

        Example: `Assets/Plugins/RNBO_FMOD/Runtime/` and
        `Assets/Plugins/RNBO_FMOD/{plugin_name}/`. Not under
        `Assets/Plugins/FMOD/platforms/.../lib`.

        Tick `{RUNTIME_AMALG}` in the runtime folder and `{amalg_name}` here.
        In FMOD Settings, add `{plugin_name}_GetDSPDescription` to **Static Plugins**.
        Keep the dynamic plugin on **Dynamic Plugins** for the Editor.
        """
    )


def _editor_script() -> str:
    return textwrap.dedent(
        """\
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
                    var current = StripOurArgs(PlayerSettings.GetAdditionalIl2CppArgs() ?? "");
                    var dirs = FindIncludeDirs();
                    if (dirs.Count == 0)
                    {
                        PlayerSettings.SetAdditionalIl2CppArgs(current);
                        return;
                    }

                    var flags = new List<string>();
                    foreach (var dir in dirs)
                        flags.Add("-I" + Quote(dir));
                    flags.Add("-D" + MarkerDefine + "=1");

                    var extra = "--compiler-flags=\\"" + string.Join(" ", flags) + "\\"";
                    PlayerSettings.SetAdditionalIl2CppArgs((current + " " + extra).Trim());
                    Debug.Log("[RNBO-FMOD] IL2CPP include paths refreshed for RNBO runtime + plugins");
                }

                static string StripOurArgs(string current)
                {
                    return System.Text.RegularExpressions.Regex.Replace(
                        current ?? "",
                        "--compiler-flags=\\"[^\\"]*" + MarkerDefine + "[^\\"]*\\"",
                        "").Trim();
                }

                static List<string> FindIncludeDirs()
                {
                    var result = new List<string>();
                    var assets = Application.dataPath;
                    if (!Directory.Exists(assets))
                        return result;

                    foreach (var marker in Directory.GetFiles(assets, "FMOD_UnityInc.h", SearchOption.AllDirectories))
                    {
                        var root = Path.GetDirectoryName(marker);
                        if (!string.IsNullOrEmpty(root))
                            AddDir(result, root);
                    }

                    foreach (var marker in Directory.GetFiles(assets, "RNBO_UnityBuild.h", SearchOption.AllDirectories))
                    {
                        var root = Path.GetDirectoryName(marker);
                        if (!string.IsNullOrEmpty(root))
                            AddDir(result, root);
                    }

                    foreach (var marker in Directory.GetFiles(assets, "*_unity.cpp", SearchOption.AllDirectories))
                    {
                        if (Path.GetFileName(marker) == "RNBO_runtime_unity.cpp")
                            continue;
                        var root = Path.GetDirectoryName(marker);
                        if (!string.IsNullOrEmpty(root))
                            AddDir(result, root);
                    }
                    return result;
                }

                static void AddDir(List<string> list, string dir)
                {
                    if (Directory.Exists(dir) && !list.Contains(dir))
                        list.Add(dir);
                }

                static string Quote(string path)
                {
                    return path.Replace("\\\\", "/");
                }
            }
        }
        """
    )


def _dest_name(rel: str, used_h: set[str]) -> str:
    """Map a source-relative path to a flattened Unity filename."""
    rel_u = rel.replace("\\", "/")
    if rel_u.startswith("3rdparty/"):
        parts = Path(rel_u).parts[1:]
        if not parts:
            return Path(rel_u).name
        *dirs, filename = parts
        stem = Path(filename).stem
        suffix = Path(filename).suffix.lower()
        joined = "_".join([*dirs, stem]) if dirs else stem
        if suffix in SOURCE_SUFFIXES:
            return f"{joined}.inc.h"
        if suffix in {".h", ".hpp", ".hh", ".inl"}:
            return f"{joined}.h"
        return "_".join([*dirs, filename]) if dirs else filename

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


def _rewrite_include(inc: str, from_rel: str, dest_by_rel: dict[str, str], used_h: set[str]) -> str:
    inc_u = inc.replace("\\", "/")
    from_rel_u = from_rel.replace("\\", "/")
    from_dir = posixpath.dirname(from_rel_u)

    candidates = [inc_u]
    if from_dir and from_dir != ".":
        candidates.append(posixpath.normpath(f"{from_dir}/{inc_u}").replace("\\", "/"))
    else:
        candidates.append(posixpath.normpath(inc_u).replace("\\", "/"))
    if inc_u.startswith("src/"):
        candidates.append(inc_u[4:])
    elif not inc_u.startswith("3rdparty/"):
        candidates.append(posixpath.normpath(f"src/{inc_u}").replace("\\", "/"))

    for cand in candidates:
        if cand in dest_by_rel:
            return dest_by_rel[cand]
    return _dest_name(inc_u, used_h)


def _rewrite_file_text(text: str, from_rel: str, dest_by_rel: dict[str, str], used_h: set[str]) -> str:
    def repl(match: re.Match[str]) -> str:
        prefix, inc, suffix = match.group(1), match.group(2), match.group(3)
        return f"{prefix}{_rewrite_include(inc, from_rel, dest_by_rel, used_h)}{suffix}"

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


def _reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def _emit_files(
    root: Path,
    planned: list[tuple[Path, str, str]],
    dest_by_rel: dict[str, str],
    used_h: set[str],
) -> None:
    for src, rel, dest in planned:
        dst = root / dest
        dst.parent.mkdir(parents=True, exist_ok=True)
        raw = src.read_text(encoding="utf-8", errors="replace")
        _write(dst, _rewrite_file_text(raw, rel, dest_by_rel, used_h))


def export_bundle(args: argparse.Namespace) -> None:
    plugin_out = Path(args.out).resolve()
    runtime_out = Path(args.runtime_out).resolve()
    fmod_out = Path(args.fmod_out).resolve()
    _reset_dir(plugin_out)
    _reset_dir(runtime_out)
    _reset_dir(fmod_out)

    rnbo_src = Path(args.rnbo_src).resolve()
    rnbo_root = rnbo_src / "rnbo"
    if not (rnbo_root / "RNBO.cpp").is_file():
        raise SystemExit(f"RNBO.cpp not found under {rnbo_root}")

    patcher_files = list(rnbo_src.glob("*.cpp"))
    if not patcher_files:
        raise SystemExit(f"No patcher .cpp in {rnbo_src}")

    plugin_extras: list[tuple[Path, str]] = []
    for patcher in patcher_files:
        plugin_extras.append((patcher, patcher.name))
    plugin_extras.append((Path(args.generated), "RNBO_FMOD.cpp"))

    runtime_extras: list[tuple[Path, str]] = []
    runtime_extras.append((Path(args.wrapper_dir) / "RNBOWrapper.cpp", "RNBOWrapper.cpp"))
    runtime_extras.append((Path(args.wrapper_dir) / "RNBOWrapper.hpp", "RNBOWrapper.hpp"))
    decoder_dir = Path(args.decoder_dir)
    for name in ("dr_wav.h", "dr_mp3.h"):
        src = decoder_dir / name
        if src.is_file():
            runtime_extras.append((src, name))

    fmod_files: list[Path] = []
    fmod_inc_src = Path(args.fmod_inc)
    if fmod_inc_src.is_dir():
        fmod_files = [
            p for p in fmod_inc_src.iterdir()
            if p.is_file() and p.suffix.lower() in {".h", ".hpp"}
        ]

    used_h = {p.name for p in fmod_files if p.suffix.lower() == ".h"}
    used_h.update({"RNBO_UnityBuild.h", FMOD_INC_MARKER})

    runtime_jobs: list[tuple[Path, str]] = []
    for src in _collect_flat_files(rnbo_root):
        if src.parent == rnbo_root:
            rel = src.name
        elif (rnbo_root / "src") in src.parents:
            rel = src.relative_to(rnbo_root / "src").as_posix()
        else:
            rel = src.name
        runtime_jobs.append((src, rel))
    runtime_jobs.extend(runtime_extras)

    fmod_jobs: list[tuple[Path, str]] = [(src, src.name) for src in fmod_files]

    def plan(jobs: list[tuple[Path, str]]) -> list[tuple[Path, str, str]]:
        dest_used: set[str] = set()
        planned: list[tuple[Path, str, str]] = []
        for src, rel in jobs:
            dest = _dest_name(rel, used_h)
            if dest in dest_used:
                raise SystemExit(f"Flatten collision: {rel} -> {dest}")
            dest_used.add(dest)
            planned.append((src, rel, dest))
        return planned

    plugin = args.plugin_name
    runtime_planned = plan(runtime_jobs)
    plugin_planned = plan(plugin_extras)
    fmod_planned = plan(fmod_jobs)
    plugin_planned = [
        (src, rel, f"{plugin}_{dest}") for src, rel, dest in plugin_planned
    ]

    dest_by_rel: dict[str, str] = {}
    for _src, rel, dest in runtime_planned + plugin_planned + fmod_planned:
        dest_by_rel[rel.replace("\\", "/")] = dest

    _emit_files(runtime_out, runtime_planned, dest_by_rel, used_h)
    _emit_files(plugin_out, plugin_planned, dest_by_rel, used_h)
    _emit_files(fmod_out, fmod_planned, dest_by_rel, used_h)

    amalg_name = f"{plugin}_unity.cpp"
    patcher_inc = f"{plugin}_{Path(patcher_files[0].name).stem}.inc.h"
    fmod_inc = f"{plugin}_RNBO_FMOD.inc.h"

    _write(fmod_out / FMOD_INC_MARKER, "#pragma once\n")
    _write(fmod_out / "README.md", _fmod_readme())

    _write(runtime_out / "RNBO_UnityBuild.h", _unity_build_header(args.legacy_factory))
    _write(
        runtime_out / RUNTIME_AMALG,
        textwrap.dedent(
            f"""\
            #include "RNBO_UnityBuild.h"
            #include "RNBOWrapper.inc.h"
            #include "RNBO.inc.h"
            """
        ),
    )
    _write(runtime_out / f"{RUNTIME_AMALG}.meta", _plugin_meta(enabled=True))
    _write(runtime_out / "README.md", _runtime_readme())
    editor = runtime_out / "Editor"
    editor.mkdir()
    _write(editor / "RNBOFMODUnityIncludes.cs", _editor_script())

    _write(
        plugin_out / amalg_name,
        textwrap.dedent(
            f"""\
            #include "RNBO_UnityBuild.h"
            #include "{patcher_inc}"
            #include "{fmod_inc}"
            """
        ),
    )
    _write(plugin_out / f"{amalg_name}.meta", _plugin_meta(enabled=True))
    _write(plugin_out / "README.md", _plugin_readme(plugin, amalg_name))

    _strip_exec(runtime_out)
    _strip_exec(plugin_out)
    _strip_exec(fmod_out)

    print(f"Unity FMOD headers written to {fmod_out}")
    print(f"Unity RNBO runtime written to {runtime_out}")
    print(f"Tick only: {RUNTIME_AMALG}")
    print(f"Unity plugin source written to {plugin_out}")
    print(f"Tick only: {amalg_name}")
    print(f"Register in FMOD Static Plugins: {plugin}_GetDSPDescription")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--runtime-out", required=True)
    parser.add_argument("--fmod-out", required=True)
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
