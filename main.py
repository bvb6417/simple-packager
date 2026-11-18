"""Double-click for GUI; pass a subcommand for headless CLI."""
import sys

def main():
    if len(sys.argv) == 1 or sys.argv[1:] == ['gui']:
        from packager_gui import launch_gui
        launch_gui()
        return 0
    from packager_cli import main as cli_main
    return cli_main(sys.argv[1:])

if __name__ == '__main__':
    raise SystemExit(main())
