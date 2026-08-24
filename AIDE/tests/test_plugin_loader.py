import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.plugin_base import AIDEPlugin, PluginFileInfo
from core.plugin_loader import discover_plugins


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def test_discover_plugins_finds_valid_plugin(tmp_path):
    plugin_dir = tmp_path / "plugins" / "hello_plugin"
    _write(
        str(plugin_dir / "main_plugin.py"),
        "from core.plugin_base import AIDEPlugin\n"
        "class HelloPlugin(AIDEPlugin):\n"
        "    @property\n"
        "    def plugin_name(self):\n"
        "        return 'Hello Plugin'\n",
    )

    plugins = discover_plugins(str(tmp_path / "plugins"))
    assert "Hello Plugin" in plugins
    assert isinstance(plugins["Hello Plugin"], AIDEPlugin)


def test_discover_plugins_ignores_folder_without_main_plugin(tmp_path):
    empty_dir = tmp_path / "plugins" / "not_a_plugin"
    empty_dir.mkdir(parents=True)
    (empty_dir / "readme.txt").write_text("hej")

    plugins = discover_plugins(str(tmp_path / "plugins"))
    assert plugins == {}


def test_discover_plugins_survives_broken_plugin(tmp_path):
    broken_dir = tmp_path / "plugins" / "broken_plugin"
    _write(str(broken_dir / "main_plugin.py"), "raise RuntimeError('kaputt')\n")

    good_dir = tmp_path / "plugins" / "good_plugin"
    _write(
        str(good_dir / "main_plugin.py"),
        "from core.plugin_base import AIDEPlugin\n"
        "class GoodPlugin(AIDEPlugin):\n"
        "    @property\n"
        "    def plugin_name(self):\n"
        "        return 'Good Plugin'\n",
    )

    log_messages = []
    plugins = discover_plugins(str(tmp_path / "plugins"), log_callback=log_messages.append)

    assert "Good Plugin" in plugins
    assert any("kaputt" in msg or "broken_plugin" in msg for msg in log_messages)


def test_discover_plugins_missing_directory_returns_empty():
    plugins = discover_plugins("/path/does/not/exist")
    assert plugins == {}


def test_plugin_base_default_hooks_are_safe_noops():
    class MinimalPlugin(AIDEPlugin):
        @property
        def plugin_name(self):
            return "Minimal"

    p = MinimalPlugin()
    info = PluginFileInfo(
        relative_path="a.xyz", absolute_path="/tmp/a.xyz", filename="a.xyz",
        extension=".xyz", category="Okänd", size_bytes=10,
        is_sensitive=False, is_binary=False,
    )

    assert p.on_classify(info) is None
    assert p.on_scan_complete([info]) is None
    assert p.on_before_export([info]) is None
    assert p.get_exporters() == {}
    p.initialize()
    p.shutdown()


def test_example_plugin_reclassifies_aide_files(tmp_path):
    import sys as _sys
    plugins_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins"))
    plugins = discover_plugins(plugins_root)
    assert "AIDE Example Plugin" in plugins

    plugin = plugins["AIDE Example Plugin"]
    info = PluginFileInfo(
        relative_path="project.aide", absolute_path="/tmp/project.aide",
        filename="project.aide", extension=".aide", category="Okänd",
        size_bytes=20, is_sensitive=False, is_binary=False,
    )
    result = plugin.on_classify(info)
    assert result is not None
    assert result["category"] == "AIDE Meta"


def test_example_plugin_filters_large_files():
    plugins_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins"))
    plugins = discover_plugins(plugins_root)
    plugin = plugins["AIDE Example Plugin"]

    small = PluginFileInfo("a.txt", "/tmp/a.txt", "a.txt", ".txt", "Text", 100, False, False)
    huge = PluginFileInfo("b.bin", "/tmp/b.bin", "b.bin", ".bin", "Binär", 6 * 1024 * 1024, False, True)

    filtered = plugin.on_before_export([small, huge])
    assert filtered == [small]
