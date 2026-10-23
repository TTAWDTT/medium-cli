"""dispatch 层断言：--print-command 只打印拼装好的上游命令，不执行。"""

from typer.testing import CliRunner

from medium_cli.cli import app

runner = CliRunner()


def test_hot_print_command_zhihu():
    r = runner.invoke(app, ["hot", "-p", "zhihu", "--print-command"])
    assert r.exit_code == 0
    assert "zhihu hot -l 20 --json" in r.output


def test_search_print_command_xhs():
    r = runner.invoke(app, ["search", "咖啡", "-p", "xhs", "--print-command"])
    assert r.exit_code == 0
    assert "xhs search 咖啡 --json" in r.output


def test_search_with_type():
    r = runner.invoke(app, ["search", "rust", "-p", "bili", "--type", "video", "--max", "5", "--print-command"])
    assert r.exit_code == 0
    assert "bili search rust --type video -n 5 --json" in r.output


def test_unsupported_verb_multi():
    """--print-command 时缺该动词的平台（如 telegram 无 hot）报"不支持"，有动词的平台照常打印。"""
    r = runner.invoke(app, ["hot", "-p", "telegram", "-p", "zhihu", "--print-command"])
    assert r.exit_code == 0
    assert "zhihu hot -l 20 --json" in r.output
    assert "不支持" in r.output


def test_platforms_lists_all():
    r = runner.invoke(app, ["platforms"])
    assert r.exit_code == 0
    for name in ("知乎", "小红书", "B站", "微博", "豆瓣", "V2EX", "Twitter/X", "Reddit", "Telegram", "Discord", "公众号", "BOSS直聘"):
        assert name in r.output


def test_unknown_platform_exits_2():
    r = runner.invoke(app, ["status", "-p", "nope"])
    assert r.exit_code == 2
    assert "未知平台" in r.output


def test_version():
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0
    assert "medium-cli" in r.output