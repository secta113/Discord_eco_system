import argparse
import os
import subprocess
import sys

# Windows での絵文字表示とリダイレクト時のエンコーディング対策
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        # Python < 3.7 の場合は古い方法を試みる
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

try:
    from colorama import Fore, Style, init

    # Windows ターミナルでの色表示を有効化
    init(autoreset=True)
    COLORAMA_INSTALLED = True
except ImportError:
    # colorama がない場合は色なしでフォールバック
    COLORAMA_INSTALLED = False

    class EmptyString:
        def __getattr__(self, name):
            return ""

    Fore = Style = EmptyString()


def run_command(command, description):
    print(f"\n{Fore.CYAN}{Style.BRIGHT}--- {description} ---")
    print(f"{Fore.BLACK}{Style.DIM}Command: {' '.join(command)}")
    try:
        # ストリームをリアルタイムで表示
        result = subprocess.run(command, check=True, text=True)
        print(f"{Fore.GREEN}✅ {description} passed.")
        return True
    except subprocess.CalledProcessError:
        print(f"{Fore.RED}❌ {description} failed.")
        return False
    except FileNotFoundError:
        print(f"{Fore.YELLOW}⚠️  {command[0]} not found. Skipping...")
        return None


def main():
    parser = argparse.ArgumentParser(description="Enhanced CI checks and quality control.")
    parser.add_argument(
        "--fix", action="store_true", help="Automatically fix formatting and linting issues."
    )
    args = parser.parse_args()

    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)

    # 実行前に古い一時DBを掃除
    import glob

    for f in glob.glob(os.path.join(root_dir, "data", "test_db_*.db")):
        try:
            os.remove(f)
        except Exception:
            pass

    # venv のパス解決
    venv_python = os.path.join(root_dir, "venv", "Scripts", "python.exe")
    venv_ruff = os.path.join(root_dir, "venv", "Scripts", "ruff.exe")
    venv_pytest = os.path.join(root_dir, "venv", "Scripts", "pytest.exe")

    if not os.path.exists(venv_python):
        print(f"{Fore.RED}❌ Error: Virtual environment not found at {venv_python}")
        print(
            f"{Fore.YELLOW}💡 Hint: Please run this script using the virtual environment's python:"
        )
        print(f"   .\\venv\\Scripts\\python.exe {os.path.basename(__file__)}")
        sys.exit(1)

    if not COLORAMA_INSTALLED:
        print(f"{Fore.YELLOW}⚠️  Warning: colorama is not installed in the current environment.")
        print(
            f"{Fore.YELLOW}💡 Recommended to run with venv: .\\venv\\Scripts\\python.exe {os.path.basename(__file__)}"
        )
        print("-" * 40)

    results = []

    # 1. Auto-fix (Optional or forced by --fix)
    if args.fix:
        print(f"{Fore.MAGENTA}{Style.BRIGHT}🔧 Running Auto-fixes...")
        run_command([venv_ruff, "format", "."], "Auto-format (Ruff)")
        run_command([venv_ruff, "check", "--fix", "."], "Auto-fix Lint (Ruff)")

    # 2. Check phase
    print(f"\n{Fore.WHITE}{Style.BRIGHT}🔍 Verification Phase...")

    # Lint Check
    lint_ok = run_command([venv_ruff, "check", "."], "Lint Check (Ruff)")
    results.append(("Lint", lint_ok))

    # Format Check
    format_ok = run_command([venv_ruff, "format", "--check", "."], "Format Check (Ruff)")
    results.append(("Format", format_ok))

    # Unit Tests
    pytest_cmd = [venv_pytest, "tests", "--dist=loadscope"]

    # pytest-xdist がインストールされているか確認して並列数を決定
    try:
        # プラグインの有無を確認 (pytest --trace-config はテスト実行を誘発するため避ける)
        check_proc = subprocess.run(
            [
                venv_python,
                "-c",
                "import importlib.util; print('xdist' if importlib.util.find_spec('xdist') else '')",
            ],
            capture_output=True,
            text=True,
        )
        if "xdist" in check_proc.stdout.strip():
            # 24コア等の多コア環境でのオーバーヘッドを考慮し、最大でも12プロセス程度に調整
            # (テスト数が少ない場合はコアを使い切るより、適度な数の方が速いため)
            cpu_count = os.cpu_count() or 1
            n_workers = min(cpu_count, 12)
            pytest_cmd.extend(["-n", str(n_workers)])
            print(f"{Fore.CYAN}🚀 Parallel mode enabled: using {n_workers} workers.")
    except Exception:
        pass

    test_ok = run_command(pytest_cmd, "Unit Tests (Pytest)")
    results.append(("Tests", test_ok))

    # Summary
    print(f"\n{Fore.WHITE}{Style.BRIGHT}{'=' * 40}")
    print(f"{Fore.WHITE}{Style.BRIGHT}       QUALITY CONTROL SUMMARY")
    print(f"{Fore.WHITE}{Style.BRIGHT}{'=' * 40}")

    all_passed = True
    for name, ok in results:
        if ok is True:
            status = f"{Fore.GREEN}PASSED"
        elif ok is False:
            status = f"{Fore.RED}FAILED"
            all_passed = False
        else:
            status = f"{Fore.YELLOW}SKIPPED"

        print(f" {name:<10}: {status}")

    print(f"{Fore.WHITE}{Style.BRIGHT}{'=' * 40}")

    if all_passed:
        print(f"\n{Fore.GREEN}{Style.BRIGHT}✨ Excellence achieved. Environment is clean.")
        sys.exit(0)
    else:
        print(f"\n{Fore.RED}{Style.BRIGHT}❌ some checks failed. Please review the output above.")
        print(f"{Fore.YELLOW}💡 Try running 'python run_ci.py --fix' to solve lint/format issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()
